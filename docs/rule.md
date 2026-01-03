# AI 对话评测系统 - 功能规则与使用指南

> 本文档详细说明系统的核心逻辑、评测规则、数据规范和使用方法

---

## 一、系统概述

### 1.1 设计理念

本系统基于 **LLM-as-a-Judge** 范式，采用大语言模型作为评测裁判，对 **单轮对话** (Single Turn)、**多轮对话** (Multi Turn) 和 **Agent 智能体** 进行自动化质量评估。

核心设计原则：

- **统一调度**：无论何种评测类型，通过统一调度器路由，确保流程一致
- **效率优先**：合并评测，每条回复/任务只做 1 次 LLM 调用
- **精准识别**：最低分惩罚机制，防止低分被平均分掩盖
- **全链路追踪**：引入 Trace 机制，完整记录输入、输出、耗时与 Token
- **可持久**：SQLite 本地存储，支持历史记录回溯

### 1.2 评测流程

```
┌─────────────────────────────────────────────────────────────┐
│                        评测流程                              │
├─────────────────────────────────────────────────────────────┤
│  加载数据 → 统一调度 → 评测执行 → 结果标准化 → 写入 Trace    │
│     ↓          ↓          ↓           ↓            ↓        │
│    JSON   eval_dispatcher run_eval  EvalResultDTO  SQLite   │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、评测规则

### 2.1 对话评分维度 (Chat Evaluation)

适用于单轮对话和多轮对话：

| 维度代码 | 中文名称 | 评估内容 |
|----------|----------|----------|
| `clarity_sentence_structure` | 表达清晰度 | 语句通顺、结构清晰、逻辑连贯 |
| `proactivity_interaction` | 主动引导能力 | 主动提问、引导对话、挖掘需求 |
| `content_benefits` | 内容价值呈现 | 信息量、价值传递、利益点突出 |
| `persona_authority` | 专业权威感 | 专业术语使用、权威感建立 |
| `accuracy_truthfulness` | 信息准确性 | 事实正确、无虚假承诺 |
| `tone_empathy` | 语气共情度 | 语气亲和、情感共鸣、换位思考 |

### 2.2 Agent 评分维度 (Agent Evaluation)

适用于 Agent 任务执行评测：

| 维度代码 | 中文名称 | 评估内容 |
|----------|----------|----------|
| `task_completion` | 任务完成度 | 任务目标是否达成，结果是否正确 |
| `tool_selection_accuracy` | 工具选择准确性 | 是否选择了正确的工具，参数是否正确 |
| `decision_reasoning` | 决策推理逻辑 | 思考过程 (Thought) 是否清晰合理 |
| `execution_efficiency` | 执行效率 | 是否存在冗余步骤或无效操作 |

### 2.3 评分标准（1-5 分制）

| 分数 | 等级 | 描述 |
|------|------|------|
| **5** | 优秀 | 完美无问题，可作为标杆 |
| **4** | 良好 | 仅有细微瑕疵，整体优秀 |
| **3** | 一般 | 有待改进，存在轻微问题 |
| **2** | 较差 | 问题明显，部分检查清单命中 |
| **1** | 严重 | 问题严重，多项检查清单命中 |

### 2.4 综合分算法

```python
综合分 = min(平均分, 最低分 + 1.5)
```

**设计原理**：
- 单纯平均分会掩盖某维度的严重问题
- 最低分惩罚机制确保任意维度的重大缺陷都能被识别

---

## 三、数据规范

### 3.1 基础字段

所有数据类型均包含以下通用字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 唯一标识符 |
| `eval_type` | string | `single_turn` / `multi_turn` / `agent` |
| `domain` | string | 业务领域（可选） |

### 3.2 多轮/单轮对话数据

```json
{
  "session_id": "chat_001",
  "eval_type": "multi_turn",
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "您好！有什么可以帮您？"}
  ]
}
```

### 3.3 Agent 执行数据

```json
{
  "task_id": "agent_001",
  "eval_type": "agent",
  "task": "查询北京今天天气",
  "tool_calls": [
    {"name": "get_weather", "arguments": {"city": "Beijing"}}
  ],
  "output": "北京今天晴，气温 20度",
  "latency_ms": 1200,
  "token_usage": {"total": 150}
}
```

---

## 四、使用指南

### 4.1 功能导航 (4 入口)

系统采用精简的 4 入口导航结构：

| 功能模块 | 对应页面 | 主要功能 |
|----------|----------|----------|
| **📊 首页看板** | `dashboard` | 统计图表 (趋势/性能/能力)、快捷入口 |
| **🚀 评测中心** | `eval_center` | 数据加载、评测执行、简报查看 |
| **📜 数据浏览** | `data_explorer` | 日志回放、Trace 详情、历史记录回溯 |
| **⚙️ 系统设置** | `settings` | 评分标准配置、Prompt 模板管理 |

### 4.2 执行评测

1. 进入 **🚀 评测中心**。
2. 选择评测数据源 (支持上传 JSON 或加载测试数据)。
3. 系统自动识别数据类型 (单轮/多轮/Agent)。
4. 点击「开始评测」，观察实时进度条。
5. 完成后查看摘要，可点击「查看详情」跳转至数据浏览页。

### 4.3 数据分析

- **首页看板**：查看整体评分趋势、性能散点图 (Latency vs Score)、维度能力热力图。
- **数据浏览**：
  - 在列表页筛选「低分」或特定「类型」。
  - 点击列表项展开详情，查看具体的 Agent 思考链或对话气泡。
  - 关注 Latency 和 Token 消耗，识别性能瓶颈。

---

## 五、技术架构

### 5.1 模块依赖

```
app.py (Web UI)
    ├── eval_dispatcher.py (统一调度)
    │   ├── run_eval.py (对话评测引擎)
    │   └── agent_eval.py (Agent 评测引擎)
    ├── trace_store.py (Trace 存储与查询)
    └── database.py (基础 DB 操作)
```

### 5.2 数据库表结构 (SQLite)

核心表为 `traces` 和 `scores`：

```sql
-- 评测追踪记录
CREATE TABLE traces (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT,
    eval_type TEXT,        -- agent / multi_turn / single_turn
    input_data TEXT,       -- JSON: messages 或 task info
    output_data TEXT,      -- JSON: agent output 或 response
    model TEXT,
    latency_ms INTEGER,
    token_usage TEXT,      -- JSON
    avg_score REAL,
    status TEXT,           -- success / error
    created_at TIMESTAMP
);

-- 维度评分详情
CREATE TABLE scores (
    id INTEGER PRIMARY KEY,
    trace_id TEXT,
    name TEXT,             -- 维度名称
    value REAL,            -- 分数
    reasoning TEXT,        -- 理由
    turn_index INTEGER     -- 多轮对话的轮次
);
```

---

## 六、最佳实践

1. **类型明确**：在数据中显式指定 `eval_type`，避免系统误判。
2. **性能监控**：在 Agent 数据中记录 `latency_ms` 和 `token_usage`，以便在看板中生成性能散点图。
3. **定期清理**：在「数据浏览」页面的历史记录功能中，定期删除过期的测试批次。
4. **标准微调**：针对不同业务场景，在「系统设置」中微调评分维度的 Prompt 描述。

---

*AI 对话评测系统 Pro v0.9.0 | 功能规则文档*