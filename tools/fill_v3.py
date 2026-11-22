# -*- coding: utf-8 -*-
"""v3（以 v2 为基线）：补齐横向道路缺口 + 西端引道 + 端头车位/警示灯归位。

基线问题：
  - 5 行横向道路（y=-840/120/1000/1960/2920）只有零星碎片，
    路口之间 640~890px 的段大量缺失，网格是断的；
  - 西端引道仅 44px(3.7m)，顶行 y=-840 干脆没有引道；
  - 中轴 x=1552 的十字路口（lanes=2 -> 横向 168px）与横向 84px 直道形成台阶，
    y=1960 已有 2->4 渐变段，y=120 缺同样两段；
  - 东端 4 个泊车位左缘分别落在 4160.2/4172.2/4180.2，未对齐路口右缘 4180；
  - 警示灯落在路口内部（4068,1000）、（1552,2920）。

保留：所有路口坐标、竖向直道、可变车道、环岛、车辆、信号灯、泊车位 id 不变。
输出：tracks/港口测试赛道-本科组-v3.json
"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
from collections import defaultdict

SRC = 'tracks/港口测试赛道-本科组-v2.json'
OUT = 'tracks/港口测试赛道-本科组-v3.json'

PPM, LW = 12.0, 3.5
WEST = -1240.0                      # 西端引道终点（20m）
ROWS = [-840, 120, 1000, 1960, 2920]
J_R = 180.0                         # 路口半宽
SLAB = 560.0                        # 西侧第二个路口右缘 -> 中轴渐变段西端
GRE_W = (1102.0, 1372.0)            # 中轴西侧 2->4 渐变段
GRE_E = (1732.0, 2004.0)            # 中轴东侧 4->2 渐变段
PARK_W = None                       # 运行时按泊车位实际包围盒求

d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
by = {e['id']: e for e in els}


def make_straight(eid, x0, x1, y, lanes=2, note=None):
    L = round(x1 - x0, 1)
    e = {"id": eid, "type": "lane", "subtype": "straight", "rotation": 90,
         "x": round((x0 + x1) / 2, 1), "y": float(y), "w": round(lanes * LW * PPM, 1),
         "h": L, "props": {"laneW": LW, "lanes": lanes,
                           "length_m": round(L / PPM, 4), "twoWay": True}}
    if note:
        e["note"] = note
    return e


def make_var(eid, x0, x1, y, rot, note=None):
    L = round(x1 - x0, 1)
    e = {"id": eid, "type": "lane", "subtype": "variable_lane", "rotation": rot,
         "x": round((x0 + x1) / 2, 1), "y": float(y), "w": 168.0, "h": L,
         "props": {"laneW": LW, "lanesIn": 2, "lanesOut": 4,
                   "length_m": round(L / PPM, 4)}}
    if note:
        e["note"] = note
    return e


# ---------- 1. 读路口 / 泊车位 ----------
inter = defaultdict(list)
for e in els:
    if e['type'] != 'lane':
        continue
    if e['subtype'] in ('crossroads', 't_junction', 'roundabout'):
        ry = round(e['y'])
        if ry in ROWS:
            inter[ry].append((round(e['x'] - e['w'] / 2, 1), round(e['x'] + e['w'] / 2, 1), e['id']))

park_left = {}
for e in els:
    if e['subtype'] == 'parking':
        box_w = e['h'] if round(e.get('rotation', 0)) % 180 else e['w']
        park_left[round(e['y'])] = round(e['x'] - box_w / 2, 1)

# ---------- 2. 逐行生成目标段 ----------
plan = defaultdict(list)      # y -> [(kind, x0, x1, extra)]
for y in ROWS:
    sp = sorted(inter[y])
    gaps = [(WEST, sp[0][0])]
    for a, b in zip(sp, sp[1:]):
        gaps.append((a[1], b[0]))

    for g0, g1 in gaps:
        # 中轴两侧需要 2->4 渐变（仅 y=120 / y=1960 的中轴十字横向 168px）
        if y in (120, 1960) and abs(g0 - SLAB) < 1 and abs(g1 - GRE_W[1]) < 1:
            plan[y].append(('straight', g0, GRE_W[0], None))
            plan[y].append(('var', GRE_W[0], GRE_W[1], 270))
        elif y in (120, 1960) and abs(g0 - GRE_E[0]) < 1 and g1 > GRE_E[0]:
            plan[y].append(('var', GRE_E[0], GRE_E[1], 90))
            plan[y].append(('straight', GRE_E[1], g1, None))
        else:
            plan[y].append(('straight', g0, g1, None))

# ---------- 3. 复用池：现有横向直道 / 渐变段 ----------
pool = defaultdict(lambda: {'s': [], 'v': []})
for e in els:
    if e['type'] != 'lane':
        continue
    ry = round(e['y'])
    if ry not in ROWS:
        continue
    if e['subtype'] == 'straight' and round(e.get('rotation', 0)) % 180 == 90:
        pool[ry]['s'].append(e)
    elif e['subtype'] == 'variable_lane':
        pool[ry]['v'].append(e)
for k in pool:
    pool[k]['s'].sort(key=lambda e: e['x'])
    pool[k]['v'].sort(key=lambda e: e['x'])

used, drops = set(), []
new_els = []

for y in ROWS:
    cand = pool[y]['s']
    candv = pool[y]['v']
    for kind, x0, x1, rot in plan[y]:
        if kind == 'straight':
            if cand:
                e = cand.pop(0)
                e['x'] = round((x0 + x1) / 2, 1)
                e['y'] = float(y)
                e['rotation'] = 90
                e['w'] = round(2 * LW * PPM, 1)
                e['h'] = round(x1 - x0, 1)
                e['props'] = {"laneW": LW, "lanes": 2,
                              "length_m": round((x1 - x0) / PPM, 4), "twoWay": True}
                e['note'] = (f"补齐：横向直道 {x0:.0f}~{x1:.0f}"
                             f"（{x1 - x0:.0f}px={(x1 - x0) / PPM:.1f}m）2 车道，"
                             f"两端严格对齐路口边缘")
                used.add(e['id'])
            else:
                new_els.append(make_straight(
                    f"el_fix_h{ROWS.index(y)}_s{len(new_els)}", x0, x1, y, 2,
                    note=f"补齐：横向直道 {x0:.0f}~{x1:.0f}"
                         f"（{x1 - x0:.0f}px={(x1 - x0) / PPM:.1f}m），连通相邻路口"))
        else:
            # 渐变段：y=1960 已有两个，复用；其余新建
            e = candv.pop(0) if candv else None
            if e:
                e['x'] = round((x0 + x1) / 2, 1)
                e['y'] = float(y)
                e['rotation'] = rot
                e['h'] = round(x1 - x0, 1)
                e['props'] = {"laneW": LW, "lanesIn": 2, "lanesOut": 4,
                              "length_m": round((x1 - x0) / PPM, 4)}
                e['note'] = (f"补齐：中轴{'西' if rot == 270 else '东'}侧 2↔4 车道渐变段 "
                             f"{x0:.0f}~{x1:.0f}，两端宽度分别对齐 84px 直道与 168px 中轴路口")
                used.add(e['id'])
            else:
                new_els.append(make_var(
                    f"el_fix_h{ROWS.index(y)}_{'gw' if rot == 270 else 'ge'}", x0, x1, y, rot,
                    note=f"补齐：中轴{'西' if rot == 270 else '东'}侧 2↔4 车道渐变段 "
                         f"{x0:.0f}~{x1:.0f}，消除 84px 直道与 168px 中轴路口之间的台阶"))
    # 该行未用上的旧横向直道 / 渐变段全部淘汰（碎片/重叠）
    for e in cand + candv:
        drops.append(e['id'])

# ---------- 4. 端头归位 ----------
for e in els:
    if e['subtype'] == 'parking':
        e['x'] = 4247.8
        e['note'] = ("补齐：泊车位左缘 4180 严格对齐东侧路口右缘，"
                     "3 车位垂直式（2.5m×5.3m）+ 6m 通道")
# 中轴接缝清理：环岛 1px 偏移归位，两段可变车道端点严格对齐路口 / 环岛边缘
by['el_mwrizovo0r4o5']['x'] = 1552.0
by['el_mwrj26oe2lhkg']['x'] = 1552.0


def fit_var_y(eid, y0, y1, note):
    e = by[eid]
    e['x'] = 1552.0
    e['y'] = round((y0 + y1) / 2, 1)
    e['h'] = round(y1 - y0, 1)
    e['props']['length_m'] = round((y1 - y0) / PPM, 4)
    e['note'] = note


fit_var_y('el_mwrj0lewhxgrk', 300.0, 649.0,
          "补齐：中轴北段 2->4 可变车道 300~649，上端对齐顶行十字(120)下缘、下端对齐环岛上缘")
fit_var_y('el_mwrj143t6tc2w', 1351.0, 1780.0,
          "补齐：中轴南段 4->2 可变车道 1351~1780，上端对齐环岛下缘、下端对齐 j_r2c2 上缘")

# 警示灯移出路口内部
by['el_mwrj5xwvo1lrw']['x'] = 3780.0
by['el_mwrj5xwvo1lrw']['y'] = 1000.0
by['el_mwrj5xwvo1lrw']['note'] = "补齐：警示灯移到横向道路末端（x=3780），不再压在路口内部"
by['el_mwrj4yqijbrue']['x'] = 1552.0
by['el_mwrj4yqijbrue']['y'] = 3132.0
by['el_mwrj4yqijbrue']['note'] = "补齐：警示灯移到中轴底行丁字路口南缘外侧（断头端），标识禁止南行"

# ---------- 5. 组装 ----------
drop = set(drops)
keep = [e for e in els if e['id'] not in drop] + new_els
lanes = [e for e in keep if e['type'] == 'lane']
others = [e for e in keep if e['type'] != 'lane']
d['elements'] = lanes + others

# ---------- 6. 视图 ----------
def fbox(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


boxes = [fbox(e) for e in d['elements']]
x0 = min(b[0] for b in boxes)
x1 = max(b[1] for b in boxes)
y0 = min(b[2] for b in boxes)
y1 = max(b[3] for b in boxes)
cw, ch, pad = 1200, 860, 56
sc = max(0.1, min(4, min((cw - pad * 2) / (x1 - x0), (ch - pad * 2) / (y1 - y0))))
d['view'] = {"scale": round(sc, 4),
             "tx": round(cw / 2 - (x0 + x1) / 2 * sc, 3),
             "ty": round(ch / 2 - (y0 + y1) / 2 * sc, 3)}

d['meta']['name'] = '港口测试赛道-本科组-v3'
d['meta']['updated_at'] = "2026-11-22 18:20:00"
d['meta']['saved_at'] = "2026/11/22 18:20:00"
d['meta']['description'] = (
    "《港口迷雾协同运输场景》v3（以 v2 为基线补齐）：5 行横向道路按路口边缘严格重建，"
    "补齐 y=-840/120/1000/1960/2920 各行缺失的 640~890px 段；西端引道统一为 -1240~-1000（20m）；"
    "中轴 x=1552 十字两侧补 2↔4 车道渐变段，消除 84px 直道与 168px 路口的台阶；"
    "4 个泊车位左缘统一对齐 4180；警示灯移出路口内部。"
)

json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f"out={OUT}  elements={len(d['elements'])}  (删除 {len(drop)} 个碎片, 新增 {len(new_els)} 段)")
print(f"范围 x[{x0:.1f},{x1:.1f}] y[{y0:.1f},{y1:.1f}]")
for y in ROWS:
    seg = sorted([e for e in d['elements'] if e['type'] == 'lane' and round(e['y']) == y
                  and e['subtype'] in ('straight', 'variable_lane')
                  and round(e.get('rotation', 0)) % 180 == 90],
                 key=lambda e: e['x'])
    print(f"  y={y:6.0f}: " + '  '.join(
        f"{e['props'].get('lanesIn', e['props'].get('lanes'))}L"
        f"[{e['x'] - e['h'] / 2:.0f}~{e['x'] + e['h'] / 2:.0f}]" for e in seg))
