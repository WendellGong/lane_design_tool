# -*- coding: utf-8 -*-
"""v4：在 v3 基础上增设施工障碍，提高规划与局部避障难度。

设计约束
  1. 任一断面净宽 >= 38px（3.17m），卡车宽 2.5m 可通过，但要求精准控车；
  2. 障碍一律避开中央路口中心 6m（72px）互斥控制区；
  3. 只做“收窄 / 绕行 / 封路”，封路段另设绕行通路，不留完全封死的必经断面。

产出：tracks/港口测试赛道-本科组-v4.json
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import json

SRC = 'tracks/港口测试赛道-本科组-v3.json'
OUT = 'tracks/港口测试赛道-本科组-v4.json'
PPM = 12.0

# 横向路面纵向范围（行 y -> (y0, y1)）
ROWS_Y = {
    -840: (-882.0, -798.0),
    120: (78.0, 162.0),
    1000: (958.0, 1042.0),
    1960: (1918.0, 2002.0),
    2920: (2878.0, 2962.0),
}
AXIS_X = (1468.0, 1636.0)          # 中轴 4 车道路面横向范围

W = {'cone': 24, 'water_barrier': 46, 'crash_barrel': 34, 'guardrail': 96,
     'fence': 96, 'beacon': 24}
H = {'cone': 28, 'water_barrier': 28, 'crash_barrel': 36, 'guardrail': 22,
     'fence': 32, 'beacon': 28}


def footprint(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


def ob(oid, subtype, x, y, rot, note):
    return {"id": oid, "type": "obstacle", "subtype": subtype,
            "x": float(x), "y": float(y), "rotation": rot,
            "w": float(W[subtype]), "h": float(H[subtype]), "props": {}, "note": note}


NEW = [
    # ---------- ① 中行 y=1960：2004~2620 段 S 形绕行 ----------
    ob('ob_slalom_1', 'crash_barrel', 2180, 1981, 90,
       "施工绕行 1/2：中行东段南半幅占道，北半幅净宽 3.8m；运输车需先取北侧车道"),
    ob('ob_slalom_2', 'crash_barrel', 2420, 1939, 90,
       "施工绕行 2/2：中行东段北半幅占道，南半幅净宽 3.9m；与前一处交错形成 S 弯，"
       "间距 20m，要求完成一次变道 + 一次回正"),

    # ---------- ②③ 中央路口东西进口错位窄口 ----------
    ob('ob_gate_w', 'water_barrier', 1330, 1939, 90,
       "中央路口西进口窄口：北半幅占道，净宽 3.33m；6m 互斥区外 19m，"
       "运输车须减速对准南半幅进入"),
    ob('ob_gate_e', 'water_barrier', 1774, 1981, 90,
       "中央路口东进口窄口：南半幅占道，净宽 3.33m；东西两口错位，"
       "两车进出口方向不同，必须各自重新对线"),

    # ---------- ④⑤ 顶行 / 底行窄口 ----------
    ob('ob_h0_gate', 'water_barrier', 2200, 101, 90,
       "顶行东段窄口：北半幅占道，净宽 3.17m；运输车 B 东行必经，需贴南侧精确通过"),
    ob('ob_h3_gate', 'water_barrier', 2200, 2899, 90,
       "底行东段窄口：北半幅占道，净宽 3.33m；通往 B 泊位必经"),

    # ---------- ⑥⑦ 泊位入口单侧收窄（置于东侧路口之外） ----------
    ob('ob_berthA_gate', 'water_barrier', 3760, 1930, 90,
       "A 泊位入口收窄：北侧占道，净宽 4.08m；入口偏置，需斜向对位后回正入库"),
    ob('ob_berthB_gate', 'water_barrier', 3760, 2890, 90,
       "B 泊位入口收窄：北侧占道，净宽 4.08m；与 A 泊位同向偏置"),

    # ---------- ⑧ y=1000 东段施工封闭（迫使绕行） ----------
    ob('ob_close_fence', 'fence', 3500, 1000, 90,
       "施工封闭：y=1000 东段 2980~3820 整幅封闭，动态路障即设于此；"
       "所有车辆必须改由 x=2800 / x=4000 纵列绕行，单程增加约 260m"),
    ob('ob_close_c1', 'cone', 3300, 984, 0, "封闭区西端锥桶，提示改道"),
    ob('ob_close_c2', 'cone', 3300, 1016, 0, "封闭区西端锥桶，提示改道"),
    ob('ob_close_c3', 'cone', 3700, 984, 0, "封闭区东端锥桶，提示改道"),
    ob('ob_close_c4', 'cone', 3700, 1016, 0, "封闭区东端锥桶，提示改道"),

    # ---------- ⑨ 环岛东出口窄口 ----------
    ob('ob_rb_out', 'water_barrier', 2200, 1019, 90,
       "环岛东出口窄口：南半幅占道，净宽 3.17m；出环后立即收窄，考验出环轨迹"),

    # ---------- ⑩⑪ 上下游补充窄口 ----------
    ob('ob_h0_mid', 'water_barrier', 820, 101, 90,
       "顶行西段窄口：北半幅占道，净宽 3.17m；巡检车前往 A 号信号途经"),
    ob('ob_h3_mid', 'water_barrier', 2400, 2899, 90,
       "底行中段窄口：北半幅占道，净宽 3.33m；B 泊位方向第二处收窄"),

    # ---------- ⑫ 中轴 4 车道收窄（护栏） ----------
    ob('ob_axis_narrow', 'guardrail', 1520, 2300, 0,
       "中轴南段（2140~2740）14m 四车道收窄至 5.7m：护栏占西侧 8m，车辆须在东侧通过"),
]


def net_width(e, row=None):
    x0, x1, y0, y1 = footprint(e)
    if row is not None:
        ry0, ry1 = ROWS_Y[row]
        occ = max(0.0, min(y1, ry1) - max(y0, ry0))
        return (ry1 - ry0) - occ
    occ = max(0.0, min(x1, AXIS_X[1]) - max(x0, AXIS_X[0]))
    return (AXIS_X[1] - AXIS_X[0]) - occ


d = json.load(open(SRC, encoding='utf-8'))
els = d['elements']
have = {e['id'] for e in els}

# 恢复泊位 A/B 标识（v3 生成时被通用文案覆盖）
BERTH = {
    'el_mwrj8ozwernkn': 'A 泊位（Berth_A，200 分）：中央路口东出口正对的东端泊位',
    'el_mwrj8tuwo5zc3': 'B 泊位（Berth_B，200 分）：底行东端泊位',
    'el_mwrl33wty6gvc': '普通停车区（非任务泊位）：顶行东端，仅作场景收头',
    'el_mwrj8f2sneme2': '普通停车区（非任务泊位）：中行东端',
}
for e in els:
    if e['id'] in BERTH:
        e['note'] = BERTH[e['id']]

added = [e for e in NEW if e['id'] not in have]

print('=== 断面净宽自检（>= 38px = 3.17m 视为可通行）===')
bad = 0
for e in added:
    if e['subtype'] == 'fence':
        print(f"  {e['id']:18s} 全幅封闭（该段设绕行通路：x=2800 / x=4000 纵列）")
        continue
    row = next((ry for ry in ROWS_Y
                if abs(e['y'] - ry) < 60
                and footprint(e)[2] < ROWS_Y[ry][1] and footprint(e)[3] > ROWS_Y[ry][0]), None)
    if row is None:
        net, where = net_width(e), '中轴竖向'
    else:
        net, where = net_width(e, row), f'行 y={row:.0f}'
    if net < 38:
        bad += 1
    print(f"  {e['id']:18s} {where:12s} 净宽 {net:6.1f}px = {net / PPM:4.2f} m  "
          + ('OK' if net >= 38 else '>>> 过窄'))

if bad:
    raise SystemExit(f'有 {bad} 处断面过窄，已中止写入')

# 与既有非道路元素（车辆 / 信号灯 / 障碍）的重叠检查
print('\n=== 与既有元素的包围盒冲突检查 ===')
conflict = 0
for e in added:
    a0, a1, b0, b1 = footprint(e)
    for o in els:
        if o['type'] == 'lane':
            continue
        c0, c1, d0, d1 = footprint(o)
        if min(a1, c1) - max(a0, c0) > 1 and min(b1, d1) - max(b0, d0) > 1:
            conflict += 1
            print(f"  ! {e['id']} 与 {o['id']}({o['subtype']}) 重叠")
if not conflict:
    print('  无冲突')

# 图层顺序：道路 -> 车辆 -> 信号灯 -> 标志 -> 障碍
def order(e):
    return {'lane': 0, 'car': 1, 'light': 2, 'sign': 3, 'obstacle': 4}.get(e['type'], 5)


d['elements'] = sorted(els + added, key=order)

d['meta']['name'] = '港口测试赛道-本科组-v4'
d['meta']['updated_at'] = "2026-11-22 19:30:00"
d['meta']['saved_at'] = "2026/11/22 19:30:00"
d['meta']['description'] = (
    "《港口迷雾协同运输场景》v4（加难版）：在 v3 完整网格上增设 15 处施工障碍 —— "
    "中行 S 形绕行 2 处、中央路口东西进口错位窄口 2 处、顶/底行窄口 4 处、"
    "A/B 泊位入口偏置收窄 2 处、y=1000 东段整幅封闭（迫使命中绕行 +260m）、"
    "环岛出口窄口 1 处、中轴四车道收窄至 5.7m 1 处。"
    "所有断面净宽 >= 3.17m，可通行但要求高精度局部规划与避障。"
)

json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

st = {}
for e in d['elements']:
    st[e['subtype']] = st.get(e['subtype'], 0) + 1
print(f"\nout={OUT}  elements={len(d['elements'])}  obstacle={sum(1 for e in d['elements'] if e['type'] == 'obstacle')}")
print('  ' + ', '.join(f'{k}={v}' for k, v in sorted(st.items())))
