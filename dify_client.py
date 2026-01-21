"""
Dify API 客户端 - v1.0.0

功能:
- 工作流入参定义获取 (GET /v1/parameters)
- 对话消息发送 (POST /v1/chat-messages)
- 工作流执行 (POST /v1/workflows/run)
- 连接测试
"""

import requests
from typing import Dict, List, Optional, Any
import json


class DifyClient:
    """Dify API 客户端"""
    
    def __init__(self, host: str, api_key: str, timeout: int = 60):
        """
        初始化 Dify 客户端
        
        Args:
            host: Dify API 地址 (如 https://api.dify.ai)
            api_key: API Key (sk-xxx)
            timeout: 请求超时时间（秒）
        """
        self.host = host.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_parameters(self) -> Dict:
        """
        获取工作流入参定义
        
        Returns:
            {
                "user_input_form": [
                    {"label": "客户名称", "variable": "customer_name", "required": True},
                    {"label": "对话内容", "variable": "dialogue", "required": True, "type": "paragraph"},
                    ...
                ],
                "file_upload": {...},
                "system_parameters": {...}
            }
        """
        try:
            response = requests.get(
                f"{self.host}/v1/parameters",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "user_input_form": []}
    
    def chat(self, query: str, inputs: Dict = None, user: str = "test",
             conversation_id: str = None, response_mode: str = "blocking") -> Dict:
        """
        发送对话消息
        
        Args:
            query: 用户问题
            inputs: 额外输入参数
            user: 用户标识
            conversation_id: 会话 ID (用于多轮对话)
            response_mode: blocking / streaming
            
        Returns:
            {
                "answer": "AI 回复内容",
                "conversation_id": "xxx",
                "message_id": "xxx",
                "metadata": {...}
            }
        """
        payload = {
            "inputs": inputs or {},
            "query": query,
            "user": user,
            "response_mode": response_mode
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        try:
            response = requests.post(
                f"{self.host}/v1/chat-messages",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "answer": ""}
    
    def run_workflow(self, inputs: Dict, user: str = "test",
                     response_mode: str = "blocking") -> Dict:
        """
        执行工作流
        
        Args:
            inputs: 工作流输入参数
            user: 用户标识
            response_mode: blocking / streaming
            
        Returns:
            {
                "workflow_run_id": "xxx",
                "task_id": "xxx",
                "data": {
                    "outputs": {...},
                    "status": "succeeded",
                    "elapsed_time": 1.5,
                    "total_tokens": 100,
                    ...
                }
            }
        """
        payload = {
            "inputs": inputs,
            "user": user,
            "response_mode": response_mode
        }
        
        try:
            response = requests.post(
                f"{self.host}/v1/workflows/run",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "data": {}}
    
    def test_connection(self) -> Dict:
        """
        测试 API 连接是否正常
        
        Returns:
            {"success": True/False, "message": "...", "parameters": {...}}
        """
        try:
            result = self.get_parameters()
            if "error" in result:
                return {
                    "success": False,
                    "message": f"连接失败: {result['error']}"
                }
            return {
                "success": True,
                "message": "连接成功",
                "parameters": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接异常: {str(e)}"
            }
    
    def get_input_form_fields(self) -> List[Dict]:
        """
        获取输入表单字段定义（简化版）
        
        Returns:
            [
                {"label": "客户名称", "variable": "customer_name", "required": True, "type": "text"},
                {"label": "对话内容", "variable": "dialogue", "required": True, "type": "paragraph"},
                ...
            ]
        """
        params = self.get_parameters()
        if "error" in params:
            return []
        
        user_input_form = params.get("user_input_form", [])
        
        # 标准化字段定义
        fields = []
        for item in user_input_form:
            field = {
                "label": item.get("label", item.get("variable", "未知")),
                "variable": item.get("variable", ""),
                "required": item.get("required", False),
                "type": self._normalize_field_type(item),
                "default": item.get("default", ""),
                "options": item.get("options", []),
                "max_length": item.get("max_length", 0)
            }
            fields.append(field)
        
        return fields
    
    def _normalize_field_type(self, item: Dict) -> str:
        """标准化字段类型"""
        # Dify 的 user_input_form 结构可能包含不同的类型标识
        if "paragraph" in str(item):
            return "paragraph"
        if "select" in str(item) or item.get("options"):
            return "select"
        if "number" in str(item):
            return "number"
        return "text"


# 便捷创建函数
def create_dify_client(host: str, api_key: str) -> DifyClient:
    """创建 Dify 客户端实例"""
    return DifyClient(host, api_key)


if __name__ == "__main__":
    # 测试代码
    client = DifyClient("https://api.dify.ai", "your-api-key")
    result = client.test_connection()
    print(f"连接测试: {result}")
