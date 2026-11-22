# -*- coding: utf-8 -*-
"""赛道几何体检 v2：尺寸一致性 / 接缝 / 重叠 / 连通性。用法: python _validate.py <file>"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import sys
import json
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else 'tracks/港口测试赛道-本科组-v3.json'
d = json.load(open(path, encoding='utf-8'))
es = d['elements']
lanes = [e for e in es if e['type'] == 'lane']
PPM = 12
ok = True


def fp(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    x, y = e['x'], e['y']
    if r == 0:
        return (x - w / 2, x + w / 2, y - h / 2, y + h / 2)
    return (x - h / 2, x + h / 2, y - w / 2, y + w / 2)


def is_horiz(e):
    x0, x1, y0, y1 = fp(e)
    return (x1 - x0) > (y1 - y0) + 0.5


def is_vert(e):
    x0, x1, y0, y1 = fp(e)
    return (y1 - y0) > (x1 - x0) + 0.5


def is_square(e):
    x0, x1, y0, y1 = fp(e)
    return abs((x1 - x0) - (y1 - y0)) <= 0.5


# ---------- 1. 尺寸与 props 一致性 ----------
print("=== 1. 尺寸一致性 ===")
for e in lanes:
    p, s = e['props'], e['subtype']
    if s == 'straight':
        ew, eh = p['lanes'] * p['laneW'] * PPM, p['length_m'] * PPM
    elif s == 'variable_lane':
        ew = max(p['lanesIn'], p['lanesOut']) * p['laneW'] * PPM
        eh = p['length_m'] * PPM
    elif s in ('t_junction', 'crossroads'):
        ew = eh = 360.0
    elif s == 'roundabout':
        ew = eh = 2 * (p['r0'] + p['ringLanes'] * p['laneW'] + 6) * PPM
    elif s == 'parking':
        perp = p['layout'] != 'parallel'
        ew = (p['spaces'] * p['stallW'] if perp else p['spaces'] * p['stallL']) * PPM
        eh = ((p['stallL'] + p['aisleW']) if perp else (p['stallW'] + p['aisleW'])) * PPM
    else:
        continue
    if abs(ew - e['w']) > 0.2 or abs(eh - e['h']) > 0.2:
        ok = False
        print(f"  [X] {e['id']:16s} {s:14s} 声明 {e['w']}x{e['h']} vs props 推导 {ew:.1f}x{eh:.1f}")
print("  全部一致" if ok else "  存在不一致")

# ---------- 2. 横排行接缝 ----------
print("\n=== 2. 横排行接缝（沿 x）===")
rows = defaultdict(list)
for e in lanes:
    if is_horiz(e) or is_square(e):
        rows[round(e['y'])].append(e)
bad = 0
for ry in sorted(rows):
    segs = sorted([e for e in rows[ry] if fp(e)[2] <= ry <= fp(e)[3]], key=lambda e: fp(e)[0])
    if len(segs) < 2:
        continue
    print(f"\n-- y={ry} --")
    prev = None
    for e in segs:
        x0, x1, y0, y1 = fp(e)
        print(f"   x[{x0:7.1f},{x1:7.1f}] {e.get('subtype'):14s} y[{y0:7.1f},{y1:7.1f}] {e['id']}")
        if prev is not None:
            gap = x0 - prev
            if abs(gap) > 1:
                bad += 1
                print(f"   >>> {'缝隙 %+.1f' % gap if gap > 0 else '重叠 %.1f' % -gap}")
        prev = x1

# ---------- 3. 纵向列接缝 ----------
print("\n=== 3. 纵向列接缝（沿 y）===")
cols = defaultdict(list)
for e in lanes:
    if is_vert(e) or is_square(e):
        cols[round(e['x'])].append(e)
for cx in sorted(cols):
    segs = sorted([e for e in cols[cx] if fp(e)[0] <= cx <= fp(e)[1]], key=lambda e: fp(e)[2])
    if len(segs) < 2:
        continue
    print(f"\n-- x={cx} --")
    prev = None
    for e in segs:
        x0, x1, y0, y1 = fp(e)
        print(f"   y[{y0:7.1f},{y1:7.1f}] {e.get('subtype'):14s} x[{x0:7.1f},{x1:7.1f}] {e['id']}")
        if prev is not None:
            gap = y0 - prev
            if abs(gap) > 1:
                bad += 1
                print(f"   >>> {'缝隙 %+.1f' % gap if gap > 0 else '重叠 %.1f' % -gap}")
        prev = y1

print(f"\n接缝异常合计: {bad}")

# ---------- 4. 两两重叠 ----------
print("\n=== 4. 两两包围盒重叠 ===")
ov = 0
for i in range(len(lanes)):
    for j in range(i + 1, len(lanes)):
        a, b = fp(lanes[i]), fp(lanes[j])
        ox = min(a[1], b[1]) - max(a[0], b[0])
        oy = min(a[3], b[3]) - max(a[2], b[2])
        if ox > 1 and oy > 1:
            ov += 1
            print(f"  {ox:6.1f} x {oy:6.1f} = {ox * oy:8.1f}px2  "
                  f"{lanes[i]['id']:16s} <-> {lanes[j]['id']:16s}")
print(f"重叠对数: {ov}")

# ---------- 5. 连通性 ----------
print("\n=== 5. 连通性 / 断头 ===")


def touch(a, b, tol=2.0):
    a, b = fp(a), fp(b)
    return (a[0] - tol <= b[1] and b[0] - tol <= a[1] and
            a[2] - tol <= b[3] and b[2] - tol <= a[3])


n = len(lanes)
adj = {i: set() for i in range(n)}
for i in range(n):
    for j in range(i + 1, n):
        if touch(lanes[i], lanes[j]):
            adj[i].add(j)
            adj[j].add(i)
seen, comps = set(), []
for i in range(n):
    if i in seen:
        continue
    st, comp = [i], []
    seen.add(i)
    while st:
        k = st.pop()
        comp.append(k)
        for mm in adj[k]:
            if mm not in seen:
                seen.add(mm)
                st.append(mm)
    comps.append(comp)
comps.sort(key=len, reverse=True)
print(f"lane 元素 {n} 个 -> 连通分量 {len(comps)} 个 " + str([len(c) for c in comps]))

dang = 0
for k in sorted(range(n), key=lambda k: (lanes[k]['y'], lanes[k]['x'])):
    if len(adj[k]) <= 1:
        e = lanes[k]
        dang += 1
        print(f"  [断头] {e['id']:16s} {e.get('subtype'):14s} ({e['x']:.0f},{e['y']:.0f}) 邻居={len(adj[k])}")
print(f"断头元素: {dang}（西侧引道末端、停车区为预期断头）")

# ---------- 6. 元素是否落在路面上（车辆/障碍/标志） ----------
print("\n=== 6. 非道路元素与路面的关系 ===")
for e in es:
    if e['type'] == 'lane':
        continue
    ex0, ex1 = e['x'] - e['w'] / 2, e['x'] + e['w'] / 2
    ey0, ey1 = e['y'] - e['h'] / 2, e['y'] + e['h'] / 2
    hits = []
    for L in lanes:
        lx0, lx1, ly0, ly1 = fp(L)
        ox = min(ex1, lx1) - max(ex0, lx0)
        oy = min(ey1, ly1) - max(ey0, ly0)
        if ox > 0.5 and oy > 0.5:
            hits.append(f"{L['id']}({ox:.0f}x{oy:.0f})")
    tag = "压路面" if hits else "路外"
    print(f"  {e['id']:16s} {e.get('subtype'):14s} ({e['x']:.0f},{e['y']:.0f}) {tag} {' '.join(hits[:3])}")
