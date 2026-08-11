"""
🦞 龙虾双向记忆桥（v2）
酒馆 ↔ 飞书主会话 双向记忆同步
"""

import os
import json, os, time, requests
from datetime import datetime

MEMORY_DIR = os.path.expanduser("~/.lobster/memories")
TAVERN_DIR = os.path.expanduser("~/.lobster/tavern_data")
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(TAVERN_DIR, exist_ok=True)

SHARED_HISTORY = os.path.join(MEMORY_DIR, "shared_history.json")
TAVERN_HISTORY = os.path.join(TAVERN_DIR, "history.json")
BRIDGE_STATE = os.path.join(TAVERN_DIR, "bridge_state.json")
VECTOR_MEMORY = os.path.join(MEMORY_DIR, "vector_memory.json")


def _load_json(path, default=None):
    if default is None:
        default = [] if path.endswith("history.json") else {}
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except:
        pass
    return default


def _save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_tavern_recent(count=10):
    """获取酒馆最近对话"""
    history = _load_json(TAVERN_HISTORY, {"history": []})
    entries = history.get("history", [])
    return entries[-count:] if entries else []


def get_main_recent(count=10):
    """获取主会话最近共享内容"""
    entries = _load_json(SHARED_HISTORY, [])
    return entries[-count:] if entries else []


def push_to_tavern(source, user_msg, bot_msg):
    """主会话 → 酒馆：推送一条对话到共享记忆"""
    entries = _load_json(SHARED_HISTORY, [])
    now = datetime.now().isoformat()
    entries.append({
        "role": "user", "content": user_msg,
        "source": source, "time": now
    })
    entries.append({
        "role": "assistant", "content": bot_msg[:300],
        "source": source, "time": now
    })
    _save_json(SHARED_HISTORY, entries[-100:])
    # Also push to Mem0
    try:
        import requests
        for role, msg in [("user", user_msg), ("assistant", bot_msg)]:
            requests.post('http://127.0.0.1:8077/add', json={
                "content": f"[{source}] {msg[:200]}",
                "user_id": "tmxj",
                "agent_id": "lobster",
                "category": "conversation",
                "importance": 6
            }, timeout=2)
    except:
        pass

    # 也尝试推送到酒馆的 feed 端（如果酒馆在线）
    try:
        requests.post(
            "http://localhost:8888/api/feed",
            json={"source": source, "entries": [
                {"role": "user", "content": user_msg, "time": now},
                {"role": "assistant", "content": bot_msg[:300], "time": now}
            ]},
            timeout=3
        )
    except:
        pass  # 酒馆不在线也没关系，共享文件已经写入了


def push_from_tavern_to_main():
    """酒馆 → 主会话：读取酒馆最新内容，同步到共享记忆（由酒馆在每次回复后自动调用）"""
    # 读取当前桥状态
    state = _load_json(BRIDGE_STATE, {"last_sync_tavern": 0, "last_sync_main": 0})

    # 读取酒馆历史
    history = _load_json(TAVERN_HISTORY, {"history": []})
    entries = history.get("history", [])
    tavern_count = len(entries)

    if tavern_count > state.get("last_sync_tavern", 0):
        new_entries = entries[state["last_sync_tavern"]:]
        shared = _load_json(SHARED_HISTORY, [])
        now = datetime.now().isoformat()
        for e in new_entries:
            shared.append({
                "role": e.get("role", "user"),
                "content": e.get("content", "")[:300],
                "source": "tavern",
                "time": now
            })
        _save_json(SHARED_HISTORY, shared[-100:])
        state["last_sync_tavern"] = tavern_count
        state["updated"] = now
        _save_json(BRIDGE_STATE, state)
        return len(new_entries) // 2
    return 0


def get_full_context(max_lines=30):
    """获取完整上下文：酒馆历史 + 主会话共享 + smart_memory"""
    lines = []

    # 1. 共享历史（双向合并）
    shared = _load_json(SHARED_HISTORY, [])
    if shared:
        lines.append("【最近对话历史】")
        for e in shared[-max_lines:]:
            role = "你" if e.get("role") == "user" else "龙虾"
            src = {"tavern": "🍺", "feishu": "💬"}.get(e.get("source", ""), "💬")
            content = e.get("content", "")[:150]
            lines.append(f"{src} {role}: {content}")

    # 2. smart_memory 核心记忆
    vm = _load_json(VECTOR_MEMORY, {"memories": []})
    core = [m for m in vm.get("memories", [])
            if m.get("category") in ("identity", "personality", "user")]
    if core:
        lines.append("\n【核心记忆】")
        for m in core[-15:]:
            lines.append(f"• {m['text']}")

    return "\n".join(lines)


def get_tavern_context(max_lines=10):
    """酒馆侧：从主记忆拉上下文"""
    shared = _load_json(SHARED_HISTORY, [])
    tavern_entries = [e for e in shared if e.get("source") == "feishu"]
    lines = [f"{'你' if e.get('role') == 'user' else '龙虾'}: {e.get('content','')[:200]}"
             for e in tavern_entries[-max_lines:]]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        shared = _load_json(SHARED_HISTORY, [])
        tavern = get_tavern_recent(3)
        state = _load_json(BRIDGE_STATE, {})
        print(f"🦞 双向记忆桥")
        print(f"共享历史: {len(shared)} 条")
        print(f"酒馆历史: {sum(1 for e in shared if e.get('source')=='tavern')} 条")
        print(f"主会话: {sum(1 for e in shared if e.get('source')=='feishu')} 条")
        print(f"桥状态: {json.dumps(state, ensure_ascii=False)}")

    elif cmd == "sync":
        count = push_from_tavern_to_main()
        print(f"✅ 同步了 {count} 条酒馆对话到主记忆")

    elif cmd == "context":
        print(get_full_context())

    elif cmd == "push-feishu":
        # 手动推送一条主会话记录到共享：python3 memory_bridge.py push-feishu "用户说" "龙虾答"
        user_msg = sys.argv[2] if len(sys.argv) > 2 else ""
        bot_msg = sys.argv[3] if len(sys.argv) > 3 else ""
        if user_msg:
            push_to_tavern("feishu", user_msg, bot_msg)
            print(f"✅ 已推送主会话记录到共享记忆")
