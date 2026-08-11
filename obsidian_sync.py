"""
龙虾 ↔ Obsidian 双向同步
模式A: 直接写文件到Vault目录（Obsidian关了也能用）
模式B: REST API（Obsidian打开+插件装好时用）
"""
import os, json, datetime, subprocess, urllib.request

VAULT_DIR = os.path.expanduser("~/Documents/Obsidian/main")
OBSIDIAN_URL = os.environ.get("OBSIDIAN_URL", "")
OBSIDIAN_API_KEY = os.environ.get("OBSIDIAN_API_KEY", "")

class ObsidianSync:
    def __init__(self):
        self.notes_dir = os.path.join(VAULT_DIR, "龙虾笔记")
        os.makedirs(self.notes_dir, exist_ok=True)
    
    def write_note(self, title: str, content: str, tags: list = None):
        """写入笔记 - 先试API再试文件"""
        frontmatter = {
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tags": tags or ["龙虾"]
        }
        fm = "---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n"
        full_content = fm + content
        
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        filepath = os.path.join(self.notes_dir, filename)
        
        # 模式A: 直接写文件（总是可用）
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 模式B: REST API（如果配置了）
        if OBSIDIAN_URL and OBSIDIAN_API_KEY:
            try:
                req = urllib.request.Request(
                    f"{OBSIDIAN_URL}/vault/龙虾笔记/{filename}",
                    data=json.dumps({"content": full_content}).encode(),
                    headers={
                        "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    method="PUT"
                )
                urllib.request.urlopen(req, timeout=5)
            except:
                pass  # API不可用时自动降级到文件模式
        
        return filepath
    
    def log_learning(self, topic: str, details: str):
        """记录一次学习"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        note = f"""## {topic}

{details}

---
*由龙虾自动记录于 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        return self.write_note(f"{today}-{topic}", note, tags=["龙虾", "学习日志"])

sync = ObsidianSync()
