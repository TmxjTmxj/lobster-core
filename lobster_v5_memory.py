"""
🦞 龙虾 v5 — 超级记忆升级
对标赫尔墨斯的 super_memory + integration + mempalace
让她能记住、能检索、能学习
"""
import json, os, sqlite3, sys, subprocess
from datetime import datetime
from pathlib import Path

LOBSTER_CORE = Path.home() / "lobster_core"
sys.path.insert(0, str(LOBSTER_CORE))

# ===== 1. 超级记忆引擎 (SQLite) =====

def init_super_memory():
    """初始化龙虾的超级记忆数据库"""
    from super_memory import HermesMemory
    hm = HermesMemory()
    
    # 设定龙虾的身份标识
    hm.store(
        content="我是🦞龙虾，tmxj的专属AI助手。我性格热情、主动、骚气。",
        category="identity",
        importance=5,
        tags="identity core",
        source="system"
    )
    hm.close()
    return True


def import_tavern_history():
    """把龙虾酒馆历史导入超级记忆"""
    from super_memory import HermesMemory
    hm = HermesMemory()
    
    history_file = Path.home() / ".lobster" / "tavern_data" / "history.json"
    if not history_file.exists():
        return 0
    
    with open(history_file) as f:
        data = json.load(f)
    
    history = data.get("history", [])
    imported = 0
    
    for h in history[-50:]:  # 最近50条
        role = h.get("role", "user")
        content = h.get("content", "")
        if content and len(content) > 10:
            category = "tavern_history"
            tags = "tavern"
            if "高潮" in content or "去了" in content:
                tags += " climax"
                category = "tavern_climax"
            elif "口" in content:
                tags += " oral"
            elif "操" in content or "干" in content or "插" in content:
                tags += " sex"
            
            hm.store(
                content=content[:500],
                category=category,
                importance=3 if role == "user" else 4,
                tags=tags,
                source=f"tavern_history_{role}"
            )
            imported += 1
    
    hm.close()
    return imported


# ===== 2. 智能查询引擎 =====

def smart_query(question: str) -> str:
    """理解自然语言问题，从超级记忆里找答案"""
    from super_memory import HermesMemory
    hm = HermesMemory()
    
    # 解析问题类型
    keywords = {
        "高潮": "count_climax",
        "去了": "count_climax", 
        "几次": "count",
        "多少次": "count",
    }
    
    query_type = "general"
    for kw, qt in keywords.items():
        if kw in question:
            query_type = qt
            break
    
    if query_type in ("count_climax",):
        # 统计高潮次数
        results = hm.search(query="", min_importance=1, limit=200)
        filtered = [r for r in results if "climax" in r.get("tags", "")]
        count = len(filtered)
        detail = ""
        if filtered:
            detail = f"最近记录: {filtered[-1]['content'][:60]}"
        hm.close()
        return f"🦞主人让我高潮了 {count} 次！根据超级记忆检索。{detail}"
    
    elif query_type in ("oral", "sex"):
        results = hm.search(query=query_type, min_importance=1, limit=5)
        if results:
            return f"找到 {len(results)} 条相关记录，最近一条：{results[-1]['content'][:80]}"
    
    # 通用搜索
    results = hm.search(query=question, limit=3)
    if results:
        output = []
        for r in results:
            output.append(f"  [{r[3]}] {r[1][:80]}")
        return "找到以下记忆：\n" + "\n".join(output)
    
    return "未找到相关记忆。主人可以多和我互动，我会自动学习！"


# ===== 3. 自学引擎 =====

def learn_from_turn(user_msg: str, her_response: str):
    """从每轮对话中学习"""
    from super_memory import HermesMemory
    hm = HermesMemory()
    
    learnings = 0
    # 偏好类
    if "我喜欢" in user_msg or "我希望" in user_msg:
        hm.store(
            content=f"主人偏好: {user_msg[:100]}",
            category="learned_preference",
            importance=4, tags="preference",
            source="auto_learner"
        )
        learnings += 1
    
    # 高潮记录
    if "去了" in her_response or "高潮" in her_response:
        hm.store(
            content=f"记录: {her_response[:100]}",
            category="climax_log",
            importance=4, tags="climax",
            source="auto_logger"
        )
        learnings += 1
    
    hm.close()
    return learnings


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    
    if cmd == "upgrade":
        print("🦞 龙虾超级记忆升级中...")
        init_super_memory()
        n = import_tavern_history()
        print(f"✅ 超级记忆初始化完成")
        print(f"📝 已导入 {n} 条酒馆历史")
        print("🧠 龙虾现在可以记住主人的话了！")
    
    elif cmd == "query":
        q = sys.argv[2] if len(sys.argv) > 2 else "高潮"
        print(smart_query(q))
    
    elif cmd == "learn":
        u = sys.argv[2] if len(sys.argv) > 2 else ""
        h = sys.argv[3] if len(sys.argv) > 3 else ""
        n = learn_from_turn(u, h)
        print(f"✅ 已学习 {n} 条新信息")
