"""客行录 · 食光小记数据层

和其余模块共用同一个 SQLite 文件（data/yingjianlu.db），多一张 food_items 表：
喝到的饮料、吃到的饭菜都是值得收藏的"食光"，支持照片、评分、店铺记录。

kind 取值：饮料 / 饭菜（用于配色和图标）。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from database import DB_PATH, get_conn

FOOD_DIR = os.path.join(os.path.dirname(DB_PATH), "food")   # 美食照片

FIELDS = ["kind", "name", "place", "eat_date", "price", "rating", "note", "image"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS food_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT DEFAULT '饭菜',   -- 饮料 / 饭菜
    name       TEXT,                  -- 名称（如 生椰拿铁 / 妈妈的红烧肉）
    place      TEXT,                  -- 店铺 / 地点
    eat_date   TEXT,                  -- 日期 YYYY-MM-DD
    price      TEXT,                  -- 价格（文字，如 "18" / "人均 60"）
    rating     INTEGER DEFAULT 0,     -- 评分 0~5 星
    note       TEXT,                  -- 备注 / 感想
    image      TEXT,                  -- 照片本地路径
    created_at TEXT
);
"""


def init_db() -> None:
    os.makedirs(FOOD_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(CREATE_SQL)


init_db()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_food() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM food_items ORDER BY eat_date = '' ASC,"
            " eat_date DESC, id DESC")
        return [_row_to_dict(r) for r in rows]


def get_food(food_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM food_items WHERE id = ?", (food_id,)).fetchone()
        return _row_to_dict(row) if row else None


def add_food(**fields) -> int:
    data = {k: (str(fields.get(k)).strip() if fields.get(k) is not None else "")
            for k in FIELDS}
    if not data["kind"]:
        data["kind"] = "饭菜"
    try:
        rating = int(float(data["rating"]))
    except ValueError:
        rating = 0
    data["rating"] = max(0, min(5, rating))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO food_items ({', '.join(FIELDS)}, created_at) "
            f"VALUES ({', '.join('?' for _ in FIELDS)}, ?)",
            [data[k] for k in FIELDS] + [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        )
        return int(cur.lastrowid)


def update_food(food_id: int, **fields) -> None:
    keys = [k for k in FIELDS if k in fields]
    if not keys:
        return
    if "rating" in fields:
        try:
            fields["rating"] = max(0, min(5, int(float(fields["rating"]))))
        except (TypeError, ValueError):
            fields["rating"] = 0
    sets = ", ".join(f"{k} = ?" for k in keys)
    with get_conn() as conn:
        conn.execute(f"UPDATE food_items SET {sets} WHERE id = ?",
                     [str(fields[k]).strip() if fields[k] is not None else ""
                      for k in keys] + [food_id])


def delete_food(food_id: int) -> dict | None:
    """删除记录，返回被删的行（便于调用方清理照片）。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM food_items WHERE id = ?", (food_id,)).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM food_items WHERE id = ?", (food_id,))
    return _row_to_dict(row)


def stats() -> dict:
    """统计：总数 / 饮料数 / 饭菜数 / 店铺数。"""
    items = list_food()
    places: set[str] = set()
    drinks = 0
    for t in items:
        if t.get("kind") == "饮料":
            drinks += 1
        if (t.get("place") or "").strip():
            places.add(t["place"].strip())
    return {"total": len(items), "drinks": drinks, "meals": len(items) - drinks,
            "places": len(places)}
