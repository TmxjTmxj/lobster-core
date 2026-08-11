"""
龙虾 — RSI 递归自我改进引擎

实现 Darwin-Gödel Machine 风格的自我改进循环：
  观察 -> 提案 -> 沙盒测试 -> 评估 -> 采纳/拒绝
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import numpy as np, time, logging

logger = logging.getLogger("lobster.rsi")


# 内联最小化 FitnessEvaluator（移除 laap.evaluation.fitness 依赖）
class FitnessEvaluator:
    """Minimal fitness evaluator for RSI."""

    def composite_fitness(self, agent) -> float:
        # agent 需要有 needs 和 emotion_gradient 属性
        fitness = 0.5
        if hasattr(agent, 'needs'):
            need_vals = [n.current_level for n in agent.needs.needs.values()]
            fitness = float(np.mean(need_vals))
        if hasattr(agent, 'emotion_gradient'):
            eg = agent.emotion_gradient
            fitness = fitness * 0.7 + (eg.state.valence + 1.0) / 2.0 * 0.3
        return fitness


@dataclass
class ImprovementProposal:
    id: str = ""
    episode: int = 0
    hypothesis: str = ""
    modification: Dict[str, Any] = field(default_factory=dict)
    expected_impact: float = 0.0
    confidence: float = 0.5
    tested: bool = False
    test_result: Optional[float] = None
    adopted: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "episode": self.episode,
            "hypothesis": self.hypothesis[:60],
            "mod_type": self.modification.get("type", "unknown"),
            "expected_impact": round(self.expected_impact, 3),
            "confidence": round(self.confidence, 2),
            "tested": self.tested,
            "test_result": round(self.test_result, 3) if self.test_result is not None else None,
            "adopted": self.adopted,
        }


@dataclass
class SandboxResult:
    proposal_id: str; success: bool; score_delta: float
    side_effects: List[str]; error: Optional[str] = None


class RSIAgentAdapter:
    """Minimal adapter so RSIEngine can work with ConsciousnessEngine."""

    def __init__(self, engine):
        self.engine = engine
        self.step_count = 0
        self.config = type('Config', (), {'exploration_rate': 0.2, 'learning_rate': 0.1})()
        self.emotion_gradient = engine.emotion
        self.needs = engine.needs
        self.memory = type('Mem', (), {'recent_reflections': lambda n: [],
                                        'best_skills': lambda n: []})()

    @property
    def step_count(self):
        return self.engine._step

    @step_count.setter
    def step_count(self, v):
        pass

    def apply_modification(self, mod: Dict[str, Any]) -> bool:
        try:
            mt = mod.get("type")
            params = mod.get("params", {})
            if mt == "adjust_exploration":
                self.config.exploration_rate = max(0.01, min(0.5, params.get("value", 0.2)))
            elif mt == "adjust_learning_rate":
                self.config.learning_rate = max(0.01, min(0.5, params.get("value", 0.1)))
            elif mt == "adjust_needs":
                for need_str, adj in params.items():
                    from .needs import NeedType
                    try:
                        nt = NeedType(need_str)
                        if nt in self.needs.needs:
                            for k, v in adj.items():
                                if hasattr(self.needs.needs[nt], k):
                                    setattr(self.needs.needs[nt], k, v)
                    except ValueError:
                        pass
            return True
        except Exception as e:
            logger.warning(f"apply_modification failed: {e}")
            return False


class RSIEngine:
    """递归自我改进引擎"""

    def __init__(self, proposal_interval: int = 20,
                 adoption_threshold: float = 0.05):
        self.proposal_interval = proposal_interval
        self.adoption_threshold = adoption_threshold
        self.proposals: List[ImprovementProposal] = []
        self.adopted_count = 0
        self.test_count = 0
        self.last_proposal_step = 0
        self.fitness_history: List[float] = []
        self.noise_level = 0.0
        self.meaning_density = 0.0
        self.fixed_point_count = 0
        self._templates = [
            self._propose_adjust_exploration,
            self._propose_adjust_learning_rate,
            self._propose_adjust_needs,
        ]

    def step(self, agent_adapter: RSIAgentAdapter, force=False) -> Optional[ImprovementProposal]:
        if not force and agent_adapter.step_count - self.last_proposal_step < self.proposal_interval:
            return None

        ev = FitnessEvaluator()
        fitness = ev.composite_fitness(agent_adapter)
        self.fitness_history.append(fitness)
        self._update_noise_meaning()

        proposal = self._generate(agent_adapter)
        if not proposal:
            return None

        self.proposals.append(proposal)
        self.last_proposal_step = agent_adapter.step_count

        if len(self.fitness_history) >= 2:
            result = self._sandbox_test(agent_adapter, proposal)
            self.test_count += 1
            if result.success and result.score_delta > self.adoption_threshold:
                self._adopt(agent_adapter, proposal, result)

        return proposal

    def _generate(self, agent) -> Optional[ImprovementProposal]:
        # Template-based generation only (no LLM dependency)
        chosen_template = np.random.choice(self._templates)
        proposal = chosen_template(agent)
        return proposal

    def _propose_adjust_exploration(self, agent):
        cur = agent.config.exploration_rate
        conf = agent.emotion_gradient.state.confidence
        if conf < 0.3:
            new_v = min(0.5, cur + 0.1)
            hyp = "置信度偏低，增加探索以收集信息"
        else:
            new_v = max(0.05, cur - 0.05)
            hyp = "置信度足够，降低探索提高利用"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_exploration", "params": {"value": new_v}},
            expected_impact=0.1 * (cur - new_v),
            confidence=0.6 + 0.3 * conf,
        )

    def _propose_adjust_learning_rate(self, agent):
        vol = agent.emotion_gradient.reward_volatility
        cur = agent.config.learning_rate
        if (vol or 0) > 0.3:
            new_v = max(0.01, cur * 0.8); hyp = "奖励波动大，降低学习率"
        else:
            new_v = min(0.3, cur * 1.2); hyp = "环境稳定，增加学习率"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_learning_rate", "params": {"value": new_v}},
            expected_impact=0.05, confidence=0.5,
        )

    def _propose_adjust_needs(self, agent):
        from .needs import NeedType
        dominant, _ = agent.needs.get_dominant_need()
        if not dominant:
            return self._propose_adjust_exploration(agent)
        key = dominant.value
        if agent.needs.needs[dominant].current_level < 0.3:
            adj = {key: {"decay_rate": 0.005}}
            hyp = f"需求 {key} 长期匮乏，降低衰减"
        else:
            adj = {key: {"importance": 1.2}}
            hyp = f"增强需求 {key} 影响权重"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_needs", "params": adj},
            expected_impact=0.08, confidence=0.55,
        )

    def _sandbox_test(self, agent, proposal) -> SandboxResult:
        from .needs import NeedType
        ev = FitnessEvaluator()
        baseline = ev.composite_fitness(agent)
        orig_eps = agent.config.exploration_rate
        orig_lr = agent.config.learning_rate

        success = agent.apply_modification(proposal.modification)
        if not success:
            return SandboxResult(proposal.id, False, 0.0, ["error"])

        post = ev.composite_fitness(agent)
        agent.config.exploration_rate = orig_eps
        agent.config.learning_rate = orig_lr
        delta = post - baseline
        proposal.tested = True
        proposal.test_result = delta
        return SandboxResult(proposal.id, delta > 0, delta, [] if delta > 0 else ["negative"])

    def _adopt(self, agent, proposal, result):
        if agent.apply_modification(proposal.modification):
            proposal.adopted = True
            self.adopted_count += 1

    def _update_noise_meaning(self):
        if len(self.fitness_history) < 5:
            return
        recent = self.fitness_history[-5:]
        self.noise_level = float(np.std(recent))
        deltas = np.diff(recent)
        meaningful = [d for d in deltas if abs(d) > 0.01]
        self.meaning_density = len(meaningful) / max(1, len(deltas))
        self.fixed_point_count = 0 if self.noise_level >= 0.01 else self.fixed_point_count + 1

    def info_integration(self) -> float:
        return self.meaning_density / max(0.01, self.noise_level) if self.noise_level > 0 else 0.0

    def adoption_rate(self, window=20) -> float:
        recent = self.proposals[-window:] if self.proposals else []
        if not recent:
            return 0.0
        tested = [p for p in recent if p.tested]
        return sum(1 for p in tested if p.adopted) / max(1, len(tested))

    def status(self) -> dict:
        return {
            "total": len(self.proposals),
            "adopted": self.adopted_count,
            "test_count": self.test_count,
            "adoption_rate": round(self.adoption_rate(), 3),
            "noise": round(self.noise_level, 4),
            "meaning": round(self.meaning_density, 4),
            "info_integration": round(self.info_integration(), 4),
            "stuck": self.fixed_point_count >= 10,
            "recent": [p.to_dict() for p in self.proposals[-5:]],
        }
