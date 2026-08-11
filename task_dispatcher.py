"""龙虾任务分发器 — 借鉴orca并行Agent理念"""
import threading
class TaskDispatcher:
    def parallel_map(self, tasks: list, worker_func, max_workers: int = 3):
        results = {}; threads = []; lock = threading.Lock()
        def worker(tid, td):
            try:
                with lock: results[tid] = {"status": "ok", "result": worker_func(td)}
            except Exception as e:
                with lock: results[tid] = {"status": "failed", "error": str(e)}
        for i, task in enumerate(tasks[:max_workers]):
            t = threading.Thread(target=worker, args=(i, task), daemon=True)
            t.start(); threads.append(t)
        for t in threads: t.join(timeout=60)
        return results
