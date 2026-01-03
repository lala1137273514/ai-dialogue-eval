"""
评测调度器 (Evaluation Dispatcher) v0.9.0

功能:
- 统一评测入口，根据数据类型 (eval_type) 路由到不同的评测引擎
- 数据格式标准化 (normalize_data)
- 输入验证 (validate_input)
- 完整错误处理和反馈
- 返回结构化结果 (EvalResultDTO, EvalSummaryDTO)
"""

import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Callable, Optional, Tuple
from enum import Enum

from run_eval import run_log_evaluation
from agent_eval import evaluate_agent_from_dict
from trace_store import TraceStore


# ==========================================
# 数据类型定义
# ==========================================

class EvalStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class EvalResultDTO:
    """评测结果传输对象"""
    session_id: str
    eval_type: str
    status: str
    scores: dict
    avg_score: float
    error_message: str = ""
    duration_ms: int = 0
    llm_called: bool = True
    trace_id: str = ""


@dataclass
class EvalSummaryDTO:
    """评测汇总"""
    total: int
    success: int
    error: int
    skipped: int
    avg_score: float
    duration_ms: int


# ==========================================
# 数据验证与标准化
# ==========================================

def validate_input(item: dict) -> Tuple[bool, str]:
    """
    验证输入数据
    
    Returns:
        (是否有效, 错误信息)
    """
    if not isinstance(item, dict):
        return False, "输入必须是字典"
    
    # 检查是否有可评测内容
    has_messages = 'messages' in item and item['messages']
    has_user_turns = 'user_turns' in item and item['user_turns']
    has_agent_data = 'task' in item or 'tool_calls' in item or 'task_description' in item
    
    if not (has_messages or has_user_turns or has_agent_data):
        return False, "缺少可评测内容 (messages/user_turns/task)"
    
    return True, ""


def normalize_data(item: dict) -> dict:
    """
    将不同格式的输入标准化
    
    支持格式:
    1. messages 格式 (标准) - 直接使用
    2. user_turns 格式 (test_cases.json) - 转换为 messages
    3. Agent 格式 - 提取关键字段
    """
    # 1. 已是标准 messages 格式
    if 'messages' in item and item['messages']:
        if isinstance(item['messages'], list) and len(item['messages']) > 0:
            if isinstance(item['messages'][0], dict) and 'role' in item['messages'][0]:
                return {
                    'session_id': item.get('session_id', item.get('id', 'unknown')),
                    'eval_type': item.get('eval_type', 'multi_turn'),
                    'domain': item.get('domain', 'general'),
                    **item
                }
    
    # 2. user_turns 格式 → messages 格式
    if 'user_turns' in item and item['user_turns']:
        messages = []
        for turn in item['user_turns']:
            messages.append({'role': 'user', 'content': turn})
            # 添加占位 assistant 回复 - 标记为待生成
            messages.append({'role': 'assistant', 'content': '[待评测回复]'})
        
        return {
            'session_id': item.get('id', item.get('session_id', 'unknown')),
            'eval_type': 'multi_turn',
            'domain': item.get('category', 'general'),
            'messages': messages,
            '_needs_response': True,  # 标记：需要先生成回复才能评测
            'original_data': item  # 保留原始数据供调试
        }
    
    # 3. Agent 格式
    if 'task' in item or 'tool_calls' in item or 'task_description' in item:
        return {
            'session_id': item.get('session_id', item.get('task_id', item.get('id', 'unknown'))),
            'eval_type': 'agent',
            'task': item.get('task', item.get('task_description', '')),
            'task_description': item.get('task_description', item.get('task', '')),
            'tool_calls': item.get('tool_calls', []),
            'decisions': item.get('decisions', item.get('decision_steps', [])),
            'output': item.get('output', item.get('final_output', '')),
            'success': item.get('success', False),
            'latency_ms': item.get('latency_ms'),
            'ttft_ms': item.get('ttft_ms'),
            'token_usage': item.get('token_usage')
        }
    
    # 无法识别，原样返回
    return {
        'session_id': item.get('session_id', item.get('id', 'unknown')),
        'eval_type': item.get('eval_type', 'unknown'),
        **item
    }


# ==========================================
# 单项评测执行
# ==========================================

def execute_single_eval(item: dict, rubrics: List[Dict] = None) -> dict:
    """
    执行单项评测
    
    根据 eval_type 路由到不同的评测引擎
    """
    eval_type = item.get('eval_type', 'multi_turn')
    
    if eval_type == 'agent':
        # Agent 评测
        result = evaluate_agent_from_dict(item)
        return {
            'session_id': item.get('session_id', 'unknown'),
            'eval_type': 'agent',
            'status': EvalStatus.SUCCESS.value,
            'scores': result.get('scores', {}),
            'avg_score': result.get('avg_score', 0),
            'trace_id': result.get('trace_id', ''),
            'llm_called': True
        }
    else:
        # 单轮/多轮对话评测
        # 使用 run_log_evaluation 处理单个会话
        results = run_log_evaluation(
            logs=[item],
            rubrics=rubrics,
            progress_callback=None
        )
        
        if results and len(results) > 0:
            res = results[0]
            return {
                'session_id': res.get('session_id', item.get('session_id', 'unknown')),
                'eval_type': item.get('eval_type', 'multi_turn'),
                'status': EvalStatus.SUCCESS.value,
                'scores': res.get('dimension_averages', {}),
                'avg_score': res.get('avg_score', res.get('overall_score', 0)),
                'trace_id': res.get('trace_id', ''),
                'llm_called': True
            }
        else:
            return {
                'session_id': item.get('session_id', 'unknown'),
                'eval_type': item.get('eval_type', 'unknown'),
                'status': EvalStatus.ERROR.value,
                'scores': {},
                'avg_score': 0,
                'error_message': '评测返回空结果',
                'llm_called': False
            }


# ==========================================
# 统一评测入口
# ==========================================

def run_evaluation_task(
    data_list: List[Dict], 
    rubrics: List[Dict] = None,
    progress_callback: Callable = None
) -> Tuple[List[dict], dict]:
    """
    统一评测任务入口
    
    Args:
        data_list: 待评测数据列表
        rubrics: 评分标准
        progress_callback: 进度回调函数 fn(current, total, message)
    
    Returns:
        (results, summary) - 结果列表 + 汇总统计
    """
    start_total = time.time()
    
    results = []
    summary = {
        "total": len(data_list),
        "success": 0,
        "error": 0,
        "skipped": 0,
        "avg_score": 0,
        "duration_ms": 0
    }
    all_scores = []
    
    for i, item in enumerate(data_list):
        start_item = time.time()
        session_id = item.get('session_id', item.get('id', f'item_{i}'))
        
        # 1. 输入验证
        valid, error_msg = validate_input(item)
        if not valid:
            results.append(asdict(EvalResultDTO(
                session_id=session_id,
                eval_type='unknown',
                status=EvalStatus.SKIPPED.value,
                scores={},
                avg_score=0,
                error_message=error_msg,
                llm_called=False,
                duration_ms=int((time.time() - start_item) * 1000)
            )))
            summary['skipped'] += 1
            
            if progress_callback:
                progress_callback(i + 1, len(data_list), f"⚠️ 跳过 {session_id}: {error_msg}")
            continue
        
        # 2. 数据标准化
        try:
            normalized = normalize_data(item)
        except Exception as e:
            results.append(asdict(EvalResultDTO(
                session_id=session_id,
                eval_type='unknown',
                status=EvalStatus.ERROR.value,
                scores={},
                avg_score=0,
                error_message=f"数据格式化失败: {str(e)}",
                llm_called=False,
                duration_ms=int((time.time() - start_item) * 1000)
            )))
            summary['error'] += 1
            continue
        
        # 2.5 检测是否需要先生成回复 (user_turns 格式)
        if normalized.get('_needs_response'):
            results.append(asdict(EvalResultDTO(
                session_id=normalized.get('session_id', 'unknown'),
                eval_type=normalized.get('eval_type', 'multi_turn'),
                status=EvalStatus.SKIPPED.value,
                scores={},
                avg_score=0,
                error_message="此数据只有用户输入，没有AI回复。请使用包含完整对话的数据文件。",
                llm_called=False,
                duration_ms=int((time.time() - start_item) * 1000)
            )))
            summary['skipped'] += 1
            
            if progress_callback:
                progress_callback(i + 1, len(data_list), f"⚠️ 跳过 {normalized.get('session_id')}: 缺少AI回复")
            continue
        
        # 3. 执行评测
        try:
            if progress_callback:
                progress_callback(i + 1, len(data_list), f"⏳ 评测 {normalized.get('session_id', 'unknown')}...")
            
            eval_result = execute_single_eval(normalized, rubrics)
            eval_result['duration_ms'] = int((time.time() - start_item) * 1000)
            
            # 验证结果有效性
            if eval_result.get('avg_score', 0) > 0:
                eval_result['status'] = EvalStatus.SUCCESS.value
                summary['success'] += 1
                all_scores.append(eval_result['avg_score'])
            else:
                eval_result['status'] = EvalStatus.ERROR.value
                if not eval_result.get('error_message'):
                    eval_result['error_message'] = "评测返回空结果"
                summary['error'] += 1
            
            results.append(eval_result)
            
        except Exception as e:
            results.append(asdict(EvalResultDTO(
                session_id=normalized.get('session_id', 'unknown'),
                eval_type=normalized.get('eval_type', 'unknown'),
                status=EvalStatus.ERROR.value,
                scores={},
                avg_score=0,
                error_message=str(e),
                llm_called=False,
                duration_ms=int((time.time() - start_item) * 1000)
            )))
            summary['error'] += 1
    
    # 计算汇总
    summary['avg_score'] = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0
    summary['duration_ms'] = int((time.time() - start_total) * 1000)
    
    return results, summary
