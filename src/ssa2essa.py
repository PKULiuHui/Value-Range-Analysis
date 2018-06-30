# coding:utf-8

import argparse
import os
import re

parser = argparse.ArgumentParser(description='Convert SSA to eSSA')
parser.add_argument('-data_dir', type=str, default='../benchmark/')
parser.add_argument('-phase', type=str, default='t1')
args = parser.parse_args()


class Block:  # 基本块

    def __init__(self, blk):
        self.id = 0  # 块号，<bb k>的块号为k，<Lk>的块号为-k
        self.statements = []
        self.next = []  # 后继块号，共3种情况：无goto语句(下一块号)，1个goto语句(goto 块号)，2个goto语句(True块号和False块号)
        self.cond = []  # 如果存在条件分支，记录判断条件
        stats = blk.split('\n')
        self.id = int(re.search(r'\d+', stats[0]).group(0))
        if '<L' in stats[0]:
            self.id = -self.id
        for i in range(1, len(stats)):
            self.statements.append(stats[i].strip())
            match = re.search(r'if \((.*)\)', stats[i])
            if match is not None:
                self.cond = match.group(1).split()  # var1 rel var2
            if 'goto' in stats[i]:
                if '<bb' in stats[i]:
                    self.next.append(int(re.search(r'\d+', stats[i]).group(0)))
                elif '<L' in stats[i]:
                    self.next.append(-int(re.search(r'\d+', stats[i]).group(0)))

    def __str__(self):
        rst = ''
        rst += 'Block id:%d\n' % self.id
        rst += 'Successors id:' + ', '.join(str(num) for num in self.next) + '\n'
        rst += 'Condition:' + str(self.cond) + '\n'
        rst += 'Statements:\n'
        for stat in self.statements:
            rst += stat + '\n'
        return rst


class Function:  # 函数

    def __init__(self, name, paras, body):
        self.name = name
        self.paras = []  # 参数
        self.vars = {}  # 变量及对应类型
        self.blks = []  # 该函数的所有基本块
        for para in paras.strip().split(','):
            para = para.strip().split()
            if len(para) == 2:
                self.paras.append(para[1])
        for blk in body.split('\n\n'):
            if '>:' in blk:  # 基本块，包括<bb k>和<Lk>
                self.blks.append(Block(blk.strip()))
            else:  # 变量定义部分
                for stat in blk.split(';'):
                    stat = stat.strip().split()
                    if len(stat) == 2:
                        self.vars[stat[1]] = stat[0]
        for i in range(0, len(self.blks)):  # 设置无goto语句的基本块的后继
            if len(self.blks[i].next) == 0:
                if i < len(self.blks) - 1:
                    self.blks[i].next.append(self.blks[i + 1].id)
        self.to_essa()  # 将ssa表示转成essa

    def __str__(self):
        rst = 'Func name: %s\n' % self.name
        rst += 'Para list: %s\n' % str(self.paras)
        rst += 'Vars: %s\n' % str(self.vars)
        rst += 'Blocks:\n\n'
        for blk in self.blks:
            rst += str(blk) + '\n'
        return rst

    # 根据块号找到对应块
    def find_blk(self, blk_id):
        for blk in self.blks:
            if blk.id == blk_id:
                return blk
        return None

    # 替换一个块为新的块
    def replace_blk(self, blk):
        for i in range(0, len(self.blks)):
            if self.blks[i].id == blk.id:
                self.blks[i] = blk
                return

    # 检查变量在当前路径上是否有被Use，如果没有就不需要添加var_t/var_f变量
    def check_used_var(self, checked, cur_id, var):
        cur_blk = self.find_blk(cur_id)
        # 检查当前块的语句中是否使用了该变量
        for stat in cur_blk.statements:
            # 如果不是赋值语句，只要出现就算Use，否则需要出现在' = '之后才算Use
            if stat.rfind(var) > stat.find(' = ') and 'ft' not in stat:
                return True
            # 如果出现在' = '之前，变量被重新定义，当前路径没有Use
            if stat.find(var) < stat.find(' = ') and stat.find(var) != -1:
                return False

        checked.append(cur_id)
        # 检查当前块的后继
        for blk_id in cur_blk.next:
            if blk_id not in checked and blk_id != self.blks[-1].id:
                tmp_rst = self.check_used_var(checked, blk_id, var)
                if tmp_rst:
                    return True
        return False

    # 将当前路径上所有旧变量的Use替换成新变量的Use，并在路径第一个块中初始化新变量
    def insert_var(self, checked, cur_id, var_old, var_new, var_init):
        blk = self.find_blk(cur_id)
        cont = True  # continue flag
        if var_old + '_t' == var_new:
            another = var_old + '_f'
        else:
            another = var_old + '_t'
        for i in range(0, len(blk.statements)):
            if blk.statements[i].find(var_old) > blk.statements[i].find(' = ') and 'ft' not in blk.statements[i]:
                if another in blk.statements[i]:  # 当前变量既可以来自var_t，也可以来自var_f，所以变回var
                    blk.statements[i] = blk.statements[i].replace(another, var_old)
                    if 'if' in blk.statements[i]:
                        for j in range(0, len(blk.cond)):
                            if blk.cond[j] == another:
                                blk.cond[j] = var_old
                else:  # 将var变成var_t或var_f（绝大多数情况）
                    blk.statements[i] = blk.statements[i].replace(var_old, var_new)
                    if 'if' in blk.statements[i]:
                        for j in range(0, len(blk.cond)):
                            if blk.cond[j] == var_old:
                                blk.cond[j] = var_new

            if blk.statements[i].find(var_old) < blk.statements[i].find(' = ') and blk.statements[i].find(
                    var_old) != -1:
                # 注意此时var出现在赋值语句左边
                # blk.statements[i].replace(var_new, var_old, 1)
                cont = False
                break
        if var_init is not None:
            blk.statements.insert(0, var_new + ' = ' + var_init)
        self.replace_blk(blk)
        checked.append(cur_id)
        if not cont:
            return
        for blk_id in blk.next:
            if blk_id not in checked and blk_id != self.blks[-1].id:
                self.insert_var(checked, blk_id, var_old, var_new, None)  # 后续的块不需要初始化

    # 处理 var1 rel var2 型比较语句
    @staticmethod
    def eval_cond_var(x, y, rel):
        x_true = x_false = x + ' ∩ '
        y_true = y_false = y + ' ∩ '
        if rel == '>':
            x_true += '[ft(%s)+1, +inf]' % y
            x_false += '[-inf, ft(%s)]' % y
            y_true += '[-inf, ft(%s)-1]' % x
            y_false += '[ft(%s), +inf]' % x
        elif rel == '<':
            x_true += '[-inf, ft(%s)-1]' % y
            x_false += '[ft(%s), +inf]' % y
            y_true += '[ft(%s)+1, +inf]' % x
            y_false += '[-inf, ft(%s)]' % x
        elif rel == '<=':
            x_true += '[-inf, ft(%s)]' % y
            x_false += '[ft(%s)+1, +inf]' % y
            y_true += '[ft(%s), +inf]' % x
            y_false += '[-inf, ft(%s)-1]' % x
        elif rel == '>=':
            x_true += '[ft(%s), +inf]' % y
            x_false += '[-inf, ft(%s)-1]' % y
            y_true += '[-inf, ft(%s)]' % x
            y_false += '[ft(%s)+1, +inf]' % x
        elif rel == '==':
            x_true = '[ft(%s), ft(%s)]' % (y, y)
            x_false = '[-inf, +inf]'
            y_true = '[ft(%s), ft(%s)]' % (x, x)
            y_false = '[-inf, +inf]'
        elif rel == '!=':
            x_true = '[-inf, +inf]'
            x_false = '[ft(%s), ft(%s)]' % (y, y)
            y_true = '[-inf, +inf]'
            y_false = '[ft(%s), ft(%s)]' % (x, x)
        else:
            print('Unknown rel op %s!' % rel)
            assert False
        return x_true, x_false, y_true, y_false

    # 处理 var rel const 型比较语句
    @staticmethod
    def eval_cond_const(x, c, rel):
        x_true = x_false = x + ' ∩ '
        if rel == '>':
            x_true += '[%s, +inf]' % str(c + 1)
            x_false += '[-inf, %s]' % str(c)
        elif rel == '<':
            x_true += '[-inf, %s]' % str(c - 1)
            x_false += '[%s, +inf]' % str(c)
        elif rel == '<=':
            x_true += '[-inf, %s]' % str(c)
            x_false += '[%s, +inf]' % str(c + 1)
        elif rel == '>=':
            x_true += '[%s, +inf]' % str(c)
            x_false += '[-inf, %s]' % str(c - 1)
        elif rel == '==':
            x_true = '[%s, %s]' % (str(c), str(c))
            x_false = '[-inf, +inf]'
        elif rel == '!=':
            x_true = '[-inf, +inf]'
            x_false = '[%s, %s]' % (str(c), str(c))
        else:
            print('Unknown rel op %s!' % rel)
            assert False
        return x_true, x_false

        # 根据SSA的控制流图，处理条件判断语句，改造成eSSA控制流图

    def to_essa(self):
        # 依次处理存在条件判断的块
        queue = [self.blks[0]]
        reached = []
        while len(queue) != 0:
            blk = queue[0]
            queue = queue[1:]
            reached.append(blk.id)
            for next_blk_id in blk.next:
                if next_blk_id not in reached:
                    queue.append(self.find_blk(next_blk_id))
            if len(blk.cond) != 3:
                continue
            related_vars = []  # 条件判断有两种类型: var rel var | var rel const
            related_const = []  # 记录条件中的变量和常量
            for i in [0, 2]:
                match = re.search(r'[a-zA-Z_]+', blk.cond[i])  # 只有带字母或下划线的才是变量，否则是常量
                if match:
                    related_vars.append(blk.cond[i])
                else:
                    related_const.append(eval(blk.cond[i]))
            assert len(related_vars) + len(related_const) == 2 and len(related_const) <= 1

            if len(related_const) == 0:  # var rel var的情况
                var1_true, var1_false, var2_true, var2_false = Function.eval_cond_var(related_vars[0], related_vars[1],
                                                                                      blk.cond[1])
                if self.check_used_var([], blk.next[0], related_vars[0]):
                    self.insert_var([], blk.next[0], related_vars[0], related_vars[0] + '_t', var1_true)
                if self.check_used_var([], blk.next[0], related_vars[1]):
                    self.insert_var([], blk.next[0], related_vars[1], related_vars[1] + '_t', var2_true)
                if self.check_used_var([], blk.next[1], related_vars[0]):
                    self.insert_var([], blk.next[1], related_vars[0], related_vars[0] + '_f', var1_false)
                if self.check_used_var([], blk.next[1], related_vars[1]):
                    self.insert_var([], blk.next[1], related_vars[1], related_vars[1] + '_f', var2_false)

            else:  # var rel const的情况
                var_true, var_false = Function.eval_cond_const(related_vars[0], related_const[0], blk.cond[1])
                if self.check_used_var([], blk.next[0], related_vars[0]):
                    self.insert_var([], blk.next[0], related_vars[0], related_vars[0] + '_t', var_true)
                if self.check_used_var([], blk.next[1], related_vars[0]):
                    self.insert_var([], blk.next[1], related_vars[0], related_vars[0] + '_f', var_false)


# 将字符串转换成数值
def my_eval(num):
    if num == '-inf':
        return -1e20
    elif num == '+inf':
        return 1e20
    else:
        return eval(num)


class eSSA:

    def __init__(self, data_dir, phase):
        self.input = []
        self.output = []
        self.funcs = []

        # 解析.c文件中，读取输入输出范围
        with open(os.path.join(data_dir, phase + '.c'), 'r') as f:
            state = 0
            for line in f.readlines():
                if 'input' in line:
                    state = 1
                if 'output' in line:
                    state = 2
                if state == 1:
                    m = re.search(r'(\w*) in \[([-\d.]*|-inf), ([-\d.]*|\+inf)\]', line)
                    if m is not None:
                        self.input.append([m.group(1), my_eval(m.group(2)), my_eval(m.group(3))])
                if state == 2:
                    m = re.search(r'(\w*) in \[([-\d.]*|-inf), ([-\d.]*|\+inf)\]', line)
                    if m is not None:
                        self.output.append([m.group(1), my_eval(m.group(2)), my_eval(m.group(3))])

        # 解析.ssa文件，为每一个函数生成控制流图(即Block列表)，并将其改造成eSSA的控制流图
        with open(os.path.join(data_dir, phase + '.ssa'), 'r') as f:
            ssa = f.read()
            # group1: func_name, group2: para_list, group3: body
            p = re.compile(r'(\w*)\s*\((.*)\)\s*{([^}]*)}', flags=re.M)
            funcs = re.finditer(p, ssa)
            for func in funcs:
                self.funcs.append(Function(func.group(1), func.group(2), func.group(3)))

    def __str__(self):
        rst = 'input: %s\n' % str(self.input)
        rst += 'output: %s\n\n' % str(self.output)
        for func in self.funcs:
            rst += str(func) + '\n'
        return rst


if __name__ == '__main__':
    essa = eSSA(args.data_dir, args.phase)
    print(essa)
