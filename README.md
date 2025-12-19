# AI 对话评测系统 Pro

> 基于 LLM-as-a-Judge 的多轮对话质量评测平台，支持工作流节点溯源与智能诊断

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 **合并评测** | 每条回复只做 1 次 LLM 调用，一次性输出 6 维度评分 |
| ⚖️ **综合分算法** | 最低分惩罚机制，防止低分维度被平均分掩盖 |
| 🔍 **深度分析** | 低分回复自动触发根因分析 + 工作流节点溯源 |
| 📊 **可视化仪表盘** | 雷达图、评分分布、会话对比 |
| 📚 **历史记录** | SQLite 持久化存储，支持增删改查 |
| 📥 **报告导出** | Markdown / JSON 完整评测报告 |

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
ai-dialogue-eval-main/
├── app.py              # Streamlit 主应用
├── run_eval.py         # 评测执行引擎
├── database.py         # SQLite 数据库模块
├── agent.py            # LLM 调用封装
├── workflow_parser.py  # Dify 工作流解析器
├── prompt_optimizer.py # Prompt 优化工具
├── rubric.json         # 评分标准配置
├── test_cases1.json    # 示例对话日志
├── Dify.yml            # 示例工作流配置
└── eval_results.db     # SQLite 数据库文件
```

## 📋 功能模块

### 1. 📊 工作台
- 数据源加载状态
- 快捷操作入口
- 系统概览

### 2. 📜 日志回放
- 三栏布局：会话列表 | 对话内容 | 评测结果
- 对话消息与评分联动
- 实时查看各维度得分

### 3. 🚀 智能评测
- **Phase 1**: 合并快速评测（1次调用 = 6维度分数）
- **Phase 2**: 低分深度分析（根因 + 溯源 + 建议）
- 可配置低分阈值（1-4 分）
- 自动保存到 SQLite

### 4. 🔍 低分分析
- 问题回复聚合展示
- 根因分析 + 修改建议
- 工作流节点溯源

### 5. 📚 历史评测
- 历史批次列表
- 关联文件查看（日志/工作流/评分标准）
- 批次详情与 Turn 级评分
- 删除功能

### 6. 🛠️ 评分标准配置
- 在线编辑 rubric.json
- 维度权重调整

### 7. 💡 Prompt 工坊
- Prompt 生成与优化
- 流式输出

### 8. 🎬 演示教程
- 交互式功能引导
- 7 步快速了解系统
- 支持自动播放（3秒/步）
- 随时可从侧边栏启动

## 📐 评分维度

| 维度 | 说明 |
|------|------|
| clarity_sentence_structure | 表达清晰度 |
| proactivity_interaction | 主动引导能力 |
| content_benefits | 内容价值呈现 |
| persona_authority | 专业权威感 |
| accuracy_truthfulness | 信息准确性 |
| tone_empathy | 语气共情度 |

## 📊 综合分算法

```
综合分 = min(平均分, 最低分 + 1.5)
```

**示例**：
- 各维度 [1, 5, 5, 5, 5, 5] → 平均 4.33，综合分 **2.5**（触发深度分析）
- 各维度 [4, 4, 4, 4, 4, 4] → 平均 4.0，综合分 **4.0**（正常）

## 📁 数据格式

### 对话日志 (JSON)

```json
[
  {
    "session_id": "consult_001",
    "domain": "医美咨询",
    "messages": [
      {"role": "user", "content": "想了解瘦脸针"},
      {"role": "assistant", "content": "您好！瘦脸针是..."}
    ]
  }
]
```

### 评分标准 (rubric.json)

```json
{
  "rubrics": [
    {
      "name": "clarity_sentence_structure",
      "description": "表达清晰度评估",
      "criteria": {"5": "完美", "4": "良好", "3": "一般", "2": "较差", "1": "严重问题"},
      "low_score_checklist": ["语句不通顺", "表达含糊"]
    }
  ],
  "low_score_threshold": 3
}
```

## 🔧 环境变量

```bash
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

## 📝 更新日志

### v3.1 (2024-12-19)
- 🎬 演示教程：交互式功能引导，7步快速上手
- 🔄 自动播放：勾选后每3秒自动切换下一步
- 🎯 侧边栏控制：演示进度和按钮统一显示

### v3.0 (2024-12-18)
- ✨ 合并评测：每条回复 1 次调用输出 6 维度分数
- ⚖️ 综合分算法：最低分惩罚机制
- 📚 历史评测：SQLite 持久化 + 增删改查
- 🔧 低分阈值可选 1-4

### v2.0
- 两阶段评测：快速打分 + 深度分析
- 工作流节点溯源
- 报告导出（Markdown / JSON）
- 日志回放增强

### v1.0
- 基础评测功能
- 多维度打分
- 可视化仪表盘

---

**Powered by LLM-as-a-Judge** | 支持工作流节点溯源 | AI 对话评测系统 Pro v3.0
