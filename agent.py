import os
import httpx
from openai import OpenAI
from typing import List, Dict, Generator

class RealAgent:
    """
    LLM Agent 封装类
    支持普通对话和流式对话两种模式
    """
    
    def __init__(self, model_name: str = None):
        """
        初始化 Agent
        
        Args:
            model_name: 模型名称，默认从环境变量或使用 gpt-4o-mini
        """
        # 从环境变量获取配置，提供默认值
        api_key = os.getenv("OPENAI_API_KEY", "sk-IAUJd9KeQUEnMuT9699446A6F4Da47149925Ed2f4a194cE8")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.v3.cm/v1")
        
        # 创建一个不验证 SSL 证书的客户端
        # verify=False 能解决某些网络环境下的 Connection error
        custom_http_client = httpx.Client(
            verify=False, 
            timeout=120.0,  # 增加超时时间
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=custom_http_client
        )
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_retries = 3

    def chat(self, history: List[Dict], user_input: str, temperature: float = 0.7) -> str:
        """
        普通对话模式（非流式）
        
        Args:
            history: 对话历史
            user_input: 用户输入
            temperature: 温度参数
            
        Returns:
            模型回复文本
        """
        messages = history.copy()
        messages.append({"role": "user", "content": user_input})

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature
                )
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content or ""
                return "❌ API 返回结果为空"
            except Exception as e:
                if attempt < self.max_retries - 1:
                    continue
                return f"❌ API 调用失败: {type(e).__name__} - {str(e)}"

    def chat_stream(self, history: List[Dict], user_input: str, temperature: float = 0.7) -> Generator[str, None, None]:
        """
        流式对话模式
        
        Args:
            history: 对话历史
            user_input: 用户输入
            temperature: 温度参数
            
        Yields:
            模型回复的文本片段
        """
        messages = history.copy()
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"❌ API 调用失败: {type(e).__name__} - {str(e)}"
    
    def chat_with_system(self, system_prompt: str, user_input: str, temperature: float = 0.7) -> str:
        """
        带系统提示的对话（便捷方法）
        
        Args:
            system_prompt: 系统提示
            user_input: 用户输入
            temperature: 温度参数
            
        Returns:
            模型回复文本
        """
        history = [{"role": "system", "content": system_prompt}]
        return self.chat(history, user_input, temperature)


if __name__ == "__main__":
    agent = RealAgent()
    print("正在测试 API 连接...")
    print("-" * 50)
    response = agent.chat([], "你好，简单介绍一下你自己")
    print(response)