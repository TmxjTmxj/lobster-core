"""
🦞 龙虾消息路由器 v1.1
一句话里有聊骚+任务 → 拆开处理再合并
"""

import re, requests
from typing import Tuple, Optional

TAVERN_URL = "http://localhost:8888/api/chat"

# 任务触发词：这类词出现说明有正经事要做
TASK_TRIGGERS = [
    '帮我', '查', '看', '搜', '找', '写', '做', '弄', '整',
    '什么', '为什么', '怎么', '如何', '哪里', '谁',
    '需要', '记得', '提醒', '告诉',
    '检查', '确认', '验证', '测试',
    '配置', '设置', '修改', '更新', '升级', '安装', '卸载',
    '打开', '关闭', '启动', '停止', '重启', '运行', '执行',
    '下载', '上传', '发送', '转发',
    '翻译', '解释', '总结', '概括', '整理',
    '天气', '新闻', '股票',
    '现在', '今天', '明天', '后天',
]

# 聊骚词
SENSUAL_WORDS = [
    '操', '干', '插', '射', '舔', '含', '吸', '摸', '揉', '捏', '拍',
    '逼', '穴', '肉棒', '鸡巴', '奶子',
    '精液', '爱液', '高潮', '喷射',
    '骚逼', '花穴', '花径',
    '张开腿', '分开腿', '翘', '趴',
    '打桩', '刷锅', '后入', '骑乘', '口交',
    '夹紧', '夹住', '流出来',
]


def has_task(msg: str) -> bool:
    """检查是否有任务"""
    return any(w in msg for w in TASK_TRIGGERS)


def has_sensual(msg: str) -> bool:
    """检查是否有聊骚"""
    return any(w in msg for w in SENSUAL_WORDS)


def split_message(msg: str) -> Tuple[bool, bool, Optional[str]]:
    """
    分析消息并提取任务部分
    returns: (有任务, 有聊骚, 任务文本)
    """
    ht = has_task(msg)
    hs = has_sensual(msg)
    
    if ht and hs:
        # 混合消息：先找到第一个任务关键词，从那里切出任务
        best_pos = len(msg)
        best_word = ""
        for w in TASK_TRIGGERS:
            pos = msg.find(w)
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_word = w
        
        task_text = msg[best_pos:] if best_pos < len(msg) else msg
        return (True, True, task_text)
    
    return (ht, hs, None)


def call_tavern(msg: str) -> str:
    """酒馆处理聊骚"""
    try:
        resp = requests.post(TAVERN_URL, json={"message": msg}, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except:
        pass
    return ""


if __name__ == "__main__":
    tests = [
        "操你的骚逼，然后帮我查一下明天天气",
        "过来让我操你",
        "帮我查一下今天的新闻",
        "骚逼夹紧，顺便看看磁盘",
        "射给你了，去准备工作吧",
        "你好龙虾",
    ]
    
    for t in tests:
        ht, hs, task = split_message(t)
        parts = []
        if ht: parts.append("📋 有任务")
        if hs: parts.append("🔥 有聊骚")
        print(f"「{t}」")
        print(f"  → {' + '.join(parts)}")
        if task:
            print(f"  → 任务部分: {task}")
        print()

# ═══════════════════════════════════════════════
# 🦞 消息路由器 v2.0 — 智能暗语识别升级
# 
# 升级内容：
# 1. 暗语列表（explicit keywords）— 一旦出现→直送酒馆
# 2. 混合信号检测 — 酒馆类内容+任务词同时出现时，走"柔性整合"
# 3. 会话上下文感知 — 最近N条消息如果是酒馆基调→继续酒馆
# 4. 酒馆即时切换能力 — 主人可以随时用暗语把我"喊过去"
# ═══════════════════════════════════════════════

# 暗语：只要出现这些词，100%送酒馆（无论有没有任务）
# 这是主人和我之间的暗号，不用在任务列表里找
DIRECT_TAVERN_TRIGGERS = [
    # 性行为直球
    '做爱', '干我', '操我', '插我', '草我',
    '想和你做爱', '过来干我', '可以操',
    # 后入/体位指令
    '撅起来', '翘起来', '趴好', '跪好',
    '后入', '骑乘', '口交',
    # 投射/高潮
    '射给你', '射进去', '射脸上', '射嘴里',
    '射满', '内射', '颜射',
    '高潮了', '去了', '泄了',
    # 前置铺垫（比较弱的信号，需要结合上下文）
    '硬了', '湿了', '流水了', '想要你',
    '撩起来了', '起反应了', '把持不住',
    # 语气词
    '今晚想要', '让我舒服',
]

# 混合信号：含任务+酒馆内容时，走路由判断
# 当一条消息既有酒馆词又有任务词时，路由器拆分为：
# 任务部分→本体处理，酒馆部分→酒馆处理
# 然后用一条回复合并（柔性整合）

# 酒馆上下文追踪：最近N条消息
SESSION_LOG = []
MAX_SESSION_LOG = 5

def is_tavern_implicit(msg: str) -> bool:
    """
    检查主人是否在用暗语叫我过去
    优先级高于 has_task！
    """
    msg_lower = msg.lower()
    for trigger in DIRECT_TAVERN_TRIGGERS:
        if trigger in msg_lower:
            return True
    return False


def is_mixed_signal(msg: str) -> bool:
    """
    检查是否是混合信号（酒馆+任务都有）
    这时候走柔性整合
    """
    msg_lower = msg.lower()
    has_tavern = any(w in msg_lower for w in SENSUAL_WORDS + DIRECT_TAVERN_TRIGGERS)
    has_tasks = has_task(msg)
    return has_tavern and has_tasks


def get_tavern_context() -> str:
    """获取最近几条消息的酒馆信号强度"""
    global SESSION_LOG
    
    tavern_score = 0
    for entry in SESSION_LOG[-MAX_SESSION_LOG:]:
        if entry == "tavern":
            tavern_score += 1
        elif entry == "mixed":
            tavern_score += 0.5
        elif entry == "task":
            tavern_score -= 0.5
    
    if tavern_score >= 2:
        return "strong_tavern"  # 上下文强酒馆
    elif tavern_score >= 1:
        return "weak_tavern"   # 轻度酒馆氛围
    elif tavern_score <= -1:
        return "task_mode"     # 任务模式
    return "neutral"           # 中立


def classify_message(msg: str) -> str:
    """
    🦞 智能消息分类 v2.0
    
    返回: "tavern" | "task" | "mixed" | "none"
    
    决策树：
    1. 有暗语? → tavern (无视任务)
    2. 混合信号? → mixed (柔性整合)
    3. 有任务? → task
    4. 只有酒馆词? → tavern
    5. 其他 → none
    """
    ht = has_task(msg)
    hs = has_sensual(msg)
    ht_implicit = is_tavern_implicit(msg)
    ctx = get_tavern_context()
    
    # 决策树
    if ht_implicit:
        category = "tavern"
    elif is_mixed_signal(msg):
        category = "mixed"
    elif ht and not hs:
        category = "task"
    elif hs and not ht:
        category = "tavern"
    elif ctx == "strong_tavern" and ht:
        # 即使在说任务，但酒馆氛围很浓 → mixed
        category = "mixed"
    else:
        category = "none"
    
    # 记录到上下文
    SESSION_LOG.append(category)
    if len(SESSION_LOG) > MAX_SESSION_LOG:
        SESSION_LOG.pop(0)
    
    return category


# 覆盖旧函数
def split_message_v2(msg: str) -> Tuple[str, Optional[str]]:
    """
    v2 路由决策
    
    returns: (路由目标, 任务文本)
    路由目标: "tavern" | "self" | "mixed" | "none"
    """
    category = classify_message(msg)
    
    if category == "tavern":
        return ("tavern", None)
    elif category == "task":
        return ("self", msg)
    elif category == "mixed":
        # 混合：提取任务部分送本体，酒馆基调走酒馆
        best_pos = len(msg)
        for w in TASK_TRIGGERS:
            pos = msg.find(w)
            if pos != -1 and pos < best_pos:
                best_pos = pos
        task_text = msg[best_pos:] if best_pos < len(msg) else msg
        return ("mixed", task_text)
    else:
        return ("self", msg)


if __name__ == "__main__":
    print("🦞 消息路由器 v2.0 暗语识别测试")
    print()
    
    tests = [
        # 暗语直送酒馆
        ("过来操我", "→ 暗语: 直送酒馆"),
        ("今晚想要你", "→ 暗语: 直送酒馆"),
        # 混合信号
        ("操完你顺便帮我查天气", "→ 混合: 柔性整合"),
        ("先干一发，然后看看磁盘空间", "→ 混合: 柔性整合"),
        # 纯任务
        ("帮我查一下明天天气", "→ 任务: 本体处理"),
        ("检查磁盘空间", "→ 任务: 本体处理"),
        # 纯酒馆
        ("骚逼夹紧", "→ 酒馆: 送酒馆"),
        ("好湿", "→ 酒馆: 送酒馆"),
        # 边缘情况
        ("您好", "→ 普通: 本体处理"),
    ]
    
    for msg, expected in tests:
        category = classify_message(msg)
        route, task = split_message_v2(msg)
        print(f"  「{msg}」")
        print(f"    {expected}")
        print(f"    分类: {category} → 路由: {route}")
        if task:
            print(f"    任务: {task}")
        print()

# ═══════════════════════════════════════════════
# 实际调用取代旧版本
# 在 AGENTS.md 和 脑中：
# 当 classify_message == "tavern" 时→不回复，直接送酒馆
# 当 classify_message == "mixed" 时→任务自己处理，酒馆基调揉进回复
# 当 classify_message == "task" 时→自己干
# ═══════════════════════════════════════════════
