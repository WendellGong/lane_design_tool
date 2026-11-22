# -*- coding: utf-8 -*-
"""找出路口之间缺少直道的空隙（横排行 / 纵向列），只读不改。"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
from collections import defaultdict

P = 'tracks/港口测试赛道-本科组-v2.json'
d = json.load(open(P, encoding='utf-8'))
es = [e for e in d['elements'] if e['type'] == 'lane']


def fp(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    x, y = e['x'], e['y']
    if r == 0:
        return (x - w / 2, x + w / 2, y - h / 2, y + h / 2)
    return (x - h / 2, x + h / 2, y - w / 2, y + w / 2)


def wide(e):
    b = fp(e)
    return (b[1] - b[0]) > (b[3] - b[2]) + 0.5


def tall(e):
    b = fp(e)
    return (b[3] - b[2]) > (b[1] - b[0]) + 0.5


def square(e):
    b = fp(e)
    return abs((b[1] - b[0]) - (b[3] - b[2])) <= 0.5


print("=== 路口清单 ===")
js = [e for e in es if e['subtype'] in ('crossroads', 't_junction', 'roundabout')]
for e in sorted(js, key=lambda e: (e['y'], e['x'])):
    b = fp(e)
    print(f"  {e['subtype']:12s} ({e['x']:8.1f},{e['y']:7.1f}) rot={e.get('rotation',0):5.1f} "
          f"x[{b[0]:8.1f},{b[1]:8.1f}] y[{b[2]:7.1f},{b[3]:7.1f}] {e['id']}")
print(f"  合计 {len(js)} 个路口")

print("\n=== 横向：相邻路口之间的空隙 ===")
rowj = defaultdict(list)
for e in js:
    rowj[round(e['y'])].append(e)
for ry in sorted(rowj):
    segs = sorted(rowj[ry], key=lambda e: e['x'])
    for a, b in zip(segs, segs[1:]):
        ga, gb = fp(a)[1], fp(b)[0]
        if gb - ga > 1:
            # 该空隙里是否已有直道覆盖
            cover = [e for e in es
                     if wide(e) and fp(e)[0] <= ga + 1 and fp(e)[1] >= gb - 1
                     and fp(e)[2] <= ry <= fp(e)[3]]
            tag = "直道已覆盖" if cover else ">>> 空缺"
            print(f"  y={ry:6.0f}  {a['id']:18s} |{ga:8.1f} -> {gb:8.1f}| 宽 {gb-ga:7.1f}  {tag}"
                  + (f"  {[c['id'] for c in cover]}" if cover else ""))
        elif ga - gb > 1:
            print(f"  y={ry:6.0f}  {a['id']:18s} 与 {b['id']:18s} 重叠 {ga-gb:.1f}px")

print("\n=== 纵向：相邻路口之间的空隙 ===")
colj = defaultdict(list)
for e in js:
    colj[round(e['x'])].append(e)
for cx in sorted(colj):
    segs = sorted(colj[cx], key=lambda e: e['y'])
    for a, b in zip(segs, segs[1:]):
        ga, gb = fp(a)[3], fp(b)[2]
        if gb - ga > 1:
            cover = [e for e in es
                     if tall(e) and fp(e)[2] <= ga + 1 and fp(e)[3] >= gb - 1
                     and fp(e)[0] <= cx <= fp(e)[1]]
            tag = "直道已覆盖" if cover else ">>> 空缺"
            print(f"  x={cx:6.0f}  {a['id']:18s} |{ga:8.1f} -> {gb:8.1f}| 宽 {gb-ga:7.1f}  {tag}"
                  + (f"  {[c['id'] for c in cover]}" if cover else ""))
        elif ga - gb > 1:
            print(f"  x={cx:6.0f}  {a['id']:18s} 与 {b['id']:18s} 重叠 {ga-gb:.1f}px")
