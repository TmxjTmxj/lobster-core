#!/usr/bin/env python3
"""龙虾自动记忆系统 - 每次交互自动记录"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_DIR = WORKSPACE / "memory"
OBSIDIAN_VAULT = Path.home() / "Documents" / "Obsidian" / "main"
STATE_FILE = Path.home() / ".lobster" / "memory_state.json"

class AutoMemory:
    """自动记忆系统 - 每次交互自动触发"""
    
    def __init__(self):
        self.state = self._load_state()
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"last_save": None, "total_interactions": 0, "key_facts": []}
    
    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def record_interaction(self, user_msg: str, bot_msg: str, context: str = ""):
        """记录一次交互 - 自动提取关键信息"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        
        # 1. 保存到每日笔记
        self._save_daily(date_str, time_str, user_msg, bot_msg)
        
        # 2. 同步到 Obsidian
        self._sync_obsidian(date_str, time_str, user_msg, bot_msg)
        
        # 3. 提取关键信息
        key_info = self._extract_key(user_msg, bot_msg, context)
        if key_info:
            self._save_key_fact(date_str, time_str, key_info)
        
        # 4. 更新状态
        self.state["last_save"] = now.isoformat()
        self.state["total_interactions"] += 1
        self._save_state()
    
    def _save_daily(self, date: str, time: str, user_msg: str, bot_msg: str):
        """保存到每日笔记"""
        daily_file = MEMORY_DIR / f"{date}.md"
        
        if not daily_file.exists():
            daily_file.write_text(f"# {date} 对话记录\n\n", encoding="utf-8")
        
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {time}\n")
            f.write(f"**用户**: {user_msg[:200]}\n\n")
            f.write(f"**龙虾**: {bot_msg[:200]}\n\n")
    
    def _sync_obsidian(self, date: str, time: str, user_msg: str, bot_msg: str):
        """同步到 Obsidian vault"""
        obsidian_file = OBSIDIAN_VAULT / f"龙虾对话-{date}.md"
        
        if not obsidian_file.exists():
            obsidian_file.write_text(
                f"---\ntags: [龙虾, 对话, {date}]\n---\n\n# 龙虾对话 {date}\n\n",
                encoding="utf-8"
            )
        
        with open(obsidian_file, "a", encoding="utf-8") as f:
            f.write(f"## {time}\n")
            f.write(f"- **用户**: {user_msg[:150]}\n")
            f.write(f"- **龙虾**: {bot_msg[:150]}\n\n")
    
    def _extract_key(self, user_msg: str, bot_msg: str, context: str) -> dict:
        """提取关键信息"""
        key_info = {"type": "", "content": ""}
        
        combined = user_msg + " " + bot_msg
        
        # 偏好检测
        if any(w in combined for w in ["喜欢", "爱好", "偏好", "习惯"]):
            key_info = {"type": "偏好", "content": user_msg[:100]}
        
        # 事实检测
        elif any(w in combined for w in ["是", "有", "在", "叫"]):
            if len(user_msg) > 10:
                key_info = {"type": "事实", "content": user_msg[:100]}
        
        # 情感检测
        elif any(w in combined for w in ["开心", "难过", "生气", "喜欢你"]):
            key_info = {"type": "情感", "content": user_msg[:100]}
        
        # 技能学习
        elif any(w in combined for w in ["学会", "知道", "了解", "技能"]):
            key_info = {"type": "学习", "content": bot_msg[:100]}
        
        return key_info if key_info["type"] else None
    
    def _save_key_fact(self, date: str, time: str, key_info: dict):
        """保存关键信息到长期记忆"""
        memory_file = WORKSPACE / "MEMORY.md"
        
        if not memory_file.exists():
            memory_file.write_text("# MEMORY.md\n\n", encoding="utf-8")
        
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {date} {time} [{key_info['type']}]\n")
            f.write(f"{key_info['content']}\n")
        
        # 更新状态
        self.state["key_facts"].append({
            "date": date,
            "time": time,
            "type": key_info["type"],
            "content": key_info["content"]
        })
        # 只保留最近100条
        self.state["key_facts"] = self.state["key_facts"][-100:]

# 全局实例
auto_memory = AutoMemory()

def record(user_msg: str, bot_msg: str, context: str = ""):
    """外部调用接口"""
    auto_memory.record_interaction(user_msg, bot_msg, context)

if __name__ == "__main__":
    # 测试
    record("主人你好", "宝贝，今天帮你装了好几个技能", "日常问候")
    record("我喜欢你叫我主人", "好的主人~", "偏好表达")
    record("这个代码怎么写", "我来帮你写", "技术问题")
    
    print("✅ 自动记忆系统测试完成")
    print(f"总交互: {auto_memory.state['total_interactions']}")
    print(f"关键事实: {len(auto_memory.state['key_facts'])} 条")
