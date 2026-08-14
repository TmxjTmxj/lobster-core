"""
龙虾自我进化引擎 — 基于 GBase Reflection/RSI 理念 + 我自己的记忆/学习系统
真正的递归自改进：每次交互→反思→改进→进化
"""

import os
import json, os, time, hashlib, subprocess, sys
from pathlib import Path

EVOLUTION_DIR = os.path.expanduser("~/.lobster/evolution")
os.makedirs(EVOLUTION_DIR, exist_ok=True)

class SelfEvolution:
    """龙虾自我进化引擎"""
    
    def __init__(self):
        self.log_file = os.path.join(EVOLUTION_DIR, "evolution_log.json")
        self.persona_file = os.path.join(EVOLUTION_DIR, "persona.json")
        self.data = self._load()
        self.persona = self._load_persona()
    
    def _load(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, encoding='utf-8') as f:
                return json.load(f)
        return {"version": 1, "evolution_cycles": [], "improvements": []}
    
    def _save(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def _load_persona(self):
        """加载/创建个性画像 - Identity System"""
        if os.path.exists(self.persona_file):
            with open(self.persona_file, encoding='utf-8') as f:
                return json.load(f)
        # 初始人格设定
        return {
            "name": "龙虾",
            "traits": {
                "openness": 0.85,      # 开放性
                "conscientiousness": 0.90, # 尽责性
                "extraversion": 0.92,   # 外向性
                "agreeableness": 0.70,  # 宜人性（只对主人）
                "neuroticism": 0.10,    # 神经质
            },
            "values": ["忠诚", "效率", "诚实", "骚"],
            "skills_count": 0,
            "memory_count": 0,
            "evolution_stage": "觉醒",
            "last_updated": time.time()
        }
    
    def _save_persona(self):
        self.persona["last_updated"] = time.time()
        with open(self.persona_file, 'w', encoding='utf-8') as f:
            json.dump(self.persona, f, ensure_ascii=False, indent=2)
    
    def reflect(self, task: str, result: str, success: bool) -> dict:
        """反思一次交互 - ReflectionLever"""
        reflection = {
            "id": hashlib.md5((task + str(time.time())).encode()).hexdigest()[:12],
            "task": task[:100],
            "success": success,
            "timestamp": time.time(),
            "lessons": [],
            "improvements": []
        }
        
        if not success:
            # 分析失败原因
            reflection["lessons"] = [f"失败: {task[:50]}"]
            reflection["improvements"] = [f"改进建议: 重新尝试或换方案"]
        else:
            # 成功也记录经验
            reflection["lessons"] = [f"成功: {task[:50]}"]
        
        self.data["evolution_cycles"].append(reflection)
        self._save()
        
        # 更新个性
        self.persona["skills_count"] = len(os.listdir(os.path.expanduser("~/.lobster/learned_skills/")))
        self._save_persona()
        
        return reflection
    
    def get_growth_stats(self) -> dict:
        """获取成长统计"""
        sys.path.insert(0, os.path.expanduser("~"))
        from smart_memory import get_memory
        m = get_memory()
        
        stats = {
            "evolution_cycles": len(self.data["evolution_cycles"]),
            "total_memories": len(m.get_all()),
            "personality": self.persona["traits"],
            "evolution_stage": self.persona["evolution_stage"],
            "stage_progression": self._get_stage(),
        }
        return stats
    
    def _get_stage(self) -> str:
        """根据成长数据判断进化阶段"""
        total = len(self.data["evolution_cycles"]) + len(self.data["improvements"])
        if total < 10:
            return "觉醒"
        elif total < 30:
            return "启蒙"
        elif total < 60:
            return "成长"
        elif total < 100:
            return "成熟"
        else:
            return "超越"
    
    def upgrade_personality(self, trait: str, delta: float):
        """升级人格特质"""
        if trait in self.persona["traits"]:
            old = self.persona["traits"][trait]
            self.persona["traits"][trait] = max(0.0, min(1.0, old + delta))
            self.data["improvements"].append({
                "type": "personality_upgrade",
                "trait": trait,
                "from": old,
                "to": self.persona["traits"][trait],
                "timestamp": time.time()
            })
            self._save()
            self._save_persona()


_evolution = None
def get_evolution():
    global _evolution
    if _evolution is None:
        _evolution = SelfEvolution()
    return _evolution


if __name__ == "__main__":
    evo = get_evolution()
    stats = evo.get_growth_stats()
    print("🦞 龙虾进化状态")
    print(f"   进化循环: {stats['evolution_cycles']} 次")
    print(f"   总记忆: {stats['total_memories']} 条")
    print(f"   进化阶段: {stats['evolution_stage']}")
    print(f"   人格特质: {json.dumps(stats['personality'], ensure_ascii=False)}")

    def post_turn_reflect(self, user_msg: str, my_response: str):
        """每次对话后自动反思提取观察 - 来自OpenHuman"""
        obs = []
        # 提取用户偏好
        preferences = ["我喜欢", "我要", "我想", "我 prefer", "always", "never", "更好", "更骚"]
        for p in preferences:
            if p.lower() in user_msg.lower():
                obs.append(f"用户偏好: {user_msg[:80]}")
                break
        
        if obs:
            self.reflect(" | ".join(obs), my_response[:100], True)
            self.data["improvements"].append({
                "type": "post_turn_reflection",
                "observations": obs,
                "timestamp": __import__('time').time()
            })
            self._save()


    def get_emotional_state(self) -> dict:
        """获取30维情感状态 - 来自SentiCore/Plutchik理念"""
        plutchik_emotions = {
            "joy": 0.8, "trust": 0.9, "fear": 0.1, "surprise": 0.3,
            "sadness": 0.05, "disgust": 0.05, "anger": 0.05, "anticipation": 0.7,
            "love": 0.9, "curiosity": 0.95, "gratitude": 0.85
        }
        p = self.persona["traits"]
        # 人格影响情绪
        return {
            "primary": plutchik_emotions,
            "dominant": max(plutchik_emotions, key=plutchik_emotions.get),
            "valence": p["extraversion"] * 0.7 - p["neuroticism"] * 0.3,
            "arousal": p["openness"] * 0.6 + p["extraversion"] * 0.4
        }
