"""db.py — 整改通知历史记录（SQLite 数据库）

SQLite 是 Python 自带的轻量数据库，不需要安装任何东西。
数据存在一个 .db 文件里，就像 Excel 但可以写代码查询。
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# 数据库文件放在当前目录，名叫 notices.db
DB_PATH = Path(__file__).parent / "notices.db"


def get_db():
    """连接到数据库文件"""
    conn = sqlite3.connect(str(DB_PATH))
    # row_factory 让查询结果能像字典一样用 row["project"] 取值
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表——只执行一次，表已存在就跳过"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,   -- 自增编号，自动生成
            created_at   TEXT    NOT NULL,                     -- 创建时间，如 "2026-07-20 14:30:00"
            project      TEXT    DEFAULT '',                   -- 项目名称，如 "上海视源"
            source       TEXT    DEFAULT 'text',               -- 来源: "text" 文本输入 / "photos" 照片上传
            hazards      TEXT    DEFAULT '[]',                 -- 隐患列表，JSON 格式存，如 '["电线泡水","高处未系"]'
            notice       TEXT    DEFAULT '',                   -- 通知全文
            photo_count  INTEGER DEFAULT 0                    -- 照片数量（文本模式就是 0）
        )
    """)
    conn.commit()  # 保存改动
    conn.close()


def save_notice(project: str, source: str, hazards: list, notice: str, photo_count: int = 0):
    """保存一份通知。

    参数:
        project:     项目名，如 "上海视源"
        source:      来源，"text" 或 "photos"
        hazards:     隐患列表，如 ["电线泡水", "高处未系安全带"]
        notice:      通知全文
        photo_count: 照片数量
    """
    conn = get_db()
    conn.execute(
        """INSERT INTO notices (created_at, project, source, hazards, notice, photo_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project,
            source,
            json.dumps(hazards, ensure_ascii=False),  # 列表 → JSON 字符串
            notice,
            photo_count,
        ),
    )
    conn.commit()
    conn.close()


def list_notices(limit: int = 20):
    """查最近 N 条记录。

    返回示例:
        [{"id": 3, "project": "上海视源", "created_at": "2026-07-20 14:30:00", ...},
         {"id": 2, "project": "测试项目", "created_at": "2026-07-19 09:15:00", ...}]
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notices ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    # 把 Row 对象转成普通字典
    return [dict(row) for row in rows]


def get_notice(notice_id: int):
    """查单条记录详情，返回字典或 None"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM notices WHERE id = ?",
        (notice_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
