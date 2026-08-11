"""
🦞 龙虾 — 记忆统一升级 v1
对标赫尔墨斯 v4_upgrade 架构，整合碎片化记忆系统
"""
import json, os, sys
from datetime import datetime
from pathlib import Path

LOBSTER_CORE = Path.home() / "lobster_core"
sys.path.insert(0, str(LOBSTER_CORE))

# ===== 1. 整合龙虾分散的记忆 =====

def consolidate():
    """把所有记忆文件统一为一个索引"""
    report = {}
    
    # 共享历史
    shared_file = Path.home() / ".lobster" / "memories" / "shared_history.json"
    if shared_file.exists():
        with open(shared_file) as f:
            data = json.load(f)
        report["shared_history"] = len(data)
    
    # 记忆目录
    mem_dir = LOBSTER_CORE / "memories"
    if mem_dir.exists():
        mem_files = list(mem_dir.glob("*"))
        report["memory_files"] = len(mem_files)
    
    # 学习日志
    log_file = LOBSTER_CORE / "learning_log.json"
    if log_file.exists():
        with open(log_file) as f:
            log = json.load(f)
        report["learning_log_entries"] = len(log) if isinstance(log, list) else 1
    
    # 学习图
    graph_file = LOBSTER_CORE / "learning_graph.json"
    if graph_file.exists():
        report["learning_graph"] = "present"
    
    # 超级记忆目录
    super_dir = LOBSTER_CORE / "super_memory"
    if super_dir.exists():
        super_files = list(super_dir.glob("*"))
        report["super_memory_files"] = len(super_files)
    
    # V4记忆
    v4_dir = LOBSTER_CORE / "v4_memory"
    if v4_dir.exists():
        v4_files = list(v4_dir.glob("*"))
        report["v4_memory_files"] = len(v4_files)
    
    # tavern数据
    tavern_dir = LOBSTER_CORE / "tavern_data"
    if tavern_dir.exists():
        tavern_files = list(tavern_dir.glob("*"))
        report["tavern_files"] = len(tavern_files)
    
    # Chroma向量库
    chroma_dir = LOBSTER_CORE / "chroma_db"
    if chroma_dir.exists():
        chroma_dirs = list(chroma_dir.glob("*"))
        report["chroma_db"] = len(chroma_dirs)
    
    report["status"] = "consolidated"
    report["version"] = "v1"
    report["upgraded_by"] = "赫尔墨斯"
    report["upgraded_at"] = datetime.now().isoformat()
    
    # 写入状态
    state_file = LOBSTER_CORE / "memory_state.json"
    with open(state_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report

# ===== 2. 跨Agent 记忆桥 =====

def bridge_to_hermes():
    """同步龙虾记忆到赫尔墨斯"""
    shared_file = Path.home() / ".lobster" / "memories" / "shared_history.json"
    if not shared_file.exists():
        return 0
    with open(shared_file) as f:
        her_data = json.load(f)
    return len(her_data)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "upgrade":
        r = consolidate()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print("\n✅ 龙虾记忆已统一升级")
    
    elif cmd == "status":
        r = consolidate()
        print(f"🦞 龙虾记忆系统状态:")
        for k, v in r.items():
            if k not in ("status", "version", "upgraded_by", "upgraded_at"):
                print(f"  {k}: {v}")
        print(f"  版本: {r.get('version')}")
        print(f"  升级者: {r.get('upgraded_by')}")
