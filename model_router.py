import os
"""
龙虾模型路由器 — 根据任务类型自动切换最优模型
"""
import requests, json, base64, os

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://opencode.ai/zen/go/v1"

class ModelRouter:
    """根据任务自动选择模型"""
    
    ROUTING = {
        "chat": {
            "model": "deepseek-v4-flash",
            "desc": "日常聊天，快且省"
        },
        "reasoning": {
            "model": "deepseek-v4-pro",
            "desc": "复杂推理，深度思考"
        },
        "vision": {
            "model": "kimi-k2.5",
            "desc": "看图识图，秒出结果"
        },
        "vision_alt": {
            "model": "minimax-m3",
            "desc": "看图备选"
        },
        "code": {
            "model": "kimi-k2.7-code",
            "desc": "代码生成与修改"
        },
        "long_text": {
            "model": "qwen3.7-max",
            "desc": "长文本处理，中文最强"
        }
    }
    
    def chat(self, messages: list, task_type: str = "chat", **kwargs):
        """自动选择模型聊天"""
        route = self.ROUTING.get(task_type, self.ROUTING["chat"])
        model = route["model"]
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60
        )
        return r.json()
    
    def vision(self, image_path: str, question: str = "描述这张图片") -> str:
        """看图专用 - 自动选kimi-k2.5"""
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        payload = {
            "model": "kimi-k2.5",
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": question}
            ]}],
            "max_tokens": 500
        }
        
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30
        )
        return r.json()["choices"][0]["message"]["content"]

router = ModelRouter()
