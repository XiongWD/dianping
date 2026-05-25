"""
大众点评 — 数据采集管理
SQLite 存储：截图记录、VL标注结果、采集状态
"""
import sqlite3
import json
import hashlib
import threading
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "output" / "collect.db"

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

_lock = threading.Lock()
_conn = None

def get_db():
    global _conn
    with _lock:
        if _conn is None:
            _conn = _get_conn()
            _init_db(_conn)
    return _conn

def _init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            page_type TEXT DEFAULT 'unknown',
            description TEXT DEFAULT '',
            node_count INTEGER DEFAULT 0,
            ui_tree TEXT DEFAULT '[]',
            img_hash TEXT,
            file_size INTEGER,
            width INTEGER,
            height INTEGER,
            status TEXT DEFAULT 'pending',  -- pending/annotating/done/error
            vl_result TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            annotated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS collect_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type TEXT,  -- homepage/shop_detail/search/...
            total_shots INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',  -- running/done
            started_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_status ON screenshots(status);
        CREATE INDEX IF NOT EXISTS idx_page_type ON screenshots(page_type);
        CREATE INDEX IF NOT EXISTS idx_hash ON screenshots(img_hash);
    """)
    conn.commit()

def record_screenshot(filename, description="", node_count=0, ui_tree="[]",
                      img_hash="", file_size=0, width=0, height=0):
    """记录一张截图，返回记录 id。如果 hash 重复则跳过。"""
    db = get_db()
    # 检查重复
    if img_hash:
        dup = db.execute("SELECT id FROM screenshots WHERE img_hash=?", (img_hash,)).fetchone()
        if dup:
            return dup["id"], True  # 重复
    try:
        cur = db.execute(
            """INSERT OR IGNORE INTO screenshots
            (filename, description, node_count, ui_tree, img_hash, file_size, width, height, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (filename, description, node_count, ui_tree, img_hash, file_size, width, height)
        )
        db.commit()
        rid = cur.lastrowid
        return rid, False
    except sqlite3.IntegrityError:
        return None, True

def update_vl_result(filename, vl_result):
    """更新 VL 标注结果"""
    db = get_db()
    db.execute(
        """UPDATE screenshots SET vl_result=?, status='done', annotated_at=datetime('now')
        WHERE filename=?""",
        (json.dumps(vl_result, ensure_ascii=False), filename)
    )
    db.execute(
        """UPDATE screenshots SET page_type=? WHERE filename=?""",
        (vl_result.get("page_type", "unknown"), filename)
    )
    db.commit()

def mark_annotating(filename):
    db = get_db()
    db.execute("UPDATE screenshots SET status='annotating' WHERE filename=?", (filename,))
    db.commit()

def get_stats():
    """采集统计"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
    by_status = dict(db.execute(
        "SELECT status, COUNT(*) FROM screenshots GROUP BY status"
    ).fetchall())
    by_page = dict(db.execute(
        "SELECT page_type, COUNT(*) FROM screenshots GROUP BY page_type"
    ).fetchall())
    return {"total": total, "by_status": by_status, "by_page": by_page}

def get_pending(limit=10):
    """获取待标注的截图"""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM screenshots WHERE status='pending' ORDER BY id LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

def img_hash_from_bytes(data):
    """计算图片 perceptual hash 的简化版（MD5）"""
    return hashlib.md5(data).hexdigest()
