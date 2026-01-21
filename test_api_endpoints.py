"""
TDD 测试: API 端点和工作流分组功能

RED 阶段: 先写测试，看着它失败
"""

import pytest
import json
import sys
import os
import tempfile

# 设置测试环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask.testing import FlaskClient


class TestWorkflowDatasetGrouping:
    """测试按工作流名称自动分组功能"""
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """每个测试使用独立的临时数据库"""
        db_file = tmp_path / "test_traces.db"
        os.environ['TEST_DB_PATH'] = str(db_file)
        
        # 初始化数据库
        from dify_store import init_dify_tables, DB_PATH
        import dify_store
        dify_store.DB_PATH = str(db_file)
        init_dify_tables()
        
        yield
        
        # 清理
        if db_file.exists():
            db_file.unlink()
    
    def test_trace_create_groups_by_workflow_name(self):
        """
        静态凭证回传时，应按工作流名称自动创建评测集
        工作流 "CRM时间线抽取" → "CRM时间线抽取-评测集"
        """
        from langfuse_adapter import handle_trace_create
        from dify_store import DifyStore
        from datetime import datetime
        
        # Given: 一个来自 "CRM时间线抽取" 工作流的 trace
        trace_body = {
            "id": "test-trace-workflow-1",
            "name": "CRM时间线抽取",
            "input": "测试输入内容",
            "output": "测试输出结果"
        }
        
        # When: 调用 handle_trace_create (dify_app=None 表示静态凭证)
        handle_trace_create(trace_body, datetime.now().isoformat(), dify_app=None)
        
        # Then: 应该创建 "CRM时间线抽取-评测集" 评测集
        datasets = DifyStore.list_datasets()
        workflow_dataset = next(
            (d for d in datasets if d['name'] == 'CRM时间线抽取-评测集'), 
            None
        )
        
        assert workflow_dataset is not None, \
            f"应该创建 'CRM时间线抽取-评测集'，实际评测集: {[d['name'] for d in datasets]}"
    
    def test_same_workflow_uses_same_dataset(self):
        """
        同一工作流的多次调用应存入同一评测集
        """
        from langfuse_adapter import handle_trace_create
        from dify_store import DifyStore
        from datetime import datetime
        
        # Given: 两个来自同一工作流的 trace
        trace1 = {"id": "trace-1", "name": "客户画像", "input": "输入1", "output": "输出1"}
        trace2 = {"id": "trace-2", "name": "客户画像", "input": "输入2", "output": "输出2"}
        
        # When: 两次调用
        handle_trace_create(trace1, datetime.now().isoformat(), dify_app=None)
        handle_trace_create(trace2, datetime.now().isoformat(), dify_app=None)
        
        # Then: 应该只有一个 "客户画像-评测集"，里面有 2 条记录
        datasets = DifyStore.list_datasets()
        workflow_datasets = [d for d in datasets if d['name'] == '客户画像-评测集']
        
        assert len(workflow_datasets) == 1, "同一工作流应该只有一个评测集"
        assert workflow_datasets[0]['record_count'] == 2, "评测集应该有 2 条记录"


class TestDatasetAPI:
    """测试评测集 API 端点"""
    
    @pytest.fixture
    def client(self, tmp_path):
        """创建测试客户端"""
        db_file = tmp_path / "test_api.db"
        os.environ['TEST_DB_PATH'] = str(db_file)
        
        import dify_store
        dify_store.DB_PATH = str(db_file)
        dify_store.init_dify_tables()
        
        from api_server import create_app
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            yield client
    
    def test_get_datasets_returns_list(self, client):
        """
        GET /api/v1/datasets 应返回评测集列表
        """
        from dify_store import DifyStore
        
        # Given: 数据库中有 2 个评测集
        DifyStore.create_dataset(name="测试评测集1", source_type="dify")
        DifyStore.create_dataset(name="测试评测集2", source_type="dify")
        
        # When: GET /api/v1/datasets
        response = client.get('/api/v1/datasets')
        
        # Then: 返回 200 和包含 2 个评测集的列表
        assert response.status_code == 200
        data = response.get_json()
        assert 'datasets' in data
        assert len(data['datasets']) >= 2
    
    def test_get_dataset_records(self, client):
        """
        GET /api/v1/datasets/<id>/records 应返回评测集的记录
        """
        from dify_store import DifyStore
        
        # Given: 一个评测集，里面有 1 条记录
        dataset_id = DifyStore.create_dataset(name="带记录的评测集", source_type="dify")
        DifyStore.add_record(
            dataset_id=dataset_id,
            inputs='{"input": "测试"}',
            query="测试查询",
            output="测试输出",
            source="test"
        )
        
        # When: GET /api/v1/datasets/<id>/records
        response = client.get(f'/api/v1/datasets/{dataset_id}/records')
        
        # Then: 返回 200 和包含 1 条记录的列表
        assert response.status_code == 200
        data = response.get_json()
        assert 'records' in data
        assert len(data['records']) == 1
        assert data['records'][0]['query'] == "测试查询"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
