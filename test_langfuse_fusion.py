"""
融合 Langfuse 可观测数据与评测数据 - 测试文件

TDD 流程：先写测试，看到失败，再实现功能。
"""

import sys
import os
import json
import time

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 测试用例
# ==========================================

def test_langfuse_events_table_exists():
    """测试: langfuse_events 表应该存在"""
    from trace_store import get_db
    
    with get_db() as conn:
        result = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='langfuse_events'
        """).fetchone()
        
    assert result is not None, "langfuse_events 表不存在"
    print("✅ test_langfuse_events_table_exists PASSED")


def test_save_raw_event():
    """测试: 能够保存原始 Langfuse 事件"""
    from langfuse_adapter import save_raw_event
    
    event_data = {
        "event_id": f"test_event_{int(time.time())}",
        "event_type": "generation-create",
        "trace_id": None,
        "parent_id": None,
        "name": "Test Generation",
        "raw_body": {"test": "data"},
        "model": "gpt-4o-mini",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "latency_ms": 500,
        "start_time": "2026-01-20T08:00:00Z",
        "end_time": "2026-01-20T08:00:01Z"
    }
    
    result = save_raw_event(**event_data)
    assert result is True, "保存原始事件失败"
    print("✅ test_save_raw_event PASSED")


def test_get_langfuse_events():
    """测试: 能够获取 Langfuse 事件列表"""
    from langfuse_adapter import get_langfuse_events
    
    events = get_langfuse_events(limit=10)
    assert isinstance(events, list), "返回值应该是列表"
    print(f"✅ test_get_langfuse_events PASSED (获取到 {len(events)} 条)")


def test_get_trace_with_events():
    """测试: 获取 Trace 时包含关联的 Langfuse 事件"""
    from langfuse_adapter import get_trace_with_events
    from trace_store import TraceStore
    
    # 先创建一个 trace
    trace_id = TraceStore.create_trace(
        session_id="test_session_events",
        name="Test Trace with Events",
        eval_type="single_turn",
        input_data={"input": "test"},
        output_data={"output": "test"}
    )
    
    result = get_trace_with_events(trace_id)
    assert result is not None, "获取 Trace 失败"
    assert "events" in result, "返回结果应包含 events 字段"
    print("✅ test_get_trace_with_events PASSED")


def test_api_langfuse_events_endpoint():
    """测试: API 端点 /api/v1/langfuse/events 可用"""
    import requests
    
    # 测试本地 API
    try:
        resp = requests.get("http://localhost:5000/api/v1/langfuse/events", timeout=5)
        assert resp.status_code == 200, f"API 返回状态码 {resp.status_code}"
        data = resp.json()
        assert "events" in data, "返回数据应包含 events 字段"
        print("✅ test_api_langfuse_events_endpoint PASSED")
    except requests.exceptions.ConnectionError:
        print("⚠️ test_api_langfuse_events_endpoint SKIPPED (API Server 未运行)")


# ==========================================
# 运行测试
# ==========================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🧪 Langfuse 数据融合 - TDD 测试")
    print("=" * 50 + "\n")
    
    tests = [
        test_langfuse_events_table_exists,
        test_save_raw_event,
        test_get_langfuse_events,
        test_get_trace_with_events,
        test_api_langfuse_events_endpoint,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            if "SKIPPED" in str(e):
                skipped += 1
            else:
                print(f"❌ {test.__name__} ERROR: {e}")
                failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 结果: {passed} 通过, {failed} 失败, {skipped} 跳过")
    print("=" * 50 + "\n")
    
    if failed > 0:
        print("🔴 存在失败测试，这符合 TDD 的 RED 阶段预期。")
        print("   接下来需要实现功能让测试通过。")
    else:
        print("🟢 所有测试通过！")
