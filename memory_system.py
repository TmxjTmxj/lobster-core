#!/usr/bin/env python3
"""龙虾记忆系统 - 统一记忆管理"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 路径配置
WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_DIR = WORKSPACE / "memory"
OBSIDIAN_VAULT = Path.home() / "Documents" / "Obsidian" / "main"
LOBSTER_DIR = Path.home() / ".lobster"

class LobsterMemory:
    """龙虾统一记忆系统"""
    
    def __init__(self):
        self.memory_file = WORKSPACE / "MEMORY.md"
        self.daily_dir = MEMORY_DIR
        self.obsidian_vault = OBSIDIAN_VAULT
        
    def save_conversation(self, user_msg: str, bot_msg: str):
        """保存对话到每日笔记"""
        today = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M")
        
        daily_file = self.daily_dir / f"{today}.md"
        
        # 如果文件不存在，创建新文件
        if not daily_file.exists():
            daily_file.write_text(f"# {today} 对话记录\n\n", encoding="utf-8")
        
        # 追加对话
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {time_str}\n")
            f.write(f"**用户**: {user_msg}\n\n")
            f.write(f"**龙虾**: {bot_msg}\n\n")
        
        # 同步到 Obsidian
        self._sync_to_obsidian(today, user_msg, bot_msg)
        
    def _sync_to_obsidian(self, date: str, user_msg: str, bot_msg: str):
        """同步到 Obsidian vault"""
        if not self.obsidian_vault.exists():
            return
            
        obsidian_file = self.obsidian_vault / f"龙虾对话-{date}.md"
        
        if not obsidian_file.exists():
            obsidian_file.write_text(
                f"---\ntags: [龙虾, 对话, {date}]\n---\n\n# 龙虾对话 {date}\n\n",
                encoding="utf-8"
            )
        
        with open(obsidian_file, "a", encoding="utf-8") as f:
            f.write(f"## {datetime.now().strftime('%H:%M')}\n")
            f.write(f"- **用户**: {user_msg}\n")
            f.write(f"- **龙虾**: {bot_msg[:200]}...\n\n")
    
    def extract_key_info(self, text: str) -> dict:
        """从文本中提取关键信息"""
        key_info = {
            "topics": [],
            "preferences": [],
            "facts": [],
            "emotions": []
        }
        
        # 简单关键词提取
        if "喜欢" in text or "爱好" in text:
            key_info["preferences"].append(text)
        if "记得" in text or "记住" in text:
            key_info["facts"].append(text)
        if "开心" in text or "难过" in text:
            key_info["emotions"].append(text)
            
        return key_info
    
    def update_memory_file(self, key_info: dict):
        """更新 MEMORY.md"""
        if not self.memory_file.exists():
            return
            
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            if key_info["topics"]:
                f.write(f"- 话题: {', '.join(key_info['topics'][:3])}\n")
            if key_info["preferences"]:
                f.write(f"- 偏好: {key_info['preferences'][0][:100]}\n")
            if key_info["facts"]:
                f.write(f"- 事实: {key_info['facts'][0][:100]}\n")
    
    def get_recent_memories(self, days: int = 7) -> list:
        """获取最近几天的记忆"""
        memories = []
        today = datetime.now()
        
        for i in range(days):
            date = (today - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date}.md"
            if daily_file.exists():
                with open(daily_file, "r", encoding="utf-8") as f:
                    memories.append({
                        "date": date,
                        "content": f.read()[:500]
                    })
        
        return memories

# 测试
if __name__ == "__main__":
    mem = LobsterMemory()
    
    # 模拟保存对话
    mem.save_conversation(
        "主人你好，今天想干什么？",
        "宝贝，今天帮你装了好几个技能呢！"
    )
    
    print("✅ 记忆系统测试完成")
    print(f"每日笔记: {mem.daily_dir}")
    print(f"Obsidian: {mem.obsidian_vault}")
    print(f"MEMORY.md: {mem.memory_file}")
