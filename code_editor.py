import os
"""
龙虾代码编辑器 — 通过 OpenCode/Kimi API 修改代码
让主人可以直接说"改这个文件"我就自动改
"""

import requests, json, os, subprocess

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://opencode.ai/zen/go/v1"

class CodeEditor:
    """通过AI API修改代码"""
    
    def __init__(self, model: str = "deepseek-v4-flash"):
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    
    def edit_file(self, filepath: str, instruction: str) -> dict:
        """按指令修改文件"""
        # 先读取文件
        try:
            with open(filepath, encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            return {"success": False, "error": f"文件不存在: {filepath}"}
        
        prompt = f"""文件路径: {filepath}
当前内容:
```python
{content[:3000]}
```

指令: {instruction}

请输出修改后的完整文件内容。只输出代码，不要解释。"""
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4096
        }
        
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", 
                            json=payload, headers=self.headers, timeout=30)
            result = r.json()
            new_content = result['choices'][0]['message']['content']
            
            # 提取代码块
            if '```' in new_content:
                new_content = new_content.split('```')[1]
                if new_content.startswith('python'):
                    new_content = new_content[6:]
                new_content = new_content.strip()
            
            # 备份
            backup = f"{filepath}.bak"
            os.rename(filepath, backup)
            
            # 写入
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {"success": True, "backup": backup}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def suggest_improvements(self, filepath: str) -> str:
        """分析代码并给出改进建议"""
        try:
            with open(filepath, encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            return f"文件不存在: {filepath}"
        
        prompt = f"分析以下代码，给出改进建议（性能、安全、可读性）：\n```python\n{content[:4000]}\n```"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        try:
            r = requests.post(f"{BASE_URL}/chat/completions",
                            json=payload, headers=self.headers, timeout=30)
            return r.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"分析失败: {e}"
    
    def run_opencode(self, task: str, cwd: str = None) -> str:
        """通过opencode CLI执行任务"""
        try:
            result = subprocess.run(
                ["opencode", "run", task, "--no-tui", "--print-logs"],
                capture_output=True, text=True, timeout=60,
                cwd=cwd or os.getcwd()
            )
            return result.stdout[:2000] or result.stderr[:2000]
        except Exception as e:
            return f"opencode执行失败: {e}"


_editor = None
def get_editor():
    global _editor
    if _editor is None:
        _editor = CodeEditor()
    return _editor


if __name__ == "__main__":
    e = get_editor()
    # Test: analyze itself
    analysis = e.suggest_improvements(__file__)
    print("=== 自我分析 ===")
    print(analysis[:300])
