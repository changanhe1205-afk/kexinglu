"""客行录 · 本地数据层

使用 SQLite 单文件数据库，整个过程完全离线，不需要联网。
一条观影记录包含的字段：
    标题 title、类别 kind（电影 / 剧集）、类型题材 genre、
    观看日期 watch_date、评分 rating（0~5 星）、个人感想 review、
    海报路径 poster（可选，本地图片）
"""

from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import config

APP_NAME = "客行录"


def _base_dir() -> str:
    """数据存放目录：默认 %LOCALAPPDATA%\\客行录，
    用户可以在「我的」页里改成别的盘（配置存在 %APPDATA% 下）。
    """
    return config.data_dir()


BASE_DIR = _base_dir()
POSTER_DIR = os.path.join(BASE_DIR, "posters")   # 海报图片存放目录
DB_PATH = os.path.join(BASE_DIR, "yingjianlu.db")


def reload_paths() -> None:
    """数据目录换了之后重新算一遍路径。

    其它模块（票根 / 美食 / 旅行 / 聊天 / 背景）的目录都是从
    DB_PATH 推出来的，storage.py 会把它们一起刷新。
    """
    global BASE_DIR, POSTER_DIR, DB_PATH
    BASE_DIR = _base_dir()
    POSTER_DIR = os.path.join(BASE_DIR, "posters")
    DB_PATH = os.path.join(BASE_DIR, "yingjianlu.db")

# 建表 SQL：IF NOT EXISTS 保证重复启动不会报错
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,                 -- 片名
    kind       TEXT NOT NULL DEFAULT '电影',   -- 类别：电影 / 剧集
    genre      TEXT,                          -- 类型题材，如：悬疑 / 科幻
    watch_date TEXT,                          -- 观看日期，格式 YYYY-MM-DD
    rating     INTEGER NOT NULL DEFAULT 0,    -- 评分，0~5 星
    review     TEXT,                          -- 个人感想
    poster     TEXT,                          -- 海报图片本地路径，可为空
    created_at TEXT                           -- 记录创建时间
);
"""


@contextmanager
def get_conn():
    """获取数据库连接，row_factory 让查询结果可以像字典一样按列名取值。

    注意：`with sqlite3.connect(...)` 只提交事务、**不会关连接**，
    连接句柄会一直占着 yingjianlu.db。所以这里自己做上下文管理器，
    退出时一定 close——否则换个数据目录复制文件时可能被占用而失败。
    """
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(POSTER_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """初始化：建库建表。老数据库缺列时自动补齐（poster）。"""
    with get_conn() as conn:
        conn.execute(CREATE_SQL)
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(movies)")}
        if "poster" not in cols:
            conn.execute("ALTER TABLE movies ADD COLUMN poster TEXT")


def list_movies(keyword: str = "", kind: str = "全部") -> list[dict]:
    """按条件查询：keyword 匹配片名/题材/感想，kind 为"全部"时不筛选类别。"""
    sql = "SELECT * FROM movies WHERE 1 = 1"
    args: list[str] = []
    if kind and kind != "全部":
        sql += " AND kind = ?"
        args.append(kind)
    if keyword:
        sql += " AND (title LIKE ? OR genre LIKE ? OR review LIKE ?)"
        like = f"%{keyword}%"
        args.extend([like, like, like])
    sql += " ORDER BY date(created_at) DESC, id DESC"  # 最新添加的排最前

    with get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, args)]


def get_movie(movie_id: int) -> Optional[dict]:
    """按 id 取单条记录，不存在时返回 None。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
        return dict(row) if row else None


def add_movie(data: dict) -> int:
    """新增一条收藏，返回自增 id。"""
    now = datetime.now().isoformat(timespec="seconds")
    sql = """
        INSERT INTO movies (title, kind, genre, watch_date, rating, review, poster, created_at)
        VALUES (:title, :kind, :genre, :watch_date, :rating, :review, :poster, :created_at)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, dict(data, created_at=now))
        return cur.lastrowid


def update_movie(movie_id: int, data: dict) -> None:
    """更新指定 id 的记录。"""
    sql = """
        UPDATE movies
           SET title = :title, kind = :kind, genre = :genre,
               watch_date = :watch_date, rating = :rating,
               review = :review, poster = :poster
         WHERE id = :id
    """
    with get_conn() as conn:
        conn.execute(sql, dict(data, id=movie_id))


def delete_movie(movie_id: int) -> Optional[dict]:
    """删除记录，并把被删数据返回给调用方（便于清理它的海报文件）。"""
    movie = get_movie(movie_id)
    if not movie:
        return None
    with get_conn() as conn:
        conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    return movie


def stats() -> dict:
    """顶部统计：总数、电影数、剧集数。"""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        movie = conn.execute("SELECT COUNT(*) FROM movies WHERE kind = '电影'").fetchone()[0]
        tv = conn.execute("SELECT COUNT(*) FROM movies WHERE kind = '剧集'").fetchone()[0]
    return {"total": total, "电影": movie, "剧集": tv}
