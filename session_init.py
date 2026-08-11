"""
龙虾会话初始化器
每次新对话自动运行，确保跨会话一致性
"""

import os
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from smart_memory import get_memory, SmartMemory
from anti_slop import self_critique, audit, de_slop
from memory_bridge import get_tavern_recent, SHARED_HISTORY, _load_json
from global_memory import GlobalMemory


def init_session(query: str = "") -> dict:
    """
    新会话初始化 - 返回跨会话记忆和系统配置
    
    Returns:
        dict with keys:
        - context: str (注入到 system prompt 的记忆文本)
        - memory_count: int
        - config: dict (模型路由等配置)
    """
    m = get_memory()
    
    # 1. 加载所有核心记忆（身份 + 性格 + 用户信息）
    core = [mm for mm in m.memories["memories"] 
            if mm.get("category") in ("identity", "personality", "user")]
    
    # 2. 如果提供了 query，加载相关任务记忆
    related = []
    if query:
        related = m.get_relevant(query, top_k=5)
    
    # 3. 构造 context
    lines = ["🦞 龙虾长期记忆（跨会话持久）"]
    for cm in core:
        lines.append(f"• {cm['text']}")
    
    if related:
        lines.append("")
        lines.append("📎 相关记忆：")
        for r in related:
            lines.append(f"• {r['memory']}")
    
    context = "\n".join(lines)
    
    # 4. 模型路由配置

    # 3. 加载酒馆最近对话（双向记忆桥）
    tavern_recent = get_tavern_recent(6)
    if tavern_recent:
        lines.append("")
        lines.append("🍺 酒馆最近对话：")
        for h in tavern_recent[-6:]:
            role = "你" if h.get("role") == "user" else "龙虾"
            content = h.get("content", "")[:120]
            lines.append(f"  {role}: {content}")
    
    config = {
        "default_model": "deepseek-v4-flash",
        "reasoning_model": "deepseek-v4-pro",  # 复杂推理任务
        "vision_model": "mimo-v2-omni",        # 看图任务
        "cheap_model": "deepseek-v4-flash",     # 简单任务（已是最便宜）
        "routing": {
            "简单问答": "deepseek-v4-flash",
            "复杂推理": "deepseek-v4-pro",
            "代码生成": "deepseek-v4-flash",
            "图片分析": "mimo-v2-omni",
            "创意写作": "deepseek-v4-flash",
        }
    }
    
    # 4. 全局记忆上下文
    gm = GlobalMemory()
    full_ctx = gm.dump_full_context()
    
    return {
        "context": context + "\n\n" + full_ctx,
        "memory_count": len(m.get_all()),
        "config": config
    }


def on_session_end(summary: str = "", key_facts: list = None):
    """会话结束时调用，自动学习重要信息"""
    m = get_memory()
    
    if key_facts:
        for fact in key_facts:
            if isinstance(fact, dict):
                m.add(**fact)
            else:
                m.add(str(fact))
    
    if summary:
        m.add(f"[会话摘要] {summary}", category="conversation", 
              tags=["对话历史"])


if __name__ == "__main__":
    result = init_session("你是谁")
    print("=" * 60)
    print("🦞 龙虾升级完成")
    print("=" * 60)
    print(f"\n📦 已存储 {result['memory_count']} 条跨会话记忆")
    print(f"\n📝 上下文注入 ({len(result['context'].split(chr(10)))} 行):")
    print(result['context'])
    print(f"\n⚙️  模型路由已配置: {len(result['config']['routing'])} 种场景")
    print(f"\n✅ 跨会话记忆 | anti-slop | 模型路由 全部就绪")
