# coding: utf-8
import argparse
import re
from ssa2essa import eSSA
from build_graph import Graph
from build_graph import extract_constraints
from build_graph import merge
import copy
import math

parser = argparse.ArgumentParser(description='Build Constraint Graph and Widen')
parser.add_argument('-data_dir', type=str, default='../benchmark/')
parser.add_argument('-phase', type=str, default='t1')
args = parser.parse_args()


def widenSCC(scc, graph):
    while True:
        ranges = widenSCConce(scc, graph, graph.ranges)
        flag = 0
        for i in scc:
            if not ranges[i] == graph.ranges[i]:
                flag = 1
        if flag == 0:
            break
        else:
            graph.ranges = ranges
        print('!!', graph.ranges)


def widenSCConce(scc, graph, initialRange):
    ranges = copy.deepcopy(initialRange)

    reached = []
    flag = 0
    for i in scc:
        for j in range(len(initialRange)):
            if graph.matrix[j][i] == 1 and not j in scc:
                dfs(ranges, i, graph, scc, reached)
                flag = 1
                break
        if flag == 1:
            break
    if flag == 0:
        dfs(ranges, scc[0], graph, scc, reached)
    return ranges


def dfs(ranges, i, graph, scc, reached):
    determineRange(i, graph, ranges)
    reached += [i]
    for j in range(len(ranges)):
        if graph.matrix[i][j] == 1 and j in scc and not j in reached:
            dfs(ranges, j, graph, scc, reached)


def determineRange(i, graph, ranges):
    use = []
    for j in range(len(ranges)):
        if graph.matrix[j][i] == 1:
            use += [j]
    if i in graph.cons:
        assert ('=' in graph.vertex[i])
        terms = graph.vertex[i].split('=')
        # var=terms[0].strip()
        exp = terms[1].replace('(float)', '').strip()
        print('widen', terms)
        if re.match(r'^\[(.*),(.*)\]$', exp):
            m = re.match(r'^\[(.*),(.*)\]$', exp)
            x1 = m.group(1).strip()
            x2 = m.group(2).strip()
            if x1 == '-inf' or 'ft' in x1:
                ranges[i][0] = float('-inf')
            else:
                ranges[i][0] = float(x1)
            if x2 == '+inf' or 'ft' in x2:
                ranges[i][1] = float('+inf')
            else:
                ranges[i][1] = float(x2)
        elif ' + ' in exp:
            factors = exp.split(' + ')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + ranges[use[0]][0]
                    ranges[i][1] = ranges[use[0]][1] + ranges[use[0]][1]
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) + float(x2)
                ranges[i][1] = float(x1) + float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + float(x2)
                    ranges[i][1] = ranges[use[0]][1] + float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + float(x1)
                    ranges[i][1] = ranges[use[0]][1] + float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + ranges[use[1]][0]
                    ranges[i][1] = ranges[use[0]][1] + ranges[use[1]][1]

        elif 'PHI' in exp:
            m = re.match(r'^PHI\s*<(.*),(.*)>$', exp)
            x1 = m.group(1).strip()
            x2 = m.group(2).strip()
            assert not (x1 == x2)
            assert (len(use) == 2)
            if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                ranges[i][0] = min(ranges[use[0]][0], ranges[use[1]][0])
                ranges[i][1] = max(ranges[use[0]][1], ranges[use[1]][1])
            elif ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                ranges[i][0] = ranges[use[1]][0]
                ranges[i][1] = ranges[use[1]][1]
            elif ranges[use[1]][0] == 's' and not ranges[use[0]][0] == 's':
                ranges[i][0] = ranges[use[0]][0]
                ranges[i][1] = ranges[use[0]][1]



        elif '*' in exp:
            factors = exp.split('*')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    l1 = ranges[use[0]][0] * ranges[use[0]][0]
                    l2 = ranges[use[0]][0] * ranges[use[0]][1]
                    l3 = ranges[use[0]][1] * ranges[use[0]][1]
                    ranges[i][0] = min(l1, l2, l3)
                    ranges[i][1] = max(l1, l2, l3)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) * float(x2)
                ranges[i][1] = float(x1) * float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] * float(x2)
                    ranges[i][1] = ranges[use[0]][1] * float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] * float(x1)
                    ranges[i][1] = ranges[use[0]][1] * float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    l1 = ranges[use[0]][0] * ranges[use[1]][0]
                    l2 = ranges[use[0]][0] * ranges[use[1]][1]
                    l3 = ranges[use[0]][1] * ranges[use[1]][0]
                    l4 = ranges[use[0]][1] * ranges[use[1]][1]
                    ranges[i][0] = min(l1, l2, l3, l4)
                    ranges[i][1] = max(l1, l2, l3, l4)

        elif '^' in exp:
            if not ranges[use[0]][0] == 's':
                m = re.match(r'^(.*)\^\s*\[(.*),(.*)\]$', exp)
                if m.group(2).strip() == '-inf' or 'ft' in m.group(2):
                    l = float('-inf')
                else:
                    l = float(m.group(2).strip())
                if m.group(3).strip() == '+inf' or 'ft' in m.group(3):
                    u = float('+inf')
                else:
                    u = float(m.group(3).strip())
                assert (len(use) == 1)
                ranges[i][0] = max(ranges[use[0]][0], l)
                ranges[i][1] = min(ranges[use[0]][1], u)
                if ranges[i][0] > ranges[i][1]:
                    '''print(exp)
                    assert(False)'''
                    ranges[i][0] = 's'
                    ranges[i][1] = 's'
        elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', exp):
            ranges[i][0] = float(exp)
            ranges[i][1] = float(exp)
        elif re.match(r'^(\w+_\d+(_\w)?|_\d+)$', exp):
            assert (len(use) == 1)
            ranges[i][0] = ranges[use[0]][0]
            ranges[i][1] = ranges[use[0]][1]
        elif ' - ' in exp:
            factors = exp.split(' - ')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] - ranges[use[0]][1]
                    ranges[i][1] = ranges[use[0]][1] - ranges[use[0]][0]
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) - float(x2)
                ranges[i][1] = float(x1) - float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] - float(x2)
                    ranges[i][1] = ranges[use[0]][1] - float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = float(x1) - ranges[use[0]][1]
                    ranges[i][1] = float(x1) - ranges[use[0]][0]
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    ranges[i][0] = ranges[graph.v2id[x1]][0] - ranges[graph.v2id[x2]][1]
                    ranges[i][1] = ranges[graph.v2id[x1]][1] - ranges[graph.v2id[x2]][0]
        elif '/' in exp:
            factors = exp.split('/')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    l1 = ranges[use[0]][0] / ranges[use[0]][0]
                    l2 = ranges[use[0]][0] / ranges[use[0]][1]
                    l3 = ranges[use[0]][1] / ranges[use[0]][1]
                    ranges[i][0] = min(l1, l2, l3)
                    ranges[i][1] = max(l1, l2, l3)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) / float(x2)
                ranges[i][1] = float(x1) / float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] / float(x2)
                    ranges[i][1] = ranges[use[0]][1] / float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] / float(x1)
                    ranges[i][1] = ranges[use[0]][1] / float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    l1 = ranges[use[0]][0] / ranges[use[1]][0]
                    l2 = ranges[use[0]][0] / ranges[use[1]][1]
                    l3 = ranges[use[0]][1] / ranges[use[1]][0]
                    l4 = ranges[use[0]][1] / ranges[use[1]][1]
                    ranges[i][0] = min(l1, l2, l3, l4)
                    ranges[i][1] = max(l1, l2, l3, l4)

        elif exp.startswith('(int)'):
            assert (len(use) == 1)
            ranges[i][0] = math.floor(ranges[use[0]][0])
            ranges[i][1] = math.ceil(ranges[use[0]][1])
        else:
            print('!!!', exp)
    else:
        assert (i in graph.vars)
        print(graph.vertex[i])
        assert (len(use) == 1)
        if ranges[i][0] == 's' and not ranges[use[0]][0] == 's':
            ranges[i][0] = ranges[use[0]][0]
            ranges[i][1] = ranges[use[0]][1]
        elif not ranges[i][0] == 's' and not ranges[use[0]][0] == 's':
            if ranges[use[0]][0] < ranges[i][0]:
                ranges[i][0] = float('-inf')
            if ranges[use[0]][1] > ranges[i][1]:
                ranges[i][1] = float('+inf')


def futureRes(scc, graph):
    for constraint in scc:
        if constraint in graph.cons:
            use = []
            for j in range(len(graph.ranges)):
                if graph.matrix[j][constraint] == 2:
                    use += [j]
            assert ('=' in graph.vertex[constraint])
            terms = graph.vertex[constraint].split('=')
            var = terms[0].strip()
            exp = terms[1].strip()
            if '^' in exp:
                m = re.match(r'^(.*)\^\s*\[(.*),(.*)\]$', exp)
                f1 = m.group(2).strip()
                f2 = m.group(3).strip()
                print('future', terms)
                if not len(use) == 0 and graph.ranges[use[0]][0] == 's':
                    graph.vertex[constraint] = var + ' = ' + m.group(1).strip() + ' ^ #'
                else:
                    if 'ft' in f1:
                        if '+' in f1:
                            factors = f1.split('+')
                            # print(factors)
                            v = re.match(r'^ft\((.*)\)$', factors[0].strip())
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    change = graph.ranges[i][0] + float(factors[1].strip())
                                    break
                        elif '-' in f1:
                            factors = f1.split('-')
                            v = re.match(r'^ft\((.*)\)$', factors[0].strip())
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    change = graph.ranges[i][0] - float(factors[1].strip())
                                    break
                        else:
                            assert (re.match(r'^ft\((.*)\)$', f1))
                            v = re.match(r'^ft\((.*)\)$', f1)
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    change = graph.ranges[i][0]
                                    break
                        graph.vertex[constraint] = var + ' = ' + m.group(1).strip() + ' ^ [' + str(
                            change) + ',' + m.group(3).strip() + ']'
                        print(graph.vertex[constraint])
                    if 'ft' in f2:
                        if '+' in f2:
                            factors = f2.split('+')
                            v = re.match(r'^ft\((.*)\)$', factors[0].strip())
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    change = graph.ranges[i][1] + float(factors[1].strip())
                                    break
                        elif '-' in f2:
                            factors = f2.split('-')
                            v = re.match(r'^ft\((.*)\)$', factors[0].strip())
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    # print(graph.ranges[i][1])
                                    change = graph.ranges[i][1] - float(factors[1].strip())
                                    break
                        else:
                            assert (re.match(r'^ft\((.*)\)$', f2))
                            v = re.match(r'^ft\((.*)\)$', f2)
                            for i in use:
                                if graph.vertex[i] == v.group(1).strip():
                                    change = graph.ranges[i][1]
                                    break
                        graph.vertex[constraint] = var + ' = ' + m.group(1).strip() + ' ^ [' + m.group(
                            2).strip() + ',' + str(change) + ']'
                        print(graph.vertex[constraint])


def narrowSCC(scc, graph):
    while True:
        ranges = narrowSCConce(scc, graph, graph.ranges)
        flag = 0
        for i in scc:
            if not ranges[i] == graph.ranges[i]:
                flag = 1
        if flag == 0:
            break
        else:
            graph.ranges = ranges


def narrowSCConce(scc, graph, initialRange):
    ranges = copy.deepcopy(initialRange)
    reached = []
    flag = 0
    for i in scc:
        for j in range(len(initialRange)):
            if graph.matrix[j][i] == 1 and not j in scc:
                dfsN(ranges, i, graph, scc, reached)
                flag = 1
                break
        if flag == 1:
            break
    return ranges


def dfsN(ranges, i, graph, scc, reached):
    determineRangeN(i, graph, ranges)
    reached += [i]
    for j in range(len(ranges)):
        if graph.matrix[i][j] == 1 and j in scc and not j in reached:
            dfsN(ranges, j, graph, scc, reached)


def determineRangeN(i, graph, ranges):
    use = []
    for j in range(len(ranges)):
        if graph.matrix[j][i] == 1:
            use += [j]
    if i in graph.cons:
        assert ('=' in graph.vertex[i])
        terms = graph.vertex[i].split('=')
        print('narowing', terms)
        # var=terms[0].strip()
        exp = terms[1].replace('(float)', '').strip()
        if re.match(r'^\[(.*),(.*)\]$', exp):
            m = re.match(r'^\[(.*),(.*)\]$', exp)
            x1 = m.group(1).strip()
            x2 = m.group(2).strip()
            if x1 == '-inf' or 'ft' in x1:
                ranges[i][0] = float('-inf')
            else:
                ranges[i][0] = float(x1)
            if x2 == '+inf' or 'ft' in x2:
                ranges[i][1] = float('+inf')
            else:
                ranges[i][1] = float(x2)
        elif ' + ' in exp:
            factors = exp.split(' + ')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + ranges[use[0]][0]
                    ranges[i][1] = ranges[use[0]][1] + ranges[use[0]][1]
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) + float(x2)
                ranges[i][1] = float(x1) + float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + float(x2)
                    ranges[i][1] = ranges[use[0]][1] + float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + float(x1)
                    ranges[i][1] = ranges[use[0]][1] + float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] + ranges[use[1]][0]
                    ranges[i][1] = ranges[use[0]][1] + ranges[use[1]][1]


        elif 'PHI' in exp:
            m = re.match(r'^PHI\s*<(.*),(.*)>$', exp)
            x1 = m.group(1).strip()
            x2 = m.group(2).strip()
            assert not (x1 == x2)
            assert (len(use) == 2)
            if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                ranges[i][0] = min(ranges[use[0]][0], ranges[use[1]][0])
                ranges[i][1] = max(ranges[use[0]][1], ranges[use[1]][1])
            elif ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                ranges[i][0] = ranges[use[1]][0]
                ranges[i][1] = ranges[use[1]][1]
            elif ranges[use[1]][0] == 's' and not ranges[use[0]][0] == 's':
                ranges[i][0] = ranges[use[0]][0]
                ranges[i][1] = ranges[use[0]][1]


        elif '*' in exp:
            factors = exp.split('*')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2:
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    l1 = ranges[use[0]][0] * ranges[use[0]][0]
                    l2 = ranges[use[0]][0] * ranges[use[0]][1]
                    l3 = ranges[use[0]][1] * ranges[use[0]][1]
                    ranges[i][0] = min(l1, l2, l3)
                    ranges[i][1] = max(l1, l2, l3)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) * float(x2)
                ranges[i][1] = float(x1) * float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] * float(x2)
                    ranges[i][1] = ranges[use[0]][1] * float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] * float(x1)
                    ranges[i][1] = ranges[use[0]][1] * float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    l1 = ranges[use[0]][0] * ranges[use[1]][0]
                    l2 = ranges[use[0]][0] * ranges[use[1]][1]
                    l3 = ranges[use[0]][1] * ranges[use[1]][0]
                    l4 = ranges[use[0]][1] * ranges[use[1]][1]
                    ranges[i][0] = min(l1, l2, l3, l4)
                    ranges[i][1] = max(l1, l2, l3, l4)

        elif '^' in exp:
            if not ranges[use[0]][0] == 's' and not '#' in exp:
                m = re.match(r'^(.*)\^\s*\[(.*),(.*)\]$', exp)
                if m.group(2).strip() == '-inf' or 'ft' in m.group(2):
                    l = float('-inf')
                else:
                    l = float(m.group(2).strip())
                if m.group(3).strip() == '+inf' or m.group(3).strip() == 'inf' or 'ft' in m.group(3):
                    u = float('+inf')
                else:
                    u = float(m.group(3).strip())
                assert (len(use) == 1)
                ranges[i][0] = max(ranges[use[0]][0], l)
                ranges[i][1] = min(ranges[use[0]][1], u)
                if ranges[i][0] > ranges[i][1]:
                    ranges[i][0] = 's'
                    ranges[i][1] = 's'
        elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', exp):
            ranges[i][0] = float(exp)
            ranges[i][1] = float(exp)
        elif re.match(r'^(\w+_\d+(_\w)?|_\d+)$', exp):
            assert (len(use) == 1)
            ranges[i][0] = ranges[use[0]][0]
            ranges[i][1] = ranges[use[0]][1]
        elif ' - ' in exp:
            factors = exp.split(' - ')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] - ranges[use[0]][1]
                    ranges[i][1] = ranges[use[0]][1] - ranges[use[0]][0]
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) - float(x2)
                ranges[i][1] = float(x1) - float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] - float(x2)
                    ranges[i][1] = ranges[use[0]][1] - float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = float(x1) - ranges[use[0]][1]
                    ranges[i][1] = float(x1) - ranges[use[0]][0]
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    ranges[i][0] = ranges[graph.v2id[x1]][0] - ranges[graph.v2id[x2]][1]
                    ranges[i][1] = ranges[graph.v2id[x1]][1] - ranges[graph.v2id[x2]][0]
        elif '/' in exp:
            factors = exp.split('/')
            x1 = factors[0].strip()
            x2 = factors[1].strip()
            if x1 == x2 and not re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                assert (len(use) == 1)
                if not ranges[use[0]][0] == 's':
                    l1 = ranges[use[0]][0] / ranges[use[0]][0]
                    l2 = ranges[use[0]][0] / ranges[use[0]][1]
                    l3 = ranges[use[0]][1] / ranges[use[0]][1]
                    ranges[i][0] = min(l1, l2, l3)
                    ranges[i][1] = max(l1, l2, l3)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1) and re.match(
                    r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                ranges[i][0] = float(x1) / float(x2)
                ranges[i][1] = float(x1) / float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x2):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] / float(x2)
                    ranges[i][1] = ranges[use[0]][1] / float(x2)
            elif re.match(r'^(\+|-)?[0-9]+(.[0-9]+)?(e(\+|-)[0-9]+)?$', x1):
                if not ranges[use[0]][0] == 's':
                    ranges[i][0] = ranges[use[0]][0] / float(x1)
                    ranges[i][1] = ranges[use[0]][1] / float(x1)
            else:
                assert (len(use) == 2)
                if not ranges[use[0]][0] == 's' and not ranges[use[1]][0] == 's':
                    l1 = ranges[use[0]][0] / ranges[use[1]][0]
                    l2 = ranges[use[0]][0] / ranges[use[1]][1]
                    l3 = ranges[use[0]][1] / ranges[use[1]][0]
                    l4 = ranges[use[0]][1] / ranges[use[1]][1]
                    ranges[i][0] = min(l1, l2, l3, l4)
                    ranges[i][1] = max(l1, l2, l3, l4)
        elif exp.startswith('(int)'):
            assert (len(use) == 1)
            ranges[i][0] = math.floor(ranges[use[0]][0])
            ranges[i][1] = math.ceil(ranges[use[0]][1])
        else:
            print('!!!', exp)
    else:
        assert (i in graph.vars)
        assert (len(use) == 1)
        # assert not (ranges[i][0]=='s' or ranges[use[0]][0]=='s')
        if ranges[i][0] == float('-inf') and ranges[use[0]][0] > float('-inf'):
            ranges[i][0] = ranges[use[0]][0]
        elif ranges[use[0]][0] < ranges[i][0]:
            ranges[i][0] = ranges[use[0]][0]
        if ranges[i][1] == float('+inf') and ranges[use[0]][1] < float('+inf'):
            ranges[i][1] = ranges[use[0]][1]
        elif ranges[use[0]][1] > ranges[i][1]:
            ranges[i][1] = ranges[use[0]][1]


def departScc(scc, graph):
    sccs = []
    r_matrix = [[0] * len(graph.vertex) for i in range(0, len(graph.vertex))]
    for i in range(0, len(graph.vertex)):
        for j in range(0, len(graph.vertex)):
            if graph.matrix[i][j] == 1:
                r_matrix[j][i] = 1
    reached = []
    order = []
    for i in range(0, len(graph.matrix)):
        if i in scc and i not in reached:
            r_dfsSCC(reached, order, r_matrix, i, scc)
    order.reverse()

    reached = []
    for i in range(0, len(scc)):
        idx = order[i]
        if idx in scc and idx not in reached:
            record = []
            dfsSCC(reached, record, graph.matrix, idx, scc)
            sccs.append(record)
    return sccs


def r_dfsSCC(reached, order, matrix, vid, scc):
    reached.append(vid)
    for j in range(0, len(matrix)):
        if matrix[vid][j] == 1 and j not in reached and j in scc:
            r_dfsSCC(reached, order, matrix, j, scc)
    order.append(vid)


def dfsSCC(reached, record, matrix, vid, scc):
    reached.append(vid)
    record.append(vid)
    for j in range(0, len(matrix)):
        if matrix[vid][j] == 1 and j not in reached and j in scc:
            dfsSCC(reached, record, matrix, j, scc)


def findRange(graph):
    for scc in graph.SCC:
        sccs = departScc(scc, graph)
        for i in sccs:
            widenSCC(i, graph)
        futureRes(scc, graph)
        for i in sccs:
            narrowSCC(i, graph)
    print(graph.vertex[graph.vars[-1]], graph.ranges[graph.vars[-1]])


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
    print(graph.vars, graph.cons)
    findRange(graph)


if __name__ == '__main__':
    main()
