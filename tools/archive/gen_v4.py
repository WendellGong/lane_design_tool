# -*- coding: utf-8 -*-
"""v4：1) 西侧两列外移 252px，使全图关于 x=1552 严格镜像对称
        2) 顶行四处边界路口 十字 -> 丁字(rot=180)，消除向北出界的悬空支路

镜像轴 M = 1552  =>  镜像映射 x' = 2M - x = 3104 - x
  西侧列  436 -> 184 (镜像 2920)、 924 -> 672 (镜像 2432)
  西侧内段 852~1100 直道 + 1100~1372 收窄/加宽段  <->  东侧 1732~2004 + 2004~2252
  西端引道 135.6px（-131.6~4）与东端泊车位（3100~3235.6）等长等距
"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[2])

import json
import shutil

P = 'tracks/港口测试赛道-本科组-v2.json'
shutil.copy(P, 'backups/backup_v3.json')

PPM = 12
LW = 3.5
M = 1552.0

d = json.load(open(P, encoding='utf-8'))
els = d['elements']
by = {e['id']: e for e in els}

SHIFT = {436: 184, 924: 672}          # 西侧两列外移 -252


def set_straight(e, x, y, length_px, rot, lanes=2, note=None):
    e['x'] = round(x, 1)
    e['y'] = round(y, 1)
    e['rotation'] = rot
    e['w'] = round(lanes * LW * PPM, 1)
    e['h'] = round(length_px, 1)
    e['props'] = {"laneW": LW, "lanes": lanes,
                  "length_m": round(length_px / PPM, 4), "twoWay": True}
    if note:
        e['note'] = note


def set_variable(e, x, y, length_px, rot, lanes_in, lanes_out, note=None):
    e['x'] = round(x, 1)
    e['y'] = round(y, 1)
    e['rotation'] = rot
    e['w'] = round(max(lanes_in, lanes_out) * LW * PPM, 1)
    e['h'] = round(length_px, 1)
    e['props'] = {"lanesIn": lanes_in, "lanesOut": lanes_out, "laneW": LW,
                  "length_m": round(length_px / PPM, 4)}
    if note:
        e['note'] = note


# ---------- 1. 西侧两列整体外移 ----------
for e in els:
    if e['type'] == 'lane' and round(e['x']) in SHIFT:
        old = int(round(e['x']))
        e['x'] = float(SHIFT[old])
        if e['subtype'] in ('crossroads', 't_junction'):
            e['note'] = (f"西侧列已外移至 x={SHIFT[old]}，与东侧 x={3104 - SHIFT[old]} "
                         f"关于 x=1552 严格镜像")

# ---------- 2. 西侧横向各段按镜像重排 ----------
# 2.1 西端引道：-131.6 ~ 4（135.6px，与东端泊车位包围盒等长）
for i, (eid, ry) in enumerate([('el_h0_0_01', 120), ('el_h1_0_06', 1000),
                               ('el_h2_0_11', 1960), ('el_h3_0_16', 2920)]):
    set_straight(by[eid], (4 + (4 - 135.6)) / 2, ry, 135.6, 90, 2,
                 note="西端引道 -131.6~4（135.6px=11.3m）：与东端泊车位 3100~3235.6 "
                      "等长等距，保证东西两端到中轴 x=1552 的镜像对称；可完整容纳 9.5m 卡车")

# 2.2 j184 与 j672 之间：364~492（128px）
for eid, ry in [('el_h0_1_02', 120), ('el_h1_1_07', 1000),
                ('el_h2_1_12', 1960), ('el_h3_1_17', 2920)]:
    set_straight(by[eid], (364 + 492) / 2, ry, 128, 90, 2,
                 note="西侧外侧直道 364~492（128px），镜像东侧 2612~2740 同段")

# 2.3 y=1000 西侧：环岛西进口 852~1210（358px，镜像东侧 1894~2252）
set_straight(by['el_mwrj2pntv36r0'], (852 + 1210) / 2, 1000.0, 1210 - 852, 90, 2,
             note="环岛西进口 852~1210（358px），与东出口 1894~2252 严格镜像")

# 2.4 y=2920 西侧：852~1372（520px，镜像东侧 1732~2252）
set_straight(by['el_h3_2_18'], (852 + 1372) / 2, 2920.0, 1372 - 852, 90, 2,
             note="底行西段 852~1372（520px），与东段 1732~2252 严格镜像")

# 2.5 y=120 / y=1960 西侧：852~1100 直道 + 1100~1372 渐变段（镜像东侧）
new_lanes = []
for eid, ry, tag in [('el_mwrke7ieptqoa', 120, 'h0'), ('el_mwri62qtnk1un', 1960, 'h2')]:
    set_variable(by[eid], (1100 + 1372) / 2, ry, 272, 270, 2, 4,
                 note=f"中轴西侧渐变段 1100~1372（272px）：东端 4车道(168)接中轴路口，"
                      f"西端 2车道(84)；与东侧 1732~2004 严格镜像")
    new_lanes.append({
        "id": f"el_v4_{tag}_w", "type": "lane", "subtype": "straight",
        "rotation": 90, "x": 976.0, "y": float(ry), "w": 84.0, "h": 248.0,
        "props": {"laneW": LW, "lanes": 2, "length_m": round(248 / PPM, 4), "twoWay": True},
        "note": f"西侧拉宽段 852~1100（248px）2 车道直道，镜像东侧 2004~2252"
    })

# ---------- 3. 顶行边界路口：十字 -> 丁字 rot=180 ----------
# x=1552 保留十字（其北向支路接中轴北向引道 -660~-60，是真实道路）
TOP_J = {'el_mwrkdhwebl7wc': (184, 2), 'el_mwrkdlglm050u': (672, 2),
         'el_mwrkefp157c7o': (2432, 2), 'el_mwrkej7rp1zpx': (2920, 2)}
for jid, (jx, bl) in TOP_J.items():
    e = by[jid]
    e['subtype'] = 't_junction'
    e['rotation'] = 180
    e['w'] = e['h'] = 360
    e['props'] = {"mainLanes": 1, "branchLanes": bl, "laneW": LW, "zebra": True}
    e['note'] = (f"顶行边界丁字路口：主路(横向 y=120)双向1车道 84px，支路({bl}车道)自南接入；"
                 f"北侧无道路，原十字路口向北出界的悬空支路已消除")
# 中轴顶行保持十字（北向引道真实存在）
by['el_mwrke2dy0evg7']['note'] = (
    "顶行中轴十字路口：保留四向（北接中轴北向引道 -660~-60，南接 4->2 渐变段，东西接渐变段）")

# ---------- 4. 车辆 / 限速牌 / 西侧障碍随列外移 ----------
VEH_X = -64.0
for vid in ('el_mwriwq1kmzbh7', 'el_mwrixnrn1acyo', 'el_mwrj75wort5pw', 'el_mwrixzgn7zlze'):
    by[vid]['x'] = VEH_X
for sid in ('el_v2_limit_0', 'el_v2_limit_1', 'el_v2_limit_2', 'el_v2_limit_3'):
    by[sid]['x'] = -100.0

by['el_v2_rb_west']['x'] = 672.0
by['el_mwrj4yqijbrue']['x'] = 610.0     # 警示灯在西侧列路肩（672-62）

# ---------- 5. 重排 + 视图 ----------
have = {e['id'] for e in els}
new_lanes = [e for e in new_lanes if e['id'] not in have]
lanes = [e for e in els if e['type'] == 'lane'] + new_lanes
others = [e for e in els if e['type'] != 'lane']
d['elements'] = lanes + others

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
cw, ch, pad = 1040, 780, 48
sc = max(0.12, min(4, min((cw - pad * 2) / (x1 - x0), (ch - pad * 2) / (y1 - y0))))
d['view'] = {"scale": round(sc, 4),
             "tx": round(cw / 2 - (x0 + x1) / 2 * sc, 3),
             "ty": round(ch / 2 - (y0 + y1) / 2 * sc, 3)}

d['meta']['description'] = (
    "《港口迷雾协同运输场景》v4：全图关于 x=1552 严格镜像对称 —— 西侧两列外移 252px 至 "
    "x=184/672（镜像 2920/2432），逐行补齐 852~1100 直道与 1100~1372 渐变段，"
    "西端引道与东端泊车位等长等距；顶行四处边界十字改为丁字(rot=180)，消除向北出界的悬空支路，"
    "中轴因北向引道真实存在保留十字。")
d['meta']['updated_at'] = "2026-11-22 17:40:00"

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f"elements={len(d['elements'])}  范围 x[{x0:.1f},{x1:.1f}] y[{y0:.1f},{y1:.1f}]")
print(f"中轴 1552 左展 {M - x0:.1f}px / 右展 {x1 - M:.1f}px  -> 对称差 {abs((M - x0) - (x1 - M)):.1f}px")
for e in sorted([e for e in d['elements'] if e['type'] == 'lane'], key=lambda e: (e['y'], e['x'])):
    print(f"  {e['subtype']:14s} x={e['x']:8.1f} y={e['y']:7.1f} w={e['w']:6.1f} h={e['h']:6.1f}"
          f" rot={e.get('rotation', 0):5.1f} {e['id']}")
