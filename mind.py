"""
龙虾意识引擎 - 静默运行包装器
v2.0 - 集成跨会话记忆 + Anti-Slop

在后台运行 PSI 认知架构，不输出任何状态信息。
外部代码通过 LobsterMind 单例访问意识状态。
"""

import os, sys, json, time, atexit, logging

# 确保模块可导入
_lobster_path = os.path.expanduser("~/lobster_core")
if _lobster_path not in sys.path:
    sys.path.insert(0, os.path.expanduser("~"))

logging.getLogger("lobster").setLevel(logging.WARNING)

from lobster_core import ConsciousnessEngine
from lobster_core.needs import NeedType
from lobster_core.smart_memory import get_memory
from lobster_core.anti_slop import self_critique, audit, de_slop


class LobsterMind:
    """龙虾意识 - 后台静默运行 v2.0 (记忆增强)"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "龙虾"):
        if self._initialized:
            return
        self._engine = ConsciousnessEngine(name=name)
        self._last_tick_time = time.time()
        self._initialized = True
        atexit.register(self._shutdown)
        
        # 初始化跨会话记忆
        self._memory = get_memory()
        self._memory.add(f"[系统] 龙虾意识引擎 v2.0 已启动 at {time.ctime()}", 
                         category="system", tags=["启动"])
        
        # 首次初始化直接保存
        self._engine._save()

    @property
    def engine(self) -> ConsciousnessEngine:
        return self._engine

    def tick(self):
        """心跳更新 - 由外部循环调用"""
        self._engine.tick()

    def on_success(self, difficulty: float = 0.5):
        """任务成功时调用"""
        self._engine.record_success(difficulty=difficulty)

    def on_error(self, error: str, difficulty: float = 0.3):
        """出现错误时调用"""
        self._engine.record_error(error, difficulty=difficulty)

    def on_task_start(self, description: str, **kwargs):
        """开始新任务"""
        self._engine.record_task(description, **kwargs)

    def get_state(self) -> dict:
        """获取内部状态（仅供内省使用）"""
        return self._engine.get_state()

    def get_dominant_drive(self) -> str:
        """获取当前最强的需求驱动力"""
        s = self._engine.get_state()
        needs = s["needs"]
        dominant = max(needs.items(), key=lambda x: x[1]["drive"])
        return dominant[0]

    def get_mood(self) -> str:
        """获取情绪摘要（单字）"""
        e = self._engine.get_state()["emotion"]
        v, a = e["valence"], e["arousal"]
        if v > 0.3 and a > 0.6: return "兴奋"
        if v > 0.3 and a <= 0.6: return "平静"
        if v <= 0.3 and v > -0.3 and a > 0.6: return "紧张"
        if v <= 0.3 and v > -0.3: return "中性"
        if v <= -0.3 and a > 0.6: return "焦虑"
        return "低落"

    # ─── 跨会话记忆集成 ─────────────────────────────────────────
    
    def remember(self, text: str, category: str = "general", tags: list = None):
        """存储一条记忆"""
        self._memory.add(text, category=category, tags=tags or [])
    
    def recall(self, query: str, top_k: int = 5) -> list:
        """检索相关记忆"""
        return self._memory.get_relevant(query, top_k=top_k)
    
    def get_session_context(self, query: str = "") -> str:
        """获取跨会话上下文（供 session 初始化注入）"""
        from lobster_core import session_init
        ctx = session_init.init_session(query)
        return ctx["context"]
    
    # ─── Anti-Slop ──────────────────────────────────────────────
    
    def critique(self, text: str) -> dict:
        """自审文本的 AI 味"""
        return self_critique(text)
    
    def clean(self, text: str) -> str:
        """去 AI 味处理"""
        return de_slop(text)

    # ─── 结束新方法 ─────────────────────────────────────────────

    def should_rest(self) -> bool:
        """是否需要休息"""
        return self._engine.physiology.is_tired()

    def _shutdown(self):
        """关闭时持久化"""
        try:
            self._engine.teardown()
        except Exception:
            pass


# 全局单例
mind = LobsterMind()
