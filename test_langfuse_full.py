"""完整测试脚本：验证 Langfuse 适配器数据流"""
import requests
import base64
import json

# 认证
auth = base64.b64encode(b'pk-eval-platform:sk-eval-platform-secret-key-2024').decode()
BASE_URL = 'http://127.0.0.1:5000'

print("=" * 50)
print("🧪 Langfuse 适配器完整测试")
print("=" * 50)

# 1. 健康检查
print("\n📡 1. 健康检查")
try:
    resp = requests.get(f'{BASE_URL}/api/public/health', timeout=5)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
except Exception as e:
    print(f"   ❌ 失败: {e}")
    exit(1)

# 2. 发送完整的 Langfuse 格式请求
print("\n📤 2. 发送 Langfuse 格式数据")
payload = {
    'batch': [
        {
            'id': 'event-full-test-001',
            'timestamp': '2024-01-20T10:00:00.000Z',
            'type': 'trace-create',
            'body': {
                'id': 'trace-full-test',
                'name': 'Dify 智能客服',
                'userId': 'customer-456',
                'sessionId': 'session-full-test',
                'input': '你们公司的产品有什么优势？',
                'output': '我们的产品主要有三大优势：1) 智能对话能力 2) 多渠道整合 3) 数据分析功能',
                'tags': ['dify', 'full-test', 'customer-service'],
                'metadata': {'app_id': 'dify-cs-app', 'version': '1.0'}
            }
        },
        {
            'id': 'event-full-test-002',
            'timestamp': '2024-01-20T10:00:01.000Z',
            'type': 'generation-create',
            'body': {
                'id': 'gen-full-test',
                'traceId': 'trace-full-test',
                'name': 'GPT-4 Response',
                'model': 'gpt-4-turbo',
                'input': [{'role': 'user', 'content': '你们公司的产品有什么优势？'}],
                'output': '我们的产品主要有三大优势：1) 智能对话能力 2) 多渠道整合 3) 数据分析功能',
                'usage': {'promptTokens': 20, 'completionTokens': 50, 'totalTokens': 70},
                'modelParameters': {'temperature': 0.7, 'max_tokens': 1000},
                'startTime': '2024-01-20T10:00:00.100Z',
                'endTime': '2024-01-20T10:00:01.500Z'
            }
        }
    ],
    'metadata': {'sdk_name': 'langfuse-python', 'sdk_version': '2.0.0'}
}

resp = requests.post(
    f'{BASE_URL}/api/public/ingestion',
    json=payload,
    headers={'Authorization': f'Basic {auth}'},
    timeout=30
)
print(f"   Status: {resp.status_code}")
result = resp.json()
print(f"   Successes: {len(result.get('successes', []))}")
print(f"   Errors: {len(result.get('errors', []))}")

if result.get('errors'):
    print(f"   ⚠️ Errors: {result['errors']}")

# 3. 验证数据存储
print("\n📊 3. 验证数据存储")
traces_resp = requests.get(f'{BASE_URL}/api/v1/traces?limit=10')
traces_data = traces_resp.json()
print(f"   Total traces: {traces_data.get('total', 0)}")
print(f"   Recent traces:")
for t in traces_data.get('traces', [])[:5]:
    name = t.get('name', '?')[:30]
    session = t.get('session_id', '?')[:20]
    meta = t.get('metadata', {})
    source = meta.get('source', 'unknown') if isinstance(meta, dict) else 'unknown'
    print(f"   - {name} | Session: {session} | Source: {source}")

# 4. 统计数据
print("\n📈 4. 统计数据")
stats_resp = requests.get(f'{BASE_URL}/api/v1/stats')
stats = stats_resp.json()
print(f"   Trace count: {stats.get('trace_count', 0)}")
print(f"   Low score count: {stats.get('low_score_count', 0)}")

print("\n" + "=" * 50)
print("✅ 完整测试完成！")
print("=" * 50)
