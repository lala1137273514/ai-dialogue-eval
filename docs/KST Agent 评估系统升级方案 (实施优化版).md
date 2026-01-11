# KST Agent 评估系统升级方案 (深度优化版)

> **版本**: v3.0 深度优化版  
> **更新日期**: 2026年1月3日  
> **核心目标**: 从「离线跑一次看结果的多轮对话评测」升级为「每次调用都有记录、可追踪、可分析的统一可观测性平台」

---

## 一、升级概述

### 1.1 升级驱动力

| 当前痛点 | 升级目标 | 业务价值 |
|---------|---------|---------|
| 只能评测多轮对话 | 兼容单轮 Prompt、多轮对话、Agent 工作流 | 覆盖 CEO 大模型、交付 Agent 等场景 |
| 评测结果只存文件 | 所有调用可追踪 (Trace)、可查询、可分析 | 快速定位质量问题 |
| 无法快速定位问题 | Bad Case 快速定位 → Prompt 优化闭环 | 持续改进 AI 输出质量 |
| 手动跑脚本评测 | 自动记录、自动评分 | 降低人工成本 |

---

## 二、技术可行性评估

### 2.1 现有代码架构分析

| 模块 | 文件 | 现状 | 升级可行性 |
|------|------|------|-----------|
| LLM Agent | `agent.py` | OpenAI 兼容封装，支持重试 | ✅ 无需改动 |
| 评测引擎 | `run_eval.py` | 一次 LLM 调用评 6 维度 | ✅ 添加 Trace 钩子 |
| 数据存储 | `database.py` | SQLite 4 层表结构 | ✅ 扩展 traces 表 |
| Web UI | `app.py` | Streamlit 多 Tab | ✅ 新增 Trace Tab |
| 统一调度 | `eval_dispatcher.py` | v0.9.0 新增 | ✅ 统一评测入口 |

### 2.2 风险与缓解

| 风险项 | 影响 | 缓解措施 |
|-------|------|---------|
| 表结构变更导致数据迁移 | 历史数据丢失 | 新建 `traces` 表，保留原表 |
| 类型识别误判 | 错用评测维度 | 添加 `eval_type` 显式指定 |
| Agent 数据格式不统一 | 解析失败 | 定义标准 Schema + 容错 |

---

## 三、版本迭代排期

| 版本 | 日期 | 核心功能 | 前端改动 | 后端改动 | 状态 |
|------|------|---------|---------|---------|------|
| **v0.2.0** | 1/3-1/4 | Trace 存储 | 无 | 新建 trace_store.py | ✅ 已完成 |
| **v0.3.0** | 1/5-1/7 | UI 集成 | 新增 Trace Tab | 查询 API | ✅ 已完成 |
| **v0.4.0** | 1/8-1/10 | 统计分析 | 图表组件 | 统计 API | ✅ 已完成 |
| **v0.5.0** | 1/11-1/13 | Agent 评测 | 类型选择器 | agent_eval.py | ✅ 已完成 |
| **v0.7.0** | 1/14-1/15 | 数据浏览优化 | 列表+详情视图 | Rich List API | ✅ 已完成 |
| **v0.8.0** | 1/16-1/17 | 链路规范化 | 移除 Mock | eval_dispatcher | ✅ 已完成 |
| **v0.9.0** | 1/18-1/20 | 统一调度器 | 评测中心重构 | Dispatcher API | ✅ 已完成 |
| **v1.0.0** | 1/11 | 评估器功能 | 评估器管理+选择 | evaluator_store.py | ✅ 已完成 |

---

## 四、各版本详细设计

### 4.1 v0.2.0 - Trace 存储模块 ✅

#### 后端设计

**新建文件**: `trace_store.py`

```python
class TraceStore:
    """Trace 存储管理器 (Langfuse 风格)"""
    
    @staticmethod
    def create_trace(session_id, eval_type, input_data, model) -> str:
        """创建 Trace 记录"""
        trace_id = str(uuid.uuid4())[:8]
        # INSERT INTO traces ...
        return trace_id
    
    @staticmethod
    def add_score(trace_id, dimension, score, reasoning, turn_index=None):
        """添加评分记录"""
        # INSERT INTO scores ...
    
    @staticmethod
    def update_trace_output(trace_id, output_data, latency_ms):
        """更新 Trace 输出"""
        # UPDATE traces SET output_data = ?, latency_ms = ?
```

**修改文件**: `run_eval.py`

```python
# 在 run_log_evaluation() 中添加 Trace 钩子
def run_log_evaluation(logs, rubrics, ...):
    for session in logs:
        # 🆕 创建 Trace
        trace_id = TraceStore.create_trace(
            session_id=session['session_id'],
            eval_type='multi_turn',
            input_data={'messages': session['messages']},
            model=agent.model_name
        )
        
        for idx, msg in enumerate(messages):
            if msg['role'] == 'assistant':
                eval_res = evaluate_turn_unified(...)
                
                # 🆕 记录每维度评分
                for dim, score in eval_res['scores'].items():
                    TraceStore.add_score(trace_id, dim, score, '', idx)
```

**数据库表**:

```sql
CREATE TABLE traces (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT,
    eval_type TEXT DEFAULT 'multi_turn',
    input_data TEXT,
    output_data TEXT,
    model TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scores (
    id INTEGER PRIMARY KEY,
    trace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    reasoning TEXT,
    turn_index INTEGER,
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
);
```

---

### 4.2 v0.3.0 - UI 集成 (Trace Tab) ✅

#### 后端设计

**新增 API 函数** (在 `trace_store.py`):

```python
@staticmethod
def list_traces(session_id=None, eval_type=None, limit=50) -> List[Dict]:
    """列出 Trace 列表，支持筛选"""

@staticmethod
def get_trace_detail(trace_id) -> Dict:
    """获取 Trace 详情 + 所有评分"""
```

#### 前端设计

**修改文件**: `app.py` - 新增 Trace 追踪 Tab

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│ 🔍 Trace 追踪                                                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐ │
│  │ 🔎 Session ID    │  │ 📋 评测类型      │  │ 📊 显示条数       │ │
│  │ [输入框]         │  │ [下拉: all/...]  │  │ [滑块: 10-100]    │ │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  共 23 条记录                                                        │
│                                                                      │
│  🟢 abc123 | Session: sess_001 | 4.2/5 | multi_turn | 12-25 21:30  │
│  └─ [点击展开详情 ▼]                                                 │
│     ├─ 📥 输入: {"messages": [...]}                                 │
│     ├─ 📤 输出: {"evaluations": [...]}                              │
│     └─ ⭐ 评分: clarity 4/5, proactivity 3/5, accuracy 5/5          │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 4.3 v0.4.0 - 统计分析 ✅

#### 后端设计

**新增 API 函数**:

```python
@staticmethod
def get_dimension_stats() -> Dict[str, Dict]:
    """各维度统计"""
    # SELECT name, AVG(value), COUNT(*) FROM scores GROUP BY name
    return {"clarity": {"avg": 4.2, "count": 150}, ...}

@staticmethod
def get_low_score_traces(threshold=3, limit=20) -> List[Dict]:
    """获取低分 Trace 列表"""

@staticmethod
def get_trend_data(days=7) -> List[Dict]:
    """获取趋势数据"""
```

#### 前端设计

**扩展评测看板 Tab**:

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 评测统计看板                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 4.2/5   │ │ 3.8/5   │ │ 4.5/5   │ │ 3.2/5 ↓ │ │ 4.0/5   │       │
│  │ 清晰度  │ │ 主动性  │ │ 准确性  │ │ 意图 ⚠️ │ │ 连贯性  │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐   │
│  │     📊 维度平均分柱状图     │ │      📈 雷达图分布          │   │
│  └─────────────────────────────┘ └─────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  ⚠️ 薄弱维度: intent_tracking (3.2/5)                               │
├─────────────────────────────────────────────────────────────────────┤
│  🔴 近期低分记录 (score < 3)                                        │
│  ├─ abc123 | clarity: 2/5 - "表达混乱，逻辑不清"                    │
│  └─ def456 | proactivity: 1/5 - "完全被动"                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 4.4 v0.5.0 - Agent 评测 (三种接入方式) ✅

#### 架构设计

```plaintext
                    ┌─────────────────────────────────────────┐
                    │          Agent 评测入口                  │
                    └─────────────────────────────────────────┘
                              ▲           ▲           ▲
          ┌───────────────────┴─┐   ┌─────┴─────┐   ┌─┴───────────────────┐
          │ 方式 1: JSON 上传    │   │ 方式 2:    │   │ 方式 3: HTTP API     │
          │ (Streamlit UI)      │   │ Python API │   │ (跨系统集成)        │
          └─────────────────────┘   └───────────┘   └─────────────────────┘
                              │           │           │
                              ▼           ▼           ▼
                    ┌─────────────────────────────────────────┐
                    │     agent_eval.py (统一评测逻辑)         │
                    └─────────────────────────────────────────┘
```

---

#### 方式 1: JSON 文件上传 (离线批量评测)

**适用场景**: 批量导入历史 Agent 执行记录

**JSON Schema**:

```json
{
  "task_id": "agent_001",
  "task": "修复正则匹配错误",
  "tool_calls": [
    {"name": "search_regex", "arguments": {"pattern": "用户.*"}, "result": "找到3条"},
    {"name": "update_regex", "arguments": {"new_pattern": "用户(想要|需要).*"}}
  ],
  "decisions": [
    {"step": 1, "thought": "分析发现当前正则无法匹配'用户想要'开头的句子"}
  ],
  "output": "已更新正则表达式",
  "success": true
}
```

---

#### 方式 2: Python API (嵌入式调用)

**适用场景**: 集成到现有 Python Agent 项目

```python
from agent_eval import evaluate_agent, AgentTrace

trace = AgentTrace(
    task_id="agent_001",
    task_description="修复正则匹配错误",
    tool_calls=[{"name": "search_regex", "arguments": {"pattern": "用户.*"}}],
    decision_steps=[{"thought": "分析发现..."}],
    final_output="已更新正则表达式",
    success=True
)

result = evaluate_agent(trace)
print(f"Trace ID: {result['trace_id']}")
print(f"任务完成率: {result['scores']['task_completion']}/5")
```

---

#### 方式 3: HTTP API (跨系统集成)

**适用场景**: 非 Python 系统、微服务架构

**API 设计**:

```plaintext
POST /api/v1/eval/agent
Content-Type: application/json

{"task_id": "agent_001", "task": "...", "tool_calls": [...], "output": "..."}

Response:
{"trace_id": "abc123", "scores": {...}, "avg_score": 4.5}
```

---

#### Agent 评测维度

| 维度 | 描述 | 评分标准 |
|------|------|---------|
| `task_completion` | 任务完成率 | 1=失败, 3=部分完成, 5=完美完成 |
| `tool_selection_accuracy` | 工具选择准确性 | 1=选错, 3=可用非最优, 5=最优 |
| `decision_reasoning` | 决策推理质量 | 1=无逻辑, 3=基本合理, 5=清晰 |
| `execution_efficiency` | 执行效率 | 1=冗余多, 3=一般, 5=高效 |

---

## 五、新增文件清单

| 文件 | 版本 | 说明 |
|------|------|------|
| `trace_store.py` | v0.2.0 | Trace 存储模块 ✅ |
| `agent_eval.py` | v0.5.0 | Agent 评测核心逻辑 ✅ |
| `unified_eval.py` | v0.5.0 | 统一评测入口 ✅ |
| `api_server.py` | v0.5.0 | HTTP API 服务 (Flask) ✅ |
| `eval_dispatcher.py` | v0.9.0 | 统一评测调度器 ✅ |

---

## 六、验收标准

| 版本 | 前端验收 | 后端验收 |
|------|---------|---------|
| v0.2.0 | 无 | Trace 写入 SQLite ✅ |
| v0.3.0 | Trace Tab 可访问 ✅ | `list_traces()` 返回正确 ✅ |
| v0.4.0 | 图表渲染正确 ✅ | `get_dimension_stats()` 返回正确 ✅ |
| v0.5.0 | JSON 上传可用 ✅ | Python API + HTTP API 可调用 ✅ |
| v0.9.0 | 评测中心能自动识别类型 ✅ | `run_evaluation_task` 统一调度 ✅ |

---

## 七、关键成功因素

1. **零依赖部署** - 仅 Python + SQLite
2. **向后兼容** - 现有功能完全保留
3. **三入口支持** - JSON 上传 / Python API / HTTP API
4. **前后端解耦** - 后端提供 API，前端只做展示
5. **统一调度** - 无论何种数据类型，统一通过调度器处理

---

## 八、v0.6.0 - UI 重构 (4 入口结构) ✅

### 8.1 问题分析

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 页面混乱 | 9 个按钮分散 | 精简为 4 个入口 |
| 看板消失 | 路由映射问题 | 首页即看板 |
| 日志/Trace 分散 | 功能边界不清 | 整合到「数据浏览」 |

---

### 8.2 新导航结构 (4 入口)

```plaintext
┌─────────────────────┐
│ 📊 首页看板          │ ← 统计概览 + 快速入口
│ 🚀 评测中心          │ ← 配置 + 执行评测
│ 📜 数据浏览          │ ← 日志 + Trace + 历史 + 低分
│ ⚙️ 系统设置          │ ← 维度 + Prompt
└─────────────────────┘
```

---

### 8.3 首页看板 (dashboard)

整合原「工作台」+「统计看板」:

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 首页看板                                                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 4.2/5   │ │ 3.8/5   │ │ 4.5/5   │ │ 3.2/5 ⚠️│ │ 4.0/5   │       │
│  │ 清晰度  │ │ 主动性  │ │ 准确性  │ │ 意图    │ │ 语气    │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────────┐        │
│  │     📊 柱状图            │  │      📈 雷达图           │        │
│  └──────────────────────────┘  └──────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────┤
│  快速入口:  [🚀 开始评测]  [📜 查看数据]  [⚙️ 系统设置]            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 8.4 评测中心 (eval_center)

一站式评测配置与执行:

- **Step 1**: 选择类型 (自动/单轮/多轮/Agent)
- **Step 2**: 数据源配置 (上传/选择)
- **Step 3**: 维度配置 (勾选启用)
- **Step 4**: 开始评测

---

### 8.5 数据浏览 (data_explorer)

整合为 4 个 Tabs:

| Tab | 内容 |
|-----|------|
| 📋 日志回放 | 原 logs 页面 |
| 🔍 Trace 追踪 | 原 trace 页面 |
| 📚 历史记录 | 原 history 页面 |
| 🔴 低分分析 | 原 analysis 页面 |

---

### 8.6 系统设置 (settings)

整合为 2 个 Tabs:

| Tab | 内容 |
|-----|------|
| 🛠️ 评分维度 | 原 rubric 页面 |
| 🎨 Prompt 模板 | 原 prompt 页面 |

---

### 8.7 路由映射

| current_page | 页面 |
|--------------|------|
| dashboard | 首页看板 (含统计) |
| eval_center | 评测中心 |
| data_explorer | 数据浏览 (4 Tabs) |
| settings | 系统设置 (2 Tabs) |

---

### 8.8 验收标准

| 功能 | 验收条件 |
|------|---------|
| 侧边栏 | 精简到 4 个入口 |
| 首页 | 看到统计图表 + 快捷入口 |
| 数据浏览 | 4 个 Tab 切换正常 |
| 设置 | 2 个 Tab 切换正常 |

---

## 九、v0.7.0 - 数据浏览深度优化 (List + Detail) ✅

### 9.1 问题分析

原有的数据浏览页面存在以下问题：
1. **信息密度低**: 仅显示 ID 和分数，无法快速判断内容。
2. **交互繁琐**: 需要点击展开才能看到详情。
3. **指标缺失**: 缺乏 Latency, Token, TTFT 等关键性能指标。

### 9.2 解决方案：Rich Table View (仿 Langfuse)

重构为 **Master-Detail** 布局：

**列表区域 (Top/Left)**:
- **Columns**: 
  - `Time`: 格式化时间 (MM-DD HH:mm)
  - `ID / Session`: 智能显示 Session ID 或任务描述
  - `Input Preview`: 用户输入/任务描述预览
  - `Output Preview`: 模型输出/最终结果预览
  - `Score`: 彩色进度条可视化的平均分
  - `Latency`: 响应耗时
  - `Tokens`: Token 消耗

**详情区域 (Bottom/Right)**:
- **Single Turn**: 卡片式 Input/Output + 评分维度
- **Multi Turn**: 聊天气泡回放 + Turn 级评分
- **Agent**: 任务描述 + 工具调用链 (Timeline) + 决策步骤

---

## 十、v0.8.0 - 评测链路规范化 (Standardization) ✅

### 10.1 核心目标

解决代码中硬编码 `eval_type='multi_turn'` 导致的类型错误，并实现评测逻辑的统一调度。

### 10.2 架构改进

**统一调度器 (`eval_dispatcher.py`)**:

```python
def run_evaluation_task(data, rubrics):
    """
    统一入口，自动路由：
    - eval_type='agent' -> 调用 agent_eval.evaluate_agent
    - eval_type='single/multi' -> 调用 run_eval.run_log_evaluation
    """
```

**TraceStore 增强**:
- 支持存储性能指标 (`latency_ms`, `ttft_ms`, `token_usage`).
- 只有正确路由的评测类型才会被写入数据库。

### 10.3 模拟数据升级

更新 `populate_test_data.py`，生成包含 Mock 性能指标的测试数据，确保前端展示功能的完整性验证。

---

## 十一、v0.9.0 - 统一调度与交互升级 ✅

### 11.1 核心目标

彻底重构评测执行流，引入 `eval_dispatcher` 作为唯一评测入口，前端完全解耦具体评测逻辑，仅负责展示状态和结果。

### 11.2 功能实现

1. **统一调度器 (`eval_dispatcher.py`)**:
   - **Data Normalization**: 自动识别并转换 `user_turns` / `messages` / `agent` 格式。
   - **DTO**: 引入 `EvalResultDTO` 和 `EvalSummaryDTO` 规范化返回结果。
   - **Error Handling**: 捕获所有异常并分类为 `error` 或 `skipped`。

2. **评测中心 UI 升级**:
   - **实时进度反馈**: 进度条 + 文字状态。
   - **结果摘要卡片**: 成功/失败/跳过/平均分一览。
   - **状态筛选**: 可按评测结果状态过滤列表。

---

> 📝 **文档状态**: 已更新至 v0.9.0，所有核心模块开发完成。