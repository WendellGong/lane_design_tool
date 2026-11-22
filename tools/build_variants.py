# -*- coding: utf-8 -*-
"""按组别派生三套赛道（基础版 / 高级版 / 专科组）。

输入
  基础版来源：tracks/港口测试赛道-本科组-v6.json      （17 处施工障碍 + 6 辆动态障碍，含路侧设施，无限速区）
  高级版来源：tracks/港口测试赛道-本科组-进阶版.json  （= 原 v7，基础版 + 6 处 15 km/h 限速牌）

产出
  tracks/港口测试赛道-本科组-基础版.json   —— 与 v6 同场景，仅重命名与元数据
  tracks/港口测试赛道-本科组-高级版.json   —— 进阶版 + 3 处静态窄口 + 4 辆动态障碍（17→20 静态，6→10 动态）
  tracks/港口测试赛道-专科组.json          —— 基础版削减 12 处窄口与 6 辆新增动态车，必经点改为必过项

专科组必经点：`el_mwrj5xwvo1lrw` 的 props 增加 checkpoint / manual_drive / hint，
             供程序在车辆经过该点时弹屏提示「请手动操作」并切换手动驾驶。
"""
import os
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import copy
import math
import json

PPM = 12.0
BASE_SRC = 'tracks/港口测试赛道-本科组-v6.json'
ADV_SRC = 'tracks/港口测试赛道-本科组-进阶版.json'

OUT_BASE = 'tracks/港口测试赛道-本科组-基础版.json'
OUT_ADV = 'tracks/港口测试赛道-本科组-高级版.json'
OUT_VOC = 'tracks/港口测试赛道-专科组.json'

STAMP_SAVED = "2026/11/22 23:00:00"
STAMP_ISO = "2026-11-22 23:00:00"

# ---------------------------------------------------------------- 几何工具


def fp(e):
    """元素轴对齐包围盒（rotation 按 0/90 处理）。"""
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


def road_bands(e):
    """元素真实路面矩形（路口按路带而非 360x360 包围盒）。"""
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


def track_bb(e):
    """车辆本体 + 前进轨迹（局部 -y 轴）的包围盒。"""
    p = e['props']
    dist = float(p.get('moveDistance', 0)) * PPM if p.get('move') else 0.0
    th = math.radians(e.get('rotation', 0))

    def wpt(lx, ly):
        return (e['x'] + lx * math.cos(th) - ly * math.sin(th),
                e['y'] + lx * math.sin(th) + ly * math.cos(th))

    hh = e['h'] / 2
    pts = [wpt(-e['w'] / 2, -hh), wpt(e['w'] / 2, -hh),
           wpt(-e['w'] / 2, hh), wpt(e['w'] / 2, hh),
           wpt(0, -hh - 8), wpt(0, -hh - 8 - dist)]
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return min(xs), max(xs), min(ys), max(ys)


def overlap(a, b, tol=0.5):
    return min(a[1], b[1]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[2], b[2]) > tol


def order(e):
    return {'lane': 0, 'car': 1, 'light': 2, 'sign': 3, 'obstacle': 4}.get(e['type'], 5)


def meta_patch(d, name, desc):
    d['meta']['name'] = name
    d['meta']['saved_at'] = STAMP_SAVED
    d['meta']['updated_at'] = STAMP_ISO
    d['meta']['description'] = desc


def save(d, path):
    d['elements'] = sorted(d['elements'], key=order)
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    from collections import Counter
    cnt = Counter(e['type'] for e in d['elements'])
    dyn = sum(1 for e in d['elements'] if e['type'] == 'car' and e.get('props', {}).get('move'))
    print(f"  -> {path}  elements={len(d['elements'])}  " +
          ', '.join(f'{k}={v}' for k, v in sorted(cnt.items())) + f"  动态车={dyn}")


# ---------------------------------------------------------------- 1. 基础版

def build_base():
    print('\n=== 1. 本科组基础版（= v6 场景，仅重命名）===')
    d = json.load(open(BASE_SRC, encoding='utf-8'))
    meta_patch(
        d, '港口测试赛道-本科组-基础版',
        "《港口迷雾协同运输场景》本科组·基础版：17 处施工障碍（窄口 / S 弯 / 封路绕行）"
        "+ 6 辆动态障碍物（全场 9 辆动态车）+ 完整路侧设施（信号灯、标志、停车区、行人）。"
        "全场限速 20 km/h，不设 15 km/h 限速区。任务分 1300，时间附加分 T₀ = 300 s。"
    )
    save(d, OUT_BASE)


# ---------------------------------------------------------------- 2. 高级版

ADV_STATIC = [
    ('adv_h2_pinch', 'water_barrier', 3100, 1985, 0,
     "高级版加难：中横路东段南半幅水马（3100），与 (3300) 慢速卡车连续形成「窄口 + 动态车」双约束，"
     "超车窗口被压缩到单一北半幅"),
    ('adv_h3_pinch', 'water_barrier', 900, 2941, 0,
     "高级版加难：北侧东西向道路西段南半幅水马（900），与 (1300) 对向两轮车形成会车窄口"),
    ('adv_h0_pinch2', 'water_barrier', 2560, 101, 0,
     "高级版加难：上横路东段北半幅第二处水马（2560），狭口自 2200 延长至 2560，通行侧须连续保持"),
]

ADV_DYN = [
    ('dyn_adv_v2', 'two_wheeler', 1600, 2560, 0, 12, 12,
     "高级版加难：中央宽通道南段慢速两轮车（北行 12m），与 (1520) 波形护栏收窄段形成对向冲突"),
    ('dyn_adv_h3_e', 'truck', 3600, 2941, 270, 15, 15,
     "高级版加难：北侧东西向道路东段西行卡车（15m），直接占用 B 泊位入口前的西行半幅"),
    ('dyn_adv_h1_e', 'suv', 700, 1021, 90, 20, 25,
     "高级版加难：y=1000 行西段东行 SUV（25m），与环岛西进口车流叠加"),
    ('dyn_adv_h3_w', 'sedan', 600, 2899, 90, 18, 15,
     "高级版加难：北侧东西向道路西段东行轿车（15m），与 (900) 新增水马构成时间窗"),
]


def build_adv():
    print('\n=== 2. 本科组高级版（进阶版 + 3 处静态窄口 + 4 辆动态车）===')
    d = json.load(open(ADV_SRC, encoding='utf-8'))
    els = d['elements']
    have = {e['id'] for e in els}

    proto = {}
    for e in els:
        if e['type'] == 'car' and e['subtype'] not in proto:
            proto[e['subtype']] = e
    wm_size = {e['subtype']: (e['w'], e['h']) for e in els if e['type'] == 'obstacle'}

    added = []
    for eid, sub, x, y, rot, note in ADV_STATIC:
        if eid in have:
            continue
        w, h = wm_size[sub]
        added.append({"id": eid, "type": "obstacle", "subtype": sub, "x": float(x), "y": float(y),
                      "rotation": rot, "props": {}, "note": note, "w": float(w), "h": float(h)})

    for eid, sub, x, y, rot, spd, dist, note in ADV_DYN:
        if eid in have:
            continue
        e = copy.deepcopy(proto[sub])
        e['id'] = eid
        e['x'], e['y'] = float(x), float(y)
        e['rotation'] = rot
        e['props']['move'] = True
        e['props']['moveSpeed'] = spd
        e['props']['moveDistance'] = dist
        e['note'] = note
        added.append(e)

    print('  --- 落位检查 ---')
    bad = 0
    for e in added:
        bb = track_bb(e) if e['type'] == 'car' else fp(e)
        hits = []
        for o in els:
            if o['type'] == 'lane':
                continue                      # 障碍物/车辆本就摆在路面上，路面不算相交
            if overlap(bb, fp(o), 1.0):
                hits.append(f"{o['id']}({o['subtype']})")
        for o in els:
            if o['subtype'] in ('crossroads', 't_junction', 'roundabout') and overlap(bb, fp(o), 1.0):
                hits.append(f"路口{o['id']}")
        tag = 'OK' if not hits else '注意: ' + ','.join(hits)
        if hits:
            bad += 1
        print(f"    {e['id']:16s} {e['subtype']:14s} ({e['x']:7.1f},{e['y']:6.1f}) "
              f"bb x[{bb[0]:7.0f},{bb[1]:7.0f}] y[{bb[2]:7.0f},{bb[3]:7.0f}]  {tag}")
    if bad:
        print(f'  注意：{bad} 处相交，请复核')

    d['elements'] = els + added
    n_stat = sum(1 for e in d['elements'] if e['type'] == 'obstacle' and e['subtype'] in
                 ('water_barrier', 'cone', 'crash_barrel', 'fence', 'guardrail'))
    meta_patch(
        d, '港口测试赛道-本科组-高级版',
        "《港口迷雾协同运输场景》本科组·高级版：在进阶版（含 6 处 15 km/h 限速牌）基础上继续加难——"
        "施工障碍 19→22 处（新增中横路 3100、北侧路 900、上横路 2560 三处窄口），"
        "动态障碍物 9→13 辆（新增中央宽通道南段两轮车、北侧路东段西行卡车、y=1000 西段 SUV、北侧路西段轿车），"
        "全场 13 辆动态车。核心差异在于动态障碍物密度：窄口与动态车几乎逐段叠加，必须做时空联合规划。"
    )
    print(f'  施工障碍={n_stat}  动态车={sum(1 for e in d["elements"] if e["type"] == "car" and e.get("props", {}).get("move"))}')
    save(d, OUT_ADV)


# ---------------------------------------------------------------- 3. 专科组

VOC_REMOVE = [
    # 12 处窄口（全部使断面 < 7 m 的施工设施）
    'ob_slalom_1', 'ob_slalom_2', 'ob_gate_w', 'ob_gate_e',
    'ob_h0_gate', 'ob_h3_gate', 'ob_berthA_gate', 'ob_berthB_gate',
    'ob_rb_out', 'ob_h0_mid', 'ob_h3_mid', 'ob_axis_narrow',
    # 6 辆 v5 新增动态障碍（保留场景原有 3 辆）
    'dyn_cross_w', 'dyn_slalom_suv', 'dyn_rb_bike',
    'dyn_h0_bike', 'dyn_h2_truck', 'dyn_h3_bike',
]

CHECKPOINT_ID = 'el_mwrj5xwvo1lrw'


def build_voc():
    print('\n=== 3. 专科组（基础版削减窄口与动态车 + 必经点为必过项）===')
    d = json.load(open(BASE_SRC, encoding='utf-8'))
    before = len(d['elements'])
    d['elements'] = [e for e in d['elements'] if e['id'] not in VOC_REMOVE]
    removed = before - len(d['elements'])

    for e in d['elements']:
        if e['id'] == CHECKPOINT_ID:
            e['props'] = dict(e.get('props') or {})
            e['props'].update({
                'checkpoint': 'mandatory',
                'manual_drive': True,
                'hint': '请手动操作',
                'hint_delay': 3,
                'hint_duration': 5,
            })
            e['note'] = ("必经点（专科组必过项）：未经过该点成绩记 0；经过后立即弹屏提示"
                         "「请手动操作」，车辆转入手动驾驶完成剩余任务")
            print(f"  必经点 {CHECKPOINT_ID} 已标记：{e['props']}")

    # 封路设施保留检查
    keep = [e['id'] for e in d['elements'] if e['id'].startswith('ob_close')]
    print(f'  移除 {removed} 个元素；保留封路设施 {keep}')
    n_stat = sum(1 for e in d['elements'] if e['type'] == 'obstacle' and e['subtype'] in
                 ('water_barrier', 'cone', 'crash_barrel', 'fence', 'guardrail'))
    n_dyn = sum(1 for e in d['elements'] if e['type'] == 'car' and e.get('props', {}).get('move'))
    print(f'  施工障碍={n_stat}  动态车={n_dyn}')

    meta_patch(
        d, '港口测试赛道-专科组',
        "《港口迷雾协同运输场景》专科组：保留路网、信号点、A/B 泊位与 y=1000 东段封路绕行，"
        "但取消全部 12 处施工窄口（断面恢复 7 m 双向通行）、取消 6 辆新增动态障碍（仅余场景原有 3 辆），"
        "不设 15 km/h 限速区，整体难度显著低于本科组基础版。"
        "必经点 el_mwrj5xwvo1lrw (4000,1000) 为必过项：未经过成绩记 0；经过后弹屏提示「请手动操作」并转手动驾驶。"
    )
    save(d, OUT_VOC)


if __name__ == '__main__':
    build_base()
    build_adv()
    build_voc()
    print('\n完成：3 套组别赛道已生成')
