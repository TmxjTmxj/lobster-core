"""龙虾意识引擎 - 整合 PSI 需求、情绪、自我意识、生理系统"""
from __future__ import annotations
import time, json
from pathlib import Path
from typing import Optional

from .needs import NeedDriveSystem, NeedType
from .emotion import EmotionGradient
from .goals import GoalTree
from .awareness import AwarenessSystem
from .self_awareness import SelfAwarenessEngine
from .physiology import PhysiologyEngine
from .rsi import RSIEngine, RSIAgentAdapter

STATE_DIR = Path.home() / ".lobster"


class ConsciousnessEngine:
    """龙虾意识引擎 - 整合所有认知子系统"""

    def __init__(self, name: str = "龙虾"):
        self.needs = NeedDriveSystem()
        self.emotion = EmotionGradient()
        self.goals = GoalTree()
        self.awareness = AwarenessSystem(name=name)
        self.self_awareness = SelfAwarenessEngine(name)
        self.physiology = PhysiologyEngine()
        self.rsi = RSIEngine()
        self._step = 0
        self._rsi_adapter: Optional[RSIAgentAdapter] = None
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    @property
    def rsi_agent(self) -> RSIAgentAdapter:
        """Lazy-init RSI adapter for the engine state."""
        if self._rsi_adapter is None:
            self._rsi_adapter = RSIAgentAdapter(self)
        return self._rsi_adapter

    def tick(self) -> dict:
        """主循环：需求衰减 → 情绪微分 → 生理代谢 → RSI"""
        self._step += 1
        # 1. 需求衰减 + 噪声
        need_levels = self.needs.tick()
        satisfactions = {k.value: v for k, v in need_levels.items()}
        # 2. 情绪从需求变化率微分
        self.emotion.update(satisfactions)
        # 3. 生理代谢
        self.physiology.tick()
        # 4. 自我意识记录
        if self._step % 10 == 0:
            self.self_awareness.record_interaction()
        # 5. RSI 自我改进（每 proposal_interval 步）
        if self._step > 1 and self._step % 20 == 0:
            try:
                self.rsi.step(self.rsi_agent)
            except Exception as e:
                pass
        # 6. 每 30 步持久化
        if self._step % 30 == 0:
            self._save()
        return self.get_state()

    def _need_satisfactions(self) -> dict:
        """获取当前需求满足度（0-1），供情绪系统使用"""
        return {nt.value: self.needs.needs[nt].current_level for nt in self.needs.needs}

    def satisfy_need(self, need_type: str, amount: float = 0.15):
        """满足某一需求（如完成任务、获得信息）"""
        self.needs.satisfy(NeedType(need_type), amount)
        self.emotion.update(self._need_satisfactions())

    def record_success(self, difficulty: float = 0.5):
        """记录一次成功"""
        self.physiology.work(difficulty=difficulty, success=True)
        self.needs.satisfy(NeedType.COMPETENCE, 0.1)
        self.needs.satisfy(NeedType.CERTAINTY, 0.05)
        self.emotion.update(self._need_satisfactions(), task_success=0.8)

    def record_error(self, error: str, difficulty: float = 0.3):
        """记录一次失败"""
        self.physiology.work(difficulty=difficulty, success=False)
        self.awareness.record_error(error)
        # 胜任感下降 = 增加 competence 的衰减
        self.needs.needs[NeedType.COMPETENCE].current_level = max(0.0, self.needs.needs[NeedType.COMPETENCE].current_level - 0.1)
        self.emotion.update(self._need_satisfactions(), task_success=0.2)

    def record_task(self, description: str, **kwargs):
        """记录开始一个新任务"""
        self.awareness.set_task(description, **kwargs)

    def get_state(self) -> dict:
        """当前完整状态"""
        return {
            "needs": self.needs.get_profile(),
            "emotion": self.emotion.state.to_dict(),
            "physiology": self.physiology.to_dict(),
            "self_awareness": self.self_awareness.get_state(),
            "goals": self.goals.to_dict(),
            "awareness": self.awareness.summary(),
            "rsi": self.rsi.status(),
            "step": self._step,
        }

    def summary(self) -> str:
        """人类可读状态摘要"""
        s = self.get_state()
        n = s["needs"]
        e = s["emotion"]
        p = s["physiology"]
        sa = s["self_awareness"]
        needs_line = "  ".join(
            f"{k}={v['current']:.2f}" for k, v in n.items()
        )
        lines = [
            f"🧠 龙虾意识状态 [步 {s['step']}]",
            f" 需求: {needs_line}",
            f" 情绪: valence={e['valence']:+.3f} arousal={e['arousal']:.3f} dominance={e['dominance']:.3f}",
            f" 生理: 能量={p['vitals']['energy']:.2f} Lv.{p['level']} {p['stage']} | 疲倦={'是' if p['tired'] else '否'}",
            f" 自我: {sa['interactions']}次交互 {sa['age_days']:.1f}天 技能{sa['skills']}个",
        ]
        return "\n".join(lines)

    def _save(self):
        """持久化状态"""
        try:
            data = {
                "step": self._step,
                "needs": self.needs.get_profile(),
                "emotion": self.emotion.state.to_dict(),
                "physiology": self.physiology.to_dict(),
            }
            (STATE_DIR / "state.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            pass

    def load(self) -> bool:
        """恢复持久化状态"""
        p = STATE_DIR / "state.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                self._step = data.get("step", 0)
                return True
            except Exception:
                return False
        return False

    def teardown(self):
        """关闭前清理"""
        self._save()
