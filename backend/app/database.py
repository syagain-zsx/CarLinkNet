"""SQLite 数据库：连接、建表与默认数据播种。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import DB_PATH, DEFAULT_ADMIN
from .security import hash_password

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    rows INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS feature_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dataset_id INTEGER,
    feature_type TEXT NOT NULL,
    dimensions TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS rulesets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    filename TEXT,
    path TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    rule_count INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    mode TEXT NOT NULL,
    dataset_id INTEGER,
    ruleset_id INTEGER,
    use_student INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    message TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    confidence_avg REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    """事务上下文：退出时提交，异常时回滚。"""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(_SCHEMA)
    # 播种默认管理员
    with db() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN["username"],)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
                (
                    DEFAULT_ADMIN["username"],
                    hash_password(DEFAULT_ADMIN["password"]),
                    DEFAULT_ADMIN["display_name"],
                    DEFAULT_ADMIN["role"],
                ),
            )


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
