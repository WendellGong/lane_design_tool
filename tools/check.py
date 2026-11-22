# -*- coding: utf-8 -*-
"""检查网格连通性：每行/每列的道路覆盖是否有缺口或重叠。"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
import sys

P = sys.argv[1] if len(sys.argv) > 1 else 'tracks/港口测试赛道-本科组-v3.json'
d = json.load(open(P, encoding='utf-8'))
es = [e for e in d['elements'] if e['type'] == 'lane']


def bb(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


def merge(iv):
    iv = sorted(iv)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a <= out[-1][1] + 0.01:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


ROWS = [-840, 120, 1000, 1960, 2920]
COLS = [-820, 380, 1552, 2800, 4000]

print(f"=== 横向（每行道路覆盖） {P} ===")
for y in ROWS:
    iv = []
    for e in es:
        x0, x1, y0, y1 = bb(e)
        if y0 - 0.01 <= y <= y1 + 0.01:
            iv.append((round(x0, 1), round(x1, 1), e['id']))
    if not iv:
        print(f"  y={y:6.0f}  无元素")
        continue
    m = merge([(a, b) for a, b, _ in iv])
    lo, hi = m[0][0], m[-1][1]
    gaps = [(m[i][1], m[i + 1][0]) for i in range(len(m) - 1) if m[i + 1][0] - m[i][1] > 1]
    print(f"  y={y:6.0f}  覆盖 [{lo:.0f},{hi:.0f}]  段数={len(m)}  "
          + ("缺口=" + ', '.join(f'{a:.0f}~{b:.0f}' for a, b in gaps) if gaps else "无缺口 ✓"))

print(f"\n=== 纵向（每列道路覆盖） ===")
for x in COLS:
    iv = []
    for e in es:
        x0, x1, y0, y1 = bb(e)
        if x0 - 0.01 <= x <= x1 + 0.01:
            iv.append((round(y0, 1), round(y1, 1), e['id']))
    if not iv:
        print(f"  x={x:6.0f}  无元素")
        continue
    m = merge([(a, b) for a, b, _ in iv])
    lo, hi = m[0][0], m[-1][1]
    gaps = [(m[i][1], m[i + 1][0]) for i in range(len(m) - 1) if m[i + 1][0] - m[i][1] > 1]
    print(f"  x={x:6.0f}  覆盖 [{lo:.0f},{hi:.0f}]  段数={len(m)}  "
          + ("缺口=" + ', '.join(f'{a:.0f}~{b:.0f}' for a, b in gaps) if gaps else "无缺口 ✓"))

# 非道路元素是否落在道路上
print("\n=== 非道路元素落位 ===")
lanes = es
for e in d['elements']:
    if e['type'] == 'lane':
        continue
    ex, ey = e['x'], e['y']
    on = False
    for l in lanes:
        x0, x1, y0, y1 = bb(l)
        if l['subtype'] in ('crossroads', 't_junction', 'roundabout') or (
                x0 - 2 <= ex <= x1 + 2 and y0 - 2 <= ey <= y1 + 2):
            if x0 - 2 <= ex <= x1 + 2 and y0 - 2 <= ey <= y1 + 2:
                on = True
                break
    print(f"  {e['type']:9s} {e['subtype']:14s} ({ex:8.1f},{ey:7.1f}) "
          f"{'在道路上' if on else '>>> 不在道路上'}")
