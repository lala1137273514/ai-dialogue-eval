"""
Langfuse API 适配层 - 让评测平台接收 Dify 发送的数据

功能:
- 实现 Langfuse 兼容的 /api/public/ingestion 端点
- 支持 HTTP Basic Authentication
- 自动将 Dify 数据转换为评测格式并触发评测
- 存储到现有的 TraceStore

使用方式:
    在 Dify 中配置:
    - 密钥: sk-your-secret-key
    - 公钥: pk-your-public-key  
    - Host: http://your-server:5000

端点:
    POST /api/public/ingestion - Langfuse 兼容的数据摄入接口
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import base64
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

from trace_store import TraceStore

# ==========================================
# 配置
# ==========================================

# API 密钥配置 - 生产环境应从环境变量或配置文件读取
API_KEYS = {
    "pk-eval-platform": "sk-eval-platform-secret-key-2024"
}

# ==========================================
# Flask Blueprint
# ==========================================

langfuse_bp = Blueprint('langfuse', __name__, url_prefix='/api/public')


# ==========================================
# 认证装饰器
# ==========================================

def basic_auth_required(f):
    """HTTP Basic Auth 认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Basic '):
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing or invalid Authorization header"
            }), 401
        
        try:
            # 解码 Base64 凭证
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            public_key, secret_key = credentials.split(':', 1)
            
            # 验证密钥
            expected_secret = API_KEYS.get(public_key)
            if not expected_secret or expected_secret != secret_key:
                return jsonify({
                    "error": "Unauthorized", 
                    "message": "Invalid API credentials"
                }), 401
                
        except Exception as e:
            return jsonify({
                "error": "Unauthorized",
                "message": f"Invalid authorization header: {str(e)}"
            }), 401
        
        return f(*args, **kwargs)
    return decorated


# ==========================================
# Langfuse 兼容 API 端点
# ==========================================

@langfuse_bp.route('/ingestion', methods=['POST'])
@basic_auth_required
def ingestion():
    """
    Langfuse 兼容的 Ingestion API
    
    Dify 会发送以下类型的事件:
    - trace-create: 创建追踪记录
    - generation-create: LLM 调用记录
    - generation-update: 更新 LLM 调用
    - span-create: 时间跨度
    - score-create: 评分
    
    Request:
        {
            "batch": [
                {
                    "id": "event-uuid",
                    "timestamp": "2024-01-20T10:00:00.000Z",
                    "type": "trace-create",
                    "body": { ... }
                }
            ],
            "metadata": { ... }
        }
    
    Response (HTTP 207):
        {
            "successes": [{"id": "event-uuid", "status": 201}],
            "errors": []
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "No JSON data provided"
        }), 400
    
    batch = data.get('batch', [])
    successes = []
    errors = []
    
    for event in batch:
        event_id = event.get('id', 'unknown')
        event_type = event.get('type', '')
        timestamp = event.get('timestamp', datetime.now().isoformat())
        body = event.get('body', {})
        
        try:
            if event_type == 'trace-create':
                handle_trace_create(body, timestamp)
            elif event_type == 'generation-create':
                handle_generation_create(body, timestamp)
            elif event_type == 'generation-update':
                handle_generation_update(body)
            elif event_type == 'span-create':
                handle_span_create(body, timestamp)
            elif event_type == 'span-update':
                handle_span_update(body)
            elif event_type == 'score-create':
                handle_score_create(body)
            elif event_type == 'event-create':
                handle_event_create(body, timestamp)
            else:
                # 未知事件类型，记录但不报错
                print(f"[Langfuse Adapter] Unknown event type: {event_type}")
            
            successes.append({"id": event_id, "status": 201})
            
        except Exception as e:
            print(f"[Langfuse Adapter] Error processing event {event_id}: {e}")
            errors.append({
                "id": event_id,
                "status": 400,
                "message": str(e)
            })
    
    return jsonify({
        "successes": successes,
        "errors": errors
    }), 207


# ==========================================
# 事件处理器
# ==========================================

def handle_trace_create(body: Dict, timestamp: str):
    """
    处理 trace-create 事件
    
    Dify 发送的 trace 包含完整的对话信息
    """
    trace_id = body.get('id', f"dify_{int(time.time())}")
    session_id = body.get('sessionId', body.get('id', 'dify_session'))
    user_id = body.get('userId', 'dify_user')
    name = body.get('name', 'Dify App')
    
    input_data = body.get('input', '')
    output_data = body.get('output', '')
    metadata = body.get('metadata', {})
    tags = body.get('tags', [])
    
    # 创建 Trace
    created_trace_id = TraceStore.create_trace(
        session_id=session_id,
        name=name,
        eval_type='single_turn',  # Dify 单次对话
        input_data={
            'input': input_data,
            'user_id': user_id,
            'dify_trace_id': trace_id
        },
        output_data={
            'output': output_data
        },
        metadata={
            'source': 'dify',
            'userId': user_id,
            'tags': tags,
            'dify_trace_id': trace_id,
            'timestamp': timestamp,
            **metadata
        }
    )
    
    print(f"[Langfuse Adapter] ✅ Trace created: {created_trace_id} (Dify: {trace_id})")
    
    # 如果有 input 和 output，自动触发评测
    if input_data and output_data:
        trigger_auto_evaluation(created_trace_id, input_data, output_data)


def handle_generation_create(body: Dict, timestamp: str):
    """
    处理 generation-create 事件 (LLM 调用)
    
    包含模型信息、输入输出、Token 使用等
    """
    gen_id = body.get('id', f"gen_{int(time.time())}")
    trace_id = body.get('traceId', '')
    name = body.get('name', 'LLM Call')
    model = body.get('model', 'unknown')
    
    input_data = body.get('input', '')
    output_data = body.get('output', '')
    
    usage = body.get('usage', {})
    model_params = body.get('modelParameters', {})
    
    start_time = body.get('startTime', timestamp)
    end_time = body.get('endTime', '')
    
    # 计算延迟
    latency_ms = None
    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            latency_ms = int((end - start).total_seconds() * 1000)
        except:
            pass
    
    # 创建 Generation Trace
    created_trace_id = TraceStore.create_trace(
        session_id=trace_id or gen_id,
        name=name,
        eval_type='generation',
        input_data=input_data if isinstance(input_data, dict) else {'input': input_data},
        output_data={'output': output_data},
        model=model,
        latency_ms=latency_ms,
        metadata={
            'source': 'dify',
            'generation_id': gen_id,
            'parent_trace_id': trace_id,
            'usage': usage,
            'model_parameters': model_params,
            'metrics': {
                'prompt_tokens': usage.get('promptTokens', usage.get('input', 0)),
                'completion_tokens': usage.get('completionTokens', usage.get('output', 0)),
                'total_tokens': usage.get('totalTokens', usage.get('total', 0))
            }
        }
    )
    
    print(f"[Langfuse Adapter] 🤖 Generation: {created_trace_id} | Model: {model} | Tokens: {usage}")
    
    # 如果有输入输出，自动评测
    if input_data and output_data:
        input_text = input_data if isinstance(input_data, str) else json.dumps(input_data, ensure_ascii=False)
        output_text = output_data if isinstance(output_data, str) else str(output_data)
        trigger_auto_evaluation(created_trace_id, input_text, output_text)


def handle_generation_update(body: Dict):
    """处理 generation-update 事件"""
    gen_id = body.get('id', '')
    output_data = body.get('output', '')
    usage = body.get('usage', {})
    
    print(f"[Langfuse Adapter] 🔄 Generation update: {gen_id}")
    
    # 可以在这里更新已存在的 trace
    # 目前先跳过，因为大多数情况下 generation-create 已包含完整信息


def handle_span_create(body: Dict, timestamp: str):
    """处理 span-create 事件"""
    span_id = body.get('id', f"span_{int(time.time())}")
    trace_id = body.get('traceId', '')
    name = body.get('name', 'Span')
    
    print(f"[Langfuse Adapter] ⏱️ Span: {name} (ID: {span_id})")
    
    # Span 主要用于追踪时间，可以选择性记录


def handle_span_update(body: Dict):
    """处理 span-update 事件"""
    span_id = body.get('id', '')
    print(f"[Langfuse Adapter] ⏱️ Span update: {span_id}")


def handle_score_create(body: Dict):
    """
    处理 score-create 事件
    
    用于记录外部评分
    """
    score_id = body.get('id', f"score_{int(time.time())}")
    trace_id = body.get('traceId', '')
    name = body.get('name', 'score')
    value = body.get('value', 0)
    comment = body.get('comment', '')
    
    if trace_id:
        TraceStore.add_score(
            trace_id=trace_id,
            name=name,
            value=float(value) if isinstance(value, (int, float)) else 0,
            reasoning=comment
        )
        print(f"[Langfuse Adapter] ⭐ Score: {name} = {value} (Trace: {trace_id})")


def handle_event_create(body: Dict, timestamp: str):
    """处理 event-create 事件"""
    event_id = body.get('id', f"event_{int(time.time())}")
    name = body.get('name', 'Event')
    print(f"[Langfuse Adapter] 📌 Event: {name} (ID: {event_id})")


# ==========================================
# 自动评测
# ==========================================

def trigger_auto_evaluation(trace_id: str, input_text: str, output_text: str):
    """
    自动触发评测
    
    将 Dify 发送的对话数据转换为评测格式，调用评测引擎
    """
    try:
        # 延迟导入，避免循环依赖
        from eval_dispatcher import run_evaluation_task
        
        # 构造评测数据
        eval_data = {
            'session_id': trace_id,
            'eval_type': 'single_turn',
            'messages': [
                {'role': 'user', 'content': str(input_text)},
                {'role': 'assistant', 'content': str(output_text)}
            ]
        }
        
        # 执行评测
        results, summary = run_evaluation_task([eval_data])
        
        # 保存评分结果
        if results and len(results) > 0:
            result = results[0]
            scores = result.get('scores', {})
            avg_score = result.get('avg_score', 0)
            
            for dim, score_val in scores.items():
                score = score_val if isinstance(score_val, (int, float)) else score_val.get('value', 0)
                TraceStore.add_score(
                    trace_id=trace_id,
                    name=dim,
                    value=float(score),
                    reasoning=''
                )
            
            # 更新 Trace 输出
            TraceStore.update_trace(
                trace_id=trace_id,
                output_data={
                    'output': output_text,
                    'eval_scores': scores,
                    'avg_score': avg_score,
                    'eval_status': 'completed'
                }
            )
            
            print(f"[Langfuse Adapter] 📊 Auto eval completed: {trace_id} | Avg: {avg_score:.2f}")
        
    except ImportError as e:
        print(f"[Langfuse Adapter] ⚠️ eval_dispatcher not available: {e}")
    except Exception as e:
        print(f"[Langfuse Adapter] ❌ Auto eval failed: {e}")


# ==========================================
# 辅助函数
# ==========================================

def add_api_key(public_key: str, secret_key: str):
    """动态添加 API 密钥"""
    API_KEYS[public_key] = secret_key


def remove_api_key(public_key: str):
    """移除 API 密钥"""
    if public_key in API_KEYS:
        del API_KEYS[public_key]


def list_api_keys() -> List[str]:
    """列出所有公钥"""
    return list(API_KEYS.keys())


# ==========================================
# 健康检查端点
# ==========================================

@langfuse_bp.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        'status': 'ok',
        'adapter': 'langfuse-compatible',
        'version': '1.0.0',
        'endpoints': [
            'POST /api/public/ingestion',
            'GET /api/public/health'
        ]
    })


# ==========================================
# 测试入口
# ==========================================

if __name__ == '__main__':
    print("🧪 Testing Langfuse Adapter...")
    
    # 模拟测试请求
    test_trace_body = {
        'id': 'test-trace-001',
        'name': 'Test Dify App',
        'userId': 'test-user',
        'sessionId': 'test-session',
        'input': '你好，请介绍一下你自己',
        'output': '你好！我是一个AI助手，很高兴为你服务。',
        'tags': ['test', 'dify']
    }
    
    handle_trace_create(test_trace_body, datetime.now().isoformat())
    print("✅ Test completed!")
