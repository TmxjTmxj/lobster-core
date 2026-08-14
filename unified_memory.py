"""
🔷 赫尔墨斯 — 四层统一记忆系统
整合 super_memory + memory_bridge + mempalace + Hermes memory
"""
import os
import json, os, sys, subprocess, time
from datetime import datetime
from pathlib import Path

HERMES_CORE = Path.home() / "hermes_core"
sys.path.insert(0, str(HERMES_CORE))

from super_memory import HermesMemory
from memory_bridge import _load_json, SHARED_HISTORY, get_full_context


def memory_status() -> dict:
    """四层记忆系统全状态"""
    report = {}
    
    # Layer 1: super_memory (SQLite)
    try:
        hm = HermesMemory()
        s = hm.get_stats()
        hm.close()
        report["super_memory"] = {
            "status": "ok",
            "memories": s["memories"],
            "interactions": s["interactions"],
            "last_memory": s["last_memory"],
        }
    except Exception as e:
        report["super_memory"] = {"status": f"error: {e}"}
    
    # Layer 2: memory_bridge (shared_history)
    try:
        shared = _load_json(SHARED_HISTORY, [])
        from_feishu = sum(1 for e in shared if e.get("source") == "feishu")
        from_tavern = sum(1 for e in shared if e.get("source") == "tavern")
        report["memory_bridge"] = {
            "status": "ok",
            "total": len(shared),
            "from_feishu": from_feishu,
            "from_tavern": from_tavern,
        }
    except Exception as e:
        report["memory_bridge"] = {"status": f"error: {e}"}
    
    # Layer 3: mempalace
    try:
        result = subprocess.run(
            ["mempalace", "status"],
            capture_output=True, text=True, timeout=5,
            env={**os.environ, "PATH": f"{Path.home()}/.bun/bin:{os.environ['PATH']}"}
        )
        output = result.stdout
        import re
        drawers = re.search(r"(\d+) drawers", output)
        report["mempalace"] = {
            "status": "ok",
            "drawers": int(drawers.group(1)) if drawers else 0,
        }
    except Exception as e:
        report["mempalace"] = {"status": f"error: {e}"}
    
    # Layer 4: Hermes profile memory
    report["hermes_memory"] = {"status": "ok", "type": "profile-level"}
    
    # Overall health
    ok_count = sum(1 for v in report.values() if v.get("status") == "ok")
    report["_summary"] = {
        "layers_online": f"{ok_count}/4",
        "time": datetime.now().isoformat(),
    }
    
    return report


def quick_recall(query: str = "", limit: int = 3) -> str:
    """跨层快速召回：先查 super_memory，再查 mempalace"""
    parts = []
    
    # Try super_memory first
    try:
        hm = HermesMemory()
        results = hm.search(query, limit=limit, min_importance=3)
        hm.close()
        if results:
            parts.append("【超级记忆】")
            for r in results[:limit]:
                parts.append(f"  • {r['content'][:80]}")
    except:
        pass
    
    # Then mempalace
    try:
        source_cmd = f"source /tmp/mempalace-venv/bin/activate"
        env = os.environ.copy()
        result = subprocess.run(
            ["/bin/bash", "-c", f"{source_cmd} && mempalace search '{query}' 2>/dev/null | head -10"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Extract top matches
            lines = [l for l in output.split('\n') if 'Match:' in l or 'Source:' in l]
            if lines:
                parts.append("\n【记忆宫殿】")
                for i, l in enumerate(lines[:3]):
                    parts.append(f"  • {l.strip()[:60]}")
    except:
        pass
    
    return "\n".join(parts) if parts else "未找到相关记忆"


def auto_sync():
    """自动同步四层记忆"""
    try:
        # Sync bridge → shared_history
        from memory_bridge import push_from_tavern_to_main
        push_from_tavern_to_main()
        
        # Mine latest into mempalace
        try:
            subprocess.run(
                ["/bin/bash", "-c", "source /tmp/mempalace-venv/bin/activate && yes | mempalace mine ~/hermes_core 2>/dev/null"],
                timeout=30
            )
        except:
            pass
        
        return True
    except:
        return False


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "status":
        report = memory_status()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        print(quick_recall(query))
    
    elif cmd == "sync":
        ok = auto_sync()
        print(f"同步: {'成功 ✅' if ok else '失败 ❌'}")
