# -*- coding: utf-8 -*-
"""按路网中心线计算三条任务线路的里程，并给出 40 km/h 规划基准时间。

路网取自 tracks/港口测试赛道-本科组-v3.json 的路口网格：
  列 x = -820 / 380 / 1552 / 2800 / 4000    行 y = -840 / 120 / 1000 / 1960 / 2920
节点 = 25 个路口 + 4 个起点 + 2 个泊位 + 1 个动态路障，边权 = 中心线距离（px）。
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import heapq
import json

PPM = 12.0
V40 = 40 / 3.6                      # 40 km/h = 11.111 m/s
COLS = [-820.0, 380.0, 1552.0, 2800.0, 4000.0]
ROWS = [-840.0, 120.0, 1000.0, 1960.0, 2920.0]

d = json.load(open('tracks/港口测试赛道-本科组-v3.json', encoding='utf-8'))
els = d['elements']

# ---------- 节点与边 ----------
nodes = {}
for i, x in enumerate(COLS):
    for j, y in enumerate(ROWS):
        nodes[f"j{i}{j}"] = (x, y)

# 额外节点：起点（西端引道）与泊位（东端）
START = {120: 's0', 1000: 's1', 1960: 's2', 2920: 's3'}
for y, nid in START.items():
    nodes[nid] = (-1016.0, float(y))
nodes['pa'] = (4248.0, 1960.0)      # A 泊位中心
nodes['pb'] = (4248.0, 2920.0)      # B 泊位中心
nodes['rb'] = (3780.0, 1000.0)      # 动态路障
nodes['sA'] = (1552.0, 120.0)       # A 号现场信号
nodes['sB'] = (1552.0, 1000.0)      # B 号现场信号
nodes['sC'] = (1552.0, 1960.0)      # C 号现场信号

adj = {k: [] for k in nodes}


def link(a, b):
    if a not in nodes or b not in nodes:
        return
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    w = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    adj[a].append((b, w))
    adj[b].append((a, w))


# 横向相邻路口
for j in range(len(ROWS)):
    for i in range(len(COLS) - 1):
        link(f"j{i}{j}", f"j{i+1}{j}")
# 纵向相邻路口
for i in range(len(COLS)):
    for j in range(len(ROWS) - 1):
        link(f"j{i}{j}", f"j{i}{j+1}")
# 起点接到西侧第一列
for y, nid in START.items():
    link(nid, f"j0{ROWS.index(float(y))}")
# 泊位接到东侧最后一列
link('pa', 'j43')
link('pb', 'j44')
# 三个现场信号与其所在路口同点，直接并入路网（零长度边）
for sid, jid in (('sA', 'j21'), ('sB', 'j22'), ('sC', 'j23')):
    adj[sid].append((jid, 0.0))
    adj[jid].append((sid, 0.0))
# 动态路障插入 y=1000 行 2800~4000 之间
link('rb', 'j32')
link('rb', 'j42')


def dijkstra(a, b):
    dist = {k: float('inf') for k in nodes}
    prev = {}
    dist[a] = 0
    pq = [(0.0, a)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > dist[u] + 1e-9:
            continue
        if u == b:
            break
        for v, w in adj[u]:
            if du + w < dist[v] - 1e-9:
                dist[v] = du + w
                prev[v] = u
                heapq.heappush(pq, (du + w, v))
    path, cur = [], b
    while cur != a:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            return None, None
    path.append(a)
    return dist[b], list(reversed(path))


legs = {
    '巡检车：起点 → A 信号': ('s1', 'sA'),
    '巡检车：A → B 信号': ('sA', 'sB'),
    '巡检车：B → C 信号': ('sB', 'sC'),
    '巡检车：C → 动态路障': ('sC', 'rb'),
    '运输车 A：起点 → C 信号路口（中央路口）': ('s2', 'sC'),
    '运输车 A：中央路口 → A 泊位': ('sC', 'pa'),
    '运输车 B：起点 → 中央路口': ('s0', 'sC'),
    '运输车 B：中央路口 → B 泊位': ('sC', 'pb'),
}

print('=== 分段里程 ===')
lengths = {}
for name, (a, b) in legs.items():
    L, path = dijkstra(a, b)
    lengths[name] = L / PPM
    print(f"  {name:42s} {L/PPM:7.1f} m   {'→'.join(path)}")

L_C = sum(v for k, v in lengths.items() if k.startswith('巡检车'))
L_A = sum(v for k, v in lengths.items() if k.startswith('运输车 A'))
L_B = sum(v for k, v in lengths.items() if k.startswith('运输车 B'))

print('\n=== 单车线路总里程 ===')
for name, L in (('巡检车 C', L_C), ('运输车 A', L_A), ('运输车 B', L_B)):
    print(f"  {name}: {L:7.1f} m   @40km/h = {L / V40:6.1f} s   @20km/h = {L / (20/3.6):6.1f} s")

L_MAX = max(L_C, L_A, L_B)
T_OP = 75.0          # 作业与等待时间：信号读取 3×8s + 路障扫描 10s + 交付 2×10s + 路口互斥等待 21s
T0 = L_MAX / V40
print(f"\n最长线路 L_max = {L_MAX:.1f} m")
print(f"纯行驶基准 T_run = L_max / 40km/h = {T0:.1f} s")
print(f"作业与等待 T_op = {T_OP:.0f} s（3 次信号读取 24s + 路障扫描 10s + 2 次交付 20s + 路口互斥等待 21s）")
print(f"基准时间 T0 = {T0 + T_OP:.1f} s")
print(f"（600 s 时限 / T0 = {600 / (T0 + T_OP):.1f} 倍余量；等效平均速度 = {L_MAX / (T0 + T_OP) * 3.6:.1f} km/h）")
