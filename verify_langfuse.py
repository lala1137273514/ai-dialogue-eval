"""完整验证测试脚本 - 符合 verification-before-completion skill"""
import requests
import base64
import json
import sys

BASE_URL = 'http://127.0.0.1:5000'
auth = base64.b64encode(b'pk-eval-platform:sk-eval-platform-secret-key-2024').decode()

results = {
    'total': 0,
    'passed': 0,
    'failed': 0,
    'details': []
}

def test(name, condition, evidence):
    results['total'] += 1
    if condition:
        results['passed'] += 1
        status = '✅ PASS'
    else:
        results['failed'] += 1
        status = '❌ FAIL'
    results['details'].append({'name': name, 'status': status, 'evidence': evidence})
    print(f"{status}: {name}")
    print(f"   Evidence: {str(evidence)[:200]}")

print("=" * 60)
print("🧪 VERIFICATION TEST SUITE - Langfuse Integration")
print("=" * 60)

# Test 1: Health Endpoint
print("\n📡 Test 1: Health Endpoint")
try:
    r = requests.get(f'{BASE_URL}/api/public/health', timeout=5)
    test("Health endpoint returns 200", r.status_code == 200, f"Status: {r.status_code}")
    test("Health returns correct adapter", r.json().get('adapter') == 'langfuse-compatible', r.json())
except Exception as e:
    test("Health endpoint accessible", False, str(e))

# Test 2: Auth Required
print("\n🔒 Test 2: Authentication")
try:
    r = requests.post(f'{BASE_URL}/api/public/ingestion', json={'batch': []}, timeout=5)
    test("Unauthenticated request rejected", r.status_code == 401, f"Status: {r.status_code}")
except Exception as e:
    test("Auth check", False, str(e))

# Test 3: Valid Ingestion
print("\n📤 Test 3: Data Ingestion")
try:
    payload = {
        'batch': [{
            'id': 'verify-test-001',
            'timestamp': '2024-01-20T12:00:00.000Z',
            'type': 'trace-create',
            'body': {
                'id': 'verify-trace-001',
                'name': 'Verification Test',
                'input': '验证测试输入',
                'output': '验证测试输出'
            }
        }]
    }
    r = requests.post(
        f'{BASE_URL}/api/public/ingestion',
        json=payload,
        headers={'Authorization': f'Basic {auth}'},
        timeout=30
    )
    test("Ingestion returns 207", r.status_code == 207, f"Status: {r.status_code}")
    data = r.json()
    test("Ingestion has successes", len(data.get('successes', [])) > 0, data)
    test("Ingestion has no errors", len(data.get('errors', [])) == 0, data.get('errors', []))
except Exception as e:
    test("Ingestion test", False, str(e))

# Test 4: Data Retrieval
print("\n📊 Test 4: Data Retrieval")
try:
    r = requests.get(f'{BASE_URL}/api/v1/traces?limit=5', timeout=5)
    test("Traces endpoint returns 200", r.status_code == 200, f"Status: {r.status_code}")
    data = r.json()
    test("Traces count available", 'count' in data, data.keys())
    test("Traces list available", 'traces' in data and len(data['traces']) > 0, f"Count: {len(data.get('traces', []))}")
except Exception as e:
    test("Traces retrieval", False, str(e))

# Test 5: Stats Endpoint
print("\n📈 Test 5: Statistics")
try:
    r = requests.get(f'{BASE_URL}/api/v1/stats', timeout=5)
    test("Stats endpoint returns 200", r.status_code == 200, f"Status: {r.status_code}")
    data = r.json()
    test("Stats has trace_count", 'trace_count' in data, data)
except Exception as e:
    test("Stats endpoint", False, str(e))

# Summary
print("\n" + "=" * 60)
print(f"📋 VERIFICATION SUMMARY")
print("=" * 60)
print(f"Total Tests: {results['total']}")
print(f"Passed: {results['passed']} ✅")
print(f"Failed: {results['failed']} ❌")
print(f"Pass Rate: {results['passed']/results['total']*100:.1f}%")
print("=" * 60)

if results['failed'] > 0:
    print("\n⚠️ FAILED TESTS:")
    for d in results['details']:
        if 'FAIL' in d['status']:
            print(f"  - {d['name']}: {d['evidence']}")
    sys.exit(1)
else:
    print("\n✅ ALL TESTS PASSED - VERIFICATION COMPLETE")
    sys.exit(0)
