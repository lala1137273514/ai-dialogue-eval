"""
Dify 评测适配器单元测试 - TDD 驱动开发

测试内容：
1. 数据格式转换
2. 单条评测执行
3. 批量评测执行
"""

import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


class TestDifyEvalAdapter:
    """评测适配器测试"""
    
    def test_to_eval_format_single_field(self):
        """单字段入参应正确转换为评估器格式"""
        from dify_eval_adapter import DifyEvalAdapter
        
        record = {
            'id': 'rec_001',
            'inputs': '{}',
            'query': '你好',
            'output': '您好！有什么可以帮您？',
            'model': 'gpt-4'
        }
        
        result = DifyEvalAdapter.to_eval_format(record)
        
        assert 'messages' in result
        assert len(result['messages']) == 2
        assert result['messages'][0]['role'] == 'user'
        assert result['messages'][0]['content'] == '你好'
        assert result['messages'][1]['role'] == 'assistant'
        assert result['messages'][1]['content'] == '您好！有什么可以帮您？'
    
    def test_to_eval_format_multi_field(self):
        """多字段入参应拼接为上下文"""
        from dify_eval_adapter import DifyEvalAdapter
        
        record = {
            'id': 'rec_002',
            'inputs': json.dumps({
                "customer_name": "张三",
                "product_type": "保险",
                "dialogue_content": "用户说想了解保险产品"
            }),
            'query': '请帮我推荐一款保险',
            'output': '根据您的需求，推荐这款...'
        }
        
        result = DifyEvalAdapter.to_eval_format(record)
        
        # 应包含背景信息
        user_content = result['messages'][0]['content']
        assert '张三' in user_content or 'customer_name' in user_content
        assert '保险' in user_content
    
    def test_to_eval_format_preserves_metadata(self):
        """转换应保留元数据"""
        from dify_eval_adapter import DifyEvalAdapter
        
        record = {
            'id': 'rec_003',
            'inputs': '{}',
            'query': 'test',
            'output': 'response',
            'model': 'gpt-4',
            'total_tokens': 100,
            'latency_ms': 500
        }
        
        result = DifyEvalAdapter.to_eval_format(record)
        
        assert result['metadata']['record_id'] == 'rec_003'
        assert result['metadata']['model'] == 'gpt-4'
    
    def test_run_evaluation_returns_result(self):
        """执行评测应返回评测结果"""
        from dify_eval_adapter import DifyEvalAdapter
        from dify_store import DifyStore
        
        # 准备测试数据
        dataset_id = DifyStore.create_dataset(name="评测测试集")
        record_id = DifyStore.add_record(
            dataset_id=dataset_id,
            inputs='{}',
            query='你好',
            output='您好，有什么可以帮您的？'
        )
        
        # 执行评测
        result = DifyEvalAdapter.run_evaluation(record_id)
        
        # 验证结果结构
        assert 'status' in result
        assert result['status'] in ['success', 'error']
        
        if result['status'] == 'success':
            assert 'scores' in result
            assert 'avg_score' in result
    
    def test_run_evaluation_updates_record_status(self):
        """评测成功后应更新记录状态"""
        from dify_eval_adapter import DifyEvalAdapter
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="状态更新测试集")
        record_id = DifyStore.add_record(
            dataset_id=dataset_id,
            inputs='{}',
            query='测试问题',
            output='测试回答'
        )
        
        # 执行评测
        DifyEvalAdapter.run_evaluation(record_id)
        
        # 验证状态更新
        record = DifyStore.get_record(record_id)
        assert record['eval_status'] in ['completed', 'failed']
        assert record['eval_count'] >= 1
    
    def test_batch_evaluate_processes_multiple(self):
        """批量评测应处理多条记录"""
        from dify_eval_adapter import DifyEvalAdapter
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="批量测试集")
        record_ids = []
        for i in range(3):
            rid = DifyStore.add_record(
                dataset_id=dataset_id,
                inputs='{}',
                query=f'问题{i}',
                output=f'回答{i}'
            )
            record_ids.append(rid)
        
        # 执行批量评测
        results, summary = DifyEvalAdapter.batch_evaluate(record_ids)
        
        assert len(results) == 3
        assert 'total' in summary
        assert 'success' in summary
        assert summary['total'] == 3


# Pytest 配置：使用临时数据库
@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库"""
    test_db = tmp_path / "test_traces.db"
    monkeypatch.setattr("dify_store.DB_PATH", str(test_db))
    monkeypatch.setattr("dify_eval_adapter.DB_PATH", str(test_db))
    
    # 初始化数据库
    from dify_store import init_dify_tables
    init_dify_tables()
    
    yield


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
