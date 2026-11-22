# -*- coding: utf-8 -*-
"""按 elements.js 的几何规则把赛道绘制成 PNG，用于目视检查路口是否接上。"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
import sys
from PIL import Image, ImageDraw

P = sys.argv[1] if len(sys.argv) > 1 else 'tracks/港口测试赛道-本科组-v2.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'renders/map.png'
S = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
PPM = 12

d = json.load(open(P, encoding='utf-8'))
es = [e for e in d['elements'] if e['type'] == 'lane']


def box(e):
    w, h, r = e['w'], e['h'], e.get('rotation', 0) % 180
    if r == 0:
        return e['x'] - w / 2, e['x'] + w / 2, e['y'] - h / 2, e['y'] + h / 2
    return e['x'] - h / 2, e['x'] + h / 2, e['y'] - w / 2, e['y'] + w / 2


bbs = [box(e) for e in es]
x0 = min(b[0] for b in bbs) - 60
x1 = max(b[1] for b in bbs) + 60
y0 = min(b[2] for b in bbs) - 60
y1 = max(b[3] for b in bbs) + 60

W, H = int((x1 - x0) * S), int((y1 - y0) * S)
img = Image.new('RGB', (W, H), (18, 24, 34))
dr = ImageDraw.Draw(img, 'RGBA')


def R(ax, ay, bx, by, fill=(88, 100, 116, 255)):
    dr.rectangle([(ax - x0) * S, (ay - y0) * S, (bx - x0) * S, (by - y0) * S], fill=fill)


def rot_rect(cx, cy, w, h, rot, fill):
    """局部矩形（中心在原点，w x h）旋转后画（仅支持 0/90/180/270）。"""
    r = rot % 360
    if r in (90, 270):
        R(cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2, fill)
    else:
        R(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill)


def rect_off(cx, cy, lx, ly, lw, lh, rot, fill):
    """局部坐标矩形旋转到世界（用于 t_junction 的支路）。"""
    r = rot % 360
    # 局部中心
    lcx, lcy = lx + lw / 2, ly + lh / 2
    if r == 0:
        wcx, wcy = lcx, lcy
    elif r == 180:
        wcx, wcy = -lcx, -lcy
    elif r == 90:
        wcx, wcy = -lcy, lcx
    else:  # 270
        wcx, wcy = lcy, -lcx
    if r in (90, 270):
        lw, lh = lh, lw
    R(cx + wcx - lw / 2, cy + wcy - lh / 2, cx + wcx + lw / 2, cy + wcy + lh / 2, fill)


ROAD = (96, 108, 126, 255)
LANE = (200, 210, 225, 255)

for e in es:
    st, p, cx, cy, rot = e['subtype'], e['props'], e['x'], e['y'], e.get('rotation', 0)
    if st == 'straight':
        rot_rect(cx, cy, e['w'], e['h'], rot, ROAD)
    elif st == 'variable_lane':
        r = rot % 360
        win = max(1, p['lanesIn']) * p['laneW'] * PPM
        wout = max(1, p['lanesOut']) * p['laneW'] * PPM
        half = e['h'] / 2
        pts_local = [(-win / 2, -half), (win / 2, -half), (wout / 2, half), (-wout / 2, half)]
        def tr(pt):
            lx, ly = pt
            if r == 0:
                return cx + lx, cy + ly
            if r == 180:
                return cx - lx, cy - ly
            if r == 90:
                return cx - ly, cy + lx
            return cx + ly, cy - lx
        dr.polygon([((tr(q)[0] - x0) * S, (tr(q)[1] - y0) * S) for q in pts_local], fill=ROAD)
    elif st == 'crossroads':
        Wpx = 2 * p['lanes'] * p['laneW'] * PPM
        R(cx - 180, cy - Wpx / 2, cx + 180, cy + Wpx / 2, ROAD)
        R(cx - Wpx / 2, cy - 180, cx + Wpx / 2, cy + 180, ROAD)
    elif st == 't_junction':
        Wm = 2 * p['mainLanes'] * p['laneW'] * PPM
        Wb = p['branchLanes'] * p['laneW'] * PPM
        R(cx - 180, cy - Wm / 2, cx + 180, cy + Wm / 2, ROAD)          # 主路（横向）
        rect_off(cx, cy, -Wb / 2, -180, Wb, 180 + Wm / 2, rot, ROAD)   # 支路（默认朝北）
    elif st == 'roundabout':
        Rw = (p['r0'] + p['ringLanes'] * p['laneW']) * PPM
        hal = e['w'] / 2
        ew = 2 * p['laneW'] * PPM
        R(cx - ew / 2, cy - hal, cx + ew / 2, cy - Rw, ROAD)
        R(cx - ew / 2, cy + Rw, cx + ew / 2, cy + hal, ROAD)
        R(cx - hal, cy - ew / 2, cx - Rw, cy + ew / 2, ROAD)
        R(cx + Rw, cy - ew / 2, cx + hal, cy + ew / 2, ROAD)
        dr.ellipse([(cx - Rw - x0) * S, (cy - Rw - y0) * S,
                    (cx + Rw - x0) * S, (cy + Rw - y0) * S], fill=ROAD)
        dr.ellipse([(cx - p['r0'] * PPM - x0) * S, (cy - p['r0'] * PPM - y0) * S,
                    (cx + p['r0'] * PPM - x0) * S, (cy + p['r0'] * PPM - y0) * S],
                   fill=(40, 52, 68, 255))
    elif st == 'parking':
        rot_rect(cx, cy, e['w'], e['h'], rot, (110, 118, 132, 255))

# 路口中心与编号
for e in es:
    if e['subtype'] in ('crossroads', 't_junction', 'roundabout'):
        x, y = (e['x'] - x0) * S, (e['y'] - y0) * S
        dr.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(255, 70, 140, 255))

# 其他元素（按实际 footprint 绘制，便于核对占道与收窄）
COL = {'truck': (232, 196, 106), 'sedan': (94, 184, 255), 'suv': (123, 224, 195),
       'two_wheeler': (240, 148, 107), 'bus': (143, 208, 255), 'pedestrian': (120, 190, 240),
       'light_vehicle': (80, 240, 160), 'light_arrow': (80, 240, 160),
       'light_flash': (80, 240, 160), 'light_lane': (80, 240, 160),
       'beacon': (255, 200, 60), 'cone': (242, 122, 30), 'water_barrier': (255, 140, 60),
       'crash_barrel': (255, 90, 90), 'guardrail': (255, 120, 80), 'fence': (200, 120, 255)}
import math


def draw_track(e):
    """绘制车辆直线运动预设轨迹（沿车头方向，黄色虚线 + 终点圈）。"""
    p = e.get('props') or {}
    if not p.get('move'):
        return
    dist = float(p.get('moveDistance') or 0) * PPM
    if dist <= 0:
        return
    th = math.radians(e.get('rotation', 0))

    def wpt(lx, ly):
        return ((e['x'] + lx * math.cos(th) - ly * math.sin(th) - x0) * S,
                (e['y'] + lx * math.sin(th) + ly * math.cos(th) - y0) * S)

    ax, ay = wpt(0, -e['h'] / 2 - 8)
    bx, by = wpt(0, -e['h'] / 2 - 8 - dist)
    seg = max(2, int(dist * S / 6))
    for i in range(seg):
        if i % 2:
            continue
        t1, t2 = i / seg, (i + 1) / seg
        dr.line([ax + (bx - ax) * t1, ay + (by - ay) * t1,
                 ax + (bx - ax) * t2, ay + (by - ay) * t2], fill=(245, 197, 66, 235), width=2)
    dr.ellipse([bx - 4, by - 4, bx + 4, by + 4], outline=(245, 197, 66, 255), width=2)


for e in d['elements']:
    if e['type'] != 'lane':
        draw_track(e)

for e in d['elements']:
    if e['type'] == 'lane':
        continue
    c = COL.get(e['subtype'], (255, 255, 255))
    rot_rect(e['x'], e['y'], e['w'], e['h'], e.get('rotation', 0), c + (255,))

img.save(OUT)
print(f"{OUT}  {W}x{H}  scale={S}  x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}]")
