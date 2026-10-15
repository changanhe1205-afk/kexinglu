"""客行录 · 数据目录搬迁

用户可以在「我的」页里把数据从 C 盘挪到别的盘。做法是：
    1. 把当前数据目录里的所有文件复制到新目录
    2. 把新路径写进 %APPDATA%\\客行录\\settings.json
    3. 提示重启（重启后所有模块按新路径读数据）

之所以用"复制"而不是"移动"，是怕复制到一半失败把数据弄丢——
旧目录原样保留，用户确认新位置没问题之后可以自己删。
"""

from __future__ import annotations

import importlib
import os
import shutil
import sqlite3
import sys
from datetime import datetime

import config
import database

# 这些模块都在导入时算好了自己的目录，换位置后要重新执行一遍
_RELOAD_ORDER = ["database", "background", "chat_db", "food_db", "quotes",
                 "theme", "ticket_db", "travel_db", "weather", "ai_ocr"]


def current_dir() -> str:
    return database.BASE_DIR


def default_data_dir() -> str:
    return config.default_data_dir()


def is_default(path: str | None = None) -> bool:
    return os.path.normcase(os.path.abspath(path or current_dir())) == \
        os.path.normcase(os.path.abspath(config.default_data_dir()))


def _same(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _rewrite_paths(db_file: str, old_root: str, new_root: str) -> int:
    """把库里存的绝对路径从旧目录改成新目录。

    数据库里照片 / 海报都是按绝对路径存的，光把文件复制过去还不够，
    路径不重写的话重启后读的还是旧目录。
    """
    fixed = 0
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error:
        return 0
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        for t in tables:
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
            except sqlite3.Error:
                continue
            for c in cols:
                try:
                    cur = conn.execute(
                        f"UPDATE {t} SET {c} = REPLACE({c}, ?, ?) "
                        f"WHERE instr({c}, ?) = 1",
                        (old_root, new_root, old_root))
                    fixed += cur.rowcount or 0
                except sqlite3.Error:
                    continue
        conn.commit()
    finally:
        conn.close()
    return fixed


def reload_all() -> list[str]:
    """按依赖顺序重新执行相关模块，让所有路径立刻指向新目录。

    importlib.reload 是在同一个模块命名空间里重跑一遍，所以别处
    `import xxx` 拿到的模块对象还是同一个，函数里读到的全局变量都会更新。
    """
    done = []
    for name in _RELOAD_ORDER:
        mod = sys.modules.get(name)
        if mod is None:
            continue
        try:
            importlib.reload(mod)
            done.append(name)
        except Exception:              # noqa: BLE001 —— 单个模块失败不该影响整体
            pass
    return done


def check(new_dir: str) -> str:
    """返回空字符串表示可以迁，否则返回不能迁的原因。"""
    if not new_dir:
        return "没有选择目录"
    src = os.path.abspath(current_dir())
    dst = os.path.abspath(new_dir)
    if _same(src, dst):
        return "这已经是当前的数据目录了"
    if dst.startswith(src + os.sep):
        return "不能选当前数据目录里面的子文件夹"
    if src.startswith(dst + os.sep):
        return "不能选当前数据目录的上级文件夹"
    return ""


def has_data(path: str) -> bool:
    return os.path.exists(os.path.join(path, "yingjianlu.db"))


def migrate(new_dir: str) -> tuple[bool, str]:
    """把数据复制到新目录并改配置。返回 (是否成功, 说明文字)。"""
    reason = check(new_dir)
    if reason:
        return False, reason

    src = os.path.abspath(current_dir())
    dst = os.path.abspath(new_dir)
    failed: list[str] = []
    try:
        os.makedirs(dst, exist_ok=True)
        # 目标里要是已经有一份数据，先把它改名留档，别直接盖掉
        old_db = os.path.join(dst, "yingjianlu.db")
        if os.path.exists(old_db):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            try:
                os.replace(old_db, f"{old_db}.{stamp}.bak")
            except OSError as exc:
                return False, f"目标数据库无法备份，已停止搬迁：{exc}"
        count = 0
        for name in os.listdir(src):
            s, d = os.path.join(src, name), os.path.join(dst, name)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                elif os.path.isfile(s):
                    shutil.copy2(s, d)
                else:
                    continue
                count += 1
            except OSError as exc:
                # 个别文件被占用不该让整次迁移报废，记下来继续
                failed.append(f"{name}（{exc.strerror or exc}）")
        if not os.path.exists(os.path.join(dst, "yingjianlu.db")):
            return False, ("数据库文件没能复制过去，先不切换，旧数据还是好的。"
                           + ("；".join(failed[:3]) if failed
                              else "请确认目标文件夹可写"))
        if failed:
            return False, ("部分文件复制失败，未切换数据目录，原数据仍在原位置："
                           + "；".join(failed[:3]))
        fixed = _rewrite_paths(os.path.join(dst, "yingjianlu.db"), src, dst)
    except OSError as exc:
        return False, f"复制失败：{exc}"

    config.set_data_dir(dst)
    reload_all()
    extra = f"，改写了 {fixed} 处图片路径" if fixed else ""
    if failed:
        extra += f"；有 {len(failed)} 项没复制过去：" + "；".join(failed[:2])
    return True, f"已复制 {count} 项到 {dst}{extra}"


def reset_to_default() -> tuple[bool, str]:
    """改回默认目录。"""
    return migrate(config.default_data_dir())
