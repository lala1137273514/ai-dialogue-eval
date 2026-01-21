"""
TDD 测试: API 客户端模块 (前端通过 HTTP 调用 API 获取数据)

RED 阶段: 先写测试，看着它失败
"""

import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestAPIClient:
    """测试 API 客户端模块"""
    
    def test_api_client_get_datasets(self):
        """
        API 客户端应该能获取评测集列表
        """
        from api_client import APIClient
        
        # Given: API 返回评测集列表
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'datasets': [
                {'id': 'ds1', 'name': 'CRM时间线抽取-评测集', 'record_count': 5},
                {'id': 'ds2', 'name': '客户画像-评测集', 'record_count': 3}
            ]
        }
        
        with patch('api_client.requests.get', return_value=mock_response):
            # When: 调用 get_datasets
            client = APIClient('http://test-api.com')
            datasets = client.get_datasets()
            
            # Then: 应该返回评测集列表
            assert len(datasets) == 2
            assert datasets[0]['name'] == 'CRM时间线抽取-评测集'
    
    def test_api_client_get_records(self):
        """
        API 客户端应该能获取评测集的记录
        """
        from api_client import APIClient
        
        # Given: API 返回记录列表
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'records': [
                {'id': 'r1', 'query': '测试问题', 'output': '测试回答'},
            ]
        }
        
        with patch('api_client.requests.get', return_value=mock_response):
            # When: 调用 get_records
            client = APIClient('http://test-api.com')
            records = client.get_records('ds1')
            
            # Then: 应该返回记录列表
            assert len(records) == 1
            assert records[0]['query'] == '测试问题'
    
    def test_api_client_evaluate_record(self):
        """
        API 客户端应该能执行评测
        """
        from api_client import APIClient
        
        # Given: API 返回评测结果
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'result': {
                'avg_score': 0.85,
                'scores': {'relevance': 0.9, 'coherence': 0.8}
            }
        }
        
        with patch('api_client.requests.post', return_value=mock_response):
            # When: 调用 evaluate_record
            client = APIClient('http://test-api.com')
            result = client.evaluate_record('r1', 'evaluator_1')
            
            # Then: 应该返回评测结果
            assert result['success'] is True
            assert result['result']['avg_score'] == 0.85
    
    def test_api_client_handles_error(self):
        """
        API 客户端应该正确处理错误
        """
        from api_client import APIClient
        
        # Given: API 返回错误
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'error': '服务器错误'}
        
        with patch('api_client.requests.get', return_value=mock_response):
            # When: 调用 get_datasets
            client = APIClient('http://test-api.com')
            datasets = client.get_datasets()
            
            # Then: 应该返回空列表而不是崩溃
            assert datasets == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
