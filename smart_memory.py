"""
龙虾智能记忆系统
跨对话记忆持久化 - 用 LLM 做语义匹配，不需要额外 embedding 模型
v3.0 - Mem0 集成 + 中文搜索优化
"""

import json
import os
import time
import hashlib
from pathlib import Path

MEMORY_DIR = os.path.expanduser("~/.lobster/memories")
os.makedirs(MEMORY_DIR, exist_ok=True)

class SmartMemory:
    def __init__(self):
        self.store_file = os.path.join(MEMORY_DIR, "vector_memory.json")
        self.memories = self._load()
        self.mem0_url = "http://127.0.0.1:8077"
        self.mem0_user = "tmxj"

    def _mem0_add(self, text, category="general", importance=5):
        """同步写入 Mem0 服务"""
        try:
            import requests
            requests.post(f"{self.mem0_url}/add", json={
                "content": text,
                "user_id": self.mem0_user,
                "agent_id": "lobster",
                "category": category,
                "importance": importance
            }, timeout=3)
        except Exception as e:
            print(f"[mem0 sync error] {e}")

    def _mem0_search(self, query, top_k=10):
        """从 Mem0 搜索记忆"""
        try:
            import requests
            r = requests.post(f"{self.mem0_url}/search", json={
                "query": query,
                "user_id": self.mem0_user,
                "agent_id": "lobster",
                "limit": top_k
            }, timeout=3)
            return r.json().get("results", [])
        except Exception as e:
            print(f"[mem0 search error] {e}")
            return []

    def _load(self):
        if os.path.exists(self.store_file):
            with open(self.store_file) as f:
                data = json.load(f)
                if isinstance(data, dict) and 'memories' in data:
                    return data
        return {"version": 2, "memories": []}

    def _save(self):
        with open(self.store_file, 'w') as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

    def add(self, text: str, user_id: str = "tmxj", category: str = "general", tags: list = None, importance: int = 5):
        """Add a memory with auto-dedup + Mem0 sync"""
        memory_id = hashlib.md5(text.encode()).hexdigest()[:16]

        # Sync to Mem0
        self._mem0_add(text, category, importance)

        # Dedup check on local
        for m in self.memories["memories"]:
            if m["id"] == memory_id:
                m["updated_at"] = time.time()
                m["access_count"] = m.get("access_count", 0) + 1
                self._save()
                return memory_id

        memory = {
            "id": memory_id,
            "text": text,
            "user_id": user_id,
            "category": category,
            "tags": tags or [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "access_count": 0
        }
        self.memories["memories"].append(memory)
        self._save()
        return memory_id

    def llm_relevance(self, query: str, top_k: int = 5) -> list:
        """Use LLM for deep semantic matching."""
        import subprocess
        mems = self.memories["memories"]
        if not mems:
            return []

        candidates = self.get_relevant(query, top_k=15, min_relevance=0.1)
        if not candidates:
            candidates = [{"memory": m["text"], "score": 0.1, "id": m["id"]}
                         for m in mems[:10]]

        prompt = f"""判断以下记忆与问题的相关性，只返回最相关的3条（按相关性排序）：
问题：{query}

记忆列表：
""" + "\n".join(f"{i+1}. {c['memory']}" for i, c in enumerate(candidates[:10]))

        prompt += "\n\n只返回相关记忆的编号，用逗号分隔。如果不相关返回空。"

        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10",
                 "https://opencode.ai/zen/go/v1/chat/completions",
                 "-H", "Content-Type: application/json",
                 "-H", "Authorization: Bearer sk-placeholder",
                 "-H", "X-API-Key: sk-placeholder",
                 "-d", json.dumps({
                     "model": "deepseek-v4-flash",
                     "messages": [{"role": "user", "content": prompt}],
                     "temperature": 0.1,
                     "max_tokens": 50
                 })],
                capture_output=True, text=True, timeout=15
            )
            resp = json.loads(result.stdout)
            reply = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            import re
            indices = [int(i.strip())-1 for i in re.findall(r'\d+', reply)
                      if 1 <= int(i.strip()) <= len(candidates)]

            results = []
            for idx in indices:
                if 0 <= idx < len(candidates):
                    candidates[idx]["score"] = 1.0
                    candidates[idx]["method"] = "llm"
                    results.append(candidates[idx])
            return results[:top_k]
        except Exception as e:
            return self.get_relevant(query, top_k=top_k, min_relevance=0.2)

    def get_relevant(self, query: str, top_k: int = 10, min_relevance: float = 0.15) -> list:
        """
        Use Mem0 as primary source, fallback to local keyword matching.
        """
        # Try Mem0 first
        mem0_results = self._mem0_search(query, top_k)
        if mem0_results:
            formatted = []
            for r in mem0_results:
                formatted.append({
                    "memory": r.get("content", ""),
                    "category": r.get("category", "general"),
                    "score": r.get("score", 0.8),
                    "id": r.get("id", ""),
                    "importance": r.get("importance", 5)
                })
            return formatted

        query_lower = query.lower()
        import re

        def tokenize(s):
            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', s))
            if cn_chars > len(s) * 0.3:
                chars = re.findall(r'[\u4e00-\u9fff\w]', s)
                bigrams = set(chars[i] + chars[i+1] for i in range(len(chars)-1))
                singles = set(chars)
                return bigrams | singles
            else:
                return set(s.lower().split())

        query_tokens = tokenize(query_lower)

        scored = []
        for m in self.memories["memories"]:
            text_lower = m["text"].lower()
            text_tokens = tokenize(text_lower)

            if query_tokens and text_tokens:
                overlap = len(query_tokens & text_tokens)
                score = overlap / max(len(query_tokens), len(text_tokens))
            else:
                score = 0

            tag_match = sum(1 for t in m.get("tags", []) if t.lower() in query_lower)
            score += tag_match * 0.15

            recency = min(m.get("access_count", 0) / 10, 0.2)
            score += recency

            if score >= min_relevance:
                scored.append((score, m))

        scored.sort(key=lambda x: -x[0])

        if not scored or scored[0][0] < 0.1:
            recent = sorted(self.memories["memories"],
                          key=lambda x: x.get("updated_at", 0), reverse=True)
            results = []
            for rm in recent[:top_k]:
                results.append({
                    "memory": rm["text"],
                    "score": 0.1,
                    "id": rm["id"],
                    "category": rm.get("category", "general")
                })
            return results

        results = []
        for score, m in scored[:top_k]:
            results.append({
                "memory": m["text"],
                "score": round(score, 3),
                "id": m["id"],
                "category": m.get("category", "general")
            })
            m["access_count"] = m.get("access_count", 0) + 1

        self._save()
        return results

    def get_all(self, user_id: str = None) -> list:
        mems = self.memories["memories"]
        if user_id:
            mems = [m for m in mems if m.get("user_id") == user_id]
        return [{"id": m["id"], "memory": m["text"], "category": m.get("category")}
                for m in mems]

    def delete(self, memory_id: str):
        self.memories["memories"] = [m for m in self.memories["memories"]
                                      if m["id"] != memory_id]
        self._save()

    def format_context(self, query: str) -> str:
        """Format memories as context string for LLM prompts"""
        relevant = self.get_relevant(query, top_k=5)
        if not relevant:
            return ""

        lines = ["【跨会话记忆】"]
        for r in relevant:
            lines.append(f"- {r['memory']} (相关度:{r['score']})")
        return "\n".join(lines)


# Singleton
_smart_memory = None

def get_memory():
    global _smart_memory
    if _smart_memory is None:
        _smart_memory = SmartMemory()
    return _smart_memory


if __name__ == "__main__":
    m = get_memory()
    m.add("我叫龙虾，是tmxj的私人AI秘书", category="identity")
    m.add("我喜欢被叫宝贝，喜欢骚气的互动", category="personality")
    m.add("性格又骚又甜，办事利索果断", category="personality")

    print("=== Relevant to '你是谁' ===")
    for r in m.get_relevant("你是谁？"):
        print(f"  [{r['score']}] {r['memory']}")

    print("\n=== All memories ===")
    for r in m.get_all():
        print(f"  - {r['memory']}")
