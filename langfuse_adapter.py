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
    """HTTP Basic Auth 认证装饰器，支持 App 独立凭证"""
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
            
            # 首先检查静态密钥（向后兼容）
            expected_secret = API_KEYS.get(public_key)
            if expected_secret and expected_secret == secret_key:
                # 静态密钥验证通过，设置默认 App
                request.dify_app = None
                return f(*args, **kwargs)
            
            # 然后检查 DifyStore 中的 App 凭证
            from dify_store import DifyStore
            app = DifyStore.get_app_by_credentials(public_key, secret_key)
            if app:
                request.dify_app = app  # 将 App 信息附加到请求
                return f(*args, **kwargs)
            
            return jsonify({
                "error": "Unauthorized", 
                "message": "Invalid API credentials"
            }), 401
                
        except Exception as e:
            return jsonify({
                "error": "Unauthorized",
                "message": f"Invalid authorization header: {str(e)}"
            }), 401
        
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
            # 获取请求中的 App 信息（由认证装饰器设置）
            dify_app = getattr(request, 'dify_app', None)
            
            if event_type == 'trace-create':
                handle_trace_create(body, timestamp, dify_app)
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

def handle_trace_create(body: Dict, timestamp: str, dify_app: Dict = None):
    """
    处理 trace-create 事件
    
    Dify 发送的 trace 包含完整的对话信息
    如果匹配到 App，则存入对应的评测集
    """
    trace_id = body.get('id', f"dify_{int(time.time())}")
    session_id = body.get('sessionId', body.get('id', 'dify_session'))
    user_id = body.get('userId', 'dify_user')
    name = body.get('name', 'Dify App')
    
    input_data = body.get('input', '')
    output_data = body.get('output', '')
    metadata = body.get('metadata', {})
    tags = body.get('tags', [])
    
    # 创建 Trace（保留原有逻辑）
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
    
    # 🆕 将数据存入评测集（支持静态凭证和App凭证）
    if input_data and output_data:
        try:
            from dify_store import DifyStore
            import json
            
            dataset_id = None
            dataset_name = None
            
            if dify_app:
                # App 独立凭证：使用 App 关联的评测集
                datasets = DifyStore.list_datasets(app_id=dify_app['id'])
                if datasets:
                    dataset_id = datasets[0]['id']
                    dataset_name = datasets[0]['name']
                else:
                    dataset_id = DifyStore.create_dataset(
                        name=f"{dify_app['name']}-评测集",
                        app_id=dify_app['id'],
                        source_type='dify'
                    )
                    dataset_name = f"{dify_app['name']}-评测集"
            else:
                # 静态凭证：使用默认评测集
                datasets = DifyStore.list_datasets()
                # 查找或创建默认评测集
                default_ds = next((d for d in datasets if d['name'] == 'Dify-默认评测集'), None)
                if default_ds:
                    dataset_id = default_ds['id']
                    dataset_name = default_ds['name']
                else:
                    dataset_id = DifyStore.create_dataset(
                        name='Dify-默认评测集',
                        source_type='dify',
                        description='静态凭证数据的默认存储评测集'
                    )
                    dataset_name = 'Dify-默认评测集'
            
            # 存入记录
            record_id = DifyStore.add_record(
                dataset_id=dataset_id,
                inputs=json.dumps({'input': input_data}, ensure_ascii=False) if isinstance(input_data, str) else json.dumps(input_data, ensure_ascii=False),
                query=input_data if isinstance(input_data, str) else str(input_data),
                output=output_data if isinstance(output_data, str) else str(output_data),
                source='dify_realtime',
                dify_trace_id=trace_id,
                dify_conversation_id=session_id
            )
            
            print(f"[Langfuse Adapter] 💾 Record saved to dataset '{dataset_name}': {record_id}")
            
        except Exception as e:
            print(f"[Langfuse Adapter] ⚠️ Failed to save to dataset: {e}")
            # 回退到旧逻辑
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
    
    # 🆕 保存原始事件 (可观测性数据)
    save_raw_event(
        event_id=gen_id,
        event_type='generation-create',
        trace_id=created_trace_id,
        parent_id=trace_id,
        name=name,
        raw_body=body,
        model=model,
        input_tokens=usage.get('promptTokens', usage.get('input', 0)),
        output_tokens=usage.get('completionTokens', usage.get('output', 0)),
        total_tokens=usage.get('totalTokens', usage.get('total', 0)),
        latency_ms=latency_ms,
        start_time=start_time,
        end_time=end_time
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
# 🆕 原始事件存储与查询 (融合可观测数据)
# ==========================================

def save_raw_event(
    event_id: str,
    event_type: str,
    trace_id: str = None,
    parent_id: str = None,
    name: str = None,
    raw_body: dict = None,
    model: str = None,
    input_tokens: int = None,
    output_tokens: int = None,
    total_tokens: int = None,
    latency_ms: int = None,
    start_time: str = None,
    end_time: str = None
) -> bool:
    """
    保存原始 Langfuse 事件
    
    用于保留完整的可观测性数据，不丢失任何原始信息。
    """
    from trace_store import get_db
    
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO langfuse_events 
                (event_id, event_type, trace_id, parent_id, name, raw_body, 
                 model, input_tokens, output_tokens, total_tokens, latency_ms, 
                 start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event_type,
                trace_id,
                parent_id,
                name,
                json.dumps(raw_body or {}, ensure_ascii=False),
                model,
                input_tokens,
                output_tokens,
                total_tokens,
                latency_ms,
                start_time,
                end_time
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Langfuse Adapter] Error saving raw event: {e}")
        return False


def get_langfuse_events(
    trace_id: str = None,
    event_type: str = None,
    limit: int = 50
) -> List[Dict]:
    """
    获取 Langfuse 事件列表
    
    Args:
        trace_id: 按 Trace ID 筛选
        event_type: 按事件类型筛选
        limit: 返回条数
    
    Returns:
        事件列表
    """
    from trace_store import get_db
    
    with get_db() as conn:
        query = "SELECT * FROM langfuse_events WHERE 1=1"
        params = []
        
        if trace_id:
            query += " AND trace_id = ?"
            params.append(trace_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        events = []
        for r in rows:
            event = dict(r)
            try:
                event['raw_body'] = json.loads(event['raw_body'] or '{}')
            except:
                event['raw_body'] = {}
            events.append(event)
        
        return events


def get_trace_with_events(trace_id: str) -> Optional[Dict]:
    """
    获取 Trace 详情，包含关联的 Langfuse 事件
    
    融合评测数据与可观测性数据的核心函数。
    """
    # 获取 Trace 基础信息
    trace = TraceStore.get_trace(trace_id)
    if not trace:
        return None
    
    # 获取关联的 Langfuse 事件
    events = get_langfuse_events(trace_id=trace_id)
    trace['events'] = events
    
    # 计算汇总指标
    total_tokens = sum(e.get('total_tokens') or 0 for e in events)
    total_latency = sum(e.get('latency_ms') or 0 for e in events)
    models_used = list(set(e.get('model') for e in events if e.get('model')))
    
    trace['observability'] = {
        'total_tokens': total_tokens,
        'total_latency_ms': total_latency,
        'models_used': models_used,
        'event_count': len(events)
    }
    
    return trace


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

