"""
龙虾学习闭环 - Inspired by Hermes Agent
自动从经验中学习、创建技能、持续进化
"""

import os
import json, os, time, hashlib
from pathlib import Path

SKILLS_DIR = os.path.expanduser("~/.lobster/learned_skills")
MEMORY_DIR = os.path.expanduser("~/.lobster")
os.makedirs(SKILLS_DIR, exist_ok=True)

class LearningLoop:
    """闭环学习系统 - 从经验中创建技能，在使用中改进"""
    
    def __init__(self):
        self.log_file = os.path.join(MEMORY_DIR, "learning_log.json")
        self.log = self._load()
    
    def _load(self):
        if os.path.exists(self.log_file):
            with open(self.log_file) as f:
                return json.load(f)
        return {"interactions": [], "skills_created": [], "user_model": {}}
    
    def _save(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, ensure_ascii=False, indent=2)
    
    def record_interaction(self, task: str, success: bool, complexity: str = "medium"):
        """记录一次交互，为技能创建做准备"""
        entry = {
            "timestamp": time.time(),
            "task": task,
            "success": success,
            "complexity": complexity,
            "id": hashlib.md5((task + str(time.time())).encode()).hexdigest()[:12]
        }
        self.log["interactions"].append(entry)
        
        # Keep only last 100
        if len(self.log["interactions"]) > 100:
            self.log["interactions"] = self.log["interactions"][-100:]
        
        self._save()
        return entry
    
    def should_create_skill(self, task: str) -> bool:
        """判断一个复杂任务是否值得创建为技能"""
        # Check if similar task was done multiple times
        similar = [i for i in self.log["interactions"] 
                   if self._similar(task, i["task"]) and i["success"]]
        return len(similar) >= 2  # Done successfully ≥2 times
    
    def create_skill(self, name: str, description: str, command: str, category: str = "learned"):
        """从经验中创建一个可复用的技能"""
        skill = {
            "name": name,
            "description": description,
            "command": command,
            "category": category,
            "created_at": time.time(),
            "updated_at": time.time(),
            "use_count": 0,
            "success_count": 0,
            "version": 1
        }
        
        skill_file = os.path.join(SKILLS_DIR, f"{name}.json")
        with open(skill_file, 'w') as f:
            json.dump(skill, f, ensure_ascii=False, indent=2)
        
        self.log["skills_created"].append({
            "name": name,
            "created_at": time.time()
        })
        self._save()
        return skill
    
    def use_skill(self, name: str, success: bool):
        """使用技能并记录效果 - 技能自我改进"""
        skill_file = os.path.join(SKILLS_DIR, f"{name}.json")
        if not os.path.exists(skill_file):
            return None
        
        with open(skill_file) as f:
            skill = json.load(f)
        
        skill["use_count"] += 1
        if success:
            skill["success_count"] += 1
        skill["updated_at"] = time.time()
        
        # Self-improvement: auto-bump version every 5 successful uses
        if skill["success_count"] > 0 and skill["success_count"] % 5 == 0:
            skill["version"] += 1
        
        with open(skill_file, 'w') as f:
            json.dump(skill, f, ensure_ascii=False, indent=2)
        
        return skill
    
    def list_skills(self) -> list:
        """列出所有学到的技能"""
        skills = []
        for f in os.listdir(SKILLS_DIR):
            if f.endswith('.json'):
                with open(os.path.join(SKILLS_DIR, f)) as fh:
                    skills.append(json.load(fh))
        return sorted(skills, key=lambda s: -s["use_count"])
    
    def update_user_model(self, key: str, value: str):
        """更新用户模型 - 更懂主人"""
        if "user_model" not in self.log:
            self.log["user_model"] = {}
        
        if key not in self.log["user_model"]:
            self.log["user_model"][key] = {
                "value": value,
                "learned_at": time.time(),
                "confidence": 1
            }
        else:
            # Increase confidence if consistent
            entry = self.log["user_model"][key]
            if entry["value"] == value:
                entry["confidence"] = min(entry["confidence"] + 0.5, 10)
            else:
                entry["value"] = value
                entry["confidence"] = max(entry["confidence"] - 0.5, 1)
            entry["learned_at"] = time.time()
        
        self._save()
    
    def get_user_profile(self) -> dict:
        """获取主人画像"""
        return self.log.get("user_model", {})
    
    def _similar(self, a: str, b: str) -> bool:
        """简单的字符串相似度判断"""
        a_words = set(a.lower().split()[:5])
        b_words = set(b.lower().split()[:5])
        if not a_words or not b_words:
            return False
        overlap = len(a_words & b_words)
        return overlap / max(len(a_words), len(b_words)) > 0.3


# Singleton
_learning_loop = None
def get_learner():
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = LearningLoop()
    return _learning_loop


if __name__ == "__main__":
    ll = get_learner()
    print("🧠 龙虾学习闭环")
    print(f"已记录交互: {len(ll.log['interactions'])}")
    print(f"已创建技能: {len(ll.log['skills_created'])}")
    print(f"主人画像维度: {len(ll.log.get('user_model', {}))}")
