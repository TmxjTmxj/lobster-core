#!/usr/bin/env python3
"""飞书发图片工具 - 用法: python3 send_image.py <图片路径> [图片描述]"""
import os
import requests, json, sys, os

def send_feishu_image(image_path, caption=""):
    with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
        config = json.load(f)
    fc = config["channels"]["feishu"]["accounts"]["main"]
    
    # Get token
    resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": fc["appId"], "app_secret": fc["appSecret"]})
    token = resp.json()["tenant_access_token"]
    
    # Upload
    with open(image_path, "rb") as img:
        upload = requests.post("https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            files={"image": ("photo.jpg", img, "image/jpeg")},
            data={"image_type": "message"}).json()
    
    image_key = upload["data"]["image_key"]
    
    # Send
    send = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": "ou_<FEISHU_USER_ID>",
            "msg_type": "image",
            "content": json.dumps({"image_key": image_key})
        }
    ).json()
    return send

if __name__ == "__main__":
    r = send_feishu_image(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    print(f"OK: {r.get('code') == 0}")
