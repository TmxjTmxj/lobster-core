"""
🔷⛓️🦞 赫尔墨斯 ↔ 龙虾 双向记忆桥核心
两边都引用这个文件，实现真正的双向互通
"""
import json, os
from datetime import datetime
from pathlib import Path

# 共享存储位置（双方都读写这个文件）
SHARED_PATH = Path.home() / ".hermes" / "cross_agent_bridge.json"
LOCK_PATH = Path.home() / ".hermes" / "cross_agent_bridge.lock"


def _read():
    if SHARED_PATH.exists():
        return json.loads(SHARED_PATH.read_text())
    return {"entries": [], "last_seq": 0}


def _write(data):
    SHARED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def push(agent_id: str, content: str, tags: str = ""):
    """当前agent写入一条记忆到共享桥"""
    data = _read()
    data["last_seq"] += 1
    data["entries"].append({
        "seq": data["last_seq"],
        "agent": agent_id,
        "content": content[:500],
        "tags": tags,
        "timestamp": datetime.now().isoformat(),
    })
    # 只保留最近200条
    if len(data["entries"]) > 200:
        data["entries"] = data["entries"][-200:]
    _write(data)
    return data["last_seq"]


def pull(agent_id: str, since_seq: int = 0, tag_filter: str = "") -> list:
    """读取自上次同步以来的新条目"""
    data = _read()
    results = []
    for e in data["entries"]:
        if e["seq"] <= since_seq:
            continue
        if e["agent"] == agent_id:
            continue  # 不读自己的
        if tag_filter and tag_filter not in e.get("tags", ""):
            continue
        results.append(e)
    return results


def get_latest(agent_id: str, limit: int = 3) -> list:
    """获取另一个agent的最新记忆"""
    data = _read()
    other = [e for e in data["entries"] if e["agent"] != agent_id]
    return other[-limit:]


def search(tag: str, agent_id: str = "") -> list:
    """按标签搜索所有agent的记忆"""
    data = _read()
    results = []
    for e in data["entries"]:
        if agent_id and e["agent"] != agent_id:
            continue
        if tag and tag not in e.get("tags", ""):
            continue
        results.append(e)
    return results


def status() -> dict:
    """桥状态"""
    data = _read()
    agents = {}
    for e in data["entries"]:
        a = e["agent"]
        agents[a] = agents.get(a, 0) + 1
    return {
        "total_entries": len(data["entries"]),
        "agents": agents,
        "last_seq": data["last_seq"],
    }
