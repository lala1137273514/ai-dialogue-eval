"""
HTTP API 服务 v0.5.0

功能:
- 提供 RESTful API 接口
- 支持 Agent 评测、Trace 查询、统计分析
- 跨系统集成入口

启动方式:
    python api_server.py
    
API 端点:
    POST /api/v1/eval/agent - Agent 评测
    GET  /api/v1/traces     - 列出 Trace
    GET  /api/v1/stats      - 维度统计
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from agent_eval import evaluate_agent_from_dict, AgentTrace
from trace_store import TraceStore
from unified_eval import run_unified_evaluation, detect_evaluation_type

# 🆕 导入 Langfuse 适配器
from langfuse_adapter import langfuse_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 允许跨域

@app.before_request
def log_request_info():
    print(f"📡 [Request] {request.method} {request.url}")
    # print(f"   Headers: {dict(request.headers)}")

# 🆕 注册 Langfuse 兼容 API (支持 Dify 集成)
app.register_blueprint(langfuse_bp)

# 添加一个根路径重定向或提示，防止直接访问根目录 404
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "AI Dialogue Eval API",
        "status": "running",
        "version": "0.5.0",
        "endpoints": [
            "/api/public/health",
            "/api/public/ingestion",
            "/api/v1/traces"
        ]
    })

# 补充 Dify 可能探测的路径
@app.route('/api/public/auth', methods=['GET', 'POST'])
def auth_check():
    return jsonify({"status": "ok"}), 200

# Dify 验证连接时会调用的接口
@app.route('/api/public/projects', methods=['GET'])
def list_projects():
    return jsonify({
        "data": [
            {
                "id": "default_project",
                "name": "KST Eval Platform",
                "publicKey": "pk-eval-platform",
                "plan": "hobby",
                "status": "active"
            }
        ]
    }), 200




@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'version': '0.5.0',
        'trace_count': TraceStore.get_trace_count()
    })


@app.route('/api/v1/eval/agent', methods=['POST'])
def eval_agent():
    """
    Agent 评测 API
    
    Request:
        {
            "task_id": "agent_001",
            "task": "修复正则匹配",
            "tool_calls": [...],
            "decisions": [...],
            "output": "完成",
            "success": true
        }
    
    Response:
        {
            "trace_id": "abc123",
            "scores": {...},
            "avg_score": 4.5,
            "details": [...]
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        result = evaluate_agent_from_dict(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/eval/unified', methods=['POST'])
def eval_unified():
    """
    统一评测 API (自动类型识别)
    
    Request:
        [
            {"input": "...", "output": "..."},
            {"task": "...", "tool_calls": [...]},
            ...
        ]
    
    Response:
        {"results": [...], "count": 2}
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if not isinstance(data, list):
            data = [data]
        
        results = run_unified_evaluation(data)
        return jsonify({
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/traces', methods=['GET'])
def list_traces():
    """
    列出 Trace 记录
    
    Query params:
        session_id: 按会话筛选
        eval_type: 按类型筛选 (single_turn/multi_turn/agent)
        limit: 返回条数 (默认50)
    """
    try:
        session_id = request.args.get('session_id')
        eval_type = request.args.get('eval_type')
        limit = int(request.args.get('limit', 50))
        
        traces = TraceStore.list_traces(
            session_id=session_id,
            eval_type=eval_type,
            limit=limit
        )
        
        return jsonify({
            'traces': traces,
            'count': len(traces),
            'total': TraceStore.get_trace_count()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/traces/<trace_id>', methods=['GET'])
def get_trace(trace_id):
    """获取单个 Trace 详情"""
    try:
        trace = TraceStore.get_trace(trace_id)
        if not trace:
            return jsonify({'error': 'Trace not found'}), 404
        return jsonify(trace)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """
    获取统计数据
    
    Response:
        {
            "dimensions": {"clarity": {"avg": 4.2, "count": 100}, ...},
            "trace_count": 150,
            "low_score_count": 5
        }
    """
    try:
        stats = TraceStore.get_dimension_stats()
        low_scores = TraceStore.get_low_score_traces(threshold=3, limit=5)
        
        return jsonify({
            'dimensions': stats,
            'trace_count': TraceStore.get_trace_count(),
            'low_score_count': len(low_scores),
            'low_scores': low_scores
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/detect-type', methods=['POST'])
def detect_type():
    """
    检测评测类型
    
    Request: {"input": "...", "output": "..."}
    Response: {"eval_type": "single_turn"}
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        eval_type = detect_evaluation_type(data)
        return jsonify({'eval_type': eval_type})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Starting KST Agent Evaluation API Server...")
    print("📍 Endpoints:")
    print("   POST /api/v1/eval/agent   - Agent 评测")
    print("   POST /api/v1/eval/unified - 统一评测")
    print("   GET  /api/v1/traces       - 列出 Trace")
    print("   GET  /api/v1/stats        - 统计数据")
    print("")
    print("🔌 Langfuse 兼容 (Dify 集成):")
    print("   POST /api/public/ingestion - Langfuse 格式数据摄入")
    print("   GET  /api/public/health    - 健康检查")
    print("")
    print("📋 Dify 配置信息:")
    print("   公钥: pk-eval-platform")
    print("   密钥: sk-eval-platform-secret-key-2024")
    print(f"   Host: http://localhost:{port}")
    print("")
    app.run(host='0.0.0.0', port=port, debug=(port == 5000))

