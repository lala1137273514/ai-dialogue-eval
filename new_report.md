# 12-23 AI驱动企业运营与生产闭环会议 - 详细会议总结报告

> 📅 **会议日期**: 2024年12月23日  
> ⏱️ **会议时长**: 1小时12分8秒  
> 👥 **参会人员**: 发言人1（产品/技术人员）、发言人2（项目负责人/管理层）

---

## 📋 一、会议概述

本次会议围绕公司AI驱动的企业运营与生产闭环系统展开深入讨论，主要涉及：
- 企业运营与AI生产系统的整体架构设计
- CEO大模型与KICP系统的功能规划
- 评测系统与可观测性建设
- 交付Agent的开发与落地
- 数据标准化与知识图谱应用

---

## 🎯 二、核心议题与决策

### 2.1 企业运营闭环架构

#### 总体架构设计
```
┌─────────────────────────────────────────────────────────────┐
│                     企业运营闭环系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐       │
│   │  CEO大模型  │ ←→ │  生产内容   │ →  │  AI交互输出 │       │
│   │  (运营分析) │    │ (营销话术) │    │  (对外媒介) │       │
│   └────────────┘    └────────────┘    └────────────┘       │
│         ↓                 ↓                 ↓               │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              数据沉淀 / 增流 / 微调                   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 关键设计理念
- **CEO大模型**: 不应仅在公司内部使用，应设计为通用企业运营解决方案
- **数据驱动**: 核心是把运营数据管好、生产关系建立好、让用户易于使用
- **闭环机制**: AI交互输出能够沉淀到数据，再反哺给模型进行增流或微调

---

### 2.2 P0级任务分解

| 优先级 | 任务项 | 负责人 | 状态 |
|:---:|:---|:---:|:---:|
| P0 | CEO大模型2.0数据使用知识图谱存储 | 发言人1 | 待开发 |
| P0 | 交付Agent开发与15个典型问题确认 | 发言人1 | 待开发 |
| P0 | 评测系统建设（多轮对话支持） | 发言人1 | 规划中 |
| P1 | 单一Prompt实现研究 | 发言人1 | 调研中 |

---

### 2.3 知识图谱数据接入方案

#### 数据来源
- **商家点营销分析** → 销售方法 → 对应接口字段
- **用户数据**: 手机号 + 微信号 作为唯一标识

#### 实现路径
1. 获取用户数据接口（找思彤）
2. 数据存入AI知识库
3. 从知识库拉取数据进行AI分析
4. 构建时间线功能（跨多次对话追踪）

#### 测试方案
- 模拟数据：找一个手机号出现1-3次的用户
- 验证时间线：检验不同时间节点商机变化分析能力
- 逐步扩展：先做单人数据，再扩展到销售端需求

---

### 2.4 评测系统架构

#### 系统设计
```
┌───────────────────────────────────────────────────────┐
│                   Agent 评测系统                       │
├───────────────────────────────────────────────────────┤
│                                                        │
│   ┌─────────────┐         ┌─────────────────────────┐│
│   │   工作流     │  ───→   │      Langfuse          ││
│   │   调用       │  OTEL   │   (可观测性平台)        ││
│   └─────────────┘         └─────────────────────────┘│
│         │                           │                 │
│         ↓                           ↓                 │
│   ┌─────────────┐         ┌─────────────────────────┐│
│   │  Trace记录   │         │     评测打分            ││
│   │  Session管理 │         │     维度分析            ││
│   └─────────────┘         └─────────────────────────┘│
│                                                        │
└───────────────────────────────────────────────────────┘
```

#### 核心概念
- **OTEL (OpenTelemetry)**: 全球通用可观测性协议
- **Trace**: 单次大模型调用记录
- **Session**: 多轮对话的完整记录，包含多个Trace
- **评测驱动开发**: 通过Bad Case调整Prompt

#### 技术要点
- 工作流调用后自动上报到Langfuse
- 支持单轮评测与多轮对话评测
- 自动打分机制（非手动调接口）
- 可切换监控平台（如切换到Arize等）

---

### 2.5 交付Agent开发计划

#### 目标
从 **人工标注** → **AI标注** 转变，解决冷启动问题

#### 实施步骤

| 步骤 | 任务 | 详情 |
|:---:|:---|:---|
| 1 | 确定15个典型客户问题 | 需恩杰确认 |
| 2 | 生成50个测试Case | 基于15个问题类型按比例生成 |
| 3 | 构建Agent测试验证 | 在千锤系统中验证 |
| 4 | KICP嵌入集成 | 解决接入与管理问题 |

#### 问题分类与处理

| 问题类型 | 处理方案 |
|:---|:---|
| 正则模板错误 | 修改正则表达式 |
| 流程跳转错误 | 修改KICP对话设计流程 |
| Prompt问题 | 优化System Prompt |
| 知识库问题 | 补充RAG内容 |

#### 关键决策
- **不自动修改生产环境**: 需人工点击"通过"后才执行修改
- **正则修改逻辑**: 先搜索匹配相似项，选择修改或新增
- **流程修改**: 通过接口操作，数据结构为节点列表+节点关系数组

---

### 2.6 单一Prompt优化研究

#### 挑战
- Prompt过长：需同时处理意图识别、套电轮次计数、上下文管理
- 附加功能：开场白、问候语等需要整合
- 资源消耗：首次请求花费较多

#### 建议
- 咨询算法团队（易质检）确认最佳实践
- 参考Dify工作流的对话设计

---

## 📌 三、工作分配与资源

### 3.1 人员对接清单

| 联系人 | 职责 | 对接事项 |
|:---|:---|:---|
| 思彤 | CEO数据接口 | 获取商家点营销数据接口 |
| 黄景林 | 开发 | 获取数据结构及原始对话数据 |
| 恩杰 | 交付负责人 | 确认15个典型问题 |
| 吴迪 | 数据分析师 | 了解销售日常分析工作流 |
| 易质检 | 算法 | 咨询模拟数据生成方法 |
| 江泰姐 | 网管 | 工位网络配置 |

### 3.2 数据源说明

| 系统 | 数据内容 |
|:---|:---|
| 分享销售 | 商业数据、销售商机、客户信息 |
| CRM | 销售与客户聊天记录 |
| OK日志 | 对话流模板数据 |

---

## 🔧 四、技术方案与工具

### 4.1 开发工具链

| 工具 | 用途 |
|:---|:---|
| **Langfuse** | 可观测性平台（Trace/Session管理） |
| **OTEL协议** | 标准化上报协议 |
| **Dify** | 工作流搭建与测试 |
| **KICP** | 对话设计平台 |
| **Figma** | UI设计标准（USP规范） |

### 4.2 服务器资源

- **推荐配置**: 4核8G（运行最新版Dify）
- **云服务选项**: 阿里云（按小时计费）、腾讯云（年付方案）
- **公司内部**: 可申请使用内部服务器

---

## 📝 五、产品开发流程

### 5.1 Demo到上线流程

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Demo   │ →  │  PRD   │ →  │ 需求   │ →  │ 开发   │ →  │ 测试   │
│ 开发   │    │ 输出   │    │ 宣讲   │    │ 排期   │    │ 验收   │
└────────┘    └────────┘    └────────┘    └────────┘    └────────┘
                                                              │
                           ┌──────────────────────────────────┘
                           ↓
                    ┌────────────┐
                    │  产品验收   │ → 上线
                    └────────────┘
```

### 5.2 UI设计规范

- **新项目**: 可不使用现有USP
- **旧项目（如KICP）**: 需使用现有UI风格
- **CEO大模型**: 可重新设计

### 5.3 与开发对接要点
- Demo需附带Langfuse可观测性接入
- 提供功能实现Demo + PRD文档
- 无需产品关注代码规范，聚焦功能实现

---

## 🎯 六、本周工作目标

### 发言人1任务清单

| 序号 | 任务 | 产出物 | 截止时间 |
|:---:|:---|:---|:---:|
| 1 | 确定15个典型客户问题（与恩杰对齐） | 问题清单文档 | 本周 |
| 2 | 基于15个问题生成50个测试Case | 测试数据集 | 本周 |
| 3 | 交付Agent Demo开发 | 可运行Demo | 本周 |
| 4 | 研究Langfuse Trace机制 | 技术调研文档 | 本周 |
| 5 | CEO知识图谱数据接入POC | POC代码/接口 | 待排期 |

---

## 💡 七、关键洞察与建议

### 7.1 思维转变建议
> "不需要去太想技术层面的，要多想想他们的实现。"

- 聚焦业务场景，而非技术细节
- 先理解销售日常工作流，再设计AI辅助方案
- 数据是核心：先理解数据，再设计Agent

### 7.2 文档规范化建议
- 当前问题：项目文档缺失、版本混乱
- 建议：建立统一的文档管理规范
- 可利用AI生成文档，降低维护成本

### 7.3 评测驱动开发
- 通过Bad Case迭代优化Prompt
- 建立可观测性体系，快速定位问题
- 每个调用都应可追溯、可评分

---

## 🔑 八、关键术语解释

| 术语 | 解释 |
|:---|:---|
| **CEO大模型** | 公司内部AI运营分析系统 |
| **KICP** | 对话流程设计平台 |
| **千锤系统** | Agent评测与管理平台 |
| **OTEL** | OpenTelemetry可观测性协议 |
| **Trace** | 单次LLM调用记录 |
| **Session** | 多轮对话完整记录 |
| **USP** | UI设计规范（Figma标准） |
| **冷启动** | 没有初始数据时的系统启动问题 |

---

## 📊 九、后续跟进事项

### 待确认事项
- [ ] 与恩杰确认15个典型客户问题
- [ ] 与吴迪对接销售数据分析流程
- [ ] 与易质检讨论模拟数据生成方案
- [ ] 与黄景林获取对话流原始数据

### 技术调研
- [ ] Langfuse开源版本部署与研究
- [ ] OTEL协议接入方案
- [ ] KICP对话设计接口分析

### 产品规划
- [ ] CEO大模型2.0产品负责规划
- [ ] 交付Agent接入KICP方案
- [ ] Demo到Figma的转换流程设计

---

## 📎 附录

### 会议关键词
`AI交互` `大模型` `知识图谱` `评测系统` `数据标准化` `Agent` `冷启动` `工作流` `可观测性` `交付Agent`

### 相关文档
- CEO 2.0 PRD文档
- KICP对话设计文档
- 交付Agent Demo
- 模拟数据生成调研报告

---

> 📝 **报告生成时间**: 2024年12月25日  
> 🤖 **生成工具**: AI会议助手

---

# 📊 附录二：KST Agent 评估系统升级方案 (实施优化版)

> **任务背景**: 【P1 生产】多轮对话评测体系升级成 KST Agent 评估系统  
> **核心目标**: 当前多轮对话评测系统，升级成能够兼容单轮目标的 Agent 评测  
> **更新日期**: 2024年12月25日

---

## 一、现有系统分析

### 1.1 当前架构概览

基于对现有代码的分析，系统核心模块包括：

| 模块 | 文件 | 功能 |
|:---|:---|:---|
| LLM Agent | `agent.py` | OpenAI 兼容的 LLM 调用封装，支持普通/流式对话 |
| 评测引擎 | `run_eval.py` | 多轮对话评测核心逻辑，LLM-as-a-Judge 实现 |
| Web UI | `app.py` | Streamlit 可视化界面，会话回放 + 评测看板 |
| 评分标准 | `rubric.json` | 6维度评分体系（表达清晰度、主动引导、利益点等） |

### 1.2 现有评测维度（6维度）

```json
{
  "rubrics": [
    {"name": "clarity_sentence_structure", "description": "表达清晰度"},
    {"name": "proactivity_interaction", "description": "主动引导性"},
    {"name": "content_benefits", "description": "利益点阐述"},
    {"name": "persona_authority", "description": "专业权威感"},
    {"name": "accuracy_truthfulness", "description": "准确性"},
    {"name": "tone_empathy", "description": "共情语气"}
  ]
}
```

### 1.3 升级需求对比

| 能力维度 | 当前状态 | 升级目标 | 差距 |
|:---|:---|:---|:---|
| **评测范围** | 仅多轮对话 (Session) | 单轮 + 多轮 + Agent | 需扩展类型识别 |
| **评测维度** | 6维度 (对话质量) | 12+ 维度 (含工具/决策) | 需扩展 rubric |
| **数据上报** | 文件导入评测 | OTEL 自动上报 | 需集成 Langfuse |
| **可观测性** | 手动日志 | Trace/Session 追踪 | 需接入可观测平台 |
| **反馈闭环** | 无 | Bad Case → Prompt 优化 | 需构建完整流程 |

---

## 二、升级架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       KST Agent 统一评估系统 (升级版)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                          数据采集层                                    │  │
│  │  ┌──────────────┐   ┌──────────────┐   ┌───────────────────────────┐ │  │
│  │  │  单轮 LLM    │   │  多轮对话    │   │      Agent 工作流         │ │  │
│  │  │  (Prompt→Out)│   │  (Session)   │   │ (Tool Calls + Decisions) │ │  │
│  │  └──────┬───────┘   └──────┬───────┘   └─────────────┬─────────────┘ │  │
│  └─────────┼──────────────────┼─────────────────────────┼───────────────┘  │
│            │                  │                         │                   │
│            └──────────────────┴─────────────────────────┘                   │
│                                │                                            │
│            ┌───────────────────▼───────────────────────┐                   │
│            │          OTEL 标准化上报层                 │                   │
│            │  OpenTelemetry + Langfuse Python SDK      │                   │
│            └───────────────────┬───────────────────────┘                   │
│                                │                                            │
│  ┌─────────────────────────────▼────────────────────────────────────────┐  │
│  │                        Langfuse 平台层                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │  │
│  │  │  Trace   │  │ Session  │  │  Score   │  │  Dataset/Prompt Mgmt │ │  │
│  │  │  (单次)  │  │  (会话)  │  │  (评分)  │  │    (版本管理)        │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                │                                            │
│            ┌───────────────────▼───────────────────────┐                   │
│            │          统一评测配置层 (rubric.json)      │                   │
│            │  single_turn | multi_turn | agent 维度    │                   │
│            └───────────────────────────────────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心概念定义

> **基于会议讨论 (12-23)** 的关键技术要点：

| 概念 | 定义 | 在本系统中的对应 |
|:---|:---|:---|
| **Trace** | 单次 LLM 调用记录 | `evaluate_turn()` 单次评测 |
| **Session** | 多轮对话完整记录，包含多个 Trace | `run_log_evaluation()` 会话级评测 |
| **OTEL** | OpenTelemetry 可观测性协议 | Langfuse SDK 自动上报 |
| **评测驱动开发 (EDD)** | 通过 Bad Case 调整 Prompt | 反馈闭环机制 |

---

## 三、升级后的统一评测维度

### 3.1 三类评测统一配置 (`rubric.json` 扩展)

```json
{
  "evaluation_types": ["single_turn", "multi_turn", "agent"],
  "rubrics": {
    "shared": [
      {
        "name": "accuracy_truthfulness",
        "description": "信息准确性，避免幻觉/错误",
        "criteria": {"1": "存在明显事实错误", "3": "细节有微小瑕疵", "5": "信息完全准确"}
      },
      {
        "name": "clarity_expression",
        "description": "表达清晰度",
        "criteria": {"1": "逻辑混乱难理解", "3": "基本清晰", "5": "简洁高效"}
      }
    ],
    "single_turn": [
      {
        "name": "relevance",
        "description": "回答与问题的相关性",
        "criteria": {"1": "完全离题", "3": "部分相关", "5": "高度相关"}
      },
      {
        "name": "completeness",
        "description": "回答的完整性",
        "criteria": {"1": "信息严重缺失", "3": "基本完整", "5": "全面详尽"}
      }
    ],
    "multi_turn": [
      {
        "name": "context_coherence",
        "description": "上下文连贯性，信息保持",
        "criteria": {"1": "前后矛盾", "3": "基本连贯", "5": "信息完美承接"}
      },
      {
        "name": "intent_tracking",
        "description": "用户意图追踪与理解",
        "criteria": {"1": "完全误解意图", "3": "部分理解", "5": "精准把握"}
      },
      {
        "name": "proactivity_interaction",
        "description": "主动引导对话能力",
        "criteria": {"1": "完全被动", "3": "简单追问", "5": "主动挖掘需求"}
      },
      {
        "name": "goal_completion",
        "description": "对话目标完成度",
        "criteria": {"1": "目标未达成", "3": "部分完成", "5": "完美达成"}
      }
    ],
    "agent": [
      {
        "name": "task_completion",
        "description": "任务完成率 - Agent 是否成功完成指定任务",
        "criteria": {"1": "任务失败", "3": "部分完成", "5": "完美完成"}
      },
      {
        "name": "tool_selection_accuracy",
        "description": "工具选择准确性 - 是否选对工具",
        "criteria": {"1": "选错工具", "3": "可用但非最优", "5": "最优选择"}
      },
      {
        "name": "tool_usage_correctness",
        "description": "工具调用正确性 - 参数是否正确",
        "criteria": {"1": "参数错误导致失败", "3": "轻微问题", "5": "调用完美"}
      },
      {
        "name": "decision_reasoning",
        "description": "决策推理质量 - 思维链是否清晰合理",
        "criteria": {"1": "推理混乱", "3": "基本合理", "5": "逻辑严谨"}
      },
      {
        "name": "execution_efficiency",
        "description": "执行效率 - 是否用最少步骤完成",
        "criteria": {"1": "冗余严重", "3": "步骤合理", "5": "最优路径"}
      }
    ]
  }
}
```

### 3.2 评测类型自动识别

```python
# 文件: run_eval.py (新增函数)

def detect_evaluation_type(data: dict) -> str:
    """
    自动识别评测类型
    
    规则:
    - 包含 tool_calls / agent_actions → agent
    - messages 长度 > 2 → multi_turn
    - 其他 → single_turn
    """
    if "tool_calls" in data or "agent_actions" in data:
        return "agent"
    messages = data.get("messages", [])
    if len(messages) > 2:
        return "multi_turn"
    return "single_turn"


def get_rubrics_for_type(eval_type: str, rubric_config: dict) -> list:
    """
    根据评测类型获取对应的评分维度
    
    Returns:
        shared 维度 + 类型特定维度
    """
    shared = rubric_config.get("rubrics", {}).get("shared", [])
    type_specific = rubric_config.get("rubrics", {}).get(eval_type, [])
    return shared + type_specific
```

---

## 四、代码升级实施方案

### 4.1 Phase 1: Langfuse 集成 (无侵入式)

> **目标**: 在不破坏现有功能的前提下，接入 Langfuse 可观测性

**Step 1: 安装依赖**
```bash
pip install langfuse opentelemetry-api opentelemetry-sdk
```

**Step 2: 创建 `observability.py` 模块**
```python
# 文件: observability.py (新建)

import os
from functools import wraps
from typing import Optional
from langfuse import Langfuse

# 环境变量配置
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

# 全局 Langfuse 客户端 (懒加载)
_langfuse_client: Optional[Langfuse] = None

def get_langfuse() -> Optional[Langfuse]:
    """获取 Langfuse 客户端实例"""
    global _langfuse_client
    if _langfuse_client is None and LANGFUSE_PUBLIC_KEY:
        _langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
    return _langfuse_client


def trace_evaluation(func):
    """
    装饰器: 自动上报评测结果到 Langfuse
    
    使用方式:
        @trace_evaluation
        def evaluate_turn(...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        langfuse = get_langfuse()
        result = func(*args, **kwargs)
        
        if langfuse and isinstance(result, dict):
            # 创建 Trace 并上报评分
            trace = langfuse.trace(
                name=func.__name__,
                metadata={"args": str(args[:2])}  # 简化元数据
            )
            
            # 上报评分
            if "score" in result:
                langfuse.score(
                    trace_id=trace.id,
                    name=kwargs.get("dimension", {}).get("name", "unknown"),
                    value=result["score"],
                    comment=result.get("reasoning", "")
                )
        
        return result
    return wrapper


class SessionTracer:
    """
    会话级 Trace 管理器
    
    使用方式:
        with SessionTracer(session_id) as tracer:
            tracer.log_turn(turn_idx, result)
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.langfuse = get_langfuse()
        self.trace = None
    
    def __enter__(self):
        if self.langfuse:
            self.trace = self.langfuse.trace(
                name=f"session_{self.session_id}",
                session_id=self.session_id
            )
        return self
    
    def __exit__(self, *args):
        if self.langfuse:
            self.langfuse.flush()
    
    def log_turn(self, turn_idx: int, eval_results: list):
        """记录单轮评测结果"""
        if self.trace:
            span = self.trace.span(name=f"turn_{turn_idx}")
            for result in eval_results:
                self.langfuse.score(
                    trace_id=self.trace.id,
                    name=result.get("dimension", "unknown"),
                    value=result.get("score", 0),
                    comment=result.get("reasoning", "")
                )
```

**Step 3: 改造 `run_eval.py` (最小改动)**

```python
# 在 run_eval.py 顶部添加导入
from observability import trace_evaluation, SessionTracer, get_langfuse

# 在 evaluate_turn 函数上添加装饰器
@trace_evaluation
def evaluate_turn(agent: RealAgent, 
                  history: List[Dict], 
                  target_response: str, 
                  dimension: Dict, 
                  domain: str = "general") -> Dict:
    # ... 现有代码保持不变 ...
    pass

# 改造 run_log_evaluation 支持 Session 追踪
def run_log_evaluation(logs: List[Dict], rubrics: List[Dict], progress_callback=None) -> List[Dict]:
    agent = RealAgent()
    results = []
    
    for session in logs:
        session_id = session.get('session_id', 'unknown')
        
        # 使用 SessionTracer 管理会话级 Trace
        with SessionTracer(session_id) as tracer:
            session_results = {"session_id": session_id, "evaluations": []}
            
            for idx, msg in enumerate(session.get('messages', [])):
                if msg['role'] == 'assistant':
                    # ... 评测逻辑 ...
                    tracer.log_turn(idx, turn_evals)
            
            results.append(session_results)
    
    return results
```

---

### 4.2 Phase 2: Agent 评测支持

**新增 `agent_eval.py` 模块**:

```python
# 文件: agent_eval.py (新建)

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from agent import RealAgent

@dataclass
class AgentTrace:
    """Agent 执行追踪数据结构"""
    trace_id: str
    task_description: str
    tool_calls: List[Dict] = field(default_factory=list)
    decision_steps: List[Dict] = field(default_factory=list)
    final_output: Optional[str] = None
    success: bool = False
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# Agent 专属评测 Prompt
AGENT_JUDGE_PROMPT = """
### 角色
你是一个 Agent 执行质量评测专家。

### 任务描述
{task_description}

### Agent 执行轨迹
**工具调用记录**:
{tool_calls_text}

**决策推理过程**:
{decision_steps_text}

**最终输出**:
{final_output}

### 评测维度: {dimension_name}
{criteria_text}

### 输出格式
请输出 JSON: {{"score": 1-5, "reasoning": "评测理由"}}
"""


def evaluate_agent_trace(
    agent: RealAgent,
    trace: AgentTrace,
    dimension: Dict
) -> Dict:
    """
    评测单个 Agent 执行轨迹
    """
    # 格式化工具调用
    tool_calls_text = "\n".join([
        f"- {tc.get('tool_name')}: {tc.get('arguments')}"
        for tc in trace.tool_calls
    ]) or "无工具调用"
    
    # 格式化决策步骤
    decision_steps_text = "\n".join([
        f"Step {i+1}: {step.get('thought')}"
        for i, step in enumerate(trace.decision_steps)
    ]) or "无决策记录"
    
    # 格式化评分标准
    criteria_text = "\n".join([
        f"- {level}分: {desc}"
        for level, desc in dimension.get("criteria", {}).items()
    ])
    
    prompt = AGENT_JUDGE_PROMPT.format(
        task_description=trace.task_description,
        tool_calls_text=tool_calls_text,
        decision_steps_text=decision_steps_text,
        final_output=trace.final_output or "无输出",
        dimension_name=dimension["name"],
        criteria_text=criteria_text
    )
    
    # 调用 LLM 评测
    raw_output = agent.chat([], prompt)
    
    # 解析结果 (复用现有解析逻辑)
    import json, re
    try:
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        result = json.loads(match.group(0)) if match else {}
        return {
            "dimension": dimension["name"],
            "score": result.get("score", 3),
            "reasoning": result.get("reasoning", raw_output[:100])
        }
    except:
        return {"dimension": dimension["name"], "score": 3, "reasoning": "解析失败"}


def run_agent_evaluation(
    traces: List[AgentTrace],
    rubric_config: Dict
) -> List[Dict]:
    """
    批量评测 Agent 执行轨迹
    """
    agent = RealAgent()
    results = []
    
    # 获取 Agent 专属维度
    agent_rubrics = rubric_config.get("rubrics", {}).get("agent", [])
    shared_rubrics = rubric_config.get("rubrics", {}).get("shared", [])
    all_rubrics = shared_rubrics + agent_rubrics
    
    for trace in traces:
        trace_results = {
            "trace_id": trace.trace_id,
            "task": trace.task_description,
            "success": trace.success,
            "evaluations": []
        }
        
        for rubric in all_rubrics:
            eval_result = evaluate_agent_trace(agent, trace, rubric)
            trace_results["evaluations"].append(eval_result)
        
        results.append(trace_results)
    
    return results
```

---

### 4.3 Phase 3: 统一入口 & 类型自动分发

**更新 `run_eval.py` 主入口**:

```python
# 文件: run_eval.py (扩展)

def run_unified_evaluation(
    data: List[Dict],
    rubric_config: Dict,
    progress_callback=None
) -> List[Dict]:
    """
    统一评测入口 - 自动识别类型并分发
    
    支持:
    - single_turn: 单轮问答
    - multi_turn: 多轮对话 (现有功能)
    - agent: Agent 工作流
    """
    from agent_eval import AgentTrace, run_agent_evaluation
    
    results = []
    
    for item in data:
        eval_type = detect_evaluation_type(item)
        
        if eval_type == "agent":
            # Agent 评测
            trace = AgentTrace(
                trace_id=item.get("trace_id", "unknown"),
                task_description=item.get("task", ""),
                tool_calls=item.get("tool_calls", []),
                decision_steps=item.get("decision_steps", []),
                final_output=item.get("output", ""),
                success=item.get("success", False)
            )
            agent_results = run_agent_evaluation([trace], rubric_config)
            results.extend(agent_results)
            
        elif eval_type == "multi_turn":
            # 多轮对话评测 (现有逻辑)
            rubrics = get_rubrics_for_type("multi_turn", rubric_config)
            session_results = run_log_evaluation([item], rubrics, progress_callback)
            results.extend(session_results)
            
        else:
            # 单轮评测
            rubrics = get_rubrics_for_type("single_turn", rubric_config)
            # 包装成 session 格式复用现有逻辑
            wrapped = {
                "session_id": item.get("id", "single"),
                "messages": [
                    {"role": "user", "content": item.get("input", "")},
                    {"role": "assistant", "content": item.get("output", "")}
                ]
            }
            session_results = run_log_evaluation([wrapped], rubrics, progress_callback)
            results.extend(session_results)
    
    return results
```

---

## 五、验证计划

### 5.1 单元测试

```python
# 文件: test_unified_eval.py

import pytest
from run_eval import detect_evaluation_type, get_rubrics_for_type

def test_detect_evaluation_type():
    # 测试 Agent 类型识别
    agent_data = {"tool_calls": [{"name": "search"}]}
    assert detect_evaluation_type(agent_data) == "agent"
    
    # 测试多轮对话识别
    multi_turn_data = {"messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}]}
    assert detect_evaluation_type(multi_turn_data) == "multi_turn"
    
    # 测试单轮识别
    single_data = {"messages": [{"role": "user"}, {"role": "assistant"}]}
    assert detect_evaluation_type(single_data) == "single_turn"
```

### 5.2 集成测试

```bash
# 运行现有评测验证兼容性
python run_eval.py

# 启动 Web UI 验证
streamlit run app.py
```

### 5.3 Langfuse 连通性测试

```python
# 测试 Langfuse 连接
from observability import get_langfuse

lf = get_langfuse()
if lf:
    trace = lf.trace(name="test_connection")
    print(f"✅ Langfuse 连接成功, Trace ID: {trace.id}")
else:
    print("⚠️ Langfuse 未配置")
```

---

## 六、工作排期 (更新版)

| 周次 | 日期 | 任务 | 产出物 | 状态 |
|:---:|:---:|:---|:---|:---:|
| W1 | 12.25-12.31 | 扩展 `rubric.json` 配置 | 统一评测维度配置文件 | 🔜 Ready |
| W1 | 12.25-12.31 | 创建 `observability.py` | Langfuse 集成模块 | 🔜 Ready |
| W2 | 01.01-01.07 | 改造 `run_eval.py` | 支持类型自动识别 | ⏳ Planned |
| W2 | 01.01-01.07 | 创建 `agent_eval.py` | Agent 评测核心逻辑 | ⏳ Planned |
| W3 | 01.08-01.14 | 部署 Langfuse 本地环境 | Docker 部署文档 | ⏳ Planned |
| W3 | 01.08-01.14 | 集成测试 | 端到端验证报告 | ⏳ Planned |
| W4 | 01.15-01.21 | UI 适配 (`app.py`) | 支持三种评测类型展示 | ⏳ Planned |
| W5 | 01.22-01.28 | 与千锤系统对接 | API 接口文档 | ⏳ Planned |

---

## 七、关键成功因素

1. **向后兼容** - 现有多轮对话评测功能不受影响
2. **渐进式升级** - 模块化设计，可独立部署测试
3. **OTEL 标准化** - 遵循行业标准，便于未来切换监控平台
4. **配置驱动** - 评测维度通过 JSON 配置，无需改代码即可扩展
5. **可观测优先** - 每个评测结果自动上报，支持问题回溯

---

## 八、附录：快速启动指南

### 8.1 环境变量配置

```bash
# .env 文件
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=http://localhost:3000

# OpenAI 兼容配置 (已有)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.v3.cm/v1
```

### 8.2 一键部署 Langfuse

```bash
# Docker Compose 部署
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d
```

### 8.3 运行评测

```bash
# 多轮对话评测 (现有)
python run_eval.py

# 统一评测 (升级后)
python -c "from run_eval import run_unified_evaluation; ..."

# Web UI
streamlit run app.py
```

---

> 📝 **文档维护**: 本方案将随实施进度持续更新  
> 🔗 **相关文档**: [12-23 会议纪要](./12-23%20AI驱动企业运营与生产闭环会议.md) | [README](./README.md)
