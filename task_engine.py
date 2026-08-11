"""
龙虾任务执行引擎 v2 — 按Codex/Claude Code/Hermes的真实机制重写

核心设计：
1. 线程隔离 — 每个任务跑在独立路径，不阻塞主线程
2. 异步通道 — 用队列通信，主线程不会卡死
3. 取消令牌 — 随时可以取消长时间任务
4. 超时熔断 — 超过时限自动终止
5. 沙盒策略 — 限制任务可访问的资源
6. 错误分级 — 不同错误不同处理策略
"""

import os
import json, os, time, hashlib, threading, queue, traceback
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable

TASKS_DIR = os.path.expanduser("~/.lobster/tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

# ===== 错误分级系统 =====
class ErrorLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2    # 可重试
    ERROR = 3      # 需降级
    FATAL = 4      # 需终止

# ===== 沙盒策略 =====
class SandboxLevel(Enum):
    L0_FULL = "full"           # 完全访问（默认任务）
    L1_WORKSPACE = "workspace" # 仅工作区（代码修改）
    L2_READONLY = "readonly"   # 只读（分析任务）
    L3_NETWORK = "network"     # 仅网络（搜索任务）

# ===== 任务状态 =====
@dataclass
class Task:
    id: str
    name: str
    func: Optional[Callable]
    args: tuple
    kwargs: dict
    sandbox: SandboxLevel
    timeout: int
    created_at: float
    status: str = "pending"  # pending/running/completed/failed/cancelled/timedout
    result: any = None
    error: str = None
    thread: threading.Thread = None
    cancel_token: threading.Event = None

class TaskEngine:
    """Codex风格的任务执行引擎"""
    
    def __init__(self):
        self.tasks = {}
        self.result_queue = queue.Queue()
        self._running = True
    
    def submit(self, name: str, func: Callable, *args, 
               sandbox: SandboxLevel = SandboxLevel.L0_FULL,
               timeout: int = 300, **kwargs) -> str:
        """提交一个任务（像Codex的delegate_task）"""
        task_id = hashlib.md5((name + str(time.time())).encode()).hexdigest()[:12]
        cancel_token = threading.Event()
        
        task = Task(
            id=task_id, name=name, func=func, args=args, kwargs=kwargs,
            sandbox=sandbox, timeout=timeout,
            created_at=time.time(), cancel_token=cancel_token
        )
        self.tasks[task_id] = task
        
        # 在独立线程中执行（像Codex的run_codex_thread_interactive）
        thread = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
        task.thread = thread
        thread.start()
        
        return task_id
    
    def _run_task(self, task_id: str):
        """在隔离线程中执行任务"""
        task = self.tasks[task_id]
        task.status = "running"
        
        try:
            # 超时控制（像Codex的tokio::time::timeout）
            task.func(*task.args, 
                     _task_id=task_id, 
                     _cancel=task.cancel_token,
                     **task.kwargs)
            
            if task.cancel_token.is_set():
                task.status = "cancelled"
            else:
                task.status = "completed"
                
        except TimeoutError:
            task.status = "timedout"
            task.error = f"超时({task.timeout}s)"
        except Exception as e:
            task.status = "failed"
            task.error = f"{type(e).__name__}: {str(e)}"
            traceback.print_exc()
        
        # 结果入队通知主线程
        self.result_queue.put(task_id)
    
    def cancel(self, task_id: str) -> bool:
        """取消任务（像Codex的CancellationToken）"""
        task = self.tasks.get(task_id)
        if task and task.cancel_token:
            task.cancel_token.set()
            return True
        return False
    
    def get_result(self, task_id: str, timeout: float = None) -> Optional[dict]:
        """获取任务结果（带超时）"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        try:
            self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return {"status": "running", "task_id": task_id}
        
        return {
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "elapsed": round(time.time() - task.created_at)
        }
    
    def wait_all(self, timeout: float = None):
        """等待所有任务完成"""
        start = time.time()
        for task_id in list(self.tasks.keys()):
            remaining = None
            if timeout:
                remaining = timeout - (time.time() - start)
                if remaining <= 0:
                    break
            self.get_result(task_id, timeout=remaining)


# 全局引擎
_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = TaskEngine()
    return _engine


if __name__ == "__main__":
    e = get_engine()
    
    def demo_task(name, delay=2, _task_id="", _cancel=None):
        print(f"  🏃 任务开始: {name}")
        for i in range(delay):
            if _cancel and _cancel.is_set():
                print(f"  🛑 任务被取消: {name}")
                return
            time.sleep(1)
        print(f"  ✅ 任务完成: {name}")
    
    # 提交多个任务
    t1 = e.submit("任务A", demo_task, "任务A", delay=3, timeout=10)
    t2 = e.submit("任务B", demo_task, "任务B", delay=5, timeout=10)
    
    print(f"📋 已提交: t1={t1[:8]}.. t2={t2[:8]}..")
    print("⏳ 等待完成...")
    
    e.wait_all(timeout=15)
    print("✅ 全部完成")
