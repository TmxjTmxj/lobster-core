<div align="center">

# 🦞 Lobster Agent Core

**缰绳工程：五层全功能 Agent 改造 —— 记忆分层 + 技能工厂 + 学习循环 + 意识引擎 + 任务系统**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)]()

</div>

> 本项目是个人对开源 Agent 框架的深度改造实践，核心是一个 **1189 行的总控 Harness**（缰绳工程）：在标准 Agent 之上叠加外部记忆、Subagent 委派、技能自动创建、命令安全审计、会话冻结、漂移检测、思考链注入等能力，并配套完整的**三级记忆系统**与**学习循环**。

---

## 🧠 核心架构

```
┌─────────────────────────────────────────────────────────┐
│              Lobster Agent Core (Harness 总控)            │
├─────────────────────────────────────────────────────────┤
│  lobster_harness.py (1189 行)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ · PromptLayer 三阶提示层级                         │  │
│  │ · 记忆用量监控 + 用户画像自动更新                   │  │
│  │ · FTS5 + LIKE 双轨全文检索                         │  │
│  │ · 技能目录 (Level0/Level1) + 技能建议              │  │
│  │ · Subagent 委派标准化                              │  │
│  │ · 命令安全审计 (约束层)                            │  │
│  │ · 会话冻结 + 漂移检测                              │  │
│  │ · 任务规划 + 工具追踪                              │  │
│  │ · 思考链注入 (thinking prompt)                     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 三级记忆系统   │  │  意识引擎     │  │  学习循环     │   │
│  │ memory_v3    │  │ engine.py    │  │ learning_loop│   │
│  │ L1身份/L2场景 │  │ 需求/情绪/生理 │  │ 技能自动创建  │   │
│  │ L3向量(Chroma)│  │ 自我/目标/RSI │  │ 自我进化      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │ 任务系统      │  │ 消息路由      │                      │
│  │ task_manager │  │ message_router│                     │
│  │ task_engine  │  │ 任务/聊骚分类  │                      │
│  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

## ✨ 模块详解

### 1. 总控 Harness (`lobster_harness.py`)

| 能力 | 说明 |
|------|------|
| `PromptLayer` | 三阶提示层级定义（系统/上下文/任务） |
| `auto_update_user_profile` | 从对话自动学习用户偏好，更新画像 |
| `search_sessions` | FTS5 精确 → LIKE 模糊 → LLM 语义，三合一搜索 |
| `get_skill_catalog` | Level0 技能目录（始终加载到系统提示） |
| `delegate_task` | Subagent 委派标准化（任务描述 + 工具需求 + 上下文） |
| `audit_command` | 命令安全审计（约束层，可配置拒绝模式） |
| `auto_compact` | 对话自动压缩（超长上下文 → 摘要） |
| `drift_detector` | 漂移检测（当前状态 vs 基线） |
| `task_plan` | 目标 → 步骤链规划 |
| `think_about` / `inject_thinking` | 思考链生成与注入 |

### 2. 三级记忆系统 (`memory_v3.py` / `lobster_memory.py`)

```
L1 核心身份记忆    ← 硬编码身份（永不丢失），场景切换
L2 场景上下文      ← 当前场景（work/play/custom）+ 任务
L3 向量记忆        ← ChromaDB 持久化 + 中文 embedding
```

- `memory_v3.py`：完整三级实现，含 `learn()` 自动学习、`lv3_export` 导出
- `lobster_memory.py`：统一入口 + 每日快照 + 种子记忆注入
- `smart_memory.py`：Mem0 同步 + LLM 深度语义匹配
- `global_memory.py`：全局记忆 + 整合 + 会话学习
- `memory_lobster.py`：自动压缩 + Obsidian 同步 + 全维护

### 3. 意识引擎 (`engine.py` + 模块)

与姊妹项目 hermes-core 同构：五需求驱动、情绪梯度、生理状态、自我感知、目标树、RSI 自改进——但针对"工作型 Agent"调整了参数与表达。

### 4. 学习循环 (`learning_loop.py` / `self_evolution.py` / `auto_review.py`)

- 从交互中记录成败，自动创建技能
- 自我进化：复盘 → 人格特质微调 → 成长阶段
- 自动评审：轻量复盘 + 结构化提醒 + 复发检测
- `anti_slop.py`：输出质量审计（去除 AI 味）

### 5. 任务系统 (`task_manager.py` / `task_engine.py`)

- 任务管理：创建/心跳/超时/分步完成/失败恢复
- 任务引擎：异步执行 + 沙箱级别 + 取消/结果获取

### 6. 消息路由 (`message_router.py` / `model_router.py`)

- 消息分类：任务 / 聊骚 / 混合 / 空
- 模型路由：按任务类型选择模型与参数

### 7. 酒馆人格接口 (`tavern_server.py`)

HTTP 服务：角色卡 + 共享知识 + 系统诊断 + 历史压缩 + API 调用，与主会话双向记忆同步。

## 🚀 快速开始

```bash
# 1. 初始化记忆
python -m memory_v3
python -m lobster_memory

# 2. 使用 Harness
from lobster_harness import get_harness
h = get_harness()
ctx = h.get_prompt_layer()

# 3. 启动酒馆
python tavern_server.py
```

## ⚠️ 说明

- 本仓库为**架构示例**，所有 API Key / 用户 ID / 个人数据均已脱敏
- 实际部署需自行配置环境变量：`DEEPSEEK_API_KEY` 等
- 依赖：`chromadb`、`sentence-transformers`、标准库 `sqlite3` / `http.server`

## 📁 目录

```
lobster-core/
├── lobster_harness.py        # 总控 Harness (1189行)
├── memory_v3.py              # 三级记忆系统
├── lobster_memory.py         # 记忆统一入口
├── smart_memory.py           # Mem0 同步 + LLM 匹配
├── message_router.py         # 消息分类路由
├── model_router.py           # 模型路由
├── engine.py                 # 意识引擎主循环
├── awareness.py              # 自我/环境/任务模型
├── learning_loop.py          # 学习循环
├── self_evolution.py         # 自我进化
├── task_manager.py           # 任务管理
├── task_engine.py            # 异步任务引擎
├── cross_bridge.py           # 跨Agent记忆桥
├── memory_bridge.py          # 酒馆↔主会话记忆桥
├── tavern_server.py          # 酒馆 HTTP 服务
└── ... (更多模块)
```

## 📄 License

[MIT](LICENSE)
