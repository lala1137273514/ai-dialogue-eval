"""
统一评测入口 v0.5.0

功能:
- 自动识别评测类型 (single_turn / multi_turn / agent)
- 路由到对应的评测函数
- 统一返回格式
"""

import json
from typing import List, Dict, Optional
from trace_store import TraceStore


def detect_evaluation_type(data: dict) -> str:
    """
    自动识别评测类型
    
    Args:
        data: 输入数据
    
    Returns:
        评测类型: single_turn / multi_turn / agent
    """
    # 1. 显式指定
    if "eval_type" in data:
        return data["eval_type"]
    
    # 2. Agent 特征检测
    if "tool_calls" in data or "decisions" in data:
        return "agent"
    
    # 3. 对话轮数检测
    messages = data.get("messages", [])
    if len(messages) > 2:
        return "multi_turn"
    
    # 4. 默认单轮
    return "single_turn"


def get_rubrics_for_type(eval_type: str, config: dict) -> List[Dict]:
    """
    获取对应类型的评测维度
    
    Args:
        eval_type: 评测类型
        config: rubric 配置
    """
    rubrics = config.get('rubrics', {})
    
    # 获取共享维度
    shared = rubrics.get('shared', [])
    
    # 获取类型特定维度
    type_specific = rubrics.get(eval_type, [])
    
    return shared + type_specific


def run_unified_evaluation(
    data: List[Dict],
    config: dict = None,
    progress_callback=None
) -> List[Dict]:
    """
    统一评测入口
    
    Args:
        data: 评测数据列表
        config: rubric 配置
        progress_callback: 进度回调函数
    
    Returns:
        评测结果列表
    """
    from run_eval import run_log_evaluation
    from agent_eval import evaluate_agent_from_dict, AGENT_RUBRICS
    
    results = []
    total = len(data)
    
    for i, item in enumerate(data):
        eval_type = detect_evaluation_type(item)
        
        if progress_callback:
            progress_callback(i, total, f"正在评测 [{eval_type}] {i+1}/{total}")
        
        if eval_type == "agent":
            # Agent 评测
            result = evaluate_agent_from_dict(item)
            result['eval_type'] = 'agent'
        else:
            # 单轮/多轮评测 - 复用现有逻辑
            rubrics = get_rubrics_for_type(eval_type, config) if config else []
            
            # 包装成 session 格式
            if eval_type == "single_turn":
                session = {
                    'session_id': item.get('id', f'single_{i}'),
                    'messages': [
                        {'role': 'user', 'content': item.get('input', '')},
                        {'role': 'assistant', 'content': item.get('output', '')}
                    ]
                }
            else:
                session = item
            
            eval_results = run_log_evaluation([session], rubrics)
            result = eval_results[0] if eval_results else {}
            result['eval_type'] = eval_type
        
        results.append(result)
    
    return results


def batch_evaluate(file_path: str, config_path: str = None) -> List[Dict]:
    """
    批量评测 (从文件读取)
    
    Args:
        file_path: 数据文件路径 (JSON)
        config_path: 配置文件路径 (rubric.json)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    config = {}
    if config_path:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    return run_unified_evaluation(data, config)


if __name__ == "__main__":
    print("🧪 Testing Unified Evaluation...")
    
    # 测试类型识别
    test_cases = [
        {"input": "Hello", "output": "Hi there!"},  # single_turn
        {"session_id": "s1", "messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}, {"role": "assistant"}]},  # multi_turn
        {"task": "Fix bug", "tool_calls": [{"name": "search"}]},  # agent
        {"eval_type": "agent", "task": "Test"},  # explicit agent
    ]
    
    for tc in test_cases:
        detected = detect_evaluation_type(tc)
        print(f"✅ Detected: {detected}")
    
    print("\n🎉 Unified evaluation module loaded successfully!")
