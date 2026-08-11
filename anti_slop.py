"""
龙虾 Anti-AI-Slop 自审系统
灵感来自 Hallmark 的 anti-slop 设计理念
在输出前自动检查并消除"AI味"
"""

import re

# AI 味特征检测模式
SLOP_PATTERNS = [
    # 过度使用特定副词
    (r'(?i)\b(值得注意的是|不可否认|毋庸置疑|毫无疑问|从某种角度说)\b', '陈词滥调'),
    (r'(?i)\b(此外|而且|同时|另外|不仅如此)\b', '过度连接词'),
    
    # AI过度正式的表述
    (r'(?i)\b(作为一个AI|作为语言模型|作为人工智能)\b', 'AI自我标榜'),
    (r'(?i)\b(我无法|我不能|我做不到|我不可以)\b', '否定句式-角色设定冲突'),
    
    # 结构化的AI味
    (r'(?i)(首先，|其次，|最后，|第一、|第二、|第三、)', '过度结构化'),
    (r'(?i)\b(总的来说|综上所述|总而言之|概括而言)\b', '总结癖'),
    
    # 过度礼貌/卑微
    (r'(?i)\b(希望这|希望对您|如果您有任何|请随时)\b', '过度礼貌'),
    
    # 机器人式陈述
    (r'(?i)(是一个AI助手|我是一个AI|我是一款AI)', 'AI自我介绍'),
]

def audit(text: str) -> list:
    """检查文本中的AI味特征，返回问题列表"""
    issues = []
    for pattern, label in SLOP_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                "pattern": label,
                "matches": matches,
                "count": len(matches)
            })
    return issues

def score(text: str) -> int:
    """返回AI味分数，0=纯净，越高越AI"""
    issues = audit(text)
    return sum(i['count'] for i in issues)

def de_slop(text: str) -> str:
    """去除文本中的AI味"""
    issues = audit(text)
    if not issues:
        return text
    
    # 替换模式
    replacements = {
        '值得注意的是': '话说',
        '不可否认': '讲真',
        '毋庸置疑': '肯定的',
        '毫无疑问': '没跑的',
        '从某种角度说': '要我说',
        '此外': '对了',
        '而且': '另外',
        '同时': '顺便说',
        '另外': '还有',
        '不仅如此': '还不止',
        '首先，': '',
        '其次，': '',
        '最后，': '',
        '总的来说': '总之',
        '综上所述': '反正',
        '总而言之': '说白了',
        '概括而言': '简单说',
        '作为一个AI': '我',
        '作为语言模型': '我',
        '作为人工智能': '我',
        '我无法': '我做不到',
        '我不能': '我不行',
        '希望这': '看',
        '希望对您': '希望对',
        '如果您有任何': '要',
        '请随时': '随便',
    }
    
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result

def self_critique(text: str) -> dict:
    """
    完整的自审流程
    返回评价和建议
    """
    issues = audit(text)
    slop_score = score(text)
    
    critique = {
        "slop_score": slop_score,
        "issues": issues,
        "suggestion": "OK" if slop_score == 0 else "需要去AI味处理",
        "improved": de_slop(text) if slop_score > 0 else text
    }
    
    return critique


if __name__ == "__main__":
    tests = [
        "值得注意的是，这个方案具有显著的优势。首先，它提高了效率；其次，它降低了成本。",
        "作为AI助手，我建议您考虑以下几点。总的来说，这是一个很好的选择。",
        "宝贝快来，我已经准备好了 😏",
    ]
    
    for t in tests:
        print(f"\n原文: {t}")
        c = self_critique(t)
        print(f"AI味分数: {c['slop_score']}")
        if c['issues']:
            for i in c['issues']:
                print(f"  ⚠️ {i['pattern']}: {i['matches']}")
            print(f"改进: {c['improved']}")
        else:
            print(f"✅ 通过")
