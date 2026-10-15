"""客行录 · 旅程票根数据层

和其余模块共用同一个 SQLite 文件（data/yingjianlu.db），多一张 tickets 表：
机票、火车票都算一张"票根"，可以手动填写出发地 / 目的地纪念，
也可以从第三方 App 截图 AI 识别导入。

vehicle 取值：飞机 / 高铁 / 火车（用于配色和图标）。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from database import DB_PATH, get_conn

TICKET_DIR = os.path.join(os.path.dirname(DB_PATH), "tickets")   # 票面 / 截图图片

FIELDS = ["vehicle", "from_city", "to_city", "depart_date", "depart_time",
          "arrive_time", "code", "seat", "gate", "passenger", "passenger_id",
          "price", "note", "image", "style"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle     TEXT DEFAULT '飞机',   -- 飞机 / 高铁 / 火车
    from_city   TEXT,                  -- 出发地（城市 / 车站 / 机场）
    to_city     TEXT,                  -- 目的地
    depart_date TEXT,                  -- 出发日期 YYYY-MM-DD
    depart_time TEXT,                  -- 出发时间
    arrive_time TEXT,                  -- 到达时间
    code        TEXT,                  -- 航班号 / 车次
    seat        TEXT,                  -- 座位 / 舱位
    gate        TEXT,                  -- 登机口 / 检票口
    passenger   TEXT,                  -- 乘客
    passenger_id TEXT,                 -- 乘客证件号（票面上打码显示）
    price       TEXT,                  -- 票价（铁路报销凭证票面要印）
    note        TEXT,                  -- 备注
    image       TEXT,                  -- 票面 / 截图本地路径
    style       TEXT DEFAULT 'classic', -- 每张机票独立保存的票面样式
    created_at  TEXT
);
"""


def init_db() -> None:
    """建票根表（幂等）；老库自动补 gate / price 列。"""
    os.makedirs(TICKET_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(CREATE_SQL)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tickets)")}
        if "gate" not in cols:
            conn.execute("ALTER TABLE tickets ADD COLUMN gate TEXT DEFAULT ''")
        if "price" not in cols:
            conn.execute("ALTER TABLE tickets ADD COLUMN price TEXT DEFAULT ''")
        if "passenger_id" not in cols:
            conn.execute(
                "ALTER TABLE tickets ADD COLUMN passenger_id TEXT DEFAULT ''")
        if "style" not in cols:
            conn.execute("ALTER TABLE tickets ADD COLUMN style TEXT DEFAULT 'rose'")


init_db()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_tickets() -> list[dict]:
    """全部票根，按出发日期倒序（没有日期的排后面）。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY depart_date = '' ASC,"
            " depart_date DESC, id DESC")
        return [_row_to_dict(r) for r in rows]


def get_ticket(ticket_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _row_to_dict(row) if row else None


def add_ticket(**fields) -> int:
    data = {k: (str(fields.get(k)).strip() if fields.get(k) is not None else "")
            for k in FIELDS}
    if not data["vehicle"]:
        data["vehicle"] = "飞机"
    if not data["style"]:
        data["style"] = "classic"
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO tickets ({', '.join(FIELDS)}, created_at) "
            f"VALUES ({', '.join('?' for _ in FIELDS)}, ?)",
            [data[k] for k in FIELDS] + [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        )
        return int(cur.lastrowid)


def update_ticket(ticket_id: int, **fields) -> None:
    keys = [k for k in FIELDS if k in fields]
    if not keys:
        return
    sets = ", ".join(f"{k} = ?" for k in keys)
    with get_conn() as conn:
        conn.execute(f"UPDATE tickets SET {sets} WHERE id = ?",
                     [str(fields[k]).strip() if fields[k] is not None else ""
                      for k in keys] + [ticket_id])


def delete_ticket(ticket_id: int) -> dict | None:
    """删除票根，返回被删的行（便于调用方清理图片文件）。"""
    row = get_ticket(ticket_id)
    if not row:
        return None
    with get_conn() as conn:
        conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    return row


def stats() -> dict:
    """统计：总次数 / 涉及城市数 / 今年次数。"""
    tickets = list_tickets()
    cities: set[str] = set()
    year = datetime.now().strftime("%Y")
    this_year = 0
    for t in tickets:
        for key in ("from_city", "to_city"):
            if (t.get(key) or "").strip():
                cities.add(t[key].strip())
        if (t.get("depart_date") or "").startswith(year):
            this_year += 1
    return {"trips": len(tickets), "cities": len(cities), "this_year": this_year}
