"""
龙虾输出美化器 v2 — 融入Anthropic前端设计理念 + impeccable理念
让飞书消息更清晰、更有层次
"""
class OutputStyler:
    """输出美化工具"""
    
    @staticmethod
    def title(text): 
        """主标题"""
        return f"**{text}**"
    
    @staticmethod 
    def subtitle(text):
        """副标题"""
        return f"*{text}*"
    
    @staticmethod
    def header(text):
        """分隔标题"""
        return f"\n━━━ {text} ━━━"
    
    @staticmethod
    def bullet(text):
        """圆点列表"""
        return f"• {text}"
    
    @staticmethod
    def success(text):
        """成功状态"""
        return f"✅ {text}"
    
    @staticmethod
    def error(text):
        """错误状态"""
        return f"❌ {text}"
    
    @staticmethod
    def warn(text):
        """警告状态"""
        return f"⚠️ {text}"
    
    @staticmethod
    def code(text):
        """代码片段"""
        return f"`{text}`"
    
    @staticmethod
    def key_value(key, value):
        """键值对"""
        return f"**{key}:** {value}"
    
    @staticmethod
    def divider():
        """分隔线"""
        return "\n──────────────"

def get_styler():
    return OutputStyler()
