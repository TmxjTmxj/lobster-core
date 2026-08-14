"""lobster-core 冒烟测试 — 验证修复后核心模块可用性

运行: pip install pytest && pytest tests/ -q
"""
import sys
import os
import tempfile
from pathlib import Path

import pytest

# 确保仓库根目录在 import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── 修复后的引用可解析 ───
def test_fixed_imports():
    import smart_memory
    import super_memory
    import unified_memory  # 曾引用不存在的 memory.super_memory
    import self_evolution  # 曾引用不存在的 lobster_core.smart_memory
    assert smart_memory.get_memory is not None
    assert super_memory.HermesMemory is not None


# ─── 记忆系统基本读写 ───
def test_super_memory_roundtrip(tmp_path, monkeypatch):
    import super_memory as sm
    monkeypatch.setattr(sm, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(sm, "DB_FILE", tmp_path / "test_memory.db")

    m = sm.HermesMemory()
    m.store("测试记忆：龙虾缰绳工程可用", category="general", importance=5)
    hits = m.search("龙虾缰绳工程")
    assert any("龙虾缰绳工程" in str(h.get("content", h)) for h in hits), f"未命中: {hits}"
    m.close()


# ─── Harness 可导入且基本能力存在 ───
def test_harness_importable():
    import lobster_harness
    # 核心类/函数应存在
    for name in ["PromptLayer", "delegate_task"]:
        assert hasattr(lobster_harness, name) or any(
            hasattr(v, name) for v in vars(lobster_harness).values()
            if isinstance(v, type)), f"lobster_harness 缺少 {name}"


# ─── tavern_server 的 memory_engine 容错导入 ───
def test_tavern_memory_engine_fallback():
    src = open(Path(__file__).resolve().parent.parent / "tavern_server.py", encoding="utf-8").read()
    assert "try:" in src and "from memory_engine" in src, "memory_engine 应被 try/except 保护"
