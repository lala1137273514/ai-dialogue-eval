"""
Dify Store 单元测试 - TDD 驱动开发

测试内容：
1. dify_apps 表 CRUD
2. eval_datasets 表 CRUD
3. dataset_records 表 CRUD
4. evaluation_results 表操作
"""

import pytest
import sqlite3
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


class TestDifyApps:
    """Dify App 配置表测试"""
    
    def test_create_app_returns_id(self):
        """创建 App 应返回 ID"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(
            name="测试App",
            dify_host="https://api.dify.ai",
            api_key="sk-test-key",
            app_type="chat",
            description="测试用 App"
        )
        
        assert app_id is not None
        assert isinstance(app_id, str)
        assert len(app_id) > 0
    
    def test_get_app_returns_correct_data(self):
        """获取 App 应返回正确数据"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(
            name="获取测试App",
            dify_host="https://test.dify.ai",
            api_key="sk-get-test",
            app_type="workflow"
        )
        
        app = DifyStore.get_app(app_id)
        
        assert app is not None
        assert app['name'] == "获取测试App"
        assert app['dify_host'] == "https://test.dify.ai"
        assert app['api_key'] == "sk-get-test"
        assert app['app_type'] == "workflow"
    
    def test_list_apps_returns_all(self):
        """列出 App 应返回所有活跃的 App"""
        from dify_store import DifyStore
        
        # 创建两个 App
        DifyStore.create_app(name="App1", dify_host="h1", api_key="k1")
        DifyStore.create_app(name="App2", dify_host="h2", api_key="k2")
        
        apps = DifyStore.list_apps()
        
        assert len(apps) >= 2
        names = [a['name'] for a in apps]
        assert "App1" in names
        assert "App2" in names
    
    def test_update_app_changes_fields(self):
        """更新 App 应修改指定字段"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(name="原名", dify_host="h", api_key="k")
        
        DifyStore.update_app(app_id, name="新名", description="新描述")
        
        app = DifyStore.get_app(app_id)
        assert app['name'] == "新名"
        assert app['description'] == "新描述"
    
    def test_delete_app_removes_from_list(self):
        """删除 App 后应从列表消失"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(name="待删除App", dify_host="h", api_key="k")
        
        # 确认存在
        assert DifyStore.get_app(app_id) is not None
        
        # 删除
        DifyStore.delete_app(app_id)
        
        # 确认不存在
        assert DifyStore.get_app(app_id) is None


class TestEvalDatasets:
    """评测集表测试"""
    
    def test_create_dataset_returns_id(self):
        """创建评测集应返回 ID"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(
            name="测试评测集",
            source_type="dify"
        )
        
        assert dataset_id is not None
        assert isinstance(dataset_id, str)
    
    def test_create_dataset_with_app_id(self):
        """创建评测集可关联 App"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(name="关联App", dify_host="h", api_key="k")
        dataset_id = DifyStore.create_dataset(name="关联评测集", app_id=app_id)
        
        dataset = DifyStore.get_dataset(dataset_id)
        assert dataset['app_id'] == app_id
    
    def test_list_datasets_filters_by_app(self):
        """列出评测集应支持按 App 筛选"""
        from dify_store import DifyStore
        
        app_id = DifyStore.create_app(name="筛选App", dify_host="h", api_key="k")
        DifyStore.create_dataset(name="属于App的集", app_id=app_id)
        DifyStore.create_dataset(name="无App的集", app_id=None)
        
        datasets = DifyStore.list_datasets(app_id=app_id)
        
        for d in datasets:
            assert d['app_id'] == app_id
    
    def test_delete_dataset_cascades_records(self):
        """删除评测集应级联删除所有记录"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="级联测试集")
        DifyStore.add_record(dataset_id, inputs="{}", query="问题", output="回答")
        
        # 确认记录存在
        records = DifyStore.list_records(dataset_id)
        assert len(records) > 0
        
        # 删除评测集
        DifyStore.delete_dataset(dataset_id)
        
        # 确认记录也被删除
        records = DifyStore.list_records(dataset_id)
        assert len(records) == 0


class TestDatasetRecords:
    """对话记录表测试"""
    
    def test_add_record_returns_id(self):
        """添加记录应返回 ID"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="记录测试集")
        record_id = DifyStore.add_record(
            dataset_id=dataset_id,
            inputs=json.dumps({"customer_name": "张三"}),
            query="你好",
            output="您好！有什么可以帮您？",
            source="playground"
        )
        
        assert record_id is not None
    
    def test_get_record_returns_correct_data(self):
        """获取记录应返回正确数据"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="获取记录测试集")
        record_id = DifyStore.add_record(
            dataset_id=dataset_id,
            inputs='{"key": "value"}',
            query="测试问题",
            output="测试回答",
            model="gpt-4",
            total_tokens=100
        )
        
        record = DifyStore.get_record(record_id)
        
        assert record['query'] == "测试问题"
        assert record['output'] == "测试回答"
        assert record['model'] == "gpt-4"
        assert record['total_tokens'] == 100
        assert record['eval_status'] == "pending"
        assert record['eval_count'] == 0
    
    def test_list_records_filters_by_status(self):
        """列出记录应支持按状态筛选"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="状态筛选测试集")
        r1 = DifyStore.add_record(dataset_id, "{}", "q1", "a1")
        r2 = DifyStore.add_record(dataset_id, "{}", "q2", "a2")
        
        # 更新一条为 completed
        DifyStore.update_record_status(r1, "completed")
        
        pending_records = DifyStore.list_records(dataset_id, status="pending")
        completed_records = DifyStore.list_records(dataset_id, status="completed")
        
        assert len(pending_records) == 1
        assert len(completed_records) == 1
    
    def test_update_record_status_increments_eval_count(self):
        """更新记录状态应增加评测次数"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="评测次数测试集")
        record_id = DifyStore.add_record(dataset_id, "{}", "q", "a")
        
        # 第一次评测
        DifyStore.update_record_status(record_id, "completed", eval_count=1)
        record = DifyStore.get_record(record_id)
        assert record['eval_count'] == 1
        
        # 第二次评测（重新评测）
        DifyStore.update_record_status(record_id, "completed", eval_count=2)
        record = DifyStore.get_record(record_id)
        assert record['eval_count'] == 2


class TestEvaluationResults:
    """评测结果表测试"""
    
    def test_save_evaluation_result_creates_record(self):
        """保存评测结果应创建记录"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="结果测试集")
        record_id = DifyStore.add_record(dataset_id, "{}", "q", "a")
        
        result_id = DifyStore.save_evaluation_result(
            record_id=record_id,
            evaluator_id="eval_123",
            scores=json.dumps({"clarity": 4.5, "accuracy": 5.0}),
            avg_score=4.75,
            reasonings=json.dumps({"clarity": "表达清晰", "accuracy": "信息准确"}),
            duration_ms=1500
        )
        
        assert result_id is not None
    
    def test_get_record_evaluations_returns_history(self):
        """获取记录评测应返回所有历史"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="历史测试集")
        record_id = DifyStore.add_record(dataset_id, "{}", "q", "a")
        
        # 两次评测
        DifyStore.save_evaluation_result(record_id, "eval_1", "{}", 4.0, "{}", 100)
        DifyStore.save_evaluation_result(record_id, "eval_2", "{}", 4.5, "{}", 120)
        
        evaluations = DifyStore.get_record_evaluations(record_id)
        
        assert len(evaluations) == 2
        # 应按版本排序
        assert evaluations[0]['eval_version'] <= evaluations[1]['eval_version']
    
    def test_get_latest_evaluation_returns_newest(self):
        """获取最新评测应返回最后一次"""
        from dify_store import DifyStore
        
        dataset_id = DifyStore.create_dataset(name="最新测试集")
        record_id = DifyStore.add_record(dataset_id, "{}", "q", "a")
        
        # 两次评测
        DifyStore.save_evaluation_result(record_id, "eval_1", "{}", 3.0, "{}", 100)
        DifyStore.save_evaluation_result(record_id, "eval_2", "{}", 4.5, "{}", 120)
        
        latest = DifyStore.get_latest_evaluation(record_id)
        
        assert latest is not None
        assert latest['avg_score'] == 4.5


# Pytest 配置：使用临时数据库
@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库"""
    test_db = tmp_path / "test_traces.db"
    monkeypatch.setattr("dify_store.DB_PATH", str(test_db))
    
    # 初始化数据库
    from dify_store import init_dify_tables
    init_dify_tables()
    
    yield
    
    # 清理
    if test_db.exists():
        test_db.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
