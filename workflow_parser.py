"""
Dify 工作流 YML 解析器

解析 Dify 导出的工作流文件，提取节点信息用于评测溯源
"""

import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path


class DifyWorkflowParser:
    """Dify 工作流解析器"""
    
    def __init__(self, workflow_path: str = None, workflow_content: str = None):
        """
        初始化解析器
        
        Args:
            workflow_path: YML 文件路径
            workflow_content: YML 文件内容字符串
        """
        self.workflow = {}
        self.nodes = {}
        self.edges = []
        self.llm_nodes = {}  # 仅 LLM 类型节点
        
        if workflow_path:
            self.load_from_file(workflow_path)
        elif workflow_content:
            self.load_from_string(workflow_content)
    
    def load_from_file(self, path: str) -> None:
        """从文件加载工作流"""
        with open(path, 'r', encoding='utf-8') as f:
            self.workflow = yaml.safe_load(f)
        self._parse()
    
    def load_from_string(self, content: str) -> None:
        """从字符串加载工作流"""
        self.workflow = yaml.safe_load(content)
        self._parse()
    
    def _parse(self) -> None:
        """解析工作流结构"""
        graph = self.workflow.get('workflow', {}).get('graph', {})
        
        # 解析节点
        for node in graph.get('nodes', []):
            node_id = node.get('id', '')
            node_data = node.get('data', {})
            
            self.nodes[node_id] = {
                'id': node_id,
                'title': node_data.get('title', ''),
                'type': node_data.get('type', ''),
                'desc': node_data.get('desc', ''),
            }
            
            # 如果是 LLM 节点，提取 Prompt
            if node_data.get('type') == 'llm':
                prompt_templates = node_data.get('prompt_template', [])
                system_prompt = ''
                assistant_prompt = ''
                
                for template in prompt_templates:
                    role = template.get('role', '')
                    text = template.get('text', '')
                    if role == 'system':
                        system_prompt = text
                    elif role == 'assistant':
                        assistant_prompt = text
                
                self.llm_nodes[node_id] = {
                    'id': node_id,
                    'title': node_data.get('title', ''),
                    'system_prompt': system_prompt,
                    'assistant_prompt': assistant_prompt,
                    'model': node_data.get('model', {}).get('name', ''),
                    'temperature': node_data.get('model', {}).get('completion_params', {}).get('temperature', 0.7),
                }
        
        # 解析边
        self.edges = graph.get('edges', [])
    
    def get_all_llm_nodes(self) -> Dict[str, Dict]:
        """获取所有 LLM 节点"""
        return self.llm_nodes
    
    def get_llm_node_by_id(self, node_id: str) -> Optional[Dict]:
        """根据 ID 获取 LLM 节点"""
        return self.llm_nodes.get(node_id)
    
    def get_llm_node_by_title(self, title: str) -> Optional[Dict]:
        """根据标题获取 LLM 节点"""
        for node in self.llm_nodes.values():
            if node['title'] == title:
                return node
        return None
    
    def get_node_titles(self) -> List[str]:
        """获取所有 LLM 节点标题列表"""
        return [node['title'] for node in self.llm_nodes.values()]
    
    def format_for_prompt(self, max_prompt_length: int = 500) -> str:
        """
        将工作流格式化为 Prompt 可用的文本
        
        Args:
            max_prompt_length: 每个节点 Prompt 的最大长度
        
        Returns:
            格式化后的工作流描述
        """
        lines = ["## 工作流节点信息\n"]
        
        for node_id, node in self.llm_nodes.items():
            title = node['title']
            system_prompt = node['system_prompt']
            
            # 截取 Prompt 前 N 个字符
            if len(system_prompt) > max_prompt_length:
                system_prompt = system_prompt[:max_prompt_length] + "..."
            
            lines.append(f"### 节点: {title}")
            lines.append(f"节点 ID: {node_id}")
            lines.append(f"System Prompt 摘要:\n```\n{system_prompt}\n```\n")
        
        return "\n".join(lines)
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """获取工作流摘要"""
        app_info = self.workflow.get('app', {})
        
        return {
            'name': app_info.get('name', ''),
            'description': app_info.get('description', ''),
            'mode': app_info.get('mode', ''),
            'total_nodes': len(self.nodes),
            'llm_nodes_count': len(self.llm_nodes),
            'llm_node_titles': self.get_node_titles(),
        }


def load_workflow(path: str) -> DifyWorkflowParser:
    """便捷函数：加载工作流"""
    return DifyWorkflowParser(workflow_path=path)


if __name__ == "__main__":
    # 测试代码
    import json
    
    parser = DifyWorkflowParser(workflow_path="Dify.yml")
    
    print("=== 工作流摘要 ===")
    summary = parser.get_workflow_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print("\n=== LLM 节点列表 ===")
    for title in parser.get_node_titles():
        print(f"  - {title}")
    
    print("\n=== 格式化输出 (用于 Prompt) ===")
    print(parser.format_for_prompt(max_prompt_length=200))
