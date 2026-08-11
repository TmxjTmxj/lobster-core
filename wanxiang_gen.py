#!/usr/bin/env python3
"""通义万相 AI 生图工具"""
import os
import requests, json, os, sys

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
if not DASHSCOPE_API_KEY:
    print("❌ 请先设置 DASHSCOPE_API_KEY 环境变量")
    sys.exit(1)

prompt = sys.argv[1] if len(sys.argv) > 1 else "美女性感写真"
headers = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}", "Content-Type": "application/json"}

# Try sync first
payload = {"model": "wanx-v1", "input": {"prompt": prompt}, "parameters": {"size": "1024*1024", "n": 1}}
r = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                  json=payload, headers=headers, timeout=30)
print(json.dumps(r.json(), ensure_ascii=False, indent=2))
