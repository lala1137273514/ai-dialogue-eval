# AI 对话评测系统 Pro (v0.9.0)

> 基于 LLM-as-a-Judge 的全链路 AI 质量评测平台，支持单轮、多轮及 Agent 评测。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🌐 **全模式支持** | 统一支持 **单轮对话** (Single Turn)、**多轮对话** (Multi Turn) 和 **Agent** 评测 |
| 🔄 **统一调度器** | 全新 `eval_dispatcher` 统一入口，自动路由不同评测类型，结构化结果输出 |
| 🕵️ **Trace 追踪** | 引入 Langfuse 风格的 Trace 机制，完整记录输入、输出、耗时与 Token 消耗 |
| 📊 **Dashboard 2.0** | 全新可视化看板，包含**组合趋势图**、**性能散点图**与**能力热力图** |
| 🎯 **合并评测** | 智能调度器自动合并 LLM 调用，一次性输出多维度评分 |
| ⚖️ **综合分算法** | 最低分惩罚机制，防止低分维度被平均分掩盖 |
| 📚 **持久化存储** | 本地 SQLite `traces.db` 存储所有评测记录与评分 |
| 📥 **报告导出** | 支持导出 Markdown / JSON 完整评测报告 |

## 🚀 快速开始

### 安装依赖

```bash
pip install streamlit pandas plotly openai pyyaml
```

### 启动应用

```bash
streamlit run app.py
```

### 访问地址

http://localhost:8501

## 📂 项目结构

```
ai-dialogue-eval/
├── app.py                  # Streamlit 主应用 (UI)
├── eval_dispatcher.py      # 统一评测调度器 (v0.9.0 核心)
├── run_eval.py             # 多轮/单轮评测引擎
├── agent_eval.py           # Agent 评测引擎
├── trace_store.py          # Trace 存储与可视化数据层
├── database.py             # 基础数据库模块
├── agent.py                # LLM 调用封装
├── unified_eval.py         # 统一评测入口
├── api_server.py           # HTTP API 服务 (Flask)
├── workflow_parser.py      # Dify 工作流解析器
├── prompt_optimizer.py     # Prompt 优化工具
├── populate_test_data.py   # 模拟数据生成器
├── simulation_data_gen.py  # Bad Case 生成器
├── config/
│   └── rubric.json         # 评分标准配置
└── data/
    ├── eval_single_turn.json   # 单轮评测数据
    ├── eval_multi_turn.json    # 多轮评测数据
    └── eval_agent.json         # Agent 评测数据
```

## 📋 主要功能模块

### 1. 📊 智能工作台 (Dashboard 2.0)
- **评测趋势与质量波动**: 组合图展示评测数量与平均分趋势。
- **性能与质量关联**: 散点图分析 Latency/Tokens 与分数的关联，发现"慢且差"的异常。
- **维度能力矩阵**: 热力图展示不同模式下的能力强弱分布。
- **模式切换器**: 一键切换全部/单轮/多轮/Agent 视图。

### 2. 🚀 评测中心
- **统一调度器**: 自动识别数据类型 (单轮/多轮/Agent) 并路由到对应引擎。
- **结构化结果**: 返回 `EvalResultDTO` 包含状态、分数、耗时、trace_id 等。
- **进度反馈**: 实时进度条 + 状态文本展示评测进度。
- **错误处理**: 详细的错误分类 (success/error/skipped) 及原因说明。

### 3. 🔍 数据浏览 (Data Explorer)
- **多模式列表**: 支持按 Agent/Single/Multi 筛选。
- **详细信息**: 查看 Latency, TTFT, Tokens 等性能指标。
- **深度详情**: 
    - Agent: 完整的工具调用链与思维链展示。
    - Chat: 气泡式对话还原。

### 4. ⚙️ 系统设置
- **评分标准配置**: 在线编辑 rubric.json。
- **Prompt 工坊**: Prompt 生成与优化。

## 📝 更新日志

### v0.9.0 (2026-01-03)
- **Unified Dispatcher**: 全新 `eval_dispatcher.py` 统一评测调度。
  - 统一入口 `run_evaluation_task()` 自动路由评测类型。
  - 结构化 DTO: `EvalResultDTO`, `EvalSummaryDTO`。
  - 输入验证 + 数据标准化 (`validate_input`, `normalize_data`)。
  - 完整错误处理与状态分类 (success/error/skipped)。
- **Eval Center UI**: 评测中心 UI 重构。
  - 评测摘要卡片 (总计/成功/跳过/失败/平均分)。
  - 按状态筛选结果列表。
  - 一键跳转 Trace 详情。

### v0.8.2 (2026-01-03)
- **Vis Upgrade**: Dashboard 升级为 Plotly 高级交互图表 (Combo/Scatter/Heatmap)。
- **Performance**: Trace 列表增加 Latency/Tokens 指标展示。
- **Fix**: 修复 TraceStore 数据读取稳定性问题。

### v0.8.0 (2026-01-02)
- **Unified Eval**: 引入 `eval_dispatcher` 统一调度单轮、多轮、Agent 评测。
- **Trace System**: 实现 `TraceStore` 本地存储，替代 JSON 文件。
- **Simulation**: 新增 `populate_test_data.py` 生成全量模拟数据。

### v0.7.0 (2026-01-01)
- **Data Explorer**: 数据浏览深度优化，Master-Detail 布局。
- **Rich Table**: 仿 Langfuse 的丰富列表视图。

### v0.6.0 (2025-12-31)
- **UI Refactor**: 4 入口导航结构 (首页看板/评测中心/数据浏览/系统设置)。
- **Dashboard Mode**: 模式切换器 (全部/单轮/多轮/Agent)。

### v3.1 (Legacy)
- 演示教程与自动播放功能。
- 合并评测 + SQLite 持久化。
