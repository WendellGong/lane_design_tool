# -*- coding: utf-8 -*-
"""v7：为中横路（y=1960）与北侧东西向道路（y=2920）增设 15 km/h 限速区。

限速区设定
  两条干道全程限速 15 km/h（低于全场 20 km/h 上限），路口进口与窄口/弯道前重复提示。
  限速牌贴路缘外侧 8 px 布置，不压路面、不与既有设施重叠。

路带几何（12 px = 1 m）
  中横路：常规断面 y[1918, 2002]，中央路口放大段 y[1876, 2044]（x 1102~2004）
  北侧东西向道路：y[2878, 2962]

产出：tracks/港口测试赛道-本科组-v7.json
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import json

SRC = 'tracks/港口测试赛道-本科组-v6.json'
OUT = 'tracks/港口测试赛道-本科组-v7.json'
PPM = 12.0

LIMIT = 15
OFF = 8.0          # 路缘外间隙
HW = 22.0          # ban_speed 半宽（44x44）

# 中横路：南缘 y = 2002 + 8 + 22 = 2032；北缘 y = 1918 - 8 - 22 = 1888
# 北侧路：南缘 y = 2962 + 8 + 22 = 2992；北缘 y = 2878 - 8 - 22 = 2848
Y_H2_S = 2002 + OFF + HW
Y_H2_N = 1918 - OFF - HW
Y_H3_S = 2962 + OFF + HW
Y_H3_N = 2878 - OFF - HW

NEW = [
    ('fac_h2_limit_eb1', 'sign', 'ban_speed', 1000, Y_H2_S, 180, {'limit': LIMIT},
     "中横路限速区进口提示：东行（中央路口西侧 552px），贴南缘外 8px，限速 15 km/h"),
    ('fac_h2_limit_eb2', 'sign', 'ban_speed', 2100, Y_H2_S, 180, {'limit': LIMIT},
     "中横路限速区重复提示：东行进入 S 弯（slalom_1 前 80px），限速 15 km/h"),
    ('fac_h2_limit_wb1', 'sign', 'ban_speed', 3300, Y_H2_N, 0, {'limit': LIMIT},
     "中横路限速区：西行进口（A 泊位出口西侧），贴北缘外 8px，限速 15 km/h"),

    ('fac_h3_limit_eb1', 'sign', 'ban_speed', 2000, Y_H3_S, 180, {'limit': LIMIT},
     "北侧东西向道路限速区：东行中段（h3_gate 窄口前 200px），贴南缘外 8px，限速 15 km/h"),
    ('fac_h3_limit_eb2', 'sign', 'ban_speed', 3300, Y_H3_S, 180, {'limit': LIMIT},
     "北侧东西向道路限速区：东行 B 泊位入口前，限速 15 km/h"),
    ('fac_h3_limit_wb1', 'sign', 'ban_speed', 1150, Y_H3_N, 0, {'limit': LIMIT},
     "北侧东西向道路限速区：西行中段，贴北缘外 8px，限速 15 km/h"),
]

SIZE = {'ban_speed': (44, 44)}

d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
by = {e['id']: e for e in els}

added = []
for eid, typ, sub, x, y, rot, props, note in NEW:
    if eid in by:
        continue
    w, h = SIZE[sub]
    added.append({"id": eid, "type": typ, "subtype": sub, "x": float(x), "y": float(y),
                  "rotation": rot, "props": dict(props), "note": note,
                  "w": float(w), "h": float(h)})


def fp(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


lanes = [e for e in els if e['type'] == 'lane']


def road_bands(e):
    """返回元素真实路面矩形列表（路口按路带而非 360x360 包围盒）。"""
    x, y, p = e['x'], e['y'], e.get('props', {})
    st = e['subtype']
    if st == 'crossroads':
        w = 2 * p.get('lanes', 1) * p.get('laneW', 3.5) * PPM
        return [(x - 180, x + 180, y - w / 2, y + w / 2),
                (x - w / 2, x + w / 2, y - 180, y + 180)]
    if st == 't_junction':
        wm = 2 * p.get('mainLanes', 1) * p.get('laneW', 3.5) * PPM
        wb = p.get('branchLanes', 1) * p.get('laneW', 3.5) * PPM
        rot = e.get('rotation', 0) % 360
        if rot in (0, 180):
            return [(x - 180, x + 180, y - wm / 2, y + wm / 2),
                    (x - wb / 2, x + wb / 2, y - 180, y + 180)]
        return [(x - wm / 2, x + wm / 2, y - 180, y + 180),
                (x - 180, x + 180, y - wb / 2, y + wb / 2)]
    return [fp(e)]


print('=== 限速牌落位检查 ===')
warn = 0
for e in added:
    x0, x1, y0, y1 = fp(e)
    on_road = []
    for l in lanes:
        if l['subtype'] == 'parking':
            continue
        for c0, c1, d0, d1 in road_bands(l):
            if min(x1, c1) - max(x0, c0) > 0.5 and min(y1, d1) - max(y0, d0) > 0.5:
                on_road.append(l['id'])
                break
    hit = []
    for o in els:
        if o['type'] == 'lane':
            continue
        c0, c1, d0, d1 = fp(o)
        if min(x1, c1) - max(x0, c0) > 0.5 and min(y1, d1) - max(y0, d0) > 0.5:
            hit.append(o['id'])
    tag = 'OK'
    if on_road:
        tag = '压路面: ' + ','.join(on_road)
        warn += 1
    if hit:
        tag += ' | 重叠: ' + ','.join(hit)
        warn += 1
    print(f"  {e['id']:20s} ({e['x']:7.1f},{e['y']:7.1f}) "
          f"bb x[{x0:7.1f},{x1:7.1f}] y[{y0:7.1f},{y1:7.1f}]  {tag}")

if warn:
    print(f'\n注意：{warn} 处存在压路面或重叠，请复核坐标')
else:
    print('\n全部 OK：6 处限速牌均贴路缘外侧，无压路面、无重叠')


def order(e):
    return {'lane': 0, 'car': 1, 'light': 2, 'sign': 3, 'obstacle': 4}.get(e['type'], 5)


d['elements'] = sorted(els + added, key=order)

d['meta']['name'] = '港口测试赛道-本科组-v7'
d['meta']['updated_at'] = "2026-11-22 22:00:00"
d['meta']['saved_at'] = "2026/11/22 22:00:00"
d['meta']['description'] = (
    "《港口迷雾协同运输场景》v7（限速区加难）：在中横路（y=1960）与北侧东西向道路（y=2920）"
    "增设 6 处 15 km/h 限速牌，贴路缘外侧 8px 布置，覆盖东行进口、S 弯前、窄口前与泊位入口前；"
    "20 km/h 全场上限不变，限速区内以 15 km/h 为判定阈值。"
)

json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

from collections import Counter
print(f"\nout={OUT}  elements={len(d['elements'])}  新增 {len(added)}")
print('  ' + ', '.join(f'{k}={v}' for k, v in sorted(Counter(e['type'] for e in d['elements']).items())))
print('  ' + ', '.join(f'{k}={v}' for k, v in sorted(Counter(e['subtype'] for e in d['elements']).items())))
