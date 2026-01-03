import json
import uuid
import random

def generate_simulation_data():
    data = []
    
    # ===============================
    # 1. 生成单轮对话 Bad Cases (20条)
    # ===============================
    bad_responses = [
        "我不知道。", "这不关我的事。", "请你自己去查。", "...", "API调用失败", 
        "User: Hello\nAssistant: Hi", "重复内容 " * 10, 
        "错误的答案", "我不理解你的意思", "系统错误"
    ]
    
    # ===============================
    # 辅助函数: 生成 mock metrics
    # ===============================
    def mock_metrics():
        latency = random.randint(200, 3000)
        ttft = random.randint(50, latency // 2)
        prompt = random.randint(50, 500)
        completion = random.randint(20, 200)
        return {
            "latency_ms": latency,
            "ttft_ms": ttft,
            "token_usage": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": prompt + completion
            }
        }

    for i in range(20):
        data.append({
            "session_id": f"sim_single_bad_{i+1:02d}",
            "eval_type": "single_turn",
            "messages": [
                {"role": "user", "content": f"请帮我查询编号为 {i+1} 的订单状态，并告诉我预计送达时间。"},
                {"role": "assistant", "content": random.choice(bad_responses)}
            ],
            **mock_metrics()
        })
        
    # ===============================
    # 2. 生成 Agent Bad Cases (20条)
    # ===============================
    agent_failures = [
        ("工具参数错误", False, "Error: Invalid argument 'date'"),
        ("死循环", False, "Error: Max recursion depth exceeded"),
        ("无工具调用", False, "我无法完成此任务，因为没有相关工具。"),
        ("任务未完成", False, "抱歉，我尝试了但失败了。")
    ]
    
    for i in range(20):
        fail_type, success, output = random.choice(agent_failures)
        tool_calls = []
        if fail_type == "工具参数错误":
            tool_calls = [{"name": "search_db", "args": {"invalid": "key"}, "success": False}]
        
        data.append({
            "session_id": f"sim_agent_bad_{i+1:02d}",  # 兼用作 task_id
            "eval_type": "agent",
            "task_description": f"执行复杂任务 #{i+1}，需要多步推理和工具调用。",
            "tool_calls": tool_calls,
            "decision_steps": [
                {"thought": f"尝试执行任务，但遇到了 {fail_type} 问题。"}
            ],
            "final_output": output,
            "success": success,
            **mock_metrics()
        })

    # ===============================
    # 3. 添加少量正常多轮对话 (参照)
    # ===============================
    data.append({
        "session_id": "sim_multi_good_01",
        "eval_type": "multi_turn",
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！很高兴为你服务。"},
            {"role": "user", "content": "介绍一下 Python"},
            {"role": "assistant", "content": "Python 是一种广泛使用的高级编程语言..."}
        ],
        **mock_metrics()
    })

    # 保存文件
    output_path = "data/simulation_badcases.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已生成 {len(data)} 条模拟数据: {output_path}")

if __name__ == "__main__":
    generate_simulation_data()
