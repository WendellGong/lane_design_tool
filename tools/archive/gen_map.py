# -*- coding: utf-8 -*-
"""按物理规则生成预设港口地图 JSON：路口用原生元素，直道仅存在于路口之间。"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[2])

import json
from pathlib import Path

S = 4.0          # 图像 -> 画布缩放；确保路口间距 >= 360px
PPM = 12
JH = 180         # 路口半宽 (360/2)

# 图像坐标中的道路中心线 (x/y, 车道数)
V_ROADS = [(109, 2), (231, 2), (388, 4), (546, 2), (668, 2)]
H_ROADS = [(30, 2), (250, 2), (490, 2), (730, 2)]

# 道路在图像中的端点范围
H_X_START, H_X_END = 53, 698
H3_X_END = 641
V_Y_START, V_Y_END = 12, 775

vx = [(round(x * S, 1), lanes) for x, lanes in V_ROADS]
hy = [(round(y * S, 1), lanes) for y, lanes in H_ROADS]

elements = []
junctions = []
seg_no = 0


def add_straight(cx, cy, length, lanes, axis, tag):
    global seg_no
    if length < 20:
        return
    seg_no += 1
    length_m = round(length / PPM, 3)
    elements.append({
        "id": f"el_{tag}_{seg_no:02d}",
        "type": "lane", "subtype": "straight",
        "x": round(cx, 1), "y": round(cy, 1),
        "rotation": 90 if axis == "EW" else 0,
        "w": round(lanes * 3.5 * PPM, 1), "h": round(length_m * PPM, 1),
        "props": {"lanes": lanes, "laneW": 3.5, "length_m": length_m, "twoWay": True}
    })


# ---- 1. 路口元素 ----
for r, (y, hlanes) in enumerate(hy):
    for c, (x, vlanes) in enumerate(vx):
        jid = f"j_r{r}c{c}"
        if r == 0:
            # 最北一排：纵向道路自此向南起，为丁字路口（支路自南接入，rotation=180）
            # 主路宽 = 2×mainLanes×laneW 需与横向直道 hlanes×laneW×PPM 对齐 -> mainLanes = hlanes/2
            # 支路宽 = branchLanes×laneW 需与纵向直道 vlanes×laneW×PPM 对齐 -> branchLanes = vlanes
            elements.append({
                "id": jid, "type": "lane", "subtype": "t_junction",
                "x": x, "y": y, "rotation": 180, "w": 360, "h": 360,
                "props": {"mainLanes": max(1, hlanes // 2), "branchLanes": vlanes,
                          "laneW": 3.5, "zebra": True}
            })
            jtype = "t"
        else:
            # 十字路口：两向路宽均 = 2×lanes×laneW，需与直道对齐 -> lanes = 直道车道数/2
            elements.append({
                "id": jid, "type": "lane", "subtype": "crossroads",
                "x": x, "y": y, "rotation": 0, "w": 360, "h": 360,
                "props": {"lanes": max(1, min(hlanes, vlanes) // 2), "laneW": 3.5, "zebra": True}
            })
            jtype = "cross"
        junctions.append({
            "id": jid, "type": jtype, "pos": {"x": x, "y": y},
            "row": r, "col": c,
            "main": f"r_h{r}", "cross": f"r_v{c + 1}",
            "label": "中央路口" if (r == 2 and c == 3) else None
        })

# ---- 2. 横向直道（路口之间）----
for r, (y, hlanes) in enumerate(hy):
    x_start = H_X_START * S
    x_end = (H3_X_END if r == 3 else H_X_END) * S
    prev = x_start
    for c, (x, _) in enumerate(vx):
        add_straight((prev + x - JH) / 2, y, (x - JH) - prev, hlanes, "EW", f"h{r}_{c}")
        prev = x + JH
    add_straight((prev + x_end) / 2, y, x_end - prev, hlanes, "EW", f"h{r}_end")

# ---- 3. 纵向直道（路口之间）----
for c, (x, vlanes) in enumerate(vx):
    y_start = (hy[0][0] + JH) if c >= 0 else V_Y_START * S  # 北端丁字路口南边缘
    y_end = V_Y_END * S
    prev = y_start
    for r, (y, _) in enumerate(hy):
        if r == 0:
            continue
        add_straight(x, (prev + y - JH) / 2, (y - JH) - prev, vlanes, "NS", f"v{c}_{r}")
        prev = y + JH
    add_straight(x, (prev + y_end) / 2, y_end - prev, vlanes, "NS", f"v{c}_end")

# ---- 4. 语义数据（沿用上次识别结果，按 S=4 换算）----
old_scale = 2.5
ratio = S / old_scale
old = json.loads(Path("tracks/预设港口地图.json").read_text(encoding="utf-8"))


def scale_bbox(b):
    return {k: round(v * ratio, 1) for k, v in b.items()}


def scale_point(p):
    return {k: round(v * ratio, 1) for k, v in p.items()}


zones = []
for z in old["zones"]:
    z = dict(z)
    z["bbox"] = scale_bbox(z["bbox"])
    z["center"] = scale_point(z["center"])
    zones.append(z)

roads = []
for i, rd in enumerate(old["roads"][:9]):
    rd = dict(rd)
    rd["centerline"] = [scale_point(p) for p in rd["centerline"]]
    rd["width_px"] = round(rd["width_px"] * ratio, 1)
    roads.append(rd)

water = dict(old["water"])
water["bbox"] = scale_bbox(water["bbox"])
water["coastline"] = {**water["coastline"],
                      "from": scale_point(water["coastline"]["from"]),
                      "to": scale_point(water["coastline"]["to"])}

markers = []
for mk in old["markers"]:
    mk = dict(mk)
    for k in ("bbox",):
        if k in mk:
            mk[k] = scale_bbox(mk[k])
    for k in ("pos", "label_pos", "trigger_pos"):
        if k in mk:
            mk[k] = scale_point(mk[k])
    markers.append(mk)

# 中央路口语义标记（按图像紫点位置 480,485 换算）
markers.append({
    "id": "m_center", "type": "waypoint", "name": "中央路口",
    "pos": {"x": round(480 * S, 1), "y": round(485 * S, 1)}, "color": "purple",
    "note": "场景命名航点，位于中横路 r_h2 上、能源区东侧道路交叉口一带"
})

out = {
    "version": "1.1",
    "meta": {
        "name": "预设港口地图",
        "description": "由 pre_set_map 识别重建的平面港口自动驾驶测试场景（路口用原生十字/丁字元素连接，无立交桥）",
        "source_image": old["meta"]["source_image"],
        "image_size": old["meta"]["image_size"],
        "image_to_canvas_scale": S,
        "coordinate_system": {
            "origin": "top-left", "x": "right", "y": "down", "north": "up",
            "note": f"canvas 坐标 = 图像坐标 × {S}；遵循 PPM=12（12px = 1m）"
        },
        "physics_note": "路口元素固定 30m×30m=360px；直道 w=lanes×laneW×12、h=length_m×12，两端精确止于路口边缘(±180px)，不与路口重叠。",
        "traffic_note": "所有平面交叉均以十字/丁字路口连接，无立交桥；信号B/C为场景触发点，动态封路为两处候选(默认不激活)，泊位A/B为搜索区。",
        "saved_at": "2026-11-22 14:35:00"
    },
    "view": {"scale": 0.28, "tx": 80, "ty": 60},
    "zones": zones,
    "roads": roads,
    "junctions": junctions,
    "water": water,
    "markers": markers,
    "elements": elements
}

Path("tracks/预设港口地图.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

n_cross = sum(1 for e in elements if e["subtype"] == "crossroads")
n_t = sum(1 for e in elements if e["subtype"] == "t_junction")
n_straight = sum(1 for e in elements if e["subtype"] == "straight")
print(f"elements={len(elements)} crossroads={n_cross} t_junction={n_t} straight={n_straight} junctions={len(junctions)}")
