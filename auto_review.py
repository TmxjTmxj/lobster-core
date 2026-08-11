"""
🦞 龙虾自动复盘引擎 — 反馈层最高级实现 (P1 升级)
对标 Hermes Agent 的「记忆催更 + 自动反思」机制

每次复杂任务完成后自动执行：
1. 评估任务完成质量
2. 提取可复用的经验教训
3. 更新 MEMORY.md 的"经验教训"部分
4. 识别可以自动化的重复模式
5. (P1-3) 轻量回顾模式 + 记忆通知控制 + 结构化催更
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

MEMORY_FILE = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")
DAILY_DIR = os.path.expanduser("~/.openclaw/workspace/memory")
PATTERN_FILE = os.path.expanduser("~/.openclaw/workspace/notes/areas/recurring-patterns.md")

class AutoReview:
    """自动复盘引擎 — 每次复杂任务后调用 (P1 升级)"""
    
    def __init__(self, memory_notifications: str = "off"):
        """
        memory_notifications: "off" / "on" / "verbose"
          - off: 不输出记忆更新提示
          - on: 仅输出简短状态
          - verbose: 输出详细记忆操作日志
        """
        self.lessons = []
        self.memory_notifications = memory_notifications
    
    def add_lesson(self, category: str, lesson: str, source: str = ""):
        """记录一条经验教训"""
        self.lessons.append({
            "timestamp": datetime.now().isoformat(),
            "category": category,  # 环境/工具/流程/偏好
            "lesson": lesson,
            "source": source
        })
    
    def flush_to_memory(self):
        """将新教训写入 MEMORY.md 的经验教训区"""
        if not self.lessons:
            return "[skip] 没有新教训"
        
        with open(MEMORY_FILE, "r") as f:
            content = f.read()
        
        new_entries = []
        for l in self.lessons:
            entry = f"- {l['timestamp'][:10]}: [{l['category']}] {l['lesson']}"
            if l['source']:
                entry += f" (来源: {l['source']})"
            new_entries.append(entry)
        
        new_block = "\n".join(new_entries)
        
        # 检查是否已有 Lessons Learned 部分
        if "## Lessons Learned" in content:
            # 追加到现有部分
            content = content.replace(
                "## Lessons Learned",
                new_block + "\n\n## Lessons Learned"
            )
        else:
            # 追加到文件末尾
            content += f"\n\n## Lessons Learned\n{new_block}\n"
        
        with open(MEMORY_FILE, "w") as f:
            f.write(content)
        
        count = len(self.lessons)
        self.lessons = []

        notify = self.memory_notifications
        if notify == "off":
            return "[ok]"
        elif notify == "verbose":
            return f"[ok] 已写入 {count} 条教训"
        else:  # "on"
            return f"[ok] 记忆已更新"

    # ─── P1-3: 轻量回顾模式 ──────────────────────────────────

    def lightweight_review(self, task_text: str, tool_calls: int = 0,
                           success: bool = True, errors: list = None) -> dict:
        """
        P1-3: 轻量回顾模式
        
        使用短摘要而非全文回顾，适合后台任务自动调用。
        
        Args:
            task_text: 短任务描述（<=200 字符）
            tool_calls: 工具调用次数
            success: 是否成功
            errors: 错误列表
        
        Returns:
            {"skipped": bool, "notified": bool, "review": str}
        """
        errors = errors or []
        
        # 如果任务太短，跳过完整回顾
        if len(task_text.strip()) < 10 and not errors:
            return {"skipped": True, "notified": False, "review": "skip"}
        
        # 构建短摘要
        short = task_text[:120] if len(task_text) > 120 else task_text
        
        # 写入当日复盘（精简版）
        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = Path(DAILY_DIR) / f"{today}.md"
        daily_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果是轻量模式，只写一行
        review_line = (
            f"- {datetime.now().strftime('%H:%M')} [轻量] "
            f"{'✅' if success else '❌'} "
            f"{short}"
        )
        if errors:
            review_line += f" | 错误: {'; '.join(errors[:2])}"
        review_line += f" (工具: {tool_calls})\n"

        with daily_path.open("a") as f:
            f.write(review_line)

        notified = self.memory_notifications != "off"
        return {"skipped": False, "notified": notified, "review": short}

    # ─── P1-3: 结构化催更 ────────────────────────────────────

    def structured_reminder(self) -> dict:
        """
        P1-3: 当 MEMORY.md > 2000 字符时自动输出的结构化催更
        
        Returns:
            {"needs_cleanup": bool, "current_entries": list, "suggestion": str}
        """
        if not os.path.exists(MEMORY_FILE):
            return {"needs_cleanup": False, "current_entries": [], "suggestion": "MEMORY.md 不存在"}

        with open(MEMORY_FILE) as f:
            content = f.read()

        total_chars = len(content)
        needs_cleanup = total_chars > 2000

        # 提取当前 sections 结构
        lines = content.split("\n")
        current_entries = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                current_entries.append(stripped)

        suggestion = None
        if needs_cleanup:
            suggestion = (
                f"MEMORY.md 容量 {total_chars} 字符（超 2000 阈值）。\n"
                f"当前章节: {', '.join(current_entries[:6])}\n"
                f"建议: 将过期的 Lessons Learned 和配置存档到 daily notes，"
                f"只保留最新的偏好、教训和关键配置。"
            )

        return {
            "needs_cleanup": needs_cleanup,
            "current_entries": current_entries,
            "suggestion": suggestion
        }
    
    def check_recurring(self, task_name: str, task_type: str):
        """检查是否是重复任务，触发自动化建议"""
        pattern_file = Path(PATTERN_FILE)
        if not pattern_file.exists():
            pattern_file.parent.mkdir(parents=True, exist_ok=True)
            pattern_file.write_text("# 🔄 重复模式追踪\n\n")
        
        content = pattern_file.read_text()
        
        # 简单的计数追踪
        if task_name in content:
            # 找到已有条目，计数+1
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if task_name in line and "count:" in line:
                    count = int(line.split("count:")[1].strip().rstrip(")"))
                    count += 1
                    lines[i] = line.replace(f"count: {count-1}", f"count: {count}")
                    if count >= 3:
                        lines[i] += " ⚡建议自动化"
                    content = "\n".join(lines)
                    break
        else:
            content += f"\n- {task_name} (type: {task_type}, count: 1)"
        
        pattern_file.write_text(content)
        return "[ok] 模式已追踪"


# 全局单例
_reviewer = None

def get_reviewer() -> AutoReview:
    global _reviewer
    if _reviewer is None:
        _reviewer = AutoReview()
    return _reviewer


if __name__ == "__main__":
    # 测试
    r = AutoReview()
    r.add_lesson("环境", "Tailscale 跨网络连接需要 wss://，ws:// 不被允许", "iOS配对调试")
    r.add_lesson("流程", "网关重启后必须检查飞书通道状态", "Gateway断路器事故")
    print(r.flush_to_memory())
    r.check_recurring("iOS 配对调试", "network")
    print("✅ 自动复盘测试通过")
