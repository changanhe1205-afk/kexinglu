"""客行录 · 旅行日志数据层

和其余模块共用同一个 SQLite 文件（data/yingjianlu.db），两张表：

    travel_logs    一条日志 = 去过的一个地方（地点 / 城市 / 日期 / 评分 / 感想 / 经纬度）
    travel_photos  这条日志下面的照片，一个地方可以放很多张

照片放在 data/travel/ 目录下，数据库里只存本地路径。
经纬度由界面层用 map_data 解析地名得到，存下来是为了标记位置稳定、
以后也方便手工微调。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from database import DB_PATH, get_conn

TRAVEL_DIR = os.path.join(os.path.dirname(DB_PATH), "travel")   # 旅行照片

FIELDS = ["title", "city", "visit_date", "rating", "note", "image",
          "lon", "lat"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS travel_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,                  -- 地点名（如 西湖 / 鼓浪屿）
    city       TEXT,                  -- 城市（如 杭州 / 厦门）
    visit_date TEXT,                  -- 日期 YYYY-MM-DD
    rating     INTEGER DEFAULT 0,     -- 评分 0~5 星
    note       TEXT,                  -- 感想 / 路上的小事
    image      TEXT,                  -- 封面照片（兼容老数据）
    lon        REAL,                  -- 经度
    lat        REAL,                  -- 纬度
    created_at TEXT
);
"""

PHOTO_SQL = """
CREATE TABLE IF NOT EXISTS travel_photos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id     INTEGER NOT NULL,      -- 属于哪条日志
    image      TEXT NOT NULL,         -- 照片本地路径
    caption    TEXT DEFAULT '',       -- 一句话说明
    sort       INTEGER DEFAULT 0,     -- 排序
    created_at TEXT
);
"""


def init_db() -> None:
    """建表（幂等）；老库补 lon / lat 列，老的单图迁移进照片表。"""
    os.makedirs(TRAVEL_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(CREATE_SQL)
        conn.executescript(PHOTO_SQL)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(travel_logs)")}
        if "lon" not in cols:
            conn.execute("ALTER TABLE travel_logs ADD COLUMN lon REAL")
        if "lat" not in cols:
            conn.execute("ALTER TABLE travel_logs ADD COLUMN lat REAL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tp_log "
                     "ON travel_photos(log_id)")
        # 老数据：每条日志的 image 变成照片表里的第一张
        rows = conn.execute(
            "SELECT l.id, l.image FROM travel_logs l "
            "WHERE l.image IS NOT NULL AND l.image != '' "
            "AND NOT EXISTS (SELECT 1 FROM travel_photos p WHERE p.log_id = l.id)"
        ).fetchall()
        for r in rows:
            conn.execute(
                "INSERT INTO travel_photos (log_id, image, caption, sort, "
                "created_at) VALUES (?, ?, '', 0, ?)",
                (r[0], r[1], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


init_db()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


# ---------------- 日志 ----------------
def list_logs() -> list[dict]:
    """全部日志，按日期倒序；顺便把照片挂到每条下面。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM travel_logs ORDER BY visit_date = '' ASC,"
            " visit_date DESC, id DESC").fetchall()
        photos = conn.execute(
            "SELECT * FROM travel_photos ORDER BY sort ASC, id ASC").fetchall()
    by_log: dict[int, list[dict]] = {}
    for p in photos:
        by_log.setdefault(p["log_id"], []).append(_row_to_dict(p))
    out = []
    for r in rows:
        d = _row_to_dict(r)
        d["photos"] = by_log.get(d["id"], [])
        out.append(d)
    return out


def get_log(log_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM travel_logs WHERE id = ?",
                           (log_id,)).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["photos"] = [_row_to_dict(p) for p in conn.execute(
            "SELECT * FROM travel_photos WHERE log_id = ? ORDER BY sort, id",
            (log_id,))]
        return d


def add_log(**fields) -> int:
    data = {k: fields.get(k) for k in FIELDS}
    data["title"] = (data.get("title") or "").strip()
    data["city"] = (data.get("city") or "").strip()
    try:
        rating = int(float(data.get("rating") or 0))
    except (TypeError, ValueError):
        rating = 0
    data["rating"] = max(0, min(5, rating))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO travel_logs ({', '.join(FIELDS)}, created_at) "
            f"VALUES ({', '.join('?' for _ in FIELDS)}, ?)",
            [data[k] for k in FIELDS]
            + [datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return int(cur.lastrowid)


def update_log(log_id: int, **fields) -> None:
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
        conn.execute(f"UPDATE travel_logs SET {sets} WHERE id = ?",
                     [fields[k] for k in keys] + [log_id])


def delete_log(log_id: int) -> dict | None:
    """删除日志，连同它的照片记录一起返回，方便清文件。"""
    row = get_log(log_id)
    if not row:
        return None
    with get_conn() as conn:
        conn.execute("DELETE FROM travel_photos WHERE log_id = ?", (log_id,))
        conn.execute("DELETE FROM travel_logs WHERE id = ?", (log_id,))
    return row


# ---------------- 照片 ----------------
def photos_of(log_id: int) -> list[dict]:
    with get_conn() as conn:
        return [_row_to_dict(p) for p in conn.execute(
            "SELECT * FROM travel_photos WHERE log_id = ? ORDER BY sort, id",
            (log_id,))]


def add_photos(log_id: int, paths: list[str]) -> int:
    """给一条日志追加若干张照片，返回实际写入的数量。"""
    paths = [p for p in paths if p]
    if not paths:
        return 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        base = conn.execute("SELECT COALESCE(MAX(sort), -1) FROM travel_photos"
                            " WHERE log_id = ?", (log_id,)).fetchone()[0]
        for i, p in enumerate(paths):
            conn.execute(
                "INSERT INTO travel_photos (log_id, image, caption, sort, "
                "created_at) VALUES (?, ?, '', ?, ?)",
                (log_id, p, base + 1 + i, now))
        first = conn.execute("SELECT image FROM travel_photos WHERE log_id = ?"
                             " ORDER BY sort, id LIMIT 1", (log_id,)).fetchone()
        if first:
            conn.execute("UPDATE travel_logs SET image = ? WHERE id = ?",
                         (first[0], log_id))
    return len(paths)


def delete_photo(photo_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM travel_photos WHERE id = ?",
                           (photo_id,)).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        conn.execute("DELETE FROM travel_photos WHERE id = ?", (photo_id,))
        first = conn.execute("SELECT image FROM travel_photos WHERE log_id = ?"
                             " ORDER BY sort, id LIMIT 1", (d["log_id"],)).fetchone()
        conn.execute("UPDATE travel_logs SET image = ? WHERE id = ?",
                     (first[0] if first else "", d["log_id"]))
        return d


def photo_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM travel_photos").fetchone()[0]


def stats() -> dict:
    """统计：去过几个地方 / 几座城市 / 多少张照片。"""
    items = list_logs()
    cities = {(t.get("city") or "").strip() for t in items}
    cities.discard("")
    return {"total": len(items), "cities": len(cities),
            "photos": photo_count()}
