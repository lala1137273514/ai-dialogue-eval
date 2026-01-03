
import sqlite3
import random
import json
import uuid
import time
from datetime import datetime, timedelta
from trace_store import TraceStore, init_db

def generate_mock_data():
    print("🚀 开始生成全量测试数据...")
    init_db()
    
    # 清理旧数据 (可选，为了演示效果先保留或清理看需求，这里选择追加，但为了避免 confusion 也可以先 delete all if needed. user wanted 'complete dataset', maybe clean slate is better? No, append is safer)
    # Actually, for a clean dashboard, deleting old might be nice. But let's just append.
    
    # ==========================
    # 1. Single Turn Data
    # ==========================
    generate_single_turn(20)
    
    # ==========================
    # 2. Multi Turn Data
    # ==========================
    generate_multi_turn(15)
    
    # ==========================
    # 3. Agent Data
    # ==========================
    generate_agent(15)
    
    print("✅ 数据生成完成！请刷新页面查看。")

def mock_metrics(complexity="medium"):
    base_latency = 500 if complexity=="low" else 1500 if complexity=="medium" else 4000
    latency = random.randint(base_latency, base_latency * 2)
    ttft = random.randint(50, latency // 3)
    
    tokens_base = 100 if complexity=="low" else 500 if complexity=="medium" else 2000
    prompt = random.randint(tokens_base // 2, tokens_base)
    completion = random.randint(tokens_base // 4, tokens_base // 2)
    
    return {
        "latency_ms": latency,
        "ttft_ms": ttft,
        "token_usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion
        }
    }

def generate_single_turn(count):
    prompts = [
        "写一首关于秋天的诗", "解释量子纠缠", "Python 怎么读取 JSON", 
        "翻译这段话", "推荐一道川菜", "分析这篇新闻情感"
    ]
    responses = [
        "秋风起，落叶黄...", "量子纠缠是指...", "使用 json.load() 函数...",
        "Translation: ...", "推荐麻婆豆腐，做法是...", "整体情感偏向消极..."
    ]
    
    for i in range(count):
        prompt = random.choice(prompts)
        response = random.choice(responses)
        metrics = mock_metrics("low")
        score = random.uniform(3.0, 5.0)
        
        trace_id = TraceStore.create_trace(
            session_id=f"st_{uuid.uuid4().hex[:6]}",
            eval_type="single_turn",
            input_data={"messages": [{"role": "user", "content": prompt}]},
            output_data={"messages": [{"role": "assistant", "content": response}]}, # Simulate output structure
            model="gpt-4o",
            latency_ms=metrics['latency_ms'],
            metadata={'metrics': metrics, 'token_usage': metrics['token_usage'], 'ttft_ms': metrics['ttft_ms']}
        )
        
        # Add single turn scores
        TraceStore.add_score(trace_id, "accuracy", score, "回答准确", 0)
        TraceStore.add_score(trace_id, "clarity", random.uniform(3.5, 5), "表达清晰", 0)

def generate_multi_turn(count):
    topics = ["Debugging", "Travel Plan", "Story Writing"]
    
    for i in range(count):
        topic = random.choice(topics)
        session_id = f"mt_{topic}_{uuid.uuid4().hex[:4]}"
        msg_count = random.randint(2, 5)
        messages = []
        scores = []
        
        for turn in range(msg_count):
            messages.append({"role": "user", "content": f"User msg {turn+1} about {topic}"})
            messages.append({"role": "assistant", "content": f"Assistant response {turn+1}..."})
            scores.append(random.uniform(2.5, 4.8))
            
        metrics = mock_metrics("medium")
        
        trace_id = TraceStore.create_trace(
            session_id=session_id,
            eval_type="multi_turn",
            input_data={"messages": messages},
            output_data=None,
            model="gpt-4o",
            latency_ms=metrics['latency_ms'],
            metadata={'metrics': metrics}
        )
        
        # Add scores per turn
        for idx, s in enumerate(scores):
            TraceStore.add_score(trace_id, "overall", s, "Turn score", idx)
            TraceStore.add_score(trace_id, "logic", s, "Logic ok", idx)

def generate_agent(count):
    tasks = [
        "查询数据库并发送邮件", "分析股票并生成报告", "搜索网页并总结"
    ]
    
    for i in range(count):
        task = random.choice(tasks)
        task_id = f"agent_{uuid.uuid4().hex[:6]}"
        success = random.choice([True, True, False])
        metrics = mock_metrics("high")
        
        tool_calls = [
            {"name": "search", "args": {"q": "keyword"}, "result": "found 10 items", "success": True},
            {"name": "analyze", "args": {"data": "items"}, "result": "analysis done", "success": True}
        ]
        
        trace_id = TraceStore.create_trace(
            session_id=task_id,
            eval_type="agent",
            input_data={
                "task": task, 
                "task_description": task,
                "tool_calls": tool_calls,
                "decisions": [{"thought": "Step 1 done"}, {"thought": "Step 2 done"}]
            },
            output_data={
                "result": "Task completed successfully" if success else "Task failed", 
                "success": success
            },
            model="gpt-4o-agent",
            latency_ms=metrics['latency_ms'],
            metadata={'metrics': metrics}
        )
        
        # Agent Scores
        s_val = random.uniform(4, 5) if success else random.uniform(1, 3)
        TraceStore.add_score(trace_id, "task_completion", s_val, "Done", 0)
        TraceStore.add_score(trace_id, "tool_usage", random.uniform(3, 5), "Tool use ok", 0)

if __name__ == "__main__":
    generate_mock_data()
