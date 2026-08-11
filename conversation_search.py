"""
龙虾对话搜索 — 像 Codex/Hermes 一样搜索历史对话
"""

import os
import json, os, time, hashlib, re
from pathlib import Path

SEARCH_DIR = os.path.expanduser("~/.lobster/conversations")
os.makedirs(SEARCH_DIR, exist_ok=True)

class ConversationSearch:
    """FTS5 风格的全文本对话搜索（轻量级实现）"""
    
    def __init__(self):
        self.index_file = os.path.join(SEARCH_DIR, "search_index.json")
        self.index = self._load()
    
    def _load(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, encoding='utf-8') as f:
                return json.load(f)
        return {"conversations": [], "version": 1}
    
    def _save(self):
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def save_conversation(self, session_id: str, summary: str, 
                           key_points: list = None, topics: list = None):
        """保存一次对话的摘要"""
        entry = {
            "id": session_id,
            "summary": summary[:200],
            "key_points": key_points or [],
            "topics": topics or [],
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M")
        }
        
        # Dedup
        self.index["conversations"] = [c for c in self.index["conversations"] 
                                        if c["id"] != session_id]
        self.index["conversations"].append(entry)
        
        # Keep last 200
        if len(self.index["conversations"]) > 200:
            self.index["conversations"] = self.index["conversations"][-200:]
        
        self._save()
    
    def search(self, query: str, max_results: int = 5) -> list:
        """搜索历史对话 — 关键词+主题匹配"""
        query_lower = query.lower()
        
        scored = []
        for conv in self.index["conversations"]:
            score = 0
            
            # Search in summary
            if query_lower in conv.get("summary", "").lower():
                score += 3
            
            # Search in key points
            for kp in conv.get("key_points", []):
                if query_lower in kp.lower():
                    score += 2
            
            # Search in topics
            for topic in conv.get("topics", []):
                if query_lower in topic.lower():
                    score += 1.5
            
            # Recency boost
            score += 0.1  # All get slight recency
            
            if score > 0:
                scored.append((score, conv))
        
        scored.sort(key=lambda x: -x[0])
        return [{"score": s, **c} for s, c in scored[:max_results]]


_search = None
def get_search():
    global _search
    if _search is None:
        _search = ConversationSearch()
    return _search


if __name__ == "__main__":
    cs = get_search()
    cs.save_conversation("session_1", "安装了Agent-Reach和全网搜索能力", 
                         ["装Agent-Reach", "配B站搜索", "配Twitter搜索"], ["升级"])
    cs.save_conversation("session_2", "配置了通义万相AI生图", 
                         ["通义万相", "DashScope API", "生图测试"], ["生图"])
    print(f"✅ 已保存 {len(cs.index['conversations'])} 条对话记录")
