# coding: utf-8

import argparse
import re
from ssa2essa import eSSA
import copy

parser = argparse.ArgumentParser(description='Build Constraint Graph')
parser.add_argument('-data_dir', type=str, default='../benchmark/')
parser.add_argument('-phase', type=str, default='t4')
args = parser.parse_args()


# constraint语句规范化，删除'#'和块号信息
def normalize(stat):
    rst = stat.replace('#', '').strip()
    rst = rst.replace(';', '').strip()
    rst = re.sub(r'\((\d*)\)', '', rst)
    return rst


# 提取该函数内的constraints，保留函数调用
def extract_constraints(func, input):
    constraints = []
    for blk in func.blks:
        for stat in blk.statements:
            if func.name == 'foo':  # 如果是foo函数，函数参数被input所确定，加入额外的constraints来初始化参数
                if '(D)' in stat:  # 语句里有(D)，表明是函数参数
                    var = re.search(r'(\w*)\(D\)', stat)
                    for i in input:
                        if i[0] + '_' in var.group(1):
                            tmp = var.group(1) + ' = [' + str(i[1]) + ', ' + str(i[2]) + ']'
                            if tmp not in constraints:
                                constraints.append(tmp)
                            stat = stat.replace('(D)', '')
                            break
            if ' = ' in stat:
                constraints.append(normalize(stat))
    return constraints


# 给定所有函数的constraints，处理函数调用，合并成最终的constraints，注：递归调用将导致死循环
def merge(essa, funcs):
    foo_idx = -1  # 主函数foo编号
    for i, func in enumerate(essa.funcs):
        if func.name == 'foo':
            foo_idx = i
            break
    assert foo_idx != -1
    reserved_symbol = [tmp.name for tmp in essa.funcs] + ['inf', 'PHI', 'ft', 'e', 'int', 'float']
    call_cnt = 0  # 函数调用计数
    queue = funcs[foo_idx][:]  # 最终constraints，初始化为foo函数的constraints
    cursor = 0
    while True:
        if cursor >= len(queue):
            break
        cons = queue[cursor]
        m = re.search(r'(\w+)\s*\(([^)]*)\)', cons)
        if m is None or 'ft' in cons:  # 当前constraint中没有函数调用
            cursor += 1
            continue
        call_cnt += 1
        func_name = m.group(1)
        func_idx = -1
        func_paras = [tmp.strip() for tmp in m.group(2).split(',')]
        new_cons = []  # 因为函数调用需要新插入的constraints
        for j, para in enumerate(func_paras):  # 传递参数
            new_cons.append('para_' + str(j) + '_' + str(call_cnt) + ' = ' + para)
        for j, func in enumerate(essa.funcs):
            if func.name == func_name:
                func_idx = j
                break
        for stat in funcs[func_idx]:  # 依次加入被调用函数的constraints
            if '(D)' in stat:  # 传递参数
                var = re.search(r'(\w*)\(D\)', stat)
                assert var is not None
                for j, para in enumerate(essa.funcs[func_idx].paras):
                    if para + '_' in var.group(1):
                        stat = re.sub(r'(\w*)\(D\)', 'para_' + str(j), stat)
                        break
            vars = re.finditer(r'[a-zA-Z_]\w*', stat)  # 将被调用过程的所有变量后面加上call_cnt标记，以区分对同一函数的多次调用
            for var in vars:
                var = var.group()
                if var not in reserved_symbol:
                    stat = stat.replace(var, var + '_' + str(call_cnt))
                    stat = stat.replace(var + '_' + str(call_cnt) + '_', var + '_')
            new_cons.append(stat)
        def_cons = [cons.split(' = ')[0] + ' = ' + new_cons[-1].split(' = ')[0]]  # 将 a = bar() 改为 a = ret
        queue = queue[:cursor] + def_cons + new_cons + queue[cursor + 1:]  # 更新队列
        cursor += 1
    return queue


class Graph:
    def __init__(self, essa, constraints):
        self.vertex = []
        self.v2id = {}
        self.vars=[]
        self.cons=[]
        self.matrix = []
        self.SCC = []  # 存储强连通分量
        self.ranges=[]

        reserved_symbol = [tmp.name for tmp in essa.funcs] + ['inf', 'PHI', 'ft', 'e', 'int', 'float']
        for stat in constraints:
            vars = re.finditer(r'[a-zA-Z_]\w*', stat)
            for var in vars:
                var = var.group(0)
                if var not in reserved_symbol and var not in self.vertex:
                    self.vertex.append(var)
        for stat in constraints:
            self.vertex.append(stat)
        for i, v in enumerate(self.vertex):
            self.v2id[v] = i
        self.determineVar()
        self.initRange()
        for i in range(0, len(self.vertex)):
            self.matrix.append([0] * len(self.vertex))
        for stat in constraints:
            var_def = stat.split('=')[0].strip()
            vars = re.finditer(r'[a-zA-Z_]\w*', stat)
            for var in vars:
                var = var.group(0)
                if var not in reserved_symbol:
                    if var == var_def:
                        self.matrix[self.v2id[stat]][self.v2id[var]] = 1
                    else:
                        if 'ft(' + var + ')' in stat:
                            self.matrix[self.v2id[var]][self.v2id[stat]] = 2
                        else:
                            self.matrix[self.v2id[var]][self.v2id[stat]] = 1
        self.compute_scc()
        self.topo_sorting()


    def determineVar(self):
        for node in self.vertex:
            if '=' in node:
                self.cons.append(self.v2id[node])
            else:
                self.vars.append(self.v2id[node])

    def initRange(self):
        for i in range(len(self.vertex)):
            self.ranges.append(['s','s'])

    def compute_scc(self):
        r_matrix = [[0] * len(self.vertex) for i in range(0, len(self.vertex))]
        for i in range(0, len(self.vertex)):
            for j in range(0, len(self.vertex)):
                if self.matrix[i][j] != 0:
                    r_matrix[j][i] = 1
        reached = []
        order = []
        for i in range(0, len(self.matrix)):
            if i not in reached:
                self.r_dfs(reached, order, r_matrix, i)
        order.reverse()

        reached = []
        for i in range(0, len(self.matrix)):
            idx = order[i]
            if idx not in reached:
                record = []
                self.dfs(reached, record, self.matrix, idx)
                self.SCC.append(record)

    def r_dfs(self, reached, order, matrix, vid):
        reached.append(vid)
        for j in range(0, len(self.vertex)):
            if matrix[vid][j] != 0 and j not in reached:
                self.r_dfs(reached, order, matrix, j)
        order.append(vid)

    def dfs(self, reached, record, matrix, vid):
        reached.append(vid)
        record.append(vid)
        for j in range(0, len(self.vertex)):
            if matrix[vid][j] != 0 and j not in reached:
                self.dfs(reached, record, matrix, j)

    def topo_sorting(self):
        matrix = copy.deepcopy(self.matrix)
        sorted_scc = []
        while len(sorted_scc) < len(self.SCC):
            cur_scc = None
            for scc in self.SCC:
                if scc in sorted_scc:
                    continue
                flag = True
                for j in scc:
                    for i in range(0, len(self.vertex)):
                        if i in scc:
                            continue
                        if matrix[i][j] != 0:
                            flag = False
                            break
                    if not flag:
                        break
                if flag:
                    cur_scc = scc
                    break
            if cur_scc is None:
                print('不存在对强连通分量的拓扑排序！')
                assert False
            sorted_scc.append(cur_scc)
            for i in range(0, len(self.vertex)):
                for j in range(0, len(self.vertex)):
                    if i in cur_scc or j in cur_scc:
                        matrix[i][j] = 0
        self.SCC = sorted_scc

    def __str__(self):
        rst = '\nVertex in graph:\n'
        for v in self.vertex:
            rst += str(self.v2id[v]) + ':' + v + '\n'
        rst += '\nEdges in graph:\n'
        for i in range(0, len(self.vertex)):
            for j in range(0, len(self.vertex)):
                if self.matrix[i][j] == 1:
                    rst += self.vertex[i] + ' => ' + self.vertex[j] + '\n'
                elif self.matrix[i][j] == 2:
                    rst += self.vertex[i] + ' => ' + self.vertex[j] + ' future' + '\n'
        rst += '\nTopo sorted SCCs:\n'
        for scc in self.SCC:
            rst += str(scc) + '\n'
        return rst


def main():
    funcs = []  # 一个文件可能有多个函数，每个函数都有一组constraints
    essa = eSSA(args.data_dir, args.phase)
    for func in essa.funcs:
        funcs.append(extract_constraints(func, essa.input))
    constraints = merge(essa, funcs)
    for cons in constraints:
        print(cons)
    graph = Graph(essa, constraints)
    print(graph)


if __name__ == '__main__':
    main()
