# -*- coding: utf-8 -*-
"""在用户 demo 基础上补全「拉宽 x 轴」后的对称增补缺口。

用户已完成：东侧两列 x 2184/2672 -> 2432/2920（+248），中轴北向引道，可变车道镜像。
本脚本补齐：
  y=120  收窄可变车道 1732~2004 + 直道 2004~2252
  y=1000 环岛东出口直道 1894~2252
  y=1960 收窄可变车道 1732~2004 + 直道 2004~2252
  y=2920 直道 1732~2252、修正 2676 直道与东端泊车位
  南北对称：x=1552 补南向引道 3100~3700（与北向 -660~-60 对称）
"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[2])

import json
import shutil

SRC = 'tracks/港口测试赛道-本科组-v2.json'
shutil.copy(SRC, 'backups/backup_v2.json')

PPM = 12
LW = 3.5

d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
by = {e['id']: e for e in els}


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


new_lanes = []

# ---- y=120：中轴十字(1372~1732) 东侧的 4->2 收窄段 + 2 车道直道 ----
set_variable(by['el_mwrkecbrz8c6w'], 1868.0, 120.0, 272, 90, 2, 4,
             note="对称增补：中轴十字东侧 4车道(168)->2车道(84) 收窄段，"
                  "精确落在 1732~2004（与西侧 1104~1372 加宽段镜像）")
new_lanes.append({
    "id": "el_v3_h0_e", "type": "lane", "subtype": "straight",
    "rotation": 90, "x": 2128.0, "y": 120.0, "w": 84.0, "h": 248.0,
    "props": {"laneW": LW, "lanes": 2, "length_m": round(248 / PPM, 4), "twoWay": True},
    "note": "对称增补：拉宽段 2004~2252（248px）2 车道直道，连接收窄段与东侧十字"
})

# ---- y=1000：环岛东出口 1894~2252 单段直道 ----
set_straight(by['el_mwrj2u0ln776l'], (1894 + 2252) / 2, 1000.0, 2252 - 1894, 90, 2,
             note="环岛东出口直道：1894~2252（358px），端头分别对齐环岛包围盒与东侧十字，"
                  "替代原 1882~1992 的错位段")

# ---- y=1960：中央十字东侧 4->2 收窄段 + 2 车道直道 ----
set_variable(by['el_mwri6tvpkjwvn'], 1868.0, 1960.0, 272, 90, 2, 4,
             note="对称增补：中央十字东侧 4车道(168)->2车道(84) 收窄段，"
                  "精确落在 1732~2004（原 1700~2300 两端各压路口 32/48px）")
new_lanes.append({
    "id": "el_v3_h2_e", "type": "lane", "subtype": "straight",
    "rotation": 90, "x": 2128.0, "y": 1960.0, "w": 84.0, "h": 248.0,
    "props": {"laneW": LW, "lanes": 2, "length_m": round(248 / PPM, 4), "twoWay": True},
    "note": "对称增补：拉宽段 2004~2252（248px）2 车道直道，连接收窄段与中央路口十字"
})

# ---- y=2920：底行拉宽段单段直道 + 东端修正 ----
set_straight(by['el_h3_3_19'], (1732 + 2252) / 2, 2920.0, 2252 - 1732, 90, 2,
             note="对称增补：底行拉宽段 1732~2252（520px）2 车道直道；底行中轴丁字主路为 1 车道，"
                  "全程 84px 无需渐变")
set_straight(by['el_h3_4_20'], 2676.0, 2920.0, 128, 90, 2,
             note="修正：2612~2740，两端各消除 4px 缝隙/重叠，与顶行、中行同位直道对齐")

# ---- 东端泊车位：三处统一 3167.8（2852+248 的位置） ----
for e in els:
    if e['type'] == 'lane' and e['subtype'] == 'parking':
        e['x'] = 3167.8
        e['rotation'] = 90
        e['w'] = round(e['props']['spaces'] * e['props']['stallW'] * PPM, 1)
        e['h'] = round((e['props']['stallL'] + e['props']['aisleW']) * PPM, 1)
by['el_mwrj8tuwo5zc3']['note'] = "Berth_B（B 泊位）：3100~3235.6，东端与底行丁字路口东缘精确相接"
by['el_mwrj8ozwernkn']['note'] = "Berth_A（A 泊位）：3100~3235.6，中央路口（x=2432）东出口"
by['el_mwrj8f2sneme2']['note'] = "普通停车区（非任务泊位）：顶行东端收头"

# ---- 南北对称：补 x=1552 南向引道 ----
new_lanes.append({
    "id": "el_v3_south_axis", "type": "lane", "subtype": "straight",
    "rotation": 0, "x": 1552.0, "y": 3400.0, "w": 168.0, "h": 600.0,
    "props": {"laneW": LW, "lanes": 4, "length_m": 50, "twoWay": True},
    "note": "对称增补：中轴南向引道 3100~3700（600px，4车道），与北向引道 -660~-60 关于 y=1520 对称"
})

# ---- 重排：道路在下，其余在上 ----
lanes = [e for e in els if e['type'] == 'lane'] + new_lanes
others = [e for e in els if e['type'] != 'lane']
d['elements'] = lanes + others

d['meta']['description'] = (
    "《港口迷雾协同运输场景》v3：在 v2 基础上完成『拉宽地图 x 轴』的对称增补 —— "
    "东侧两列外移到 x=2432/2920(+248) 后，逐行补齐 4→2 收窄可变车道与 248px 直道，"
    "使 2004~2252 拉宽段在 4 条横路上均无缝衔接；中轴补南向引道与北向引道南北对称；"
    "东端三处泊车位统一到 x=3167.8。")
d['meta']['updated_at'] = "2026-11-22 17:10:00"

json.dump(d, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

st = {}
for e in d['elements']:
    st[e['subtype']] = st.get(e['subtype'], 0) + 1
print(f"updated {SRC}  elements={len(d['elements'])}")
print("  " + ", ".join(f"{k}={v}" for k, v in sorted(st.items())))
