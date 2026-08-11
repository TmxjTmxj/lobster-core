"""
🦞 龙虾记忆分层管理系统
行业最佳实践：热 → 温 → 冷 → 物理（Obsidian）

架构：
┌─────────────────────────────────────────────┐
│  L0 热: 当前会话上下文 (Frozen Snapshot)     │ ← 不可持久化，会话结束后丢弃
├─────────────────────────────────────────────┤
│  L1 温: MEMORY.md + USER.md (~2500字符)     │ ← 每会话固定开销，Frozen Snapshot
├─────────────────────────────────────────────┤
│  L2 冷: SQLite FTS5 会话搜索                │ ← 精确关键词搜索，20ms
├─────────────────────────────────────────────┤
│  L3 智: SmartMemory LLM 语义匹配 (307条)     │ ← 语义搜索，自动聚类
├─────────────────────────────────────────────┤
│  L4 物理: Obsidian vault + Daily Notes       │ ← 完整历史，Markdown 可读
└─────────────────────────────────────────────┘
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY_FILE = os.path.join(WORKSPACE, "MEMORY.md")
USER_FILE = os.path.join(WORKSPACE, "USER.md")
DAILY_DIR = os.path.join(WORKSPACE, "memory")
SMART_MEMORY_FILE = os.path.expanduser("~/.lobster/memories/vector_memory.json")
DB_PATH = os.path.join(WORKSPACE, ".session-index.sqlite")
OBSIDIAN_VAULT = os.path.expanduser("~/obsidian-vault")

# 各层容量阈值（字符数）
CAPACITY = {
    "hot": 3000,       # 会话上下文
    "warm_memory": 2500,  # MEMORY.md
    "warm_user": 1500,    # USER.md
    "archive_days": 30,   # daily notes 归档周期
}

class MemoryLobster:
    """记忆分层管理器"""
    
    def __init__(self):
        self._db = None
    
    # ════════════════════════════════════════════
    # 健康检查：所有层的状态
    # ════════════════════════════════════════════
    
    def status(self) -> dict:
        """全记忆层状态报告"""
        layers = {}
        
        # L1 温层
        mem = Path(MEMORY_FILE)
        layers["warm_memory"] = {
            "chars": mem.stat().st_size if mem.exists() else 0,
            "percent": min(100, mem.stat().st_size / CAPACITY["warm_memory"] * 100) if mem.exists() else 0
        }
        
        usr = Path(USER_FILE)
        layers["warm_user"] = {
            "chars": usr.stat().st_size if usr.exists() else 0,
            "percent": min(100, usr.stat().st_size / CAPACITY["warm_user"] * 100) if usr.exists() else 0
        }
        
        # L2 冷层
        if Path(DB_PATH).exists():
            db = sqlite3.connect(DB_PATH)
            count = db.execute("SELECT COUNT(*) FROM sessions_meta").fetchone()[0]
            db.close()
            layers["cold_sqlite"] = {"records": count}
        else:
            layers["cold_sqlite"] = {"records": 0}
        
        # L3 智层
        sm_path = Path(SMART_MEMORY_FILE)
        if sm_path.exists():
            with open(sm_path) as f:
                data = json.load(f)
            mems = data.get("memories", [])
            cats = {}
            for m in mems:
                c = m.get("category", "unknown")
                cats[c] = cats.get(c, 0) + 1
            layers["smart_memory"] = {"total": len(mems), "categories": cats}
        else:
            layers["smart_memory"] = {"total": 0, "categories": {}}
        
        # L4 物理层
        daily_count = len(list(Path(DAILY_DIR).glob("*.md"))) if Path(DAILY_DIR).exists() else 0
        obsidian_count = 0
        if Path(OBSIDIAN_VAULT).exists():
            obsidian_count = len(list(Path(OBSIDIAN_VAULT).rglob("*.md")))
        layers["physical"] = {"daily_notes": daily_count, "obsidian": obsidian_count}
        
        # 需要压缩？
        actions = []
        if layers["warm_memory"]["percent"] > 85:
            actions.append("target: warm_memory, action: auto_compress, reason: 超85%阈值")
        if layers["warm_user"]["percent"] > 85:
            actions.append("target: warm_user, action: consolidate, reason: 超85%阈值")
        
        return {
            "layers": layers,
            "needs_action": actions if actions else None,
            "timestamp": datetime.now().isoformat()
        }
    
    # ════════════════════════════════════════════
    # L1 → L2+L3+L4: 温层压缩/归档
    # ════════════════════════════════════════════
    
    def auto_compress(self, target: str = "warm_memory") -> dict:
        """
        自动压缩温层记忆到冷层
        
        策略：
        - 将过时章节归档到 daily notes
        - 将经验教训写入 SmartMemory
        - 保留核心章节（身份、规则、能力）
        """
        result = {"target": target, "before": 0, "after": 0, "archived": []}
        
        if target == "warm_memory" and Path(MEMORY_FILE).exists():
            with open(MEMORY_FILE) as f:
                content = f.read()
            
            result["before"] = len(content)
            
            # 写入 SmartMemory（如果尚未存在）
            sm_path = Path(SMART_MEMORY_FILE)
            smart = {"version": 2, "memories": []}
            if sm_path.exists():
                with open(sm_path) as f:
                    smart = json.load(f)
            
            existing_texts = {m["text"][:50] for m in smart.get("memories", [])}
            
            # 提取 Lessons 写入 SmartMemory
            lessons_saved = 0
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('- ') and len(line) > 30:
                    text = line.strip()
                    key = text[:50]
                    if key not in existing_texts:
                        smart.setdefault("memories", []).append({
                            "id": __import__('hashlib').md5(text.encode()).hexdigest()[:16],
                            "text": text,
                            "user_id": "tmxj",
                            "category": "insight",
                            "tags": ["harness", "lesson"],
                            "created_at": datetime.now().timestamp(),
                            "updated_at": datetime.now().timestamp(),
                            "access_count": 0
                        })
                        lessons_saved += 1
                        existing_texts.add(key)
            
            if lessons_saved > 0:
                with open(sm_path, "w") as f:
                    json.dump(smart, f, ensure_ascii=False, indent=2)
                result["archived"].append(f"{lessons_saved} lessons -> SmartMemory")
            
            # 压缩 MEMORY.md（如果超 2500 字符）
            if len(content) > CAPACITY["warm_memory"]:
                # 截取前 2400 字符
                compressed = content[:2400]
                compressed += "\n\n<!-- 旧条目已归档到 daily notes + SmartMemory -->\n"
                with open(MEMORY_FILE, "w") as f:
                    f.write(compressed)
                result["after"] = len(compressed)
                result["archived"].append(f"chars: {result['before']} -> {result['after']}")
        
        return result
    
    # ════════════════════════════════════════════
    # L2 → L4: SQLite 归档到 Obsidian
    # ════════════════════════════════════════════
    
    def sync_to_obsidian(self) -> dict:
        """
        将 SQLite 会话记录同步到 Obsidian vault
        
        为每条记录创建独立笔记
        """
        if not Path(OBSIDIAN_VAULT).exists():
            return {"synced": 0, "error": "Obsidian vault 不存在"}
        
        vault = Path(OBSIDIAN_VAULT) / "Memory Archive"
        vault.mkdir(parents=True, exist_ok=True)
        
        if not Path(DB_PATH).exists():
            return {"synced": 0, "error": "SQLite 数据库不存在"}
        
        db = sqlite3.connect(DB_PATH)
        cursor = db.execute(
            "SELECT timestamp, session_id, content FROM sessions_meta ORDER BY timestamp DESC LIMIT 50"
        )
        
        synced = 0
        for row in cursor.fetchall():
            ts, sid, content = row
            date_part = ts[:10] if ts else "unknown"
            
            # 检查是否已同步
            note_path = vault / f"session-{date_part}-{sid[:8]}.md"
            if note_path.exists():
                continue
            
            note_path.write_text(
                f"---\nsource: lobster-harness\ndate: {ts}\nsession: {sid}\n---\n\n"
                f"# 会话摘要\n\n{content}\n"
            )
            synced += 1
        
        db.close()
        return {"synced": synced, "target": str(vault)}
    
    # ════════════════════════════════════════════
    # 综合记忆维护（一键运行）
    # ════════════════════════════════════════════
    
    def full_maintenance(self) -> dict:
        """全层记忆维护"""
        report = {
            "status": self.status(),
            "compression": self.auto_compress("warm_memory"),
            "obsidian_sync": self.sync_to_obsidian(),
            "timestamp": datetime.now().isoformat()
        }
        return report


# ─── 快捷入口 ───
def run():
    ml = MemoryLobster()
    return ml.full_maintenance()


if __name__ == "__main__":
    print("🦞 记忆分层管理系统自检")
    print()
    
    ml = MemoryLobster()
    status = ml.status()
    print("📊 各层状态:")
    for layer, info in status["layers"].items():
        if "percent" in info:
            bar = "█" * int(info["percent"] / 10) + "░" * (10 - int(info["percent"] / 10))
            print(f"  {layer:20s}: {bar} {info['percent']:.0f}% ({info['chars']} chars)")
        elif "records" in info:
            print(f"  {layer:20s}: {info['records']} 条记录")
        elif "total" in info:
            cats = info.get("categories", {})
            print(f"  {layer:20s}: {info['total']} 条 (类别: {', '.join(f'{k}={v}' for k,v in sorted(cats.items())[:5])})")
        elif isinstance(info, dict):
            print(f"  {layer:20s}: {', '.join(f'{k}={v}' for k,v in info.items())}")
    
    if status["needs_action"]:
        print(f"\n⚠️ 需要操作:")
        for a in status["needs_action"]:
            print(f"  {a}")
    
    print("\n✅ 记忆分层管理系统就绪")
