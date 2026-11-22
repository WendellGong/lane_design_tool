# -*- coding: utf-8 -*-
"""v6：为 x=380 列三个十字路口与 x=2800 顶行丁字路口补全路侧设施。

场地点位
  el_mwrj3uk9sg9t9 = crossroads (380, 120)   上横路 × 西侧南北向道路
  j_r1c1           = crossroads (380, 1000)
  j_r2c1           = crossroads (380, 1960)  中横路
  el_mwrl3r6c7tc0w = t_junction (2800, -840) 顶行东段，支路自南接入

补全内容
  路口：斑马线开启、每口 2 组机动车信号灯、进口道限速牌（20 km/h）
  丁字：减速让行、注意危险、警示灯 ×2
  路侧：x=380 列西侧两处 3 车位停车区，配套 1 辆停放轿车与 2 名行人

产出：tracks/港口测试赛道-本科组-v6.json
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import copy
import json

SRC = 'tracks/港口测试赛道-本科组-v5.json'
OUT = 'tracks/港口测试赛道-本科组-v6.json'
PPM = 12.0

# 需要开启斑马线的路口
ZEBRA = ['el_mwrj3uk9sg9t9', 'j_r1c1', 'j_r2c1']

# (id, 类型, 子类型, x, y, rot, props, 说明)
NEW = [
    # ---------- A. (380,120) 十字路口（路带：横 y78~162，竖 x338~422） ----------
    ('fac_l0_sigA', 'light', 'light_vehicle', 316, 33, 0, {'active': 'green'},
     "上横路 × 西侧南北向道路：西北角机动车信号灯，距路缘 8px"),
    ('fac_l0_sigB', 'light', 'light_vehicle', 444, 207, 180, {'active': 'green'},
     "东南角对向机动车信号灯"),
    ('fac_l0_limit', 'sign', 'ban_speed', 516, 194, 0, {'limit': 20},
     "上横路西行进口（路口东侧 94px）限速 20 km/h"),

    # ---------- B. (380,1000) 十字路口 ----------
    ('fac_l1_sigA', 'light', 'light_vehicle', 316, 913, 0, {'active': 'green'},
     "西北角机动车信号灯"),
    ('fac_l1_sigB', 'light', 'light_vehicle', 444, 1087, 180, {'active': 'green'},
     "东南角对向机动车信号灯"),
    ('fac_l1_limit', 'sign', 'ban_speed', 516, 1074, 0, {'limit': 20},
     "降速进口限速 20 km/h"),

    # ---------- C. (380,1960) 十字路口 ----------
    ('fac_l2_sigA', 'light', 'light_vehicle', 316, 1873, 0, {'active': 'green'},
     "西北角机动车信号灯"),
    ('fac_l2_sigB', 'light', 'light_vehicle', 444, 2047, 180, {'active': 'green'},
     "东南角对向机动车信号灯"),
    ('fac_l2_limit', 'sign', 'ban_speed', 516, 2034, 0, {'limit': 20},
     "中横路西行进口限速 20 km/h"),

    # ---------- D. (2800,-840) 顶行丁字路口（主路 y-882~-798，支路 x2758~2842） ----------
    ('fac_t0_giveway', 'sign', 'ban_give_way', 2876, -700, 0, {},
     "支路（自南接入）减速让行标志，距支路东缘 10px，主路优先"),
    ('fac_t0_danger', 'sign', 'warn_danger', 2876, -560, 0, {},
     "支路进入主路前的注意危险警告"),
    ('fac_t0_beaconA', 'obstacle', 'beacon', 2650, -776, 0, {},
     "丁字路口西南角警示灯，位于主路南缘外 8px"),
    ('fac_t0_beaconB', 'obstacle', 'beacon', 2950, -776, 0, {},
     "丁字路口东南角警示灯"),

    # ---------- E. 路侧停车区与配套 ----------
    ('fac_park_w1', 'lane', 'parking', 270.2, 560, 90,
     {'spaces': 3, 'stallW': 2.5, 'stallL': 5.3, 'aisleW': 6.0, 'layout': 'perpendicular'},
     "路侧停车区 1：接西侧南北向道路西缘（x=338），3 个垂直式国标车位"),
    ('fac_park_w2', 'lane', 'parking', 270.2, 1480, 90,
     {'spaces': 3, 'stallW': 2.5, 'stallL': 5.3, 'aisleW': 6.0, 'layout': 'perpendicular'},
     "路侧停车区 2：接西侧南北向道路西缘，3 个垂直式国标车位"),
    ('fac_park_e1', 'lane', 'parking', 3200, -927, 90,
     {'spaces': 3, 'stallW': 2.5, 'stallL': 5.3, 'aisleW': 6.0, 'layout': 'perpendicular'},
     "顶行北侧停车区：接上横路北缘（y=-882），3 个垂直式国标车位"),

    ('fac_ped1', 'car', 'pedestrian', 320, 52, 0, {'shirt': '#4a90d9', 'pose': 'walk'},
     "行人：上横路北侧人行道，距路缘 13px，位于斑马线西侧"),
    ('fac_ped2', 'car', 'pedestrian', 320, 1900, 0, {'shirt': '#d97b4a', 'pose': 'stand'},
     "行人：中横路北侧人行道等待过街"),
    ('fac_car_park', 'car', 'sedan', 270, 545, 90, {},
     "路侧停车区 1 内停放的轿车（非任务车辆，静止）"),
]

SIZE = {'sedan': (26, 46), 'pedestrian': (10, 22), 'ban_speed': (44, 44),
        'ban_give_way': (48, 48), 'warn_danger': (46, 46), 'beacon': (24, 28),
        'light_vehicle': (28, 74)}

d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
by = {e['id']: e for e in els}

# 1. 开启斑马线
for eid in ZEBRA:
    e = by.get(eid)
    if e:
        e['props']['zebra'] = True
        e['note'] = (e.get('note', '') + "；已开启斑马线与行人过街标线").strip('；')

# 2. 新增设施
proto = {}
for e in els:
    if e['type'] == 'car' and e['subtype'] not in proto:
        proto[e['subtype']] = e

added = []
for eid, typ, sub, x, y, rot, props, note in NEW:
    if eid in by:
        continue
    if sub in proto and sub != 'pedestrian':      # 车辆沿用同车型完整动力学参数
        base = copy.deepcopy(proto[sub]['props'])
        base.update(props)
        base['move'] = False
        props = base
    e = {"id": eid, "type": typ, "subtype": sub, "x": float(x), "y": float(y),
         "rotation": rot, "props": dict(props), "note": note}
    if sub in SIZE:
        e['w'], e['h'] = float(SIZE[sub][0]), float(SIZE[sub][1])
    else:
        e['w'], e['h'] = 90.0, 135.6
    added.append(e)


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


print('=== 新设施落位检查 ===')
warn = 0
for e in added:
    x0, x1, y0, y1 = fp(e)
    on_road = []
    if e['subtype'] != 'parking':          # 停车区本来就要接路
        for l in lanes:
            if l['subtype'] == 'parking':  # 车辆停在车位内属正常
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
    print(f"  {e['id']:16s} {e['subtype']:14s} ({e['x']:7.1f},{e['y']:7.1f}) "
          f"bb x[{x0:7.1f},{x1:7.1f}] y[{y0:7.1f},{y1:7.1f}]  {tag}")

if warn:
    print(f'\n注意：{warn} 处存在压路面或重叠，请复核坐标')
else:
    print('\n全部 OK：标志 / 信号灯 / 行人 均在路侧空地，无压路面、无重叠')


def order(e):
    return {'lane': 0, 'car': 1, 'light': 2, 'sign': 3, 'obstacle': 4}.get(e['type'], 5)


d['elements'] = sorted(els + added, key=order)

d['meta']['name'] = '港口测试赛道-本科组-v6'
d['meta']['updated_at'] = "2026-11-22 21:00:00"
d['meta']['saved_at'] = "2026/11/22 21:00:00"
d['meta']['description'] = (
    "《港口迷雾协同运输场景》v6（路侧设施补全）：为 x=380 列的 3 个十字路口补全斑马线、"
    "双向机动车信号灯与 20 km/h 限速牌；为 x=2800 顶行丁字路口补全减速让行、注意危险与两处警示灯；"
    "并在西侧南北向道路西缘、上横路北缘增设 3 处路侧停车区，配套 1 辆停放轿车与 2 名行人。"
)

json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

from collections import Counter
print(f"\nout={OUT}  elements={len(d['elements'])}  新增 {len(added)}")
print('  ' + ', '.join(f'{k}={v}' for k, v in sorted(Counter(e['type'] for e in d['elements']).items())))
