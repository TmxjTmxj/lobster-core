"""
🔷 赫尔墨斯 — 超级记忆系统 v3
移植自 🦞 龙虾的 SuperMemory
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path.home() / ".lobster"
DB_FILE = MEMORY_DIR / "lobster_memory.db"


class HermesMemory:
    """赫尔墨斯记忆系统"""

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_FILE))
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL DEFAULT 'general', content TEXT NOT NULL, category TEXT DEFAULT 'general', importance INTEGER DEFAULT 3, tags TEXT DEFAULT '', source TEXT DEFAULT '', created REAL, accessed INTEGER DEFAULT 0, last_accessed REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, source TEXT DEFAULT '', timestamp REAL, emotion TEXT DEFAULT '', thought TEXT DEFAULT '')")
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, category, tags, content=memories, content_rowid=id)")
            # 触发器：新记录/删除自动同步 FTS 索引（否则 search 永远查不到）
            c.execute("CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN "
                      "INSERT INTO memories_fts(rowid, content, category, tags) VALUES (new.id, new.content, new.category, new.tags); END")
            c.execute("CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN "
                      "INSERT INTO memories_fts(memories_fts, rowid, content, category, tags) VALUES ('delete', old.id, old.content, old.category, old.tags); END")
        except Exception:
            pass  # FTS5 may not be available, fall back to LIKE search
        self.conn.commit()

    def store(self, content: str, category: str = "general",
              importance: int = 3, tags: str = "", source: str = ""):
        importance = max(1, min(5, importance))
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO memories (type, content, category, importance, tags, source, created) VALUES ('text', ?, ?, ?, ?, ?, ?)",
            (content, category, importance, tags, source, datetime.now().timestamp())
        )
        mem_id = c.lastrowid
        # 同步写入 FTS 索引（external-content 表不会自动同步）
        try:
            c.execute("INSERT INTO memories_fts(rowid, content, category, tags) VALUES (?, ?, ?, ?)",
                      (mem_id, content, category, tags))
        except Exception:
            pass
        self.conn.commit()
        return mem_id

    def search(self, query: str, limit: int = 10, min_importance: int = 1) -> list:
        results = []
        c = self.conn.cursor()
        if not query:
            try:
                c.execute(
                    "SELECT id, content, category, importance, tags, created, accessed FROM memories WHERE importance >= ? ORDER BY created DESC LIMIT ?",
                    (min_importance, limit)
                )
                results = c.fetchall()
            except:
                pass
        else:
            try:
                c.execute(
                    "SELECT m.id, m.content, m.category, m.importance, m.tags, m.created, m.accessed FROM memories_fts f JOIN memories m ON f.rowid = m.id WHERE memories_fts MATCH ? AND m.importance >= ? ORDER BY rank LIMIT ?",
                    (query, min_importance, limit)
                )
                results = c.fetchall()
            except:
                results = []
            # FTS5 对中文默认不分词（整句当单个 token），MATCH 命中不了 → LIKE 兜底
            if not results:
                try:
                    c.execute(
                        "SELECT id, content, category, importance, tags, created, accessed FROM memories WHERE content LIKE ? AND importance >= ? ORDER BY created DESC LIMIT ?",
                        (f"%{query}%", min_importance, limit)
                    )
                    results = c.fetchall()
                except:
                    pass
        formatted = []
        for r in results:
            formatted.append({
                "id": r[0], "content": r[1], "category": r[2],
                "importance": r[3], "tags": r[4],
                "created": datetime.fromtimestamp(r[5]).isoformat() if r[5] else "",
                "accessed": r[6],
            })
            c.execute("UPDATE memories SET accessed = accessed + 1, last_accessed = ? WHERE id = ?",
                     (datetime.now().timestamp(), r[0]))
        self.conn.commit()
        return formatted

    def store_interaction(self, role: str, content: str, source: str = "",
                          emotion: str = "", thought: str = ""):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO interactions (role, content, source, timestamp, emotion, thought) VALUES (?, ?, ?, ?, ?, ?)",
            (role, content[:2000], source, datetime.now().timestamp(), emotion, thought)
        )
        self.conn.commit()

    def get_recent_interactions(self, limit: int = 20) -> list:
        c = self.conn.cursor()
        c.execute("SELECT role, content, source, timestamp, emotion FROM interactions ORDER BY id DESC LIMIT ?", (limit,))
        results = []
        for r in c.fetchall():
            results.append({
                "role": r[0], "content": r[1][:300], "source": r[2],
                "time": datetime.fromtimestamp(r[3]).strftime("%H:%M") if r[3] else "",
                "emotion": r[4],
            })
        results.reverse()
        return results

    def get_stats(self) -> dict:
        c = self.conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM memories")
            memories = c.fetchone()[0]
        except Exception:
            memories = 0
        try:
            c.execute("SELECT MAX(created) FROM memories")
            last_mem = c.fetchone()[0]
        except Exception:
            last_mem = None
        try:
            c.execute("SELECT COUNT(*) FROM interactions")
            interactions = c.fetchone()[0]
        except Exception:
            interactions = 0
        return {
            "memories": memories,
            "interactions": interactions,
            "last_memory": datetime.fromtimestamp(last_mem).isoformat() if last_mem else "无",
        }

    def close(self):
        self.conn.close()
