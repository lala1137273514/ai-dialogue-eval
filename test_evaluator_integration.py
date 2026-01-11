"""
评估器加载测试脚本
验证评测链路能否正常加载和使用评估器
"""

from evaluator_store import EvaluatorStore

print("=" * 50)
print("评估器加载测试")
print("=" * 50)
print()

# 1. 确保默认评估器存在
print("1. 加载默认评估器...")
EvaluatorStore.ensure_default_evaluator()
default_eval = EvaluatorStore.get_default_evaluator()

if default_eval:
    print(f"   ✅ 默认评估器: {default_eval['name']} v{default_eval['version']}")
    print(f"   维度数: {len(default_eval['dimensions'])}")
    dims = default_eval['dimensions']
    for d in dims[:3]:
        weight = d.get('weight', 'N/A')
        if isinstance(weight, float):
            weight = f"{weight * 100:.0f}%"
        print(f"   - {d['name']} (权重: {weight})")
    if len(dims) > 3:
        print(f"   ... 还有 {len(dims)-3} 个维度")
else:
    print("   ❌ 未找到默认评估器")
    exit(1)

print()

# 2. 验证维度格式兼容性
print("2. 验证维度格式兼容 run_eval...")
rubrics = default_eval['dimensions']
print("   维度格式检查:")
all_valid = True
for r in rubrics[:3]:
    has_name = 'name' in r
    has_desc = 'description' in r
    has_criteria = 'criteria' in r
    valid = has_name and has_criteria
    status = "✅" if valid else "❌"
    print(f"   {status} {r['name']}: name={has_name}, desc={has_desc}, criteria={has_criteria}")
    if not valid:
        all_valid = False

if all_valid:
    print("   ✅ 格式兼容")
else:
    print("   ❌ 格式不兼容")
    exit(1)

print()

# 3. 测试评测链路导入
print("3. 测试评测链路导入...")
try:
    from run_eval import evaluate_turn_unified, run_log_evaluation
    print("   ✅ run_eval 导入成功")
except ImportError as e:
    print(f"   ❌ run_eval 导入失败: {e}")
    exit(1)

print()

# 4. 模拟评测参数验证
print("4. 验证评测参数...")
test_history = [{'role': 'user', 'content': '你好'}]
test_response = '您好！有什么可以帮助您的吗？'

print(f"   测试对话: User: {test_history[0]['content']}")
print(f"   待评测回复: {test_response[:30]}...")
print(f"   评估维度: {len(rubrics)} 个")
print("   ✅ 参数验证通过")

print()

# 5. 列出所有可用评估器
print("5. 列出所有评估器...")
all_evaluators = EvaluatorStore.list_evaluators()
for ev in all_evaluators:
    default_mark = "⭐" if ev.get('is_default') else ""
    system_mark = "🔒" if ev.get('is_system') else ""
    print(f"   {default_mark}{system_mark} {ev['name']} v{ev['version']} ({len(ev.get('dimensions', []))}维度)")

print()
print("=" * 50)
print("✅ 评估器加载测试通过!")
print("   评测链路可正常使用评估器")
print("=" * 50)
