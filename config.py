"""客行录 · 用户配置

配置文件固定放在 %APPDATA%\\客行录\\settings.json。
之所以不跟数据目录放一起，是因为数据目录本身也在这里配置——
放一起的话换了盘就找不到配置了。

目前只有一项：data_dir（数据存放目录）。
"""

from __future__ import annotations

import json
import os
import sys

APP_NAME = "客行录"
LEGACY_APP_NAME = "影笺录"

_cache: dict | None = None


def _config_dir() -> str:
    root = os.getenv("APPDATA") or os.path.expanduser("~")
    # 开发环境和打包版分开存配置，免得调试时把用户的选择覆盖掉
    name = APP_NAME if getattr(sys, "frozen", False) else APP_NAME + "-dev"
    return os.path.join(root, name)


CONFIG_PATH = os.path.join(_config_dir(), "settings.json")


def _legacy_config_path() -> str:
    root = os.getenv("APPDATA") or os.path.expanduser("~")
    suffix = "" if getattr(sys, "frozen", False) else "-dev"
    return os.path.join(root, LEGACY_APP_NAME + suffix, "settings.json")


def load() -> dict:
    global _cache
    if _cache is None:
        try:
            # 新配置优先；升级首启沿用旧版的数据位置，写入时才创建新配置。
            path = CONFIG_PATH if os.path.isfile(CONFIG_PATH) else _legacy_config_path()
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            _cache = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value) -> None:      # noqa: A001 —— 和 dict 的 set 无关
    global _cache
    data = dict(load())
    data[key] = value
    _cache = data
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def default_data_dir() -> str:
    """没配置过时的默认目录：
    开发环境放项目下的 data；打包后放 %LOCALAPPDATA%\\客行录。
    """
    if getattr(sys, "frozen", False):
        root = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        legacy = os.path.join(root, LEGACY_APP_NAME)
        current = os.path.join(root, APP_NAME)
        # 保持旧照片的绝对路径有效，也不复制或覆盖用户数据库。
        if not os.path.exists(current) and os.path.isdir(legacy):
            return legacy
        return current
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def data_dir() -> str:
    """当前生效的数据目录。"""
    return get("data_dir") or default_data_dir()


def set_data_dir(path: str) -> None:
    set("data_dir", os.path.abspath(path))
