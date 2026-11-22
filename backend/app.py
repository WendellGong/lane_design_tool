# -*- coding: utf-8 -*-
"""
自动驾驶赛道设计器 - Python (Flask) 后端
职责：
  1. 托管前端静态页面（frontend/）
  2. 赛道设计 JSON 的保存 / 加载 / 列表 / 删除（持久化到 tracks/ 目录）
"""
import json
import os
import re
import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, abort

# 目录定位：backend/ 的上一级即项目根目录（proj_design/）
# 使用 resolve() 得到规范化绝对路径，避免不同工作目录下启动时路径漂移。
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = (BASE_DIR / "frontend").resolve()
TRACKS_DIR = (BASE_DIR / "tracks").resolve()
TRACKS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 单份设计上限 16MB

# 合法赛道名：中英文、数字、下划线、短横线，防止路径穿越
SAFE_NAME_RE = re.compile(r"^[\w\u4e00-\u9fa5\-]{1,64}$")


def _track_path(name: str) -> Path:
    if not SAFE_NAME_RE.match(name):
        abort(400, description="非法赛道名称，仅允许中英文、数字、下划线与短横线")
    path = (TRACKS_DIR / f"{name}.json").resolve()
    # 防御性校验：规范化后必须仍位于 TRACKS_DIR 之内，杜绝任何越界写入。
    if path.parent != TRACKS_DIR:
        abort(400, description="非法赛道路径")
    return path


# ---------------------------------------------------------------------------
# 前端静态资源
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    full = (FRONTEND_DIR / filename).resolve()
    if TRACKS_DIR in full.parents or FRONTEND_DIR not in full.parents or not full.is_file():
        abort(404)
    return send_from_directory(str(FRONTEND_DIR), filename)


# ---------------------------------------------------------------------------
# 赛道 JSON API
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "track-designer", "time": _now()})


@app.get("/api/tracks")
def list_tracks():
    """返回所有已保存赛道的摘要信息。"""
    items = []
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    for fp in sorted(TRACKS_DIR.glob("*.json")):
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
            items.append({
                "name": fp.stem,
                "updated_at": data.get("meta", {}).get("updated_at", ""),
                "element_count": len(data.get("elements", [])),
                "size": fp.stat().st_size,
            })
        except (json.JSONDecodeError, OSError):
            continue
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return jsonify({"tracks": items})


@app.get("/api/tracks/<name>")
def load_track(name):
    fp = _track_path(name)
    if not fp.is_file():
        abort(404, description="赛道不存在")
    with fp.open("r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.post("/api/tracks/<name>")
def save_track(name):
    """保存（覆盖）一份完整赛道设计到 tracks/<name>.json。"""
    fp = _track_path(name)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        abort(400, description="请求体必须为包含 elements 数组的设计 JSON")

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta["name"] = name
    meta["updated_at"] = _now()
    if not meta.get("created_at"):
        meta["created_at"] = meta["updated_at"]
    payload["meta"] = meta

    # 写入前确保目标目录存在（目录被手动删除时也能自愈），
    # 先写临时文件再原子替换，避免中途失败留下损坏的目标文件。
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fp = fp.with_name(fp.name + ".tmp")
    try:
        with tmp_fp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_fp, fp)
    except Exception:
        if tmp_fp.exists():
            tmp_fp.unlink()
        raise

    return jsonify({
        "ok": True,
        "name": name,
        "path": str(fp.relative_to(BASE_DIR)).replace("\\", "/"),
        "element_count": len(payload["elements"]),
        "updated_at": meta["updated_at"],
    })


@app.delete("/api/tracks/<name>")
def delete_track(name):
    fp = _track_path(name)
    if not fp.is_file():
        abort(404, description="赛道不存在")
    fp.unlink()
    return jsonify({"ok": True, "name": name})


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
