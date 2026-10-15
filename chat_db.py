"""客行录 · 聊天模块数据层

和影视模块共用同一个 SQLite 文件（data/yingjianlu.db），只是多了两张表：
    conversations：一段对话（含对方头像、聊天背景）
    messages：这条对话里的每一句消息

所有的排序都用 sort 字段，方便用户手动调整消息顺序。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Optional

from database import DB_PATH, get_conn

CHAT_DIR = os.path.join(os.path.dirname(DB_PATH), "chat")        # 头像 / 背景图片
EXPORT_DIR = os.path.join(os.path.dirname(DB_PATH), "exports")   # 导出的长图

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,                    -- 对方昵称 / 备注
    subtitle    TEXT,                             -- 标题栏下方小字（如"对方正在输入…"）
    avatar      TEXT,                             -- 对方头像本地路径
    my_avatar   TEXT,                             -- 自己头像本地路径（可选）
    background  TEXT,                             -- 聊天背景图本地路径（可选）
    category    TEXT DEFAULT '未分类',             -- 分类：家人 / 朋友 / 工作 …
    theme       TEXT DEFAULT 'lemon',             -- 我的气泡配色：lemon 柔柠黄 / mist 雾霭蓝
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,             -- 属于哪段对话
    side            INTEGER NOT NULL DEFAULT 0,   -- 0 = 我，1 = 对方
    content         TEXT NOT NULL,                -- 消息内容
    time_label      TEXT,                         -- 气泡上方居中的时间文字，如 "21:30"
    msg_date        TEXT,                         -- 消息日期 YYYY-MM-DD，用于按日期查找 / 分组
    show_time       INTEGER NOT NULL DEFAULT 0,   -- 是否显示这条上方的时间分隔
    sort            INTEGER NOT NULL DEFAULT 0,   -- 顺序
    created_at      TEXT
);
"""


def init_db() -> None:
    """建聊天相关的表（幂等）。"""
    os.makedirs(CHAT_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(CREATE_SQL)
        # 老数据库补列
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(conversations)")}
        if "theme" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN theme TEXT DEFAULT 'lemon'")
        if "category" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN category TEXT DEFAULT '未分类'")

        mcols = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
        if "msg_date" not in mcols:
            conn.execute("ALTER TABLE messages ADD COLUMN msg_date TEXT")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _fetch(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, args)]


# ---------------- 会话 ----------------
def list_categories() -> list[str]:
    """所有已用过的分类名（去重、按使用先后）。"""
    with get_conn() as conn:
        rows = [r[0] for r in conn.execute(
            "SELECT DISTINCT category FROM conversations "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )]
    return [r or "未分类" for r in rows]


def category_counts() -> dict[str, int]:
    """每个分类下有多少段对话（含"全部"总量），左栏分类标签上显示数字用。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT IFNULL(category, '未分类') AS cat, COUNT(*) AS cnt "
            "FROM conversations GROUP BY cat"
        ).fetchall()
    counts = {row["cat"]: row["cnt"] for row in rows}
    counts["全部"] = sum(counts.values())
    return counts


def list_conversations(category: str = "", keyword: str = "") -> list[dict]:
    """会话列表，按最近一条消息的时间倒序；可按分类 / 关键字过滤。

    每条会话额外带上：
        message_count 消息总数
        last_preview   最后一条消息的文字预览
        last_side      最后一条是谁发的（0 我 / 1 对方）
        last_date      最后一条消息的日期
        date_from / date_to  这段对话跨越的日期范围
    """
    where = []
    args: list = []
    if category and category != "全部":
        where.append("IFNULL(c.category, '未分类') = ?")
        args.append(category)
    if keyword:
        where.append("(c.name LIKE ? OR IFNULL(c.subtitle, '') LIKE ? OR "
                     "EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id "
                     "AND m.content LIKE ?))")
        like = f"%{keyword}%"
        args.extend([like, like, like])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT c.*,
               (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS message_count,
               (SELECT content FROM messages WHERE conversation_id = c.id
                ORDER BY sort DESC, id DESC LIMIT 1) AS last_preview,
               (SELECT side FROM messages WHERE conversation_id = c.id
                ORDER BY sort DESC, id DESC LIMIT 1) AS last_side,
               (SELECT msg_date FROM messages WHERE conversation_id = c.id
                ORDER BY sort DESC, id DESC LIMIT 1) AS last_date,
               (SELECT MIN(msg_date) FROM messages WHERE conversation_id = c.id) AS date_from,
               (SELECT MAX(msg_date) FROM messages WHERE conversation_id = c.id) AS date_to
          FROM conversations c{where_sql}
         ORDER BY datetime(c.created_at) DESC, c.id DESC
    """
    with get_conn() as conn:
        return _fetch(conn, sql, tuple(args))


def get_conversation(conversation_id: int) -> Optional[dict]:
    with get_conn() as conn:
        rows = _fetch(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        return rows[0] if rows else None


def add_conversation(name: str, category: str = "未分类") -> int:
    """新建会话并返回 id。"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (name, category, created_at) VALUES (?, ?, ?)",
            (name, category, _now()),
        )
        return cur.lastrowid


def update_conversation(conversation_id: int, **fields) -> None:
    """更新会话字段（name / subtitle / avatar / my_avatar / background）。"""
    if not fields:
        return
    sets = ", ".join(f"{key} = ?" for key in fields)
    args = list(fields.values()) + [conversation_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE conversations SET {sets} WHERE id = ?", args)


def delete_conversation(conversation_id: int) -> Optional[dict]:
    """删除会话，同时清掉它的所有消息，返回被删会话（便于清理图片）。"""
    conversation = get_conversation(conversation_id)
    if not conversation:
        return None
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return conversation


# ---------------- 消息 ----------------
def list_messages(conversation_id: int) -> list[dict]:
    """按 sort 顺序取出一段对话的所有消息（从头到尾）。"""
    with get_conn() as conn:
        return _fetch(
            conn,
            """SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY sort ASC, id ASC""",
            (conversation_id,),
        )


def search_messages(conversation_id: int, keyword: str = "",
                    date_from: str = "", date_to: str = "") -> list[dict]:
    """在一段对话里按关键字和日期范围查找消息（都为空则返回全部）。"""
    sql = "SELECT * FROM messages WHERE conversation_id = ?"
    args: list = [conversation_id]

    keyword = (keyword or "").strip()
    if keyword:
        sql += " AND content LIKE ?"
        args.append(f"%{keyword}%")

    if date_from:                                  # 支持单日查询（只填一个日期）
        sql += " AND IFNULL(msg_date, '') >= ?"
        args.append(date_from)
    if date_to:
        sql += " AND IFNULL(msg_date, '') <= ?"
        args.append(date_to)

    sql += " ORDER BY sort ASC, id ASC"
    with get_conn() as conn:
        return _fetch(conn, sql, tuple(args))


def _next_sort(conversation_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(sort) FROM messages WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        return (row[0] or 0) + 1


def add_message(conversation_id: int, side: int, content: str,
                time_label: str = "", show_time: bool = False,
                msg_date: str = "") -> int:
    """新增一条消息，自动排在最后；msg_date 为空时记为今天（方便按日期查找）。"""
    if not msg_date:
        msg_date = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO messages
                   (conversation_id, side, content, time_label, msg_date, show_time,
                    sort, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, side, content, time_label, msg_date, int(show_time),
             _next_sort(conversation_id), _now()),
        )
        return cur.lastrowid


def add_messages_bulk(conversation_id: int, parsed: list[dict]) -> int:
    """批量写入导入解析出来的消息（一次提交，长记录也很快）。返回写入条数。"""
    if not parsed:
        return 0
    rows = []
    with get_conn() as conn:
        next_sort = (conn.execute(
            "SELECT COALESCE(MAX(sort), 0) + 1 FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()[0])
        now = _now()
        for msg in parsed:
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            msg_date = msg.get("date") or datetime.now().strftime("%Y-%m-%d")
            rows.append((
                conversation_id, int(msg.get("side") or 1), content,
                msg.get("time_label") or "", msg_date, int(bool(msg.get("show_time"))),
                next_sort, now,
            ))
            next_sort += 1
        conn.executemany(
            """INSERT INTO messages
                   (conversation_id, side, content, time_label, msg_date, show_time,
                    sort, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def count_messages(conversation_id: int) -> int:
    """一段对话的消息总数。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()[0]


def update_message(message_id: int, side: int, content: str,
                   time_label: str = "", show_time: bool = False,
                   msg_date: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE messages
                  SET side = ?, content = ?, time_label = ?, msg_date = ?, show_time = ?
                WHERE id = ?""",
            (side, content, time_label, msg_date, int(show_time), message_id),
        )


def delete_message(message_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))


def clear_messages(conversation_id: int) -> None:
    """清空一段对话里的所有消息（对话本身保留）。"""
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))


def move_message(message_id: int, delta: int) -> None:
    """上移 / 下移：和相邻那条消息交换 sort 值。delta = -1 上移，1 下移。"""
    with get_conn() as conn:
        row = _fetch(conn, "SELECT id, conversation_id, sort FROM messages WHERE id = ?", (message_id,))
        if not row:
            return
        current = row[0]
        target = None
        if delta < 0:
            rows = _fetch(
                conn,
                """SELECT id, sort FROM messages
                    WHERE conversation_id = ? AND sort < ?
                    ORDER BY sort DESC LIMIT 1""",
                (current["conversation_id"], current["sort"]),
            )
        else:
            rows = _fetch(
                conn,
                """SELECT id, sort FROM messages
                    WHERE conversation_id = ? AND sort > ?
                    ORDER BY sort ASC LIMIT 1""",
                (current["conversation_id"], current["sort"]),
            )
        if rows:
            target = rows[0]

        if not target:       # 已经在最前 / 最后了，直接退出
            return

        conn.execute("UPDATE messages SET sort = ? WHERE id = ?", (target["sort"], current["id"]))
        conn.execute("UPDATE messages SET sort = ? WHERE id = ?", (current["sort"], target["id"]))
