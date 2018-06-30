# coding:utf-8

# 给定一个有向图，使用Kosaraju算法求解极大强连通分量

N = 10  # 顶点数
edges = [(0, 1), (0, 4), (1, 0), (1, 8), (2, 1), (2, 4), (2, 7), (3, 4), (4, 3), (5, 0), (5, 6), (7, 9), (7, 4), (8, 5),
         (9, 2)]
graph = []
r_graph = []

for i in range(0, N):
    graph.append([0] * N)
    r_graph.append([0] * N)

for edge in edges:
    graph[edge[0]][edge[1]] = 1
    r_graph[edge[1]][edge[0]] = 1

order = []
reached = []


def dfs_r_graph(x):
    reached.append(x)
    for i in range(0, N):
        if r_graph[x][i] == 1:
            if i in reached:
                continue
            dfs_r_graph(i)
    order.append(x)


for i in range(0, N):
    if i not in reached:
        dfs_r_graph(i)

order.reverse()
print(order)

scc = []
reached = []
record = []


def dfs_graph(x):
    reached.append(x)
    record.append(x)
    for i in range(0, N):
        if graph[x][i] == 1:
            if i in reached:
                continue
            dfs_graph(i)


for idx in range(0, N):
    node = order[idx]
    if node not in reached:
        record = []
        dfs_graph(node)
        scc.append(record)

print(scc)
