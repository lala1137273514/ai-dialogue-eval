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

## 一、升级核心目的

### 1.1 一句话总结

> **从「离线跑一次看结果的多轮对话评测」升级为「每次调用都有记录、可追踪、可分析的统一可观测性平台」**

### 1.2 升级驱动力 (WHY)

| 当前痛点 | 升级目标 | 业务价值 |
|:---|:---|:---|
| 只能评测多轮对话 | 兼容单轮 Prompt、多轮对话、Agent 工作流 | 覆盖 CEO 大模型、交付 Agent 等场景 |
| 评测结果只存文件 | 所有调用可追踪 (Trace)、可查询、可分析 | 快速定位质量问题 |
| 无法快速定位问题 | Bad Case 快速定位 → Prompt 优化闭环 | 持续改进 AI 输出质量 |
| 手动跑脚本评测 | 自动记录、自动评分 | 降低人工成本 |

### 1.3 升级价值矩阵

```
升级前:                                   升级后:
┌───────────────────┐                    ┌────────────────────────────────┐
│ 多轮对话评测       │                    │ 统一 Agent 可观测性平台         │
│                   │                    │                                │
│ • 评测多轮对话     │        →           │ • 单轮/多轮/Agent 全覆盖       │
│ • 输出 JSON 文件   │                    │ • SQLite 持久化 + Trace 追踪   │
│ • 一次性看结果     │                    │ • 历史可查 + 统计可视化        │
│ • 手动定位问题     │                    │ • Bad Case 自动标记 + 优化闭环 │
└───────────────────┘                    └────────────────────────────────┘
```

---

## 二、升级内容详解 (WHAT)

### 2.1 评测范围扩展

| 评测类型 | 输入数据 | 评测维度 | 适用场景 |
|:---|:---|:---|:---|
| **单轮 (single_turn)** | 1个 Prompt + 1个 Response | 准确性、相关性、完整性、清晰度 | 销售成绩分析、单次问答 |
| **多轮 (multi_turn)** | 完整对话 Session | 上下文连贯、意图理解、主动引导、目标完成 | 客服对话、营销沟通 |
| **Agent** | 任务 + 工具调用 + 决策过程 | 任务完成率、工具选择准确性、决策质量、执行效率 | 交付 Agent、自动化工作流 |

### 2.2 新增 Trace 追踪能力

```
升级前:                              升级后:
                                    
评测脚本 → JSON输出 → 手动查看       评测脚本 → SQLite → Trace 可视化
         ↓                                     ↓
    一次性结果                        ┌─────────────────────────┐
    无法追溯                          │  traces 表              │
                                     │  ├─ trace_id (唯一ID)   │
                                     │  ├─ session_id (会话ID) │
                                     │  ├─ eval_type (评测类型)│
                                     │  ├─ input_data (输入)   │
                                     │  ├─ output_data (输出)  │
                                     │  └─ created_at (时间)   │
                                     ├─────────────────────────┤
                                     │  scores 表              │
                                     │  ├─ trace_id (关联)     │
                                     │  ├─ dimension (维度)    │
                                     │  ├─ score (评分)        │
                                     │  └─ reasoning (理由)    │
                                     └─────────────────────────┘
```

### 2.3 新增 UI 功能

| Tab | 升级前 | 升级后 |
|:---|:---|:---|
| 日志回放 | ✅ 有 | ✅ 保留 |
| 评测看板 | ✅ 有 | ✅ 增强 (柱状图+雷达图+Bad Case列表) |
| Trace 追踪 | ❌ 无 | ✅ 新增 (列表+详情+筛选) |
| 标准配置 | ✅ 有 | ✅ 保留 |

---

## 三、三种评测类型详细流程

### 3.1 单轮评测流程 (single_turn)

**适用场景**: 销售成绩分析、FAQ 问答、单次 Prompt 调用质量检测

```
┌─────────────────────────────────────────────────────────────────────┐
│                        单轮评测流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  输入数据                    评测过程                     输出结果   │
│  ┌─────────────┐            ┌──────────────┐           ┌──────────┐│
│  │ {           │            │              │           │ Trace    ││
│  │   "input":  │ ────────→  │ 类型识别     │           │ 记录     ││
│  │   "用户问题"│            │ (single_turn)│           └────┬─────┘│
│  │   "output": │            └──────┬───────┘                │      │
│  │   "AI回复"  │                   │                        │      │
│  │ }           │            ┌──────▼───────┐                │      │
│  └─────────────┘            │ 加载评分维度 │           ┌────▼─────┐│
│                             │ - 准确性     │           │ Score    ││
│                             │ - 相关性     │ ────────→ │ 写入DB   ││
│                             │ - 完整性     │           └──────────┘│
│                             │ - 清晰度     │                       │
│                             └──────┬───────┘                       │
│                                    │                               │
│                             ┌──────▼───────┐           ┌──────────┐│
│                             │ LLM Judge    │           │ 返回结果 ││
│                             │ 逐维度打分   │ ────────→ │ + UI展示 ││
│                             └──────────────┘           └──────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**代码调用示例**:
```python
# 单轮评测数据格式
single_turn_data = {
    "id": "eval_001",
    "input": "这个产品有什么优惠？",
    "output": "目前我们有新用户立减50元活动..."
}

# 自动识别为 single_turn 类型
result = run_unified_evaluation([single_turn_data], rubric_config)
```

---

### 3.2 多轮评测流程 (multi_turn)

**适用场景**: 客服对话质量、销售沟通效果、智能助手多轮交互

```
┌─────────────────────────────────────────────────────────────────────┐
│                        多轮评测流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  输入数据 (Session)          评测过程                     输出结果   │
│  ┌─────────────────┐        ┌──────────────┐           ┌──────────┐│
│  │ {               │        │              │           │Session   ││
│  │  "session_id":  │ ────→  │ 类型识别     │           │Trace     ││
│  │  "messages": [  │        │ (multi_turn) │           └────┬─────┘│
│  │    {user: ...}, │        └──────┬───────┘                │      │
│  │    {asst: ...}, │               │                        │      │
│  │    {user: ...}, │        ┌──────▼───────┐                │      │
│  │    {asst: ...}  │        │ 遍历每轮     │                │      │
│  │  ]              │        │ Assistant    │           ┌────▼─────┐│
│  │ }               │        │ 回复         │           │ 每轮     ││
│  └─────────────────┘        └──────┬───────┘           │ Score    ││
│                                    │                   │ 写入DB   ││
│                             ┌──────▼───────┐           └──────────┘│
│                             │ 对每轮评测:  │                       │
│                             │ - 上下文连贯 │                       │
│                             │ - 意图理解   │           ┌──────────┐│
│                             │ - 主动引导   │           │ 会话汇总 ││
│                             │ - 目标完成   │ ────────→ │ 综合得分 ││
│                             └──────────────┘           │ 薄弱点   ││
│                                                        └──────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**代码调用示例**:
```python
# 多轮评测数据格式 (现有格式)
multi_turn_data = {
    "session_id": "sess_001",
    "messages": [
        {"role": "user", "content": "有什么产品推荐？"},
        {"role": "assistant", "content": "您好！请问您主要关注哪方面？"},
        {"role": "user", "content": "性价比高的"},
        {"role": "assistant", "content": "推荐这款产品..."}
    ]
}

# 自动识别为 multi_turn 类型
result = run_unified_evaluation([multi_turn_data], rubric_config)
```

---

### 3.3 Agent 评测流程 (agent)

**适用场景**: 交付 Agent、自动修复工作流、任务型 Agent 质量监控

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent 评测流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  输入数据 (Agent Trace)      评测过程                     输出结果   │
│  ┌─────────────────┐        ┌──────────────┐           ┌──────────┐│
│  │ {               │        │              │           │Agent     ││
│  │  "task": "..."  │ ────→  │ 类型识别     │           │Trace     ││
│  │  "tool_calls":[│        │ (agent)      │           └────┬─────┘│
│  │    {name, args} │        └──────┬───────┘                │      │
│  │  ],             │               │                        │      │
│  │  "decisions":[  │        ┌──────▼───────┐                │      │
│  │    {thought}    │        │ 构建评测     │                │      │
│  │  ],             │        │ Prompt       │           ┌────▼─────┐│
│  │  "output":"..." │        │ 包含:        │           │ Agent    ││
│  │  "success":true │        │ - 任务描述   │           │ Score    ││
│  │ }               │        │ - 工具调用   │           │ 写入DB   ││
│  └─────────────────┘        │ - 决策过程   │           └──────────┘│
│                             │ - 最终输出   │                       │
│                             └──────┬───────┘                       │
│                                    │                               │
│                             ┌──────▼───────┐           ┌──────────┐│
│                             │ Agent维度:   │           │ 返回:    ││
│                             │ - 任务完成率 │           │ - 各维度 ││
│                             │ - 工具选择   │ ────────→ │   得分   ││
│                             │ - 决策质量   │           │ - 整体   ││
│                             │ - 执行效率   │           │   评价   ││
│                             └──────────────┘           └──────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**代码调用示例**:
```python
# Agent 评测数据格式
agent_data = {
    "id": "agent_001",
    "task": "修复正则表达式匹配错误",
    "tool_calls": [
        {"name": "search_regex", "arguments": {"pattern": "用户.*"}},
        {"name": "update_regex", "arguments": {"new_pattern": "用户(想要|需要).*"}}
    ],
    "decisions": [
        {"thought": "分析发现当前正则无法匹配'用户想要'开头的句子"},
        {"thought": "需要扩展正则模式以支持更多变体"}
    ],
    "output": "已更新正则表达式",
    "success": True
}

# 自动识别为 agent 类型
result = run_unified_evaluation([agent_data], rubric_config)
```

---

## 四、Trace 功能实现机制

### 4.1 Trace 核心概念

| 概念 | 定义 | 实现方式 |
|:---|:---|:---|
| **Trace** | 一次评测调用的完整记录 | SQLite traces 表的一条记录 |
| **Score** | 某个维度的评分及理由 | SQLite scores 表关联 trace_id |
| **Session** | 多个 Trace 的逻辑分组 | 通过 session_id 关联 |

### 4.2 Trace 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Trace 数据流                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. 评测开始                                                         │
│  ┌─────────────┐                                                    │
│  │ 调用评测   │                                                     │
│  │ 函数       │──┐                                                  │
│  └─────────────┘  │                                                 │
│                   │                                                  │
│  2. 创建 Trace    ▼                                                 │
│  ┌─────────────────────────────────────┐                            │
│  │ TraceStore.create_trace(            │                            │
│  │   session_id = "sess_001",          │                            │
│  │   eval_type = "multi_turn",         │                            │
│  │   input_data = {...},               │──→ INSERT INTO traces      │
│  │   model = "gpt-4o-mini"             │                            │
│  │ ) → 返回 trace_id                   │                            │
│  └─────────────────────────────────────┘                            │
│                   │                                                  │
│  3. 执行评测      ▼                                                 │
│  ┌─────────────────────────────────────┐                            │
│  │ 对每个维度调用 LLM Judge:           │                            │
│  │   - clarity: 4分, "表达清晰..."     │                            │
│  │   - proactivity: 3分, "略显被动..." │                            │
│  │   - accuracy: 5分, "信息准确..."    │                            │
│  └─────────────────────────────────────┘                            │
│                   │                                                  │
│  4. 记录 Score    ▼                                                 │
│  ┌─────────────────────────────────────┐                            │
│  │ TraceStore.add_score(               │                            │
│  │   trace_id = trace_id,              │                            │
│  │   dimension = "clarity",            │──→ INSERT INTO scores      │
│  │   score = 4,                        │    (重复每个维度)          │
│  │   reasoning = "表达清晰..."         │                            │
│  │ )                                   │                            │
│  └─────────────────────────────────────┘                            │
│                   │                                                  │
│  5. 查询展示      ▼                                                 │
│  ┌─────────────────────────────────────┐                            │
│  │ TraceStore.list_traces()            │                            │
│  │ TraceStore.get_trace(trace_id)      │──→ Streamlit UI 展示       │
│  │ TraceStore.get_dimension_stats()    │                            │
│  └─────────────────────────────────────┘                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Trace UI 展示

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔍 Trace 追踪                                           [筛选控件]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ 🟢 Trace: abc123 | Session: sess_001 | 得分: 4.2/5 | 12-25 21:30   │
│ ├─ 类型: multi_turn | 模型: gpt-4o-mini                             │
│ └─ 展开查看详情 ▼                                                   │
│    ┌─────────────────────────────────────────────────────────────┐ │
│    │ 📥 输入: {"messages": [...]}                                 │ │
│    │ 📤 输出: {"evaluations": [...]}                              │ │
│    │ ⭐ 评分:                                                      │ │
│    │   🟢 clarity: 4/5 - "表达清晰简洁"                           │ │
│    │   🟡 proactivity: 3/5 - "略显被动，可增加引导"               │ │
│    │   🟢 accuracy: 5/5 - "信息完全准确"                          │ │
│    └─────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ 🔴 Trace: def456 | Session: sess_002 | 得分: 2.5/5 | 12-25 21:25   │
│ ├─ 类型: agent | 模型: gpt-4o-mini                                  │
│ └─ 展开查看详情 ▼                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 五、现有系统分析

### 5.1 当前架构概览

| 模块 | 文件 | 功能 |
|:---|:---|:---|
| LLM Agent | `agent.py` | OpenAI 兼容的 LLM 调用封装 |
| 评测引擎 | `run_eval.py` | 多轮对话评测核心逻辑 |
| Web UI | `app.py` | Streamlit 可视化界面 |
| 评分标准 | `rubric.json` | 6维度评分体系 |

### 5.2 升级改造点

| 文件 | 改造内容 |
|:---|:---|
| `trace_store.py` | **新建** - SQLite 存储模块 |
| `agent_eval.py` | **新建** - Agent 评测模块 |
| `run_eval.py` | **修改** - 添加 Trace 记录 + 类型识别 |
| `app.py` | **修改** - 新增 Trace 追踪 Tab |
| `rubric.json` | **扩展** - 新增 single_turn/agent 维度 |

---

## 六、升级后的统一评测维度


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

## 四、代码升级实施方案 (轻量级方案)

> **技术选型调整**: 采用 **SQLite + Streamlit UI** 方案，无需部署额外服务，实现 Langfuse 核心功能

### 4.1 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|:---|:---|:---|:---|
| Langfuse 部署 | 功能完整、UI 现成 | 需要 Docker、4核8G 服务器 | 团队协作 |
| Langfuse Cloud | 零部署 | 数据在云端、有配额限制 | 快速验证 |
| **SQLite + Streamlit** | 零依赖、数据本地化 | 需自建 UI | ✅ 个人/小团队 |

### 4.2 轻量级架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  KST Agent 评估系统 (轻量级)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐ │
│  │  run_eval.py     │ ──写入→  │      SQLite 数据库           │ │
│  │  (评测逻辑)      │         │      traces.db               │ │
│  │                  │         │  ┌────────┐ ┌─────────────┐  │ │
│  │  agent_eval.py   │         │  │ traces │ │   scores    │  │ │
│  │  (Agent 评测)    │         │  └────────┘ └─────────────┘  │ │
│  └──────────────────┘         └──────────────┬───────────────┘ │
│                                              │                  │
│  ┌──────────────────────────────────────────┐│                  │
│  │  app.py (Streamlit UI)                   ││                  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐│◄────────────────┘ │
│  │  │日志回放 │ │评测看板 │ │ Trace 追踪  ││                    │
│  │  │(现有)   │ │(现有)   │ │ (新增)      ││                    │
│  │  └─────────┘ └─────────┘ └─────────────┘│                    │
│  └──────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、小版本迭代计划

### 📌 版本总览

| 版本 | 名称 | 核心功能 | 预计周期 |
|:---:|:---|:---|:---:|
| **v0.2.0** | Trace 基础版 | SQLite 存储 + Trace 记录 | 2 天 |
| **v0.3.0** | UI 集成版 | Streamlit Trace 查看页 | 2 天 |
| **v0.4.0** | 统计分析版 | 维度统计 + 趋势图表 | 3 天 |
| **v0.5.0** | Agent 评测版 | Agent 评测 + 类型自动识别 | 3 天 |

---

### 🔖 v0.2.0 - Trace 基础版

**目标**: 实现评测结果自动存储到 SQLite

**新建文件**: `trace_store.py`

```python
# trace_store.py - Trace 本地存储模块

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "traces.db"

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        -- Trace 表: 记录每次评测调用
        CREATE TABLE IF NOT EXISTS traces (
            trace_id TEXT PRIMARY KEY,
            session_id TEXT,
            eval_type TEXT DEFAULT 'multi_turn',
            name TEXT,
            input_data TEXT,
            output_data TEXT,
            model TEXT,
            latency_ms INTEGER,
            tokens_used INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Scores 表: 评分记录
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            dimension TEXT NOT NULL,
            score REAL NOT NULL,
            reasoning TEXT,
            turn_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
        );
        
        -- Sessions 表: 会话汇总
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            trace_count INTEGER DEFAULT 0,
            avg_score REAL,
            weak_points TEXT,
            strong_points TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);
        CREATE INDEX IF NOT EXISTS idx_scores_trace ON scores(trace_id);
        CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
    """)
    conn.commit()
    return conn


@contextmanager
def get_db():
    """获取数据库连接 (上下文管理器)"""
    conn = init_db()
    try:
        yield conn
    finally:
        conn.close()


class TraceStore:
    """Trace 存储管理器"""
    
    @staticmethod
    def create_trace(
        session_id: str,
        name: str = "evaluation",
        eval_type: str = "multi_turn",
        input_data: dict = None,
        output_data: dict = None,
        model: str = None,
        latency_ms: int = None,
        metadata: dict = None
    ) -> str:
        """创建新的 Trace 记录"""
        trace_id = str(uuid.uuid4())[:8]  # 短 ID
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO traces 
                (trace_id, session_id, eval_type, name, input_data, output_data, model, latency_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace_id,
                session_id,
                eval_type,
                name,
                json.dumps(input_data or {}, ensure_ascii=False),
                json.dumps(output_data or {}, ensure_ascii=False),
                model,
                latency_ms,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            conn.commit()
        
        return trace_id
    
    @staticmethod
    def add_score(
        trace_id: str,
        dimension: str,
        score: float,
        reasoning: str = "",
        turn_index: int = None
    ):
        """为 Trace 添加评分"""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO scores (trace_id, dimension, score, reasoning, turn_index)
                VALUES (?, ?, ?, ?, ?)
            """, (trace_id, dimension, score, reasoning, turn_index))
            conn.commit()
    
    @staticmethod
    def get_trace(trace_id: str) -> Optional[Dict]:
        """获取单个 Trace 详情"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()
            
            if not row:
                return None
            
            trace = dict(row)
            trace['input_data'] = json.loads(trace['input_data'] or '{}')
            trace['output_data'] = json.loads(trace['output_data'] or '{}')
            trace['metadata'] = json.loads(trace['metadata'] or '{}')
            
            # 获取关联的评分
            scores = conn.execute(
                "SELECT dimension, score, reasoning, turn_index FROM scores WHERE trace_id = ?",
                (trace_id,)
            ).fetchall()
            trace['scores'] = [dict(s) for s in scores]
            
            return trace
    
    @staticmethod
    def list_traces(
        session_id: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """列出 Trace 记录"""
        with get_db() as conn:
            if session_id:
                rows = conn.execute("""
                    SELECT t.*, 
                           COUNT(s.id) as score_count,
                           AVG(s.score) as avg_score
                    FROM traces t
                    LEFT JOIN scores s ON t.trace_id = s.trace_id
                    WHERE t.session_id = ?
                    GROUP BY t.trace_id
                    ORDER BY t.created_at DESC
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT t.*, 
                           COUNT(s.id) as score_count,
                           AVG(s.score) as avg_score
                    FROM traces t
                    LEFT JOIN scores s ON t.trace_id = s.trace_id
                    GROUP BY t.trace_id
                    ORDER BY t.created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset)).fetchall()
            
            return [dict(r) for r in rows]
    
    @staticmethod
    def get_dimension_stats() -> Dict[str, float]:
        """获取各维度平均分统计"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT dimension, AVG(score) as avg_score, COUNT(*) as count
                FROM scores
                GROUP BY dimension
                ORDER BY avg_score ASC
            """).fetchall()
            return {r['dimension']: {'avg': round(r['avg_score'], 2), 'count': r['count']} for r in rows}
    
    @staticmethod
    def get_session_summary(session_id: str) -> Dict:
        """获取会话汇总"""
        with get_db() as conn:
            # 计算会话统计
            stats = conn.execute("""
                SELECT 
                    COUNT(DISTINCT t.trace_id) as trace_count,
                    AVG(s.score) as avg_score
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                WHERE t.session_id = ?
            """, (session_id,)).fetchone()
            
            # 各维度得分
            dim_scores = conn.execute("""
                SELECT s.dimension, AVG(s.score) as avg_score
                FROM scores s
                JOIN traces t ON s.trace_id = t.trace_id
                WHERE t.session_id = ?
                GROUP BY s.dimension
            """, (session_id,)).fetchall()
            
            dim_dict = {r['dimension']: round(r['avg_score'], 2) for r in dim_scores}
            weak = [d for d, s in dim_dict.items() if s < 3]
            strong = [d for d, s in dim_dict.items() if s >= 4]
            
            return {
                'session_id': session_id,
                'trace_count': stats['trace_count'] or 0,
                'avg_score': round(stats['avg_score'] or 0, 2),
                'dimension_scores': dim_dict,
                'weak_points': weak,
                'strong_points': strong
            }
```

**修改文件**: `run_eval.py` (最小改动)

```python
# 在 run_eval.py 顶部添加导入
from trace_store import TraceStore
import time

# 修改 evaluate_turn 函数，添加 Trace 记录
def evaluate_turn(agent: RealAgent, 
                  history: List[Dict], 
                  target_response: str, 
                  dimension: Dict, 
                  domain: str = "general",
                  trace_id: str = None) -> Dict:  # 新增参数
    """对单个回复进行单维度打分"""
    
    start_time = time.time()
    
    # ... 原有评测逻辑 ...
    
    result = {
        "score": result.get("score", 3),
        "reasoning": result.get("reasoning", raw_output[:50])
    }
    
    # 自动记录到 TraceStore
    if trace_id:
        TraceStore.add_score(
            trace_id=trace_id,
            dimension=dimension['name'],
            score=result['score'],
            reasoning=result['reasoning']
        )
    
    return result


# 修改 run_log_evaluation，添加 Trace 创建
def run_log_evaluation(logs: List[Dict], rubrics: List[Dict], progress_callback=None) -> List[Dict]:
    agent = RealAgent()
    results = []
    
    for session in logs:
        session_id = session.get('session_id', 'unknown')
        
        # 为每个 session 创建 Trace
        trace_id = TraceStore.create_trace(
            session_id=session_id,
            name=f"eval_{session_id}",
            eval_type="multi_turn",
            input_data={"messages": session.get('messages', [])},
            model=agent.model_name
        )
        
        session_results = {"session_id": session_id, "trace_id": trace_id, "evaluations": []}
        
        # ... 原有评测循环，传入 trace_id ...
        
        results.append(session_results)
    
    return results
```

**验收标准**:
- [x] 运行 `python run_eval.py` 后，`traces.db` 文件自动创建
- [x] 数据库中有 `traces` 和 `scores` 表
- [x] 评测结果自动写入数据库

---

### 🔖 v0.3.0 - UI 集成版

**目标**: 在 Streamlit 中新增 Trace 查看页面

**修改文件**: `app.py` (新增 Tab)

```python
# 在 app.py 中新增 Tab

from trace_store import TraceStore

# 修改 Tab 定义
tab1, tab2, tab3, tab4 = st.tabs([
    "📜 日志回放", 
    "📊 评测看板", 
    "🔍 Trace 追踪",  # 新增
    "🛠️ 标准配置"
])

# 新增 Tab3: Trace 追踪
with tab3:
    st.markdown("### 🔍 Trace 追踪记录")
    
    # 筛选控件
    col1, col2 = st.columns([1, 2])
    with col1:
        session_filter = st.text_input("🔎 按 Session ID 筛选", "")
    with col2:
        limit = st.slider("显示条数", 10, 100, 50)
    
    # 加载 Trace 列表
    traces = TraceStore.list_traces(
        session_id=session_filter if session_filter else None,
        limit=limit
    )
    
    if not traces:
        st.info("暂无 Trace 记录，请先运行评测")
    else:
        st.markdown(f"共 **{len(traces)}** 条记录")
        
        for trace in traces:
            avg_score = trace.get('avg_score') or 0
            score_color = "🟢" if avg_score >= 4 else "🟡" if avg_score >= 3 else "🔴"
            
            with st.expander(
                f"{score_color} Trace: {trace['trace_id']} | Session: {trace['session_id']} | "
                f"得分: {avg_score:.1f}/5 | {trace['created_at']}"
            ):
                # Trace 详情
                detail = TraceStore.get_trace(trace['trace_id'])
                
                if detail:
                    # 输入/输出
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**📥 输入数据**")
                        st.json(detail.get('input_data', {}))
                    with col2:
                        st.markdown("**📤 输出数据**")
                        st.json(detail.get('output_data', {}))
                    
                    # 评分详情
                    st.markdown("**⭐ 评分详情**")
                    for score in detail.get('scores', []):
                        score_val = score['score']
                        badge = "🟢" if score_val >= 4 else "🟡" if score_val >= 3 else "🔴"
                        st.markdown(f"""
                        {badge} **{score['dimension']}**: {score_val}/5  
                        > {score['reasoning']}
                        """)
```

**验收标准**:
- [x] Streamlit 界面新增 "Trace 追踪" Tab
- [x] 可查看 Trace 列表和详情
- [x] 支持按 Session ID 筛选

---

### 🔖 v0.4.0 - 统计分析版

**目标**: 新增统计看板和趋势分析

**新增功能**:

```python
# 在 app.py 的 Tab2 (评测看板) 中扩展

with tab2:
    st.markdown("### 📊 评测统计看板")
    
    # 1. 整体指标卡片
    stats = TraceStore.get_dimension_stats()
    
    if stats:
        cols = st.columns(len(stats))
        for i, (dim, data) in enumerate(stats.items()):
            with cols[i]:
                delta = "↑" if data['avg'] >= 4 else "↓" if data['avg'] < 3 else ""
                st.metric(
                    label=dim.replace("_", " ").title(),
                    value=f"{data['avg']}/5",
                    delta=delta
                )
    
    st.markdown("---")
    
    # 2. 维度对比柱状图
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 各维度平均分")
        if stats:
            import plotly.express as px
            df = pd.DataFrame([
                {"维度": k, "平均分": v['avg']} 
                for k, v in stats.items()
            ])
            fig = px.bar(df, x="维度", y="平均分", color="平均分",
                        color_continuous_scale=["#ff6b6b", "#ffd93d", "#6bcb77"])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 雷达图分布")
        if stats:
            fig = create_radar_chart(
                {k: v['avg'] for k, v in stats.items()},
                title="维度得分分布"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 3. 薄弱点提示
    weak_dims = [k for k, v in stats.items() if v['avg'] < 3]
    if weak_dims:
        st.warning(f"⚠️ 薄弱维度: {', '.join(weak_dims)}")
    
    # 4. 最近 Bad Case 列表
    st.markdown("#### 🔴 近期低分记录")
    with get_db() as conn:
        bad_cases = conn.execute("""
            SELECT t.trace_id, t.session_id, s.dimension, s.score, s.reasoning
            FROM scores s
            JOIN traces t ON s.trace_id = t.trace_id
            WHERE s.score < 3
            ORDER BY t.created_at DESC
            LIMIT 10
        """).fetchall()
    
    if bad_cases:
        for case in bad_cases:
            st.error(f"Trace `{case['trace_id']}` | {case['dimension']}: {case['score']}/5 - {case['reasoning'][:50]}...")
```

**验收标准**:
- [x] 评测看板展示各维度平均分
- [x] 有柱状图和雷达图可视化
- [x] 自动标记薄弱维度
- [x] 展示最近低分记录

---

### 🔖 v0.5.0 - Agent 评测版

**目标**: 支持 Agent 类型评测 + 类型自动识别

**新建文件**: `agent_eval.py`

```python
# agent_eval.py - Agent 评测模块

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from agent import RealAgent
from trace_store import TraceStore
import json
import re

@dataclass
class AgentTrace:
    """Agent 执行轨迹"""
    task_id: str
    task_description: str
    tool_calls: List[Dict] = field(default_factory=list)
    decision_steps: List[Dict] = field(default_factory=list)
    final_output: Optional[str] = None
    success: bool = False


AGENT_JUDGE_PROMPT = """
### 角色
你是 Agent 执行质量评测专家。

### 任务
{task_description}

### 执行轨迹
**工具调用**: {tool_calls_text}
**决策过程**: {decision_steps_text}
**最终输出**: {final_output}

### 评测维度: {dimension_name}
{criteria_text}

### 输出
仅输出 JSON: {{"score": 1-5, "reasoning": "理由"}}
"""


def evaluate_agent(trace: AgentTrace, rubrics: List[Dict]) -> Dict:
    """评测单个 Agent 执行轨迹"""
    agent = RealAgent()
    
    # 创建 Trace 记录
    trace_id = TraceStore.create_trace(
        session_id=trace.task_id,
        name="agent_eval",
        eval_type="agent",
        input_data={
            "task": trace.task_description,
            "tool_calls": trace.tool_calls,
            "decisions": trace.decision_steps
        },
        output_data={"result": trace.final_output, "success": trace.success}
    )
    
    results = {"trace_id": trace_id, "task": trace.task_description, "scores": []}
    
    for rubric in rubrics:
        prompt = AGENT_JUDGE_PROMPT.format(
            task_description=trace.task_description,
            tool_calls_text=json.dumps(trace.tool_calls, ensure_ascii=False),
            decision_steps_text=json.dumps(trace.decision_steps, ensure_ascii=False),
            final_output=trace.final_output or "无",
            dimension_name=rubric['name'],
            criteria_text=json.dumps(rubric.get('criteria', {}), ensure_ascii=False)
        )
        
        raw = agent.chat([], prompt)
        
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
            score = parsed.get("score", 3)
            reasoning = parsed.get("reasoning", raw[:100])
        except:
            score, reasoning = 3, "解析失败"
        
        # 记录评分
        TraceStore.add_score(trace_id, rubric['name'], score, reasoning)
        results['scores'].append({"dimension": rubric['name'], "score": score, "reasoning": reasoning})
    
    return results
```

**修改 `run_eval.py`**: 添加类型自动识别

```python
def detect_evaluation_type(data: dict) -> str:
    """自动识别评测类型"""
    if "tool_calls" in data or "agent_actions" in data:
        return "agent"
    if len(data.get("messages", [])) > 2:
        return "multi_turn"
    return "single_turn"


def run_unified_evaluation(data: List[Dict], rubric_config: Dict) -> List[Dict]:
    """统一评测入口"""
    from agent_eval import AgentTrace, evaluate_agent
    
    results = []
    for item in data:
        eval_type = detect_evaluation_type(item)
        
        if eval_type == "agent":
            trace = AgentTrace(
                task_id=item.get("id", "unknown"),
                task_description=item.get("task", ""),
                tool_calls=item.get("tool_calls", []),
                decision_steps=item.get("decisions", []),
                final_output=item.get("output"),
                success=item.get("success", False)
            )
            agent_rubrics = rubric_config.get("rubrics", {}).get("agent", [])
            results.append(evaluate_agent(trace, agent_rubrics))
        else:
            # 复用现有多轮/单轮逻辑
            rubrics = get_rubrics_for_type(eval_type, rubric_config)
            results.extend(run_log_evaluation([item], rubrics))
    
    return results
```

**验收标准**:
- [x] 支持 Agent 类型数据输入
- [x] 自动识别 single_turn / multi_turn / agent 类型
- [x] Agent 评测结果写入 SQLite
- [x] UI 中可查看 Agent 类型的 Trace

---

## 六、完整迭代排期

| 版本 | 日期 | 核心任务 | 产出物 | 状态 |
|:---:|:---:|:---|:---|:---:|
| **v0.2.0** | 12.26-12.27 | SQLite 存储模块 | `trace_store.py` | 🔜 |
| **v0.2.0** | 12.26-12.27 | 改造 run_eval.py | 自动记录 Trace | 🔜 |
| **v0.3.0** | 12.28-12.29 | Trace 查看页面 | app.py 新增 Tab | ⏳ |
| **v0.3.0** | 12.28-12.29 | 筛选 & 详情展示 | 可交互 UI | ⏳ |
| **v0.4.0** | 12.30-01.01 | 统计看板扩展 | 柱状图/雷达图 | ⏳ |
| **v0.4.0** | 12.30-01.01 | Bad Case 列表 | 低分记录展示 | ⏳ |
| **v0.5.0** | 01.02-01.04 | Agent 评测模块 | `agent_eval.py` | ⏳ |
| **v0.5.0** | 01.02-01.04 | 类型自动识别 | 统一入口函数 | ⏳ |

---

## 七、关键成功因素

1. **零依赖部署** - 仅需 Python + SQLite，无需 Docker
2. **向后兼容** - 现有评测功能完全保留
3. **渐进式升级** - 每个小版本独立可用
4. **数据本地化** - 所有数据存储在本地 `traces.db`
5. **复用现有 UI** - 直接在 Streamlit 中扩展

---

## 八、附录：快速启动

### 8.1 运行评测并记录 Trace

```bash
# 运行评测 (自动记录到 traces.db)
python run_eval.py

# 查看数据库
sqlite3 traces.db "SELECT * FROM traces LIMIT 5;"
```

### 8.2 启动 Web UI

```bash
streamlit run app.py
# 访问新增的 "Trace 追踪" Tab
```

### 8.3 查看统计

```python
from trace_store import TraceStore

# 各维度平均分
stats = TraceStore.get_dimension_stats()
print(stats)

# 会话汇总
summary = TraceStore.get_session_summary("session_001")
print(summary)
```

---

> 📝 **文档维护**: 本方案将随实施进度持续更新  
> 🔗 **相关文档**: [12-23 会议纪要](./12-23%20AI驱动企业运营与生产闭环会议.md) | [README](./README.md)

