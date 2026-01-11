"""
评估器生成器模块 - v1.0.0

功能:
- 从自然语言生成评估器 JSON
- 从文档内容提取评估标准
- 渲染 Markdown 预览
"""

import json
import re
from typing import Dict, List, Optional
from agent import RealAgent


# ==========================================
# LLM Prompt 模板
# ==========================================

EVALUATOR_GENERATION_PROMPT = """
### 角色
你是一个专业的 AI 对话质量评估专家，擅长设计评估维度和评分标准。

### 任务
根据用户的需求描述，生成一个结构化的评估器配置。

### 用户需求
{user_input}

### 输出要求
请输出一个 JSON 格式的评估器配置，包含以下字段：

1. **name** (string): 评估器名称，简洁明了
2. **description** (string): 评估器描述，说明适用场景
3. **eval_types** (array): 适用的评测类型，可选值: ["single_turn", "multi_turn", "agent"]
4. **dimensions** (array): 评估维度列表，每个维度包含:
   - **name** (string): 维度名称
   - **weight** (number): 权重 (0-1之间，所有维度权重之和应为1)
   - **description** (string): 维度说明
   - **criteria** (object): 评分标准，key 为 1-5 的分数，value 为该分数的描述
   - **low_score_checklist** (array): 低分检查清单，用于快速识别问题

### 注意事项
1. 维度数量建议 3-6 个，不宜过多
2. 权重之和必须为 1
3. 评分标准要具体、可操作
4. 低分检查清单每个维度 2-4 项

### 输出格式
请仅输出合法的 JSON，不要包含 Markdown 代码块或其他文字：
{{
  "name": "评估器名称",
  "description": "评估器描述",
  "eval_types": ["multi_turn"],
  "dimensions": [
    {{
      "name": "维度名称",
      "weight": 0.3,
      "description": "维度说明",
      "criteria": {{
        "1": "1分标准",
        "2": "2分标准",
        "3": "3分标准",
        "4": "4分标准",
        "5": "5分标准"
      }},
      "low_score_checklist": ["检查项1", "检查项2"]
    }}
  ]
}}
"""


DOCUMENT_EXTRACTION_PROMPT = """
### 角色
你是一个专业的 AI 对话质量评估专家，擅长从文档中提取评估标准。

### 任务
从以下文档内容中提取评估维度和评分标准，生成结构化的评估器配置。

### 文档内容
{document}

### 输出要求
请分析文档内容，提取关键的评估维度和标准，输出 JSON 格式的评估器配置。

如果文档中明确提到了权重或百分比，请使用文档中的值。
如果没有明确权重，请根据重要性自动分配。

### 输出格式
请仅输出合法的 JSON，不要包含 Markdown 代码块：
{{
  "name": "从文档提取的评估器名称",
  "description": "评估器描述",
  "eval_types": ["multi_turn"],
  "dimensions": [...]
}}
"""


class EvaluatorGenerator:
    """评估器生成器 - 使用 LLM 从自然语言生成评估器"""
    
    def __init__(self, agent: RealAgent = None):
        """
        初始化生成器
        
        Args:
            agent: RealAgent 实例，如果不提供则自动创建
        """
        self.agent = agent or RealAgent()
    
    def generate_from_text(self, user_input: str) -> Dict:
        """
        从自然语言描述生成评估器 JSON
        
        Args:
            user_input: 用户的需求描述
        
        Returns:
            评估器配置字典
        """
        prompt = EVALUATOR_GENERATION_PROMPT.format(user_input=user_input)
        
        try:
            raw_output = self.agent.chat([], prompt, temperature=0.3)
            return self._parse_and_validate(raw_output)
        except Exception as e:
            return {
                "error": str(e),
                "name": "生成失败",
                "description": f"LLM 生成失败: {str(e)}",
                "eval_types": ["multi_turn"],
                "dimensions": []
            }
    
    def generate_from_document(self, document_text: str) -> Dict:
        """
        从文档内容提取评估标准
        
        Args:
            document_text: 文档文本内容
        
        Returns:
            评估器配置字典
        """
        # 截断过长文档
        if len(document_text) > 10000:
            document_text = document_text[:10000] + "\n...(文档已截断)"
        
        prompt = DOCUMENT_EXTRACTION_PROMPT.format(document=document_text)
        
        try:
            raw_output = self.agent.chat([], prompt, temperature=0.3)
            return self._parse_and_validate(raw_output)
        except Exception as e:
            return {
                "error": str(e),
                "name": "提取失败",
                "description": f"文档解析失败: {str(e)}",
                "eval_types": ["multi_turn"],
                "dimensions": []
            }
    
    def _parse_and_validate(self, raw_output: str) -> Dict:
        """
        解析并验证 LLM 输出的 JSON
        
        Args:
            raw_output: LLM 原始输出
        
        Returns:
            验证后的评估器配置
        """
        # 提取 JSON
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if not json_match:
            raise ValueError("无法从 LLM 输出中提取 JSON")
        
        json_str = json_match.group(0)
        result = json.loads(json_str)
        
        # 验证必需字段
        if 'name' not in result:
            result['name'] = '未命名评估器'
        
        if 'dimensions' not in result or not result['dimensions']:
            raise ValueError("评估器必须包含至少一个维度")
        
        if 'eval_types' not in result:
            result['eval_types'] = ['multi_turn']
        
        if 'description' not in result:
            result['description'] = ''
        
        # 验证并规范化维度
        dimensions = result['dimensions']
        total_weight = sum(d.get('weight', 0) for d in dimensions)
        
        # 如果权重之和不为1，则自动重新分配
        if abs(total_weight - 1.0) > 0.01:
            weight_per_dim = 1.0 / len(dimensions)
            for dim in dimensions:
                dim['weight'] = round(weight_per_dim, 2)
        
        # 确保每个维度有必需字段
        for dim in dimensions:
            if 'name' not in dim:
                dim['name'] = '未命名维度'
            if 'weight' not in dim:
                dim['weight'] = round(1.0 / len(dimensions), 2)
            if 'description' not in dim:
                dim['description'] = ''
            if 'criteria' not in dim:
                dim['criteria'] = {
                    "1": "严重问题",
                    "2": "较多问题",
                    "3": "基本合格",
                    "4": "表现良好",
                    "5": "表现优秀"
                }
            if 'low_score_checklist' not in dim:
                dim['low_score_checklist'] = []
        
        return result
    
    @staticmethod
    def render_as_markdown(evaluator: Dict) -> str:
        """
        将评估器 JSON 渲染为可读 Markdown
        
        Args:
            evaluator: 评估器配置字典
        
        Returns:
            Markdown 格式的文本
        """
        lines = []
        
        # 标题
        name = evaluator.get('name', '未命名评估器')
        version = evaluator.get('version', '1.0')
        lines.append(f"# {name} v{version}\n")
        
        # 描述
        if evaluator.get('description'):
            lines.append(f"{evaluator['description']}\n")
        
        # 适用类型
        eval_types = evaluator.get('eval_types', [])
        type_names = {
            'single_turn': '单轮对话',
            'multi_turn': '多轮对话',
            'agent': 'Agent 评测'
        }
        type_labels = [type_names.get(t, t) for t in eval_types]
        lines.append(f"**适用场景**: {', '.join(type_labels)}\n")
        
        lines.append("---\n")
        lines.append("## 评估维度\n")
        
        # 维度详情
        for i, dim in enumerate(evaluator.get('dimensions', []), 1):
            weight = dim.get('weight', 0)
            weight_pct = f"{weight * 100:.0f}%"
            
            lines.append(f"### {i}. {dim['name']} (权重: {weight_pct})\n")
            
            if dim.get('description'):
                lines.append(f"{dim['description']}\n")
            
            # 评分标准
            lines.append("**评分标准:**\n")
            criteria = dim.get('criteria', {})
            for score in ['1', '2', '3', '4', '5']:
                if score in criteria:
                    lines.append(f"- **{score}分**: {criteria[score]}")
            lines.append("")
            
            # 低分检查清单
            checklist = dim.get('low_score_checklist', [])
            if checklist:
                lines.append("**低分检查清单:**\n")
                for item in checklist:
                    lines.append(f"- [ ] {item}")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def validate_dimensions(dimensions: List[Dict]) -> List[str]:
        """
        验证维度配置，返回错误列表
        
        Args:
            dimensions: 维度列表
        
        Returns:
            错误消息列表 (空列表表示验证通过)
        """
        errors = []
        
        if not dimensions:
            errors.append("至少需要一个评估维度")
            return errors
        
        # 检查权重
        total_weight = sum(d.get('weight', 0) for d in dimensions)
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"维度权重之和应为 1，当前为 {total_weight:.2f}")
        
        # 检查每个维度
        names_seen = set()
        for i, dim in enumerate(dimensions):
            prefix = f"维度 {i+1}"
            
            if not dim.get('name'):
                errors.append(f"{prefix}: 缺少名称")
            elif dim['name'] in names_seen:
                errors.append(f"{prefix}: 名称 '{dim['name']}' 重复")
            else:
                names_seen.add(dim['name'])
            
            weight = dim.get('weight', 0)
            if weight <= 0 or weight > 1:
                errors.append(f"{prefix}: 权重应在 0-1 之间，当前为 {weight}")
            
            criteria = dim.get('criteria', {})
            if not criteria:
                errors.append(f"{prefix}: 缺少评分标准")
            else:
                for score in ['1', '3', '5']:  # 至少需要 1, 3, 5 分的标准
                    if score not in criteria:
                        errors.append(f"{prefix}: 缺少 {score} 分的评分标准")
        
        return errors


# 测试代码
if __name__ == "__main__":
    print("🧪 测试评估器生成器模块")
    print("=" * 50)
    
    # 1. 测试 Markdown 渲染
    print("\n1. 测试 Markdown 渲染...")
    test_evaluator = {
        "name": "客服质量评估",
        "version": "1.0",
        "description": "适用于客服对话场景的质量评估",
        "eval_types": ["multi_turn", "single_turn"],
        "dimensions": [
            {
                "name": "情绪管理",
                "weight": 0.3,
                "description": "评估客服在对话中的情绪控制能力",
                "criteria": {
                    "1": "情绪失控，使用不当语言",
                    "3": "基本保持专业",
                    "5": "全程冷静专业，有效安抚用户"
                },
                "low_score_checklist": ["是否使用攻击性语言", "是否有消极回应"]
            },
            {
                "name": "问题解决",
                "weight": 0.7,
                "description": "评估客服解决用户问题的效率和效果",
                "criteria": {
                    "1": "完全未解决问题",
                    "3": "部分解决问题",
                    "5": "完美解决问题并提供预防建议"
                },
                "low_score_checklist": ["是否理解了用户问题", "是否给出了有效方案"]
            }
        ]
    }
    
    markdown = EvaluatorGenerator.render_as_markdown(test_evaluator)
    print(markdown[:500] + "...")
    
    # 2. 测试维度验证
    print("\n2. 测试维度验证...")
    errors = EvaluatorGenerator.validate_dimensions(test_evaluator['dimensions'])
    if errors:
        print(f"   发现 {len(errors)} 个错误:")
        for e in errors:
            print(f"   - {e}")
    else:
        print("   ✅ 验证通过")
    
    # 3. 测试错误维度
    print("\n3. 测试错误维度验证...")
    bad_dims = [
        {"name": "维度1", "weight": 0.5},  # 缺少 criteria
        {"name": "维度1", "weight": 0.3, "criteria": {"1": "差"}},  # 重复名称, 缺少5分
    ]
    errors = EvaluatorGenerator.validate_dimensions(bad_dims)
    print(f"   发现 {len(errors)} 个错误:")
    for e in errors:
        print(f"   - {e}")
    
    print("\n✅ 基础功能测试完成!")
    print("\n💡 LLM 生成功能需要配置 API Key 后测试")
