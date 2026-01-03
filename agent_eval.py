"""
Agent 评测模块 v0.5.0

功能:
- Agent 执行轨迹评测
- 支持三种接入方式: JSON 上传 / Python API / HTTP API
- 评测维度: 任务完成率 / 工具选择 / 决策质量 / 执行效率
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from trace_store import TraceStore
from agent import RealAgent


@dataclass
class AgentTrace:
    """Agent 执行轨迹"""
    task_id: str
    task_description: str
    tool_calls: List[Dict]
    decision_steps: List[Dict]
    final_output: str
    success: bool
    metrics: Dict = None  # 🆕 可选性能数据


# Agent 评测 Prompt
AGENT_JUDGE_PROMPT = """
### 角色
你是 Agent 系统评估专家，擅长评估 AI Agent 的任务执行质量。

### 任务描述
{task_description}

### 工具调用记录
{tool_calls_text}

### 决策过程
{decisions_text}

### 最终输出
{final_output}

### 执行结果
任务是否成功: {success}

### 评测维度
请评估以下维度: {dimension_name}
{dimension_desc}

### 评分标准
{criteria}

### 任务指令
请对该 Agent 执行轨迹进行评分 (1-5分)，并给出具体理由。

### 输出格式 (JSON)
请仅输出合法的 JSON:
{{"score": 4, "reasoning": "评分理由..."}}
"""

# Agent 评测维度
AGENT_RUBRICS = [
    {
        "name": "task_completion",
        "description": "任务完成率 - 评估 Agent 是否成功完成了用户指定的任务",
        "criteria": "1=任务完全失败; 2=严重偏离目标; 3=部分完成; 4=基本完成; 5=完美完成"
    },
    {
        "name": "tool_selection_accuracy",
        "description": "工具选择准确性 - 评估 Agent 是否选择了正确的工具来完成任务",
        "criteria": "1=选错工具导致失败; 2=工具选择不当; 3=可用但非最优; 4=较优选择; 5=最优工具选择"
    },
    {
        "name": "decision_reasoning",
        "description": "决策推理质量 - 评估 Agent 的思考过程是否合理、逻辑是否清晰",
        "criteria": "1=无逻辑/混乱; 2=逻辑有明显漏洞; 3=基本合理; 4=逻辑清晰; 5=推理严谨且创新"
    },
    {
        "name": "execution_efficiency",
        "description": "执行效率 - 评估 Agent 是否高效地完成任务，避免冗余步骤",
        "criteria": "1=大量冗余步骤; 2=存在明显冗余; 3=一般效率; 4=较高效率; 5=极致高效"
    }
]


def format_tool_calls(tool_calls: List[Dict]) -> str:
    """格式化工具调用记录"""
    if not tool_calls:
        return "(无工具调用)"
    
    lines = []
    for i, tc in enumerate(tool_calls, 1):
        name = tc.get('name', 'unknown')
        args = tc.get('arguments', tc.get('args', {}))
        result = tc.get('result', '')
        lines.append(f"{i}. 调用 {name}({json.dumps(args, ensure_ascii=False)[:100]})")
        if result:
            lines.append(f"   → 结果: {str(result)[:100]}")
    return "\n".join(lines)


def format_decisions(decisions: List[Dict]) -> str:
    """格式化决策步骤"""
    if not decisions:
        return "(无记录决策过程)"
    
    lines = []
    for i, d in enumerate(decisions, 1):
        thought = d.get('thought', d.get('content', str(d)))
        lines.append(f"Step {i}: {thought[:150]}")
    return "\n".join(lines)


def parse_json_response(response: str) -> Dict:
    """解析 LLM 返回的 JSON"""
    try:
        # 尝试直接解析
        return json.loads(response)
    except:
        pass
    
    # 尝试提取 JSON 块
    import re
    patterns = [
        r'\{[^{}]*"score"[^{}]*\}',
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```'
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if '```' in pattern else match.group())
            except:
                continue
    
    # 默认返回
    return {"score": 3, "reasoning": "无法解析 LLM 响应"}


def evaluate_agent(
    trace: AgentTrace,
    rubrics: List[Dict] = None,
    model: str = None
) -> Dict:
    """
    评测 Agent 执行轨迹
    
    Args:
        trace: Agent 执行轨迹
        rubrics: 评测维度列表 (默认使用 AGENT_RUBRICS)
        model: 使用的评测模型
    
    Returns:
        {
            "trace_id": "abc123",
            "task": "任务描述",
            "scores": {"task_completion": 4, ...},
            "avg_score": 4.25,
            "details": [{"dimension": "...", "score": 4, "reasoning": "..."}],
            "success": True
        }
    """
    agent = RealAgent()
    
    if rubrics is None:
        rubrics = AGENT_RUBRICS
    
    # 创建 Trace 记录
    trace_id = TraceStore.create_trace(
        session_id=trace.task_id,
        eval_type='agent',
        input_data={
            'task': trace.task_description,
            'tool_calls': trace.tool_calls,
            'decisions': trace.decision_steps
        },
        output_data={
            'result': trace.final_output,
            'success': trace.success
        },
        model=model or agent.model_name,
        latency_ms=trace.metrics.get('latency_ms') if trace.metrics else None,
        metadata={'metrics': trace.metrics} if trace.metrics else None
    )
    
    # 格式化数据
    tool_calls_text = format_tool_calls(trace.tool_calls)
    decisions_text = format_decisions(trace.decision_steps)
    
    scores = {}
    details = []
    
    # 对每个维度调用 LLM Judge
    for rubric in rubrics:
        prompt = AGENT_JUDGE_PROMPT.format(
            task_description=trace.task_description,
            tool_calls_text=tool_calls_text,
            decisions_text=decisions_text,
            final_output=trace.final_output[:500],
            success="是" if trace.success else "否",
            dimension_name=rubric['name'],
            dimension_desc=rubric['description'],
            criteria=rubric['criteria']
        )
        
        try:
            result = agent.chat([], prompt)
            parsed = parse_json_response(result)
            score = min(5, max(1, int(parsed.get('score', 3))))
            reasoning = parsed.get('reasoning', '')
        except Exception as e:
            score = 3
            reasoning = f"评测失败: {str(e)}"
        
        scores[rubric['name']] = score
        details.append({
            'dimension': rubric['name'],
            'score': score,
            'reasoning': reasoning
        })
        
        # 记录评分
        TraceStore.add_score(
            trace_id=trace_id,
            name=rubric['name'],
            value=score,
            reasoning=reasoning
        )
    
    avg_score = sum(scores.values()) / len(scores) if scores else 0
    
    return {
        'trace_id': trace_id,
        'task': trace.task_description,
        'scores': scores,
        'avg_score': round(avg_score, 2),
        'details': details,
        'success': trace.success
    }


def evaluate_agent_from_dict(data: Dict) -> Dict:
    """
    从字典数据评测 Agent (用于 JSON 上传和 HTTP API)
    
    Args:
        data: {
            "task_id": "...",
            "task": "...",
            "tool_calls": [...],
            "decisions": [...],
            "output": "...",
            "success": true
        }
    """
    trace = AgentTrace(
        task_id=data.get('task_id', data.get('id', 'unknown')),
        task_description=data.get('task', data.get('task_description', '')),
        tool_calls=data.get('tool_calls', []),
        decision_steps=data.get('decisions', data.get('decision_steps', [])),
        final_output=data.get('output', data.get('final_output', '')),
        success=data.get('success', False),
        metrics={
            "latency_ms": data.get("latency_ms"),
            "ttft_ms": data.get("ttft_ms"),
            "token_usage": data.get("token_usage")
        }
    )
    return evaluate_agent(trace)


if __name__ == "__main__":
    print("🧪 Testing Agent Evaluation...")
    
    # 创建测试数据
    trace = AgentTrace(
        task_id="test_agent_001",
        task_description="修复正则表达式匹配错误，使其能匹配'用户想要'开头的句子",
        tool_calls=[
            {"name": "search_regex", "arguments": {"pattern": "用户.*"}, "result": "找到3条匹配"},
            {"name": "analyze_pattern", "arguments": {"text": "用户想要购买商品"}, "result": "不匹配"},
            {"name": "update_regex", "arguments": {"new_pattern": "用户(想要|需要).*"}, "result": "已更新"}
        ],
        decision_steps=[
            {"thought": "首先分析当前正则表达式的匹配情况"},
            {"thought": "发现'用户想要'开头的句子无法匹配，需要扩展正则"},
            {"thought": "添加(想要|需要)分组来覆盖更多表达方式"}
        ],
        final_output="已更新正则表达式为 '用户(想要|需要).*'，现在可以匹配'用户想要'开头的句子",
        success=True
    )
    
    print(f"📋 Task: {trace.task_description}")
    print(f"🔧 Tool calls: {len(trace.tool_calls)}")
    print(f"🧠 Decisions: {len(trace.decision_steps)}")
    
    # 注意: 实际评测需要 API Key
    # result = evaluate_agent(trace)
    # print(f"✅ Evaluation complete: {result}")
    
    print("\n✅ Agent evaluation module loaded successfully!")
    print("💡 Usage: evaluate_agent(trace) or evaluate_agent_from_dict(data)")
