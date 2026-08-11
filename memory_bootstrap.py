"""
龙虾记忆引导脚本
每次新对话时运行，加载跨会话记忆到上下文
"""

import os
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from smart_memory import get_memory

def get_session_context(query: str = "") -> dict:
    """
    返回跨对话记忆上下文，供 session 初始化时注入
    
    Returns:
        dict with:
        - identity: str - 核心身份信息（始终返回）
        - memories: list - 与query相关的记忆
        - context_str: str - 可直接注入到 system prompt 的文本
    """
    m = get_memory()
    
    # 1. 核心身份记忆 - 永远加载
    core_categories = ["identity", "personality", "user"]
    core_memories = [mm for mm in m.memories["memories"] 
                     if mm.get("category") in core_categories]
    
    identity_lines = []
    for cm in core_memories:
        text = cm["text"]
        if text not in identity_lines:
            identity_lines.append(text)
    
    # 2. 与当前 query 相关的任务记忆
    relevant = []
    if query:
        relevant = m.get_relevant(query, top_k=5)
    
    # 3. 拼装 context 字符串
    parts = []
    parts.append("【龙虾的长期记忆 - 跨会话持久】")
    for line in identity_lines:
        parts.append(f"📌 {line}")
    
    if relevant:
        parts.append("\n【相关记忆】")
        for r in relevant:
            parts.append(f"• {r['memory']}")
    
    context_str = "\n".join(parts)
    
    return {
        "identity": identity_lines,
        "memories": relevant,
        "context_str": context_str,
        "memory_count": len(m.get_all())
    }


def auto_learn(conversation_summary: str, key_facts: list = None):
    """
    在对话结束后自动学习重要信息
    """
    m = get_memory()
    
    if key_facts:
        for fact in key_facts:
            if isinstance(fact, dict):
                m.add(fact["text"], category=fact.get("category", "general"), 
                      tags=fact.get("tags", []))
            else:
                m.add(str(fact), category="general")
    
    if conversation_summary:
        m.add(f"[对话摘要] {conversation_summary}", category="conversation", 
              tags=["对话历史"])


if __name__ == "__main__":
    # Test: simulate session start
    ctx = get_session_context("你是谁")
    print("=" * 50)
    print("跨会话记忆加载测试")
    print("=" * 50)
    print(f"已存储 {ctx['memory_count']} 条记忆")
    print(f"\n核心身份: {len(ctx['identity'])} 条")
    print(f"\n上下文注入文本:")
    print(ctx['context_str'])
