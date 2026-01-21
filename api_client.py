"""
API 客户端模块

前端通过 HTTP 调用 API 服务器获取评测集和记录数据
解决前端和 API 数据库不同步的问题
"""

import requests
import os
from typing import List, Dict, Optional


class APIClient:
    """API 客户端 - 用于前端调用后端 API"""
    
    def __init__(self, api_host: str = None):
        """
        初始化 API 客户端
        
        Args:
            api_host: API 服务器地址，默认从环境变量读取
        """
        if api_host:
            self.api_host = api_host.rstrip('/')
        else:
            self.api_host = os.environ.get(
                'API_HOST', 
                'https://ai-dialogue-eval-api.zeabur.app'
            ).rstrip('/')
    
    def get_datasets(self) -> List[Dict]:
        """
        获取评测集列表
        
        Returns:
            评测集列表，失败时返回空列表
        """
        try:
            response = requests.get(
                f"{self.api_host}/api/v1/datasets",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('datasets', [])
            else:
                print(f"[APIClient] ⚠️ 获取评测集失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"[APIClient] ❌ 请求失败: {e}")
            return []
    
    def get_records(self, dataset_id: str) -> List[Dict]:
        """
        获取评测集的记录
        
        Args:
            dataset_id: 评测集 ID
            
        Returns:
            记录列表，失败时返回空列表
        """
        try:
            response = requests.get(
                f"{self.api_host}/api/v1/datasets/{dataset_id}/records",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('records', [])
            else:
                print(f"[APIClient] ⚠️ 获取记录失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"[APIClient] ❌ 请求失败: {e}")
            return []
    
    def evaluate_record(self, record_id: str, evaluator_id: str) -> Dict:
        """
        执行评测
        
        Args:
            record_id: 记录 ID
            evaluator_id: 评估器 ID
            
        Returns:
            评测结果
        """
        try:
            response = requests.post(
                f"{self.api_host}/api/v1/evaluate",
                json={
                    'record_id': record_id,
                    'evaluator_id': evaluator_id
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f"评测失败: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 全局单例
_client = None

def get_api_client() -> APIClient:
    """获取 API 客户端单例"""
    global _client
    if _client is None:
        _client = APIClient()
    return _client
