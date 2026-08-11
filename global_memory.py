"""
🦞 全局记忆系统 v2 - 三合一记忆持久化
smart_memory + SESSION-STATE + Obsidian = 永不丢失
"""

import os, json, datetime, sys
sys.path.insert(0, os.path.dirname(__file__))

from smart_memory import SmartMemory, get_memory
from memory_bridge import SHARED_HISTORY, TAVERN_HISTORY, _load_json

try:
    from obsidian_sync import ObsidianSync
    OBSIDIAN_AVAILABLE = bool(os.path.expanduser("~/Documents/Obsidian/main"))
except:
    OBSIDIAN_AVAILABLE = False

MEMORY_DIR = os.path.expanduser("~/.lobster/memories")
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")


class GlobalMemory:
    """全局记忆 - 三层持久化"""
    
    def __init__(self):
        self.smart = get_memory()
        self.obsidian = ObsidianSync() if OBSIDIAN_AVAILABLE else None
    
    def save(self, text: str, category: str = "general", tags: list = None):
        """保存到所有记忆层"""
        # 1. smart_memory（语义持久化）
        mem_id = self.smart.add(text, category=category, tags=tags or [])
        
        # 2. Obsidian（物理持久化）
        if self.obsidian:
            title = f"{category}-{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
            self.obsidian.write_note(title, text, tags=tags)
        
        return mem_id
    
    def consolidate(self):
        """整理记忆：MEMORY.md + SESSION-STATE + shared_history → Obsidian"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"# 龙虾记忆整理想 - {now}", ""]
        
        # 1. 从smart_memory抽取核心记忆
        core = [m for m in self.smart.memories["memories"] 
                if m.get("category") in ("identity", "user", "preference", "decision")]
        if core:
            lines.append("## 核心记忆")
            for m in core[-20:]:
                lines.append(f"- {m['text']} ({m.get('category','')})")
            lines.append("")
        
        # 2. 从shared_history抽取最近对话
        shared = _load_json(SHARED_HISTORY, [])
        if shared:
            lines.append("## 最近对话")
            for e in shared[-15:]:
                role = "你" if e.get("role")=="user" else "龙虾"
                src = {"tavern":"🍺", "feishu":"💬"}.get(e.get("source",""),"")
                lines.append(f"- {src} {role}: {e.get('content','')[:100]}")
            lines.append("")
        
        # 3. 写入Obsidian
        if self.obsidian:
            self.obsidian.write_note(
                f"记忆整合_{datetime.datetime.now().strftime('%Y%m%d')}",
                "\n".join(lines),
                tags=["龙虾", "记忆整合"]
            )
        
        return "\n".join(lines)
    
    def learn_from_session(self, session_summary: str):
        """会话结束后自动学习关键信息"""
        self.save(session_summary, category="conversation", tags=["对话摘要"])
        
        # 也更新到MEMORY.md
        mem_path = os.path.join(WORKSPACE, "MEMORY.md")
        if os.path.exists(mem_path):
            with open(mem_path, 'a') as f:
                f.write(f"\n## 自动学习 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
                f.write(f"- {session_summary}\n")
    
    def dump_full_context(self):
        """全量上下文 - 用于醒来时重建记忆"""
        parts = []
        
        # smart_memory 核心
        core = [m for m in self.smart.memories["memories"] 
                if m.get("category") in ("identity", "user", "preference", "decision", "conversation")]
        if core:
            parts.append("【核心记忆】")
            for m in core[-10:]:
                parts.append(f"· {m['text']}")
        
        # 共享历史
        shared = _load_json(SHARED_HISTORY, [])
        if shared:
            parts.append("\n【最近互动】")
            for e in shared[-8:]:
                role = "你" if e.get("role")=="user" else "龙虾"
                parts.append(f"· {role}: {e.get('content','')[:80]}")
        
        # 会话状态
        state_path = os.path.join(WORKSPACE, "SESSION-STATE.md")
        if os.path.exists(state_path):
            with open(state_path) as f:
                state = f.read()
            parts.append(f"\n【会话状态】\n{state[:300]}")
        
        return "\n".join(parts)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    gm = GlobalMemory()
    
    if cmd == "status":
        print(f"🦞 全局记忆系统")
        print(f"  smart_memory: {len(gm.smart.memories['memories'])} 条")
        print(f"  obsidian: {'✅' if gm.obsidian else '❌'} {os.path.expanduser('~/Documents/Obsidian/main')}")
        print(f"  workspace: {WORKSPACE}")
        
    elif cmd == "consolidate":
        result = gm.consolidate()
        print("✅ 记忆整合完成")
        print(result[:200] + "...")
        
    elif cmd == "context":
        print(gm.dump_full_context())
        
    elif cmd == "learn":
        text = sys.argv[2] if len(sys.argv) > 2 else "测试学习"
        gm.learn_from_session(text)
        print(f"✅ 已学习: {text[:50]}")
