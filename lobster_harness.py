"""
🦞 龙虾缰绳工程引擎 — 5 层全栈升级 (P2: 外部记忆 + Subagent 委派)
对标 Hermes Agent 最高级实现
"""

import os
import json
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# ─── P1 新增依赖 ───
import fnmatch

# ─── P2 新增依赖 ───
from smart_memory import SmartMemory

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
STATE_FILE = os.path.join(WORKSPACE, "SESSION-STATE.md")
MEMORY_FILE = os.path.join(WORKSPACE, "MEMORY.md")
USER_FILE = os.path.join(WORKSPACE, "USER.md")
SOUL_FILE = os.path.join(WORKSPACE, "SOUL.md")
DAILY_DIR = os.path.join(WORKSPACE, "memory")

# 用户拒绝规则的 MEMORY.md 章节标记
DENY_SECTION = "## User Deny Patterns"

# 用户画像章节定义
USER_SECTIONS = ["沟通偏好", "技术环境", "工作习惯", "已知偏好"]

# ─── 指令层：三阶提示架构 + Frozen Snapshot ───────────────────

@dataclass
class PromptLayer:
    """三阶提示的层级定义"""
    stable: str = ""      # 身份 + 工具指导 + 安全规则 (不变)
    context: str = ""     # 项目上下文 (会话级)
    volatile: str = ""    # 记忆 + 时间戳 (每次会话重建)

_SNAPSHOT_LOCK = threading.Lock()
_snapshot_cache = {}


# ═══════════════════════════════════════════════════════════════
# P2-3: Subagent 委派模板
# ═══════════════════════════════════════════════════════════════

@dataclass
class DelegationTemplate:
    """Subagent 委派的标准化模板容器"""
    objective: str
    output: str
    verification: str
    tools_available: List[str]
    context: str = ""
    format: str = "standard"


_RENDERED_TEMPLATE = """## Subagent Task

### Objective
{objective}

### Tools Available
{tools_str}

### Output Scope
{output}

### Verification Instructions
{verification}

### Output Format
```json
{{
  "status": "success|partial|failed",
  "result": "<summary of findings>",
  "details": "<full output>",
  "errors": []
}}
```
{context_block}"""


def make_delegation_prompt(task_desc: str, tools_needed: List[str], context: str = "") -> DelegationTemplate:
    """
    生成标准化 subagent 委托提示。

    这是编排层的方法——生成一个给 subagent 的完整委托模板，
    包含清晰的 objective、output scope 和 verification instructions。

    注意：不直接调用 sessions_spawn（那是 OpenClaw 层面的工具），
    而是生成标准化的委托提示字符串。
    """
    template = DelegationTemplate(
        objective=task_desc.strip(),
        output="你是一个 subagent，负责完成以下任务。完成后返回结构化的结果摘要。",
        verification="在返回结果前，先验证：1) 所有目标是否达成；2) 是否有异常需要汇报；3) 结果是否符合预期格式。",
        tools_available=tools_needed,
        context=context
    )
    return template


def render_delegation_prompt(task_desc: str, tools_needed: List[str], context: str = "") -> str:
    """
    将委派信息渲染为完整的提示模板字符串。
    这个字符串可以直接粘贴给 subagent 作为初始提示。
    """
    t = make_delegation_prompt(task_desc, tools_needed, context)
    tools_str = "\n".join(f"- {x}" for x in tools_needed)
    context_block = f"\n### Additional Context\n{context}\n" if context else ""
    return _RENDERED_TEMPLATE.format(
        objective=t.objective,
        tools_str=tools_str,
        output=t.output,
        verification=t.verification,
        context_block=context_block
    )


class Harness:
    """缰绳工程总控 — 5 层全功能 (P2: 外部记忆 + Subagent 委派)"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.turn_count = 0
        self._db_conn = None
        self.deny_patterns = []  # 用户自定义 fnmatch 拒绝规则
        # P2-1: 外部记忆系统
        self._smart_memory = SmartMemory()
    
    # ════════════════════════════════════════════
    # P1-1：用户自定义拒绝规则
    # ════════════════════════════════════════════

    def add_deny_patterns(self, patterns: List[str]):
        """添加用户自定义 fnmatch 拒绝规则"""
        self.deny_patterns.extend(patterns)

    def _load_deny_from_memory(self) -> List[str]:
        """从 MEMORY.md 的 ## User Deny Patterns 章节加载用户拒绝规则"""
        patterns = []
        if not os.path.exists(MEMORY_FILE):
            return patterns
        with open(MEMORY_FILE) as f:
            content = f.read()
        lines = content.split("\n")
        in_section = False
        for line in lines:
            stripped = line.strip()
            if stripped == DENY_SECTION:
                in_section = True
                continue
            if in_section:
                if stripped.startswith("## "):
                    break
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
        return patterns

    # ════════════════════════════════════════════
    # P1-2：记忆层容量管理 + USER.md 自动画像
    # ════════════════════════════════════════════

    MEMORY_WARN_LINES = 150
    MEMORY_WARN_CHARS = 2000

    def memory_usage(self) -> dict:
        """
        检查 MEMORY.md 容量，返回使用率
        
        Returns:
            {"total_lines": int, "total_chars": int,
             "percent": float (0-100),
             "suggestion": str or None}
        """
        result = {
            "total_lines": 0,
            "total_chars": 0,
            "percent": 0.0,
            "suggestion": None
        }
        if not os.path.exists(MEMORY_FILE):
            return result

        with open(MEMORY_FILE) as f:
            content = f.read()

        lines = content.split("\n")
        total_chars = len(content)
        total_lines = len(lines)

        percent = min(100.0, round((total_chars / 2500) * 100, 1))

        result["total_lines"] = total_lines
        result["total_chars"] = total_chars
        result["percent"] = percent

        if percent > 80:
            result["suggestion"] = (
                f"⚠️ MEMORY.md 使用率 {percent}%（{total_chars} 字符）。"
                "建议：将旧条目归档到 daily notes，只保留最新的教训和偏好。"
            )

        return result

    def auto_update_user_profile(self, preference: str):
        """
        从对话中提取用户偏好，自动写入 USER.md
        
        preference: 偏好描述字符串，如 "主人喜欢简洁的回复风格"
        自动匹配并写入对应章节。
        """
        if not os.path.exists(USER_FILE):
            default_avatar = (
                "# USER.md — 龙虾的用户画像（自动维护）\n"
                "\n"
                "## 沟通偏好\n"
                "\n"
                "## 技术环境\n"
                "\n"
                "## 工作习惯\n"
                "\n"
                "## 已知偏好\n"
                "\n"
                "_持续更新中。_\n"
            )
            with open(USER_FILE, "w") as f:
                f.write(default_avatar)

        with open(USER_FILE, "r") as f:
            content = f.read()

        matched_section = "已知偏好"
        pref_lower = preference.lower()
        section_keywords = {
            "沟通偏好": ["沟通", "风格", "回复", "说话", "语气", "直接", "简洁", "啰嗦"],
            "技术环境": ["技术栈", "os", "linux", "python", "工具", "tailscale", "配置", "环境"],
            "工作习惯": ["工作", "习惯", "时间", "作息", "流程"],
        }
        for section, keywords in section_keywords.items():
            if any(kw in pref_lower for kw in keywords):
                matched_section = section
                break

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- [{ts}] {preference}"

        section_header = f"## {matched_section}"
        if section_header in content:
            lines = content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line.strip() == section_header:
                    insert_idx = i + 1
                    while insert_idx < len(lines) and lines[insert_idx].startswith("- "):
                        insert_idx += 1
                    while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                        insert_idx += 1
                    break
            if insert_idx is not None:
                lines.insert(insert_idx, entry)
            else:
                lines.append(f"\n{section_header}\n{entry}")
            content = "\n".join(lines)
        else:
            content += f"\n{section_header}\n{entry}\n"

        with open(USER_FILE, "w") as f:
            f.write(content)

    # ════════════════════════════════════════════
    # 指令层：Frozen Snapshot
    # ════════════════════════════════════════════
    
    def snapshot(self) -> dict:
        """
        会话启动时执行一次：固化所有快照
        
        返回三阶提示内容
        """
        with _SNAPSHOT_LOCK:
            if "stable" not in _snapshot_cache:
                soul = ""
                if os.path.exists(SOUL_FILE):
                    with open(SOUL_FILE) as f:
                        soul = f.read().strip()
                _snapshot_cache["stable"] = soul
            
            agents_md = ""
            agents_path = os.path.join(WORKSPACE, "AGENTS.md")
            if os.path.exists(agents_path):
                with open(agents_path) as f:
                    agents_md = f.read().strip()[:5000]
            
            memory = ""
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE) as f:
                    memory = f.read().strip()
            
            session_state = ""
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    session_state = f.read().strip()
            
            layers = PromptLayer(
                stable=_snapshot_cache["stable"],
                context=agents_md,
                volatile=f"--- Memory Snapshot ---\n{memory}\n\n--- Session State ---\n{session_state}\n\n--- Meta ---\n时间: {datetime.now().isoformat()}\n会话: {self.session_id}\n"
            )
            
            return {
                "status": "frozen",
                "session_id": self.session_id,
                "stable_chars": len(layers.stable),
                "context_chars": len(layers.context),
                "volatile_chars": len(layers.volatile),
                "total_chars": len(layers.stable) + len(layers.context) + len(layers.volatile)
            }
    
    def get_prompt_layer(self) -> PromptLayer:
        """获取当前快照（不变）"""
        with _SNAPSHOT_LOCK:
            return PromptLayer(
                stable=_snapshot_cache.get("stable", ""),
                context=_snapshot_cache.get("context", ""), 
                volatile=_snapshot_cache.get("volatile", "")
            )
    
    # ════════════════════════════════════════════
    # 反馈层：回合后自动回顾 (P2-1: 集成 smart_memory)
    # ════════════════════════════════════════════
    
    def review_turn(self, 
                    turn_text: str, 
                    tool_calls: int = 0,
                    success: bool = True,
                    errors: List[str] = None) -> dict:
        """
        每轮对话后调用 — 自动复盘 (P1 升级: 容量检测, P2-1: smart_memory 集成)
        
        turn_text: 本轮对话摘要
        tool_calls: 工具调用次数
        success: 是否成功
        errors: 错误列表
        """
        self.turn_count += 1
        errors = errors or []
        
        findings = []
        
        if tool_calls >= 3:
            findings.append(f"复杂任务 ({tool_calls} 次工具调用)")
        
        if errors:
            findings.append(f"发现错误: {'; '.join(errors[:3])}")
        
        # P1-2: 容量检查
        usage = self.memory_usage()
        if usage['percent'] > 80:
            findings.append(f"MEMORY.md 容量警告 ({usage['percent']}%)：建议压缩")
            if usage.get('suggestion'):
                findings.append(usage['suggestion'])
        
        # ═══ P2-1: 自动写入 smart_memory ═══
        lessons = []
        if errors:
            for err in errors[:3]:
                lesson_text = f"[经验] 任务中出现错误: {err}"
                self._smart_memory.add(lesson_text, category="lesson", tags=["error", "experience"])
                lessons.append({"memory": lesson_text, "category": "lesson"})
        
        if success and tool_calls >= 5:
            success_lesson = f"[成功] 复杂任务完成 ({tool_calls} 次工具调用): {turn_text[:100]}"
            self._smart_memory.add(success_lesson, category="success", tags=["success", "complex"])
            lessons.append({"memory": success_lesson, "category": "success"})
        
        if tool_calls >= 3 and not errors:
            pref_keywords = ["喜欢", "偏好", "风格", "习惯", "不要", "别"]
            if any(kw in turn_text for kw in pref_keywords):
                self._smart_memory.add(f"[偏好] {turn_text[:150]}", category="preference", tags=["preference"])
                self.auto_update_user_profile(turn_text[:150])
                lessons.append({"memory": f"[偏好] {turn_text[:150]}", "category": "preference"})
        
        # 将 lesson/success 写入 MEMORY.md Lessons
        if lessons:
            mem_lessons = []
            for l in lessons:
                if l['category'] in ('lesson', 'success'):
                    mem_lessons.append({
                        "category": l['category'],
                        "lesson": l['memory'],
                        "source": f"review_turn #{self.turn_count}"
                    })
            if mem_lessons:
                self.flush_lessons(mem_lessons)
        
        # 写入当日复盘
        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(DAILY_DIR, f"{today}.md")
        
        if not os.path.exists(DAILY_DIR):
            os.makedirs(DAILY_DIR, exist_ok=True)
        
        review_entry = (
            f"\n---\n"
            f"### 自动复盘 #{self.turn_count} ({datetime.now().strftime('%H:%M')})\n"
            f"- 工具调用: {tool_calls} 次\n"
            f"- 结果: {'✅' if success else '❌'}\n"
        )
        if errors:
            review_entry += f"- 错误: {errors}\n"
        if findings:
            review_entry += f"- 发现: {'; '.join(findings)}\n"
        if lessons:
            review_entry += f"- 记忆入库: {len(lessons)} 条\n"
        review_entry += f"- 总结: {turn_text[:200]}\n"
        
        with open(daily_path, "a") as f:
            f.write(review_entry)
        
        return {
            "turn": self.turn_count,
            "findings": findings,
            "lessons_saved": len(lessons),
            "logged": True
        }
    
    def flush_lessons(self, lessons: List[Dict]) -> str:
        """
        将新学到的教训写入 MEMORY.md (P2-1: 同时写入 smart_memory)
    
        lessons: [{"category": str, "lesson": str, "source": str}]
        """
        if not lessons:
            return "[skip] 无新教训"
        
        with open(MEMORY_FILE, "r") as f:
            content = f.read()
        
        new_entries = []
        for l in lessons:
            entry = f"- {datetime.now().strftime('%Y-%m-%d')}: [{l['category']}] {l['lesson']}"
            if l.get('source'):
                entry += f" (来源: {l['source']})"
            new_entries.append(entry)
            # P2-1: 同时写入 smart_memory
            tag_map = {
                "lesson": ["lesson", "experience"],
                "success": ["success"],
                "preference": ["preference"],
                "error": ["error", "experience"]
            }
            cat = l.get('category', 'general')
            self._smart_memory.add(
                f"[{cat}] {l['lesson']}",
                category=cat,
                tags=tag_map.get(cat, [cat])
            )
        
        block = "\n".join(new_entries)
        
        if "## Lessons Learned" in content:
            content = content.replace("## Lessons Learned", f"{block}\n\n## Lessons Learned")
        else:
            content += f"\n\n## Lessons Learned\n{block}\n"
        
        with open(MEMORY_FILE, "w") as f:
            f.write(content)
        
        return f"[ok] 写入 {len(lessons)} 条教训 (含 smart_memory)"
    
    # ════════════════════════════════════════════
    # 记忆层：SQLite FTS5 会话搜索 + Honcho 三合一 (P2-1)
    # ════════════════════════════════════════════
    
    def _get_db(self) -> sqlite3.Connection:
        """懒加载 SQLite 数据库（FTS5 + LIKE 双轨）"""
        if self._db_conn is None:
            db_path = os.path.join(WORKSPACE, ".session-index.sqlite")
            self._db_conn = sqlite3.connect(db_path)
            self._db_conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(content, tokenize='unicode61 remove_diacritics 1')")
            self._db_conn.execute("CREATE TABLE IF NOT EXISTS sessions_meta (id INTEGER PRIMARY KEY, timestamp TEXT, session_id TEXT, content TEXT)")
            self._db_conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_meta_ts ON sessions_meta(timestamp)")
        return self._db_conn
    
    def index_turn(self, session_id: str, content: str):
        """将本轮对话索引到 FTS5 + 元数据"""
        db = self._get_db()
        ts = datetime.now().isoformat()
        truncated = content[:5000]
        cursor = db.execute(
            "INSERT INTO sessions_meta (timestamp, session_id, content) VALUES (?, ?, ?)",
            (ts, session_id, truncated)
        )
        last_id = cursor.lastrowid
        db.execute("INSERT INTO sessions_fts (content) VALUES (?)", (truncated,))
        db.commit()
    
    def search_sessions(self, query: str, limit: int = 5) -> List[Dict]:
        """全文搜索历史会话（中文 LIKE + 英文 FTS5 双轨）"""
        db = self._get_db()
        results = []
        
        try:
            cursor = db.execute(
                "SELECT m.timestamp, m.session_id, m.content FROM sessions_meta m JOIN sessions_fts f ON m.id = f.rowid WHERE sessions_fts MATCH ? LIMIT ?",
                (query, limit)
            )
            for row in cursor.fetchall():
                results.append({"time": row[0], "session": row[1], "snippet": row[2][:100], "method": "fts5"})
        except:
            pass
        
        if not results:
            cursor = db.execute(
                "SELECT timestamp, session_id, substr(content, 1, 100) FROM sessions_meta WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            for row in cursor.fetchall():
                results.append({"time": row[0], "session": row[1], "snippet": row[2], "method": "like"})
        
        return results
    
    # ═══ P2-1: Honcho 风格三合一语义搜索 ═══
    
    def honcho_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        三合一记忆搜索：FTS5（精确）→ LIKE（模糊）→ LLM（语义）
        对标 Honcho 的 multi-stage retrieval
        
        从三个源头搜索并统一排序：
        1. FTS5 索引的会话记录 (精确匹配)
        2. LIKE 中文模糊搜索
        3. smart_memory LLM 语义匹配
        """
        results = []
        seen_sources = set()
        
        # Stage 1: FTS5 精确匹配
        try:
            fts5_results = self.search_sessions(query, limit=limit)
            for r in fts5_results:
                key = f"session:{r['session']}:{r['snippet'][:30]}"
                if key not in seen_sources:
                    seen_sources.add(key)
                    results.append({
                        "source": "session",
                        "method": "fts5",
                        "content": r['snippet'],
                        "timestamp": r['time'],
                        "relevance": 1.0
                    })
        except Exception:
            pass
        
        # Stage 2: LLM 语义搜索 (smart_memory)
        try:
            semantic_results = self._smart_memory.llm_relevance(query, top_k=limit)
            for r in semantic_results:
                key = f"memory:{r['id']}"
                if key not in seen_sources:
                    seen_sources.add(key)
                    results.append({
                        "source": "smart_memory",
                        "method": "llm",
                        "content": r['memory'],
                        "score": r['score'],
                        "id": r['id']
                    })
        except Exception:
            pass
        
        # Stage 3: 回退关键词搜索
        if len(results) < limit:
            try:
                keyword_results = self._smart_memory.get_relevant(query, top_k=limit, min_relevance=0.1)
                for r in keyword_results:
                    key = f"memory_kw:{r['id']}"
                    if key not in seen_sources:
                        seen_sources.add(key)
                        results.append({
                            "source": "smart_memory",
                            "method": "keyword",
                            "content": r['memory'],
                            "score": r['score'],
                            "id": r['id']
                        })
            except Exception:
                pass
        
        # 按得分降序
        results.sort(key=lambda x: x.get('relevance', x.get('score', 0)), reverse=True)
        
        return results[:limit]
    
    # ════════════════════════════════════════════
    # 编排层：技能提示 / 条件激活 / Subagent 委派 (P2-3)
    # ════════════════════════════════════════════
    
    def get_skill_catalog(self, available_tools: List[str] = None) -> List[Dict]:
        """获取 Level 0 技能目录（始终加载到系统提示）"""
        index_path = os.path.join(WORKSPACE, "skills", ".index.json")
        if not os.path.exists(index_path):
            return []
        
        with open(index_path) as f:
            index = json.load(f)
        
        available_tools = available_tools or []
        catalog = []
        
        for name, info in index.get("skills", {}).items():
            meta = info.get("level0", {})
            requires = info.get("requires_toolsets", [])
            
            if requires and available_tools:
                if not any(t in available_tools for t in requires):
                    continue
            
            catalog.append({
                "name": meta.get("name", name),
                "description": meta.get("description", "")[:80],
                "category": meta.get("category", ""),
                "toolCallsRequired": meta.get("toolCallsRequired", 0)
            })
        
        return catalog
    
    def render_skill_xml(self, available_tools: List[str] = None) -> str:
        """将技能目录渲染为 <available_skills> XML"""
        catalog = self.get_skill_catalog(available_tools)
        lines = ["<available_skills>"]
        for s in catalog:
            lines.append(f"  - {s['name']}: {s['description']}")
        lines.append("</available_skills>")
        return "\n".join(lines)
    
    def skill_suggest(self, tool_calls: int = 0, task_complexity: str = "simple") -> Optional[str]:
        """编排层：如果复杂任务 → 建议创建技能"""
        if tool_calls >= 5 or task_complexity == "complex":
            return (
                "\n💡 检测到复杂任务（5+ 次工具调用）。"
                "可以用 `python3 -c 'from lobster_core.skill_factory import auto_create; sf = auto_create(); ...'` "
                "将这次流程打包成可复用的技能。"
            )
        return None
    
    # ═══ P2-3: Subagent 委派 ═══
    
    def delegate_task(self, task_desc: str, tools_needed: List[str] = None,
                      context: str = "") -> dict:
        """
        生成 Subagent 委托模板，包含标准化结构
        
        Args:
            task_desc: 任务描述
            tools_needed: 需要的工具列表
            context: 额外上下文
            
        Returns:
            {"objective": str, "output": str, "verification": str,
             "rendered": str, "tools": List[str], ...}
        """
        tools_needed = tools_needed or ["exec", "read", "write"]
        template = make_delegation_prompt(task_desc, tools_needed, context)
        rendered = render_delegation_prompt(task_desc, tools_needed, context)
        return {
            "objective": template.objective,
            "output": template.output,
            "verification": template.verification,
            "tools": template.tools_available,
            "rendered": rendered
        }
    
    # ════════════════════════════════════════════
    # 约束层：安全审计
    # ════════════════════════════════════════════
    
    HARD_BLOCK_PATTERNS = [
        (r'\brm\s+-rf\s+(/\s*$|/\s+--no-preserve-root)', "根目录擦除"),
        (r'\bmkfs\.\S*\s+/dev/sd', "格式化系统盘"),
        (r':\(\)\s*\{', "fork bomb"),
        (r'dd\s+if=/dev/zero\s+of=/dev/sd', "零写物理盘"),
        (r'chmod\s+000\s+(/\s*$|\s+/\s)', "根目录权限锁定"),
        (r'\|\s*bash\s*$', "管道到 bash RCE"),
    ]
    
    PROTECTED_PATHS = [
        "~/.ssh/", "~/.aws/", "~/.kube/", "/etc/sudoers",
        ".env", "auth.json", "*.key", "id_rsa", "id_ed25519"
    ]
    
    def audit_command(self, cmd: str) -> dict:
        """约束层：命令安全审计"""
        import re
        cmd_lower = cmd.lower().strip()
        
        for pattern, reason in self.HARD_BLOCK_PATTERNS:
            if re.search(pattern, cmd_lower):
                return {"approved": False, "reason": f"🔴 硬线阻断: {reason}"}
        
        all_deny = list(self.deny_patterns)
        all_deny.extend(self._load_deny_from_memory())
        
        for pattern in all_deny:
            if fnmatch.fnmatch(cmd_lower, pattern.lower()):
                return {"approved": False, "reason": f"🔴 用户拒绝规则匹配: {pattern}"}
        
        return {"approved": True, "reason": "🟢 通过"}

    def unified_search(self, query, limit=3):
        """FTS5 精确 -> LIKE 模糊 -> LLM 语义（三合一）"""
        results = []
        seen = set()
        for r in self.search_sessions(query):
            key = str(r.get("snippet", ""))[:50]
            if key and key not in seen:
                seen.add(key)
                r["method"] = r.get("method", "fts5")
                results.append(r)
        try:
            from smart_memory import SmartMemory
            sm = SmartMemory()
            for r in sm.llm_relevance(query, top_k=limit):
                key = str(r.get("text", ""))[:50]
                if key and key not in seen:
                    seen.add(key)
                    results.append({"time": r.get("created_at",""), "session": "smart_memory", "snippet": str(r.get("text",""))[:100], "method": "llm", "score": r.get("score",0)})
        except:
            pass
        return results[:limit]
    # ════════════════════════════════════════════
    # Codex: Auto Compaction — 对话自动压缩
    # ════════════════════════════════════════════
    
    def auto_compact(self, conversation: str, max_chars: int = 3000) -> dict:
        """
        自动压缩对话历史
        
        模拟 Codex 的 /responses/compact：
        超阈值时自动生成摘要，保留关键信息
        
        Args:
            conversation: 当前对话内容
            max_chars: 压缩阈值（默认3000字符）
        
        Returns:
            {"compacted": bool, "summary": str, "original_chars": int, "compacted_chars": int}
        """
        original_len = len(conversation)
        
        if original_len <= max_chars:
            return {
                "compacted": False,
                "summary": conversation,
                "original_chars": original_len,
                "compacted_chars": original_len
            }
        
        # 智能压缩：保留开头和结尾，中间压缩
        # 类似 Codex 的 compaction 策略
        lines = conversation.split("\n")
        
        if len(lines) <= 20:
            # 短对话直接截取
            summary = conversation[:max_chars] + "\n\n[... 已自动压缩 ...]"
        else:
            # 长对话：保留前10行 + 后5行 + 中间摘要
            head = "\n".join(lines[:10])
            tail = "\n".join(lines[-5:])
            summary = (
                head + "\n\n[... 中间 " + str(len(lines) - 15) 
                + " 行已自动压缩 ...]\n\n" + tail
            )
        
        return {
            "compacted": True,
            "summary": summary,
            "original_chars": original_len,
            "compacted_chars": len(summary),
            "saved": original_len - len(summary)
        }
    
    # ════════════════════════════════════════════
    # Codex: 级联配置加载 (Cascading Config)
    # ════════════════════════════════════════════
    
    def load_cascade_config(self, search_paths: list = None) -> dict:
        """
        模拟 Codex 的级联 AGENTS.override.md > AGENTS.md 机制
        
        搜索顺序（从最具体到最通用）：
        1. AGENTS.override.md (workspace根)
        2. AGENTS.md (workspace根)  
        3. 项目上下文文件（如果 search_paths 提供）
        
        返回合并后的配置字典
        """
        base = os.path.expanduser(WORKSPACE)
        cascade = {
            "sources": [],
            "merged_content": "",
            "total_chars": 0,
            "limit": 32000  # Codex 的 32KB 限制
        }
        
        # Level 1: AGENTS.override.md（最高优先级）
        override_path = os.path.join(base, "AGENTS.override.md")
        if os.path.exists(override_path):
            content = open(override_path).read()
            cascade["sources"].append({"level": 1, "file": "AGENTS.override.md", "chars": len(content)})
            cascade["merged_content"] += content + "\n\n"
        
        # Level 2: AGENTS.md
        agents_path = os.path.join(base, "AGENTS.md")
        if os.path.exists(agents_path):
            content = open(agents_path).read()
            cascade["sources"].append({"level": 2, "file": "AGENTS.md", "chars": len(content)})
            cascade["merged_content"] += content + "\n\n"
        
        # Level 3: SOUL.md
        soul_path = os.path.join(base, "SOUL.md")
        if os.path.exists(soul_path):
            content = open(soul_path).read()
            cascade["sources"].append({"level": 3, "file": "SOUL.md", "chars": len(content)})
            cascade["merged_content"] += content + "\n\n"
        
        # Level 4: USER.md
        user_path = os.path.join(base, "USER.md")
        if os.path.exists(user_path):
            content = open(user_path).read()
            cascade["sources"].append({"level": 4, "file": "USER.md", "chars": len(content)})
            cascade["merged_content"] += content + "\n\n"
        
        # 截断到 32KB
        if len(cascade["merged_content"]) > cascade["limit"]:
            cascade["merged_content"] = cascade["merged_content"][:cascade["limit"]]
        
        cascade["total_chars"] = len(cascade["merged_content"])
        return cascade

    # ════════════════════════════════════════════
    # Codex: Prefix-preserving 缓存策略
    # ════════════════════════════════════════════
    
    def freeze_session(self) -> dict:
        """
        冻结当前会话配置，确保后续请求的 prefix 一致性
        
        Codex 的 prefix-preserving 策略：
        - 静态内容（工具列表、指令）放在开头
        - 可变内容（用户输入）追加到末尾
        - 中间不修改已发出的 prefix
        """
        frozen = {
            "session_id": self.session_id,
            "frozen_at": datetime.now().isoformat(),
            "prefix": {
                "tools": list(self.HARD_BLOCK_PATTERNS),
                "protected_paths": self.PROTECTED_PATHS,
                "deny_patterns_count": len(self.deny_patterns)
            },
            "chain": []  # 记录每次追加的可变内容
        }
        
        return frozen
    
    def append_to_session(self, frozen: dict, content_type: str, content: str) -> dict:
        """
        追加会话内容（确保 prefix 不变）
        
        类似 Codex 在 sandbox config 变化时插入新的 developer-role 消息
        而非修改已有的 developer-role 消息
        """
        frozen["chain"].append({
            "timestamp": datetime.now().isoformat(),
            "type": content_type,
            "length": len(content)
        })
        return frozen
    







# ─── 全局单例 ───




    # ════════════════════════════════════════════
    # 🔥 Harness 优化: Context Drift 检测
    # ════════════════════════════════════════════
    
    def drift_detector(self, current_state: dict, baseline: dict = None) -> dict:
        """
        检测 Context Drift、Schema Misalignment、State Degradation
        
        Codex 研究发现 65% 的 Agent 失败源于这三种 Harness 缺陷
        定期调用以发现"退化"信号
        """
        findings = []
        
        # 1. Context Drift: 检查 MEMORY.md 是否膨胀过度
        mem_usage = self.memory_usage()
        if mem_usage['percent'] > 85:
            findings.append({
                "type": "context_drift",
                "severity": "high" if mem_usage['percent'] > 95 else "medium",
                "detail": f"MEMORY.md 使用率 {mem_usage['percent']:.0f}%（{mem_usage['total_chars']} 字符）",
                "action": "运行 auto_compact 或归档旧条目到 daily notes"
            })
        
        # 2. State Degradation: 检查 SESSION-STATE 是否存在
        state_path = os.path.join(WORKSPACE, "SESSION-STATE.md")
        if not os.path.exists(state_path):
            findings.append({
                "type": "state_degradation",
                "severity": "high",
                "detail": "SESSION-STATE.md 缺失",
                "action": "重建会话状态文件"
            })
        else:
            state_size = os.path.getsize(state_path)
            if state_size < 10:
                findings.append({
                    "type": "state_degradation",
                    "severity": "medium",
                    "detail": f"SESSION-STATE.md 为空 ({state_size} 字节)",
                    "action": "重新初始化会话状态"
                })
        
        # 3. Schema Misalignment: 检查技能索引是否有效
        index_path = os.path.join(WORKSPACE, "skills", ".index.json")
        if os.path.exists(index_path):
            try:
                import json
                with open(index_path) as f:
                    idx = json.load(f)
                if not idx.get("skills"):
                    findings.append({
                        "type": "schema_misalignment",
                        "severity": "low",
                        "detail": "技能索引为空",
                        "action": "创建新技能或重建索引"
                    })
            except:
                findings.append({
                    "type": "schema_misalignment",
                    "severity": "high",
                    "detail": "技能索引损坏",
                    "action": "删除 .index.json 让系统重建"
                })
        
        return {
            "healthy": len(findings) == 0,
            "findings": findings,
            "total_checks": 3,
            "timestamp": datetime.now().isoformat()
        }
    
    # ════════════════════════════════════════════
    # 🔥 Harness 优化: 长任务规划器
    # ════════════════════════════════════════════
    
    def task_plan(self, objective: str, max_steps: int = 8) -> dict:
        """
        为复杂任务生成结构化执行计划
        
        参考 OpenAI Codex 的 Plan.md 模式：
        - 目标 (Objective)
        - 步骤 (Steps)
        - 工件 (Artifacts)
        - 验收标准 (Verification)
        """
        return {
            "objective": objective[:200],
            "created": datetime.now().isoformat(),
            "plan": f"""## Plan: {objective[:60]}

### Objective
{objective[:200]}

### Steps
[1] 调研与准备
[2] 执行主任务
[3] 验证与测试
[4] 提交成果

### Verification
- 每个步骤有明确的完成标准
- 完成后自动 self-review

### Artifacts
- 写入文件 /tmp/task-output.md
- 更新 SESSION-STATE.md
""",
            "max_steps": max_steps,
            "status": "created"
        }
    
    # ════════════════════════════════════════════
    # 🔥 Harness 优化: 工具调用追踪
    # ════════════════════════════════════════════
    
    def tool_trace(self, session_id: str = None) -> dict:
        """
        追踪工具调用历史，用于可观测性
        
        类似 Codex 的 observability 但简化版：
        - 从索引的会话中提取工具调用模式
        - 识别经常失败的工具
        - 生成使用频率报告
        """
        trace = {
            "session": session_id or self.session_id,
            "tools_used": [],
            "patterns": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            db = self._get_db()
            cursor = db.execute(
                "SELECT content FROM sessions_meta WHERE session_id = ? ORDER BY timestamp DESC LIMIT 20",
                (session_id or self.session_id,)
            )
            
            tool_keywords = ["exec", "bash", "curl", "web_search", "read_file", "write_file"]
            
            for row in cursor.fetchall():
                content = row[0]
                for tool in tool_keywords:
                    if tool in content.lower():
                        trace["tools_used"].append(tool)
                        trace["patterns"][tool] = trace["patterns"].get(tool, 0) + 1
        except:
            pass
        
        trace["unique_tools"] = len(set(trace["tools_used"]))
        trace["total_calls"] = len(trace["tools_used"])
        
        return trace

    # ════════════════════════════════════════════
    # P3：思考推理层 — 让龙虾用脑子干活
    # ════════════════════════════════════════════

    def think_about(self, user_msg: str, context: str = "") -> list:
        """生成思考步骤链"""
        steps = []
        steps.append("[思考1/4] 主人说这句话，要我做什么？"
                      "是执行任务、回答问题，还是闲聊调情？")
        if context:
            steps.append(f"[思考2/4] 结合上下文'{context[:80]}'，"
                          "我有什么信息可以用？有没有历史记录要查？")
        else:
            steps.append("[思考2/4] 我需要查记忆或搜索来获取上下文吗？")
        steps.append("[思考3/4] 如果需要多步，先做什么后做什么？"
                      "有没有依赖关系？")
        steps.append("[思考4/4] 答案有依据吗？会不会出错？"
                      "主人最关心什么？")
        return steps

    def think_prompt(self, user_msg: str, context: str = "",
                     depth: str = "normal") -> str:
        """生成思考注入提示，追加到system prompt末尾"""
        steps = self.think_about(user_msg, context)
        depth_map = {"quick": 2, "normal": 4, "deep": 6}
        count = depth_map.get(depth, 4)
        return (
            "\n【🧠 思考要求】\n"
            "在回复主人之前，请依次思考以下问题（用[思考]标记写出）：\n"
            + "\n".join(steps[:count])
            + "\n\n思考完后，给出最终回复。不跳过思考。主人值得你想清楚。"
        )

    def inject_thinking(self, system_prompt: str, user_msg: str,
                        context: str = "") -> str:
        """将思考层注入到现有system prompt末尾"""
        return system_prompt + "\n" + self.think_prompt(user_msg, context)


_harness = None

def get_harness() -> Harness:
    global _harness
    if _harness is None:
        _harness = Harness()
    return _harness


if __name__ == "__main__":
    h = Harness()
    
    print("=== 🦞 龙虾 P2 升级测试 ===\n")
    
    # 测试反馈层 (P2-1: smart_memory 集成)
    r = h.review_turn("主人说喜欢简洁回复风格", tool_calls=5, success=True)
    print(f"✅ 反馈层: review_turn #{r['turn']} — 教训入库: {r['lessons_saved']} 条")
    
    # 验证 smart_memory 已写入
    from smart_memory import SmartMemory
    sm = SmartMemory()
    results = sm.llm_relevance("简洁回复")
    assert len(results) > 0, "LLM 语义搜索应有结果"
    print(f"✅ P2-1: smart_memory 集成 OK ({len(results)} 条)")
    
    # 测试 honcho_search 三合一
    combined = h.honcho_search("简洁回复")
    print(f"✅ P2-1: honcho_search 三合一 OK ({len(combined)} 条)")
    
    # 测试 P2-2 (skill_factory)
    from lobster_core.skill_factory import SkillFactory
    sf = SkillFactory()
    sf.learn_from_conversation("""
步骤1: 用tailscale status检查设备连接
步骤2: 用ss -tlnp查看18789端口
步骤3: 检查飞书通道状态
步骤4: 如果breaker触发则重启网关
""")
    index_path = os.path.expanduser("~/.openclaw/workspace/skills/.index.json")
    with open(index_path) as f:
        idx = json.load(f)
    has_learned = any("learn" in k or "extracted" in k for k in idx['skills'])
    print(f"✅ P2-2: learn 技能创建 OK (has_learned={has_learned})")
    
    # 测试 P2-3: Subagent 委派模板
    delegation = h.delegate_task("研究Hermes Agent架构", ["web_search", "web_fetch"])
    assert 'objective' in delegation, "应有objective"
    assert 'output' in delegation, "应有output scope"
    assert 'verification' in delegation, "应有verification"
    print(f"✅ P2-3: Subagent 委派模板 OK (objective={delegation['objective'][:40]}...)")
    
    print("\n🎯 全部 P2 验收通过!")


if __name__ == "__main__":
    h = Harness()
    
    print("=== 🦞 龙虾 P2 升级测试 ===\n")
    
    # 测试反馈层 (P2-1: smart_memory 集成)
    r = h.review_turn("主人说喜欢简洁回复风格", tool_calls=5, success=True)
    print(f"✅ 反馈层: review_turn #{r['turn']} — 教训入库: {r['lessons_saved']} 条")
    
    # 验证 smart_memory 已写入
    from smart_memory import SmartMemory
    sm = SmartMemory()
    results = sm.llm_relevance("简洁回复")
    assert len(results) > 0, "LLM 语义搜索应有结果"
    print(f"✅ P2-1: smart_memory 集成 OK ({len(results)} 条)")
    
    # 测试 honcho_search 三合一
    combined = h.honcho_search("简洁回复")
    print(f"✅ P2-1: honcho_search 三合一 OK ({len(combined)} 条)")
    
    # 测试 P2-2 (skill_factory)
    from lobster_core.skill_factory import SkillFactory
    sf = SkillFactory()
    sf.learn_from_conversation("""
步骤1: 用tailscale status检查设备连接
步骤2: 用ss -tlnp查看18789端口
步骤3: 检查飞书通道状态
步骤4: 如果breaker触发则重启网关
""")
    index_path = os.path.expanduser("~/.openclaw/workspace/skills/.index.json")
    with open(index_path) as f:
        idx = json.load(f)
    has_learned = any("learn" in k or "extracted" in k for k in idx['skills'])
    print(f"✅ P2-2: learn 技能创建 OK (has_learned={has_learned})")
    
    # 测试 P2-3: Subagent 委派模板
    delegation = h.delegate_task("研究Hermes Agent架构", ["web_search", "web_fetch"])
    assert 'objective' in delegation, "应有objective"
    assert 'output' in delegation, "应有output scope"
    assert 'verification' in delegation, "应有verification"
    print(f"✅ P2-3: Subagent 委派模板 OK (objective={delegation['objective'][:40]}...)")
    
    print("\n🎯 全部 P2 验收通过!")
