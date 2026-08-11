"""
龙虾长任务管理器 — 借鉴Codex/Hermes的任务分解和执行机制
支持：任务规划→分解→执行→进度追踪→超时恢复
防止：任务卡死、不返回结果、不回消息
"""

import os
import json, os, time, hashlib, threading, traceback, sys

TASKS_DIR = os.path.expanduser("~/.lobster/tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

class TaskManager:
    """长任务管理 - 防卡死、可恢复"""
    
    def __init__(self):
        self.active_tasks = {}
        self.timeout = 300  # 默认5分钟超时
        self.heartbeat_interval = 30  # 30秒心跳
    
    def create_task(self, name: str, steps: list, timeout: int = 300) -> str:
        """创建一个分解好的长任务"""
        task_id = hashlib.md5((name + str(time.time())).encode()).hexdigest()[:12]
        task = {
            "id": task_id,
            "name": name,
            "steps": [{"id": f"s{i}", "desc": s, "status": "pending"} 
                      for i, s in enumerate(steps)],
            "current_step": 0,
            "total_steps": len(steps),
            "status": "running",
            "created_at": time.time(),
            "timeout": timeout,
            "heartbeat": time.time(),
            "result": None,
            "error": None
        }
        
        # 持久化
        with open(os.path.join(TASKS_DIR, f"{task_id}.json"), 'w', encoding='utf-8') as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        
        self.active_tasks[task_id] = task
        return task_id
    
    def heartbeat(self, task_id: str):
        """心跳 - 告诉系统我还活着"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["heartbeat"] = time.time()
    
    def check_timeout(self, task_id: str) -> bool:
        """检查任务是否超时"""
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        elapsed = time.time() - task["heartbeat"]
        return elapsed > task["timeout"]
    
    def complete_step(self, task_id: str, step_id: str, result: str = ""):
        """完成一个子任务"""
        task = self._get_task(task_id)
        if not task:
            return False
        
        for step in task["steps"]:
            if step["id"] == step_id:
                step["status"] = "completed"
                step["result"] = result
                step["completed_at"] = time.time()
                task["current_step"] += 1
                break
        
        # 检查是否全部完成
        if task["current_step"] >= task["total_steps"]:
            task["status"] = "completed"
            task["result"] = result
        
        self._save_task(task)
        return True
    
    def fail_step(self, task_id: str, step_id: str, error: str):
        """子任务失败"""
        task = self._get_task(task_id)
        if not task:
            return
        
        for step in task["steps"]:
            if step["id"] == step_id:
                step["status"] = "failed"
                step["error"] = error
                break
        
        task["status"] = "failed"
        task["error"] = error
        self._save_task(task)
    
    def get_status(self, task_id: str) -> dict:
        """获取任务状态"""
        task = self._get_task(task_id)
        if not task:
            return {"status": "not_found"}
        
        return {
            "id": task["id"],
            "name": task["name"],
            "status": task["status"],
            "progress": f"{task['current_step']}/{task['total_steps']}",
            "current_step": task["current_step"],
            "total_steps": task["total_steps"],
            "elapsed": round(time.time() - task["created_at"])
        }
    
    def recover(self, task_id: str) -> dict:
        """恢复中断的任务"""
        task = self._get_task(task_id)
        if not task:
            return {"status": "not_found"}
        
        if task["status"] == "running":
            # 找出未完成的步骤继续
            pending = [s for s in task["steps"] if s["status"] == "pending"]
            task["heartbeat"] = time.time()
            self._save_task(task)
            
            return {
                "task_id": task_id,
                "recovered": True,
                "next_steps": pending,
                "progress": f"{task['current_step']}/{task['total_steps']}"
            }
        
        return {"task_id": task_id, "recovered": False, "reason": f"任务状态: {task['status']}"}
    
    def _get_task(self, task_id: str) -> dict:
        """获取任务，优先从内存获取"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # 从磁盘恢复
        path = os.path.join(TASKS_DIR, f"{task_id}.json")
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                task = json.load(f)
            self.active_tasks[task_id] = task
            return task
        return None
    
    def _save_task(self, task: dict):
        """持久化任务"""
        path = os.path.join(TASKS_DIR, f"{task['id']}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(task, f, ensure_ascii=False, indent=2)


# 全局单例
_task_manager = None
def get_task_manager():
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


if __name__ == "__main__":
    tm = get_task_manager()
    # 测试：创建一个分解任务
    tid = tm.create_task("搜图+分析+保存", [
        "搜索PornHub劲爆图片",
        "用MiniCPM-V分析图片内容", 
        "保存分析结果到文件"
    ], timeout=600)
    print(f"✅ 任务已创建: {tid}")
    print(f"   步骤: {tm.get_status(tid)['progress']}")
    
    tm.complete_step(tid, "s0", "搜到20张图")
    print(f"   步骤1完成, 进度: {tm.get_status(tid)['progress']}")
    
    tm.complete_step(tid, "s1", "分析完成")
    print(f"   步骤2完成, 进度: {tm.get_status(tid)['progress']}")
    
    print(f"   状态: {tm.get_status(tid)['status']}")
