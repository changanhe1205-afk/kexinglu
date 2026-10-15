"""客行录 · 背景图管理

自带多种预设背景，用户也可以上传自己的一张；
选中的那张由 main.py 铺满整个窗口，所有页面共用。

选择状态存在数据目录 background.json：
    {"type": "preset", "value": "assets/bg_warm.jpg"}
    {"type": "custom", "value": "D:/.../data/backgrounds/xxx.jpg"}
"""

from __future__ import annotations

import json
import os
import shutil
import uuid

import theme
from database import DB_PATH

DATA_DIR = os.path.dirname(DB_PATH)
STATE_PATH = os.path.join(DATA_DIR, "background.json")
STORAGE_DIR = os.path.join(DATA_DIR, "backgrounds")
PICK_EXT = ["png", "jpg", "jpeg", "webp", "bmp"]

# （显示名，资源相对路径）
PRESETS = [
    ("夜蓝", "assets/home_bg.jpg"),
    ("暖橙", "assets/bg_warm.jpg"),
    ("薄荷", "assets/bg_mint.jpg"),
    ("海盐晨光", "assets/backgrounds/sea.svg"),
    ("落日海岸", "assets/backgrounds/sunset.svg"),
    ("沙丘余晖", "assets/backgrounds/dunes.svg"),
    ("林间薄雾", "assets/backgrounds/forest.svg"),
    ("星河夜色", "assets/backgrounds/stars.svg"),
    ("纸间留白", "assets/backgrounds/paper.svg"),
]


def default_src() -> str:
    """默认背景跟随当前完整主题。"""
    return theme.res(theme.HOME_BACKGROUND).replace("\\", "/")


def preset_src(rel: str) -> str:
    """预设图的实际路径（打包后从临时目录读）。"""
    return theme.res(rel).replace("\\", "/")


def _load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def current() -> str:
    """当前要显示的背景图路径。"""
    st = _load_state()
    if st.get("type") == "custom" and st.get("value"):
        if os.path.exists(st["value"]):
            return st["value"].replace("\\", "/")
    if st.get("type") == "preset" and st.get("value") in {rel for _,rel in PRESETS}:
        return preset_src(st["value"])
    return default_src()


def current_name() -> str:
    """当前背景的显示名（给「我的」页看）。"""
    st = _load_state()
    if st.get("type") in (None, "theme"):
        return "跟随主题"
    if st.get("type") == "custom":
        return "你上传的那张"
    for name, rel in PRESETS:
        if current() == preset_src(rel):
            return name
    return "跟随主题"


def is_custom() -> bool:
    return current() != default_src() and _load_state().get("type") == "custom"


def set_preset(rel: str) -> bool:
    """选一张自带预设。"""
    if rel not in {path for _,path in PRESETS} or not os.path.exists(preset_src(rel)):
        return False
    reset()
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"type": "preset", "value": rel}, f, ensure_ascii=False)
    except OSError:
        return False
    return True


def set_custom(src: str) -> bool:
    """上传一张自己的背景。"""
    if not src or not os.path.exists(src):
        return False
    reset()
    ext = os.path.splitext(src)[1].lower() or ".jpg"
    try:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        dest = os.path.join(STORAGE_DIR, f"{uuid.uuid4().hex}{ext}")
        shutil.copyfile(src, dest)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"type": "custom", "value": dest}, f, ensure_ascii=False)
    except OSError:
        return False
    return True


def reset() -> None:
    """清掉选择，回到默认；连上传的文件一起删掉。"""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            old = json.load(f).get("value") or ""
    except (OSError, ValueError):
        old = ""
    try:
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
    except OSError:
        pass
    try:
        shutil.rmtree(STORAGE_DIR)
    except OSError:
        pass


def follow_theme() -> None:
    """只切换选择状态，不删除用户上传的文件。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"type": "theme"}, f)
