"""
龙虾澄清机制 — 像 Codex 的 clarify 工具，不懂就问
"""

class Clarify:
    """当信息不足时主动问清楚，不瞎猜"""
    
    def need(self, question: str, options: list = None, context: str = "") -> str:
        """生成一个需要主人确认的问题"""
        msg = f"🤔 {question}"
        if options:
            msg += "\n\n选项：\n" + "\n".join(f"  {i+1}. {o}" for i, o in enumerate(options))
        if context:
            msg += f"\n\n背景：{context}"
        return msg
    
    def confirm(self, action: str, risk: str = "low") -> str:
        """确认一个可能有风险的行动"""
        risk_labels = {"low": "🟢 低风险", "medium": "🟡 中风险", "high": "🔴 高风险"}
        return (
            f"{risk_labels.get(risk, '⚠️')} 确认要执行吗？\n"
            f"操作：{action}\n"
            f"回复「确认」我就继续"
        )
    
    def disambiguate(self, options: dict) -> str:
        """有多个可能的意思时请主人选一个"""
        msg = "🤔 您说的是哪个意思？\n"
        for key, desc in options.items():
            msg += f"  • 「{key}」— {desc}\n"
        return msg


_clarify = None
def get_clarify():
    global _clarify
    if _clarify is None:
        _clarify = Clarify()
    return _clarify
