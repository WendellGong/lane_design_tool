# -*- coding: utf-8 -*-
"""v5：在 v4 基础上追加 6 辆「动态障碍物」（move=true 的行驶车辆）。

动态障碍物 = 沿车头方向以指定速度前进指定距离的车辆（props.move / moveSpeed / moveDistance），
用于制造**通过时机窗口**：选手必须先判断它何时让出窄口，再决定通过或等待。
所有轨迹终点都停在非窄口位置，不会形成永久堵死。

产出：tracks/港口测试赛道-本科组-v5.json
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import copy
import json

SRC = 'tracks/港口测试赛道-本科组-v4.json'
OUT = 'tracks/港口测试赛道-本科组-v5.json'
PPM = 12.0

# 动态障碍物：(id, 车型, x, y, rot, 速度km/h, 距离m, 说明)
DYN = [
    ('dyn_cross_w', 'sedan', 1200, 1981, 270, 20, 40,
     "动态障碍：中横路西段对向轿车（借道南半幅西行 40m）。运输车东行至窄口前必须先与它会车，"
     "窄口 (1330) 只剩南半幅通行，二者方向冲突，必须一方等待"),
    ('dyn_slalom_suv', 'suv', 2060, 1939, 90, 20, 8,
     "动态障碍：S 弯入口北半幅慢速 SUV（东行 8m 后停驻）。占住 slalom_1 的对侧半幅，"
     "迫使运输车在南半幅完成第一次变道"),
    ('dyn_rb_bike', 'two_wheeler', 2100, 980, 90, 10, 25,
     "动态障碍：环岛东出口两轮车（东行 25m，穿过 (2200,1019) 窄口的唯一通行侧）。"
     "出环后须判断它是否已让开，否则只能跟随"),
    ('dyn_h0_bike', 'two_wheeler', 2350, 143, 270, 12, 20,
     "动态障碍：上横路东段对向两轮车（西行 20m，穿过 (2200,101) 窄口通行侧）。"
     "运输车 B 东行必须等它驶离窄口"),
    ('dyn_h2_truck', 'truck', 3300, 1981, 90, 15, 15,
     "动态障碍：中横路东段慢速卡车（东行 15m 后停驻）。位于通往 A 泊位的最后一段直道，"
     "宽 2.5m 占掉南半幅，超车需借用北半幅并避开泊位入口窄口"),
    ('dyn_h3_bike', 'two_wheeler', 1300, 2941, 270, 10, 15,
     "动态障碍：北侧东西向道路西段对向两轮车（西行 15m）。与运输车 B 沿底行西行段交会"),
]

d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
have = {e['id'] for e in els}

# 以同车型现有车辆为模板，保证动力学参数完整
proto = {}
for e in els:
    if e['type'] == 'car' and e['subtype'] not in proto:
        proto[e['subtype']] = e
missing = {s for _, s, *_ in DYN if s not in proto}
if missing:
    raise SystemExit(f'缺少车型模板：{missing}')

added = []
for eid, subtype, x, y, rot, spd, dist, note in DYN:
    if eid in have:
        continue
    e = copy.deepcopy(proto[subtype])
    e['id'] = eid
    e['x'], e['y'] = float(x), float(y)
    e['rotation'] = rot
    e['props']['move'] = True
    e['props']['moveSpeed'] = spd
    e['props']['moveDistance'] = dist
    e['note'] = note
    added.append(e)


def fp(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


def track_bb(e):
    """车辆本体 + 前进轨迹（沿车头方向 -y 局部轴）的包围盒。"""
    import math
    p = e['props']
    dist = float(p.get('moveDistance', 0)) * PPM if p.get('move') else 0.0
    th = math.radians(e.get('rotation', 0))
    pts = []

    def wpt(lx, ly):
        return (e['x'] + lx * math.cos(th) - ly * math.sin(th),
                e['y'] + lx * math.sin(th) + ly * math.cos(th))

    half_h = e['h'] / 2
    for lx, ly in ((-e['w'] / 2, -half_h), (e['w'] / 2, -half_h),
                   (-e['w'] / 2, half_h), (e['w'] / 2, half_h),
                   (0, -half_h - 8), (0, -half_h - 8 - dist)):
        pts.append(wpt(lx, ly))
    xs = [p_[0] for p_ in pts]
    ys = [p_[1] for p_ in pts]
    return min(xs), max(xs), min(ys), max(ys)


print('=== 动态障碍物落位检查 ===')
bad = 0
for e in added:
    x0, x1, y0, y1 = track_bb(e)
    hits = []
    for o in els:
        if o['type'] == 'lane':
            continue
        c0, c1, d0, d1 = fp(o)
        if min(x1, c1) - max(x0, c0) > 1 and min(y1, d1) - max(y0, d0) > 1:
            hits.append(f"{o['id']}({o['subtype']})")
    # 轨迹是否压到路口（路口内不停车更安全）
    for o in els:
        if o['subtype'] in ('crossroads', 't_junction', 'roundabout'):
            c0, c1, d0, d1 = fp(o)
            if min(x1, c1) - max(x0, c0) > 1 and min(y1, d1) - max(y0, d0) > 1:
                hits.append(f"路口{o['id']}")
    tag = 'OK' if not hits else '注意: ' + ', '.join(hits)
    if hits:
        bad += 1
    print(f"  {e['id']:16s} {e['subtype']:13s} ({e['x']:7.1f},{e['y']:6.1f}) rot={e['rotation']:4.0f} "
          f"{e['props']['moveSpeed']:3.0f}km/h × {e['props']['moveDistance']:3.0f}m  轨迹 "
          f"x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}]  {tag}")

if bad:
    print(f'\n注意：{bad} 辆车的本体或轨迹与既有元素/路口相交，请复核')

def order(e):
    return {'lane': 0, 'car': 1, 'light': 2, 'sign': 3, 'obstacle': 4}.get(e['type'], 5)


d['elements'] = sorted(els + added, key=order)

d['meta']['name'] = '港口测试赛道-本科组-v5'
d['meta']['updated_at'] = "2026-11-22 20:10:00"
d['meta']['saved_at'] = "2026/11/22 20:10:00"
d['meta']['description'] = (
    "《港口迷雾协同运输场景》v5（动态加难版）：在 v4 的 17 处施工障碍之上，追加 6 辆带直线运动预设的"
    "动态障碍物（move=true）——中横路对向借道轿车、S 弯入口慢速 SUV、环岛出口与顶/底行对向两轮车、"
    "通往 A 泊位的慢速卡车。动态车与静态窄口组合形成「通过时机窗口」，"
    "要求程序具备动态目标预测与通行权博弈能力，而非单纯静态避障。"
)

json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

n_dyn = sum(1 for e in d['elements'] if e['type'] == 'car' and e['props'].get('move'))
print(f"\nout={OUT}  elements={len(d['elements'])}  car={sum(1 for e in d['elements'] if e['type'] == 'car')}  "
      f"动态车={n_dyn}")
