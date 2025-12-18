"""
评测执行模块 v3.0

优化：合并评测模式
- 每条 Assistant 回复只做 1 次 LLM 调用
- 一次性输出 6 个维度的分数 + 综合分析
- 低分深度分析也是针对整条回复（而非每个维度）
"""

import json
import re
from typing import List, Dict, Any, Callable, Optional, Generator
from agent import RealAgent
from workflow_parser import DifyWorkflowParser


# ==========================================
# 1. 合并评测 Prompt（一次评测所有维度）
# ==========================================
UNIFIED_JUDGE_PROMPT = """
### 角色
你是一个严厉且专业的对话质量质检员。你需要对 AI 助手（Assistant）的回复进行全面的"负向问题检测"。

### 任务上下文
领域: {domain}

### 对话历史
{history_text}

### 待评测回复
Assistant: "{target_response}"

### 评分维度（共6个）
请对以下每个维度进行 1-5 分评分（1分=严重问题，5分=完美无问题）：

{dimensions_text}

### 任务指令
1. **负向检测**：重点检查每个维度的负向问题是否存在
2. **逐维度打分**：为每个维度给出 1-5 分评分
3. **综合分析**：给出一段整体评价，指出主要问题和亮点（100字以内）

### 输出格式 (JSON)
请仅输出合法的 JSON，不要包含 Markdown 代码块：
{{
  "scores": {{
    "clarity_sentence_structure": 4,
    "proactivity_interaction": 3,
    "content_benefits": 4,
    "persona_authority": 5,
    "accuracy_truthfulness": 4,
    "tone_empathy": 3
  }},
  "avg_score": 3.83,
  "overall_analysis": "综合分析：该回复整体表现良好，但在主动引导和共情表达方面有待改进..."
}}
"""


# ==========================================
# 2. 低分深度分析 Prompt（整体分析）
# ==========================================
UNIFIED_DEEP_ANALYSIS_PROMPT = """
### 角色
你是一名资深 AI 系统调试专家，擅长分析对话质量问题的根本原因并溯源到工作流节点。

### 任务上下文
**对话历史：**
{history_text}

**问题回复：**
{target_response}

**评分结果：**
平均分：{avg_score}/5
各维度得分：{scores_text}
初步分析：{overall_analysis}

**低分维度：**
{low_dimensions}

**工作流配置：**
{workflow_info}

### 任务指令
请针对该回复的整体问题进行深度分析：

1. **根因分析 (root_cause)**：
   综合分析该回复得低分的根本原因，不要拆分到每个维度，而是找出共性问题。

2. **节点溯源 (traced_node)**：
   根据回复内容和对话上下文，判断该回复最可能由哪个工作流节点生成。

3. **Prompt 问题 (prompt_issue)**：
   指出该节点 Prompt 的主要缺陷。

4. **修改建议 (modification_suggestion)**：
   给出可直接应用的 Prompt 修改方案，解决多个维度的问题。

### 输出格式 (JSON)
请仅输出合法的 JSON：
{{
  "root_cause": "根本原因分析",
  "traced_node_id": "节点ID",
  "traced_node_title": "节点名称",
  "prompt_issue": "Prompt问题描述",
  "modification_suggestion": "具体修改建议"
}}
"""


# ==========================================
# 3. 合并评测函数（一次评测所有维度）
# ==========================================
def evaluate_turn_unified(agent: RealAgent, 
                         history: List[Dict], 
                         target_response: str, 
                         rubrics: List[Dict], 
                         domain: str = "general") -> Dict:
    """
    Phase 1: 对单个回复进行一次性多维度评测
    
    Returns:
        {
            "scores": {"clarity": 4, "proactivity": 3, ...},
            "avg_score": 3.5,
            "overall_analysis": "综合分析..."
        }
    """
    # 格式化历史
    history_text = ""
    for msg in history[-10:]:  # 只取最近10条避免过长
        role = "User" if msg['role'] == "user" else "Assistant"
        content = msg.get('content', '')[:200]  # 截断过长内容
        history_text += f"{role}: {content}\n"
    
    if not history_text:
        history_text = "(无历史记录)"

    # 格式化所有维度
    dimensions_text = ""
    for i, rubric in enumerate(rubrics, 1):
        name = rubric['name']
        desc = rubric.get('description', '')
        
        # 简化评分标准，只展示关键档位
        criteria = rubric.get('criteria', {})
        criteria_brief = f"5分={criteria.get('5', '优秀')[:20]}; 1分={criteria.get('1', '严重问题')[:20]}"
        
        # 低分检查清单
        checklist = rubric.get('low_score_checklist', [])
        checklist_text = "; ".join(checklist[:3])  # 只取前3项
        
        dimensions_text += f"""
**{i}. {name}**
- 说明: {desc}
- 标准: {criteria_brief}
- 检查项: {checklist_text}
"""

    # 构造 Prompt
    prompt = UNIFIED_JUDGE_PROMPT.format(
        domain=domain,
        history_text=history_text,
        target_response=target_response[:500],  # 截断过长回复
        dimensions_text=dimensions_text
    )

    # 调用 LLM
    try:
        raw_output = agent.chat([], prompt)
        
        # 解析 JSON
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        json_str = match.group(0) if match else raw_output
        result = json.loads(json_str)
        
        # 确保数据完整
        scores = result.get("scores", {})
        
        # 计算平均分和最低分
        if scores:
            avg = sum(scores.values()) / len(scores)
            min_score = min(scores.values())
        else:
            avg = 3.0
            min_score = 3
        
        # 计算综合分（最低分惩罚机制）
        # 综合分 = min(平均分, 最低分 + 1.5)
        # 这样如果某维度特别低，会拉低整体分数
        combined_score = min(avg, min_score + 1.5)
        
        return {
            "scores": scores,
            "avg_score": round(result.get("avg_score", avg), 2),
            "min_score": min_score,
            "combined_score": round(combined_score, 2),
            "overall_analysis": result.get("overall_analysis", "")
        }
        
    except json.JSONDecodeError as e:
        # 返回默认分数
        default_scores = {r['name']: 3 for r in rubrics}
        return {
            "scores": default_scores,
            "avg_score": 3.0,
            "min_score": 3,
            "combined_score": 3.0,
            "overall_analysis": f"JSON解析失败: {str(e)[:50]}"
        }
    except Exception as e:
        default_scores = {r['name']: 1 for r in rubrics}
        return {
            "scores": default_scores,
            "avg_score": 1.0,
            "min_score": 1,
            "combined_score": 1.0,
            "overall_analysis": f"评测失败: {str(e)[:50]}"
        }


def analyze_low_score_unified(agent: RealAgent,
                              history: List[Dict],
                              target_response: str,
                              scores: Dict,
                              avg_score: float,
                              overall_analysis: str,
                              rubrics: List[Dict],
                              low_score_threshold: int,
                              workflow_parser: Optional[DifyWorkflowParser] = None) -> Dict:
    """
    Phase 2: 对低分回复进行整体深度分析（只做一次）
    """
    # 格式化历史
    history_text = ""
    for msg in history[-6:]:
        role = "User" if msg['role'] == "user" else "Assistant"
        history_text += f"{role}: {msg.get('content', '')[:150]}\n"
    
    if not history_text:
        history_text = "(无历史记录)"

    # 格式化分数
    scores_text = ", ".join([f"{k}: {v}分" for k, v in scores.items()])
    
    # 找出低分维度
    low_dims = [k for k, v in scores.items() if v <= low_score_threshold]
    low_dimensions = ", ".join(low_dims) if low_dims else "无"
    
    # 获取工作流信息
    if workflow_parser:
        workflow_info = workflow_parser.format_for_prompt(max_prompt_length=200)
    else:
        workflow_info = "(未提供工作流配置)"

    # 构造 Prompt
    prompt = UNIFIED_DEEP_ANALYSIS_PROMPT.format(
        history_text=history_text,
        target_response=target_response[:400],
        avg_score=avg_score,
        scores_text=scores_text,
        overall_analysis=overall_analysis,
        low_dimensions=low_dimensions,
        workflow_info=workflow_info
    )

    # 调用 LLM
    try:
        raw_output = agent.chat([], prompt, temperature=0.3)
        
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        json_str = match.group(0) if match else raw_output
        result = json.loads(json_str)
        
        return {
            "root_cause": result.get("root_cause", ""),
            "traced_node_id": result.get("traced_node_id", ""),
            "traced_node_title": result.get("traced_node_title", ""),
            "prompt_issue": result.get("prompt_issue", ""),
            "modification_suggestion": result.get("modification_suggestion", "")
        }
        
    except Exception as e:
        return {
            "root_cause": f"分析失败: {str(e)}",
            "traced_node_id": "",
            "traced_node_title": "",
            "prompt_issue": "",
            "modification_suggestion": ""
        }


# ==========================================
# 4. 主评测流程（优化版）
# ==========================================
def run_log_evaluation(logs: List[Dict], 
                       rubrics: List[Dict], 
                       workflow_parser: Optional[DifyWorkflowParser] = None,
                       low_score_threshold: int = 3,
                       progress_callback: Callable = None) -> List[Dict]:
    """
    合并评测主流程
    
    每条 Assistant 回复只做 1 次评测，输出：
    - 6 个维度的分数
    - 平均分
    - 综合分析
    - 如果平均分 ≤ 阈值，再做 1 次深度分析
    """
    agent = RealAgent()
    results = []
    
    # 计算总任务量（每条 Assistant 消息 = 1 次评测）
    total_steps = sum(
        1 for session in logs 
        for msg in session.get('messages', []) 
        if msg['role'] == 'assistant'
    )
    
    current_step = 0
    
    for session in logs:
        session_id = session.get('session_id', 'unknown')
        domain = session.get('domain', 'general')
        messages = session.get('messages', [])
        
        session_results = {
            "session_id": session_id,
            "evaluations": [],      # 每条 turn 一个评测结果
            "low_score_analyses": []
        }
        
        for idx, msg in enumerate(messages):
            if msg['role'] == 'assistant':
                target_response = msg['content']
                history = messages[:idx]
                
                # Phase 1: 一次性评测所有维度
                if progress_callback:
                    progress_callback(current_step, total_steps, 
                                     f"[{session_id}] Turn {idx}")
                
                eval_res = evaluate_turn_unified(agent, history, target_response, rubrics, domain)
                
                eval_item = {
                    "turn_index": idx,
                    "scores": eval_res['scores'],
                    "avg_score": eval_res['avg_score'],
                    "min_score": eval_res.get('min_score', 3),
                    "combined_score": eval_res.get('combined_score', eval_res['avg_score']),
                    "overall_analysis": eval_res['overall_analysis'],
                    "target_response": target_response[:200] + "..." if len(target_response) > 200 else target_response
                }
                
                # Phase 2: 深度分析触发条件
                # 触发条件：综合分 ≤ 阈值 或 任意维度分数 ≤ 阈值-1（严重问题）
                min_score = eval_res.get('min_score', 5)
                combined_score = eval_res.get('combined_score', 5)
                should_analyze = combined_score <= low_score_threshold or min_score <= (low_score_threshold - 1)
                
                if should_analyze and workflow_parser:
                    if progress_callback:
                        progress_callback(current_step, total_steps, 
                                         f"[{session_id}] Turn {idx} - 深度分析")
                    
                    analysis = analyze_low_score_unified(
                        agent, history, target_response,
                        eval_res['scores'], eval_res['avg_score'], 
                        eval_res['overall_analysis'],
                        rubrics, low_score_threshold, workflow_parser
                    )
                    
                    session_results['low_score_analyses'].append({
                        "turn_index": idx,
                        "scores": eval_res['scores'],
                        "avg_score": eval_res['avg_score'],
                        "min_score": eval_res.get('min_score', 3),
                        "combined_score": eval_res.get('combined_score', eval_res['avg_score']),
                        "overall_analysis": eval_res['overall_analysis'],
                        "target_response": target_response,
                        **analysis
                    })
                
                session_results["evaluations"].append(eval_item)
                current_step += 1
        
        results.append(session_results)
    
    return results


# ==========================================
# 5. 会话综合评分生成
# ==========================================
def generate_session_summary(session_results: Dict) -> Dict:
    """生成会话级别的综合评分"""
    evaluations = session_results.get('evaluations', [])
    if not evaluations:
        return {
            "overall_score": 0,
            "dimension_averages": {},
            "weak_points": [],
            "strong_points": [],
            "low_score_count": 0
        }
    
    # 计算各维度平均分
    dimension_scores = {}
    for eval_item in evaluations:
        for dim, score in eval_item.get('scores', {}).items():
            if dim not in dimension_scores:
                dimension_scores[dim] = []
            dimension_scores[dim].append(score)
    
    dimension_averages = {
        dim: round(sum(scores) / len(scores), 2)
        for dim, scores in dimension_scores.items()
    }
    
    # 计算综合得分
    all_avg_scores = [e.get('avg_score', 3) for e in evaluations]
    overall_score = round(sum(all_avg_scores) / len(all_avg_scores), 2)
    
    # 识别薄弱点和强项
    weak_points = [dim for dim, avg in dimension_averages.items() if avg < 3]
    strong_points = [dim for dim, avg in dimension_averages.items() if avg >= 4]
    
    return {
        "session_id": session_results.get('session_id', 'unknown'),
        "overall_score": overall_score,
        "dimension_averages": dimension_averages,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "low_score_count": len(session_results.get('low_score_analyses', []))
    }


# ==========================================
# 6. 评测报告生成
# ==========================================
def generate_markdown_report(results: List[Dict], rubrics: List[Dict] = None) -> str:
    """生成 Markdown 格式的评测报告"""
    from datetime import datetime
    
    if not results:
        return "# 评测报告\n\n暂无评测数据。"
    
    # 收集所有评测项
    all_evals = []
    all_analyses = []
    for sess in results:
        for ev in sess.get('evaluations', []):
            ev['session_id'] = sess['session_id']
            all_evals.append(ev)
        for an in sess.get('low_score_analyses', []):
            an['session_id'] = sess['session_id']
            all_analyses.append(an)
    
    if not all_evals:
        return "# 评测报告\n\n暂无评测数据。"
    
    # 计算统计
    avg_scores = [e.get('avg_score', 3) for e in all_evals]
    overall_avg = sum(avg_scores) / len(avg_scores)
    
    # 按维度统计
    dim_scores = {}
    for ev in all_evals:
        for dim, score in ev.get('scores', {}).items():
            if dim not in dim_scores:
                dim_scores[dim] = []
            dim_scores[dim].append(score)
    
    dim_averages = {d: sum(s)/len(s) for d, s in dim_scores.items()}
    
    # 生成报告
    lines = []
    lines.append("# 对话评测报告\n")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**评测会话数**: {len(results)}")
    lines.append(f"**评测回复数**: {len(all_evals)}")
    lines.append(f"**低分警示数**: {len(all_analyses)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 总体概览
    lines.append("## 📊 总体概览\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 综合平均分 | {overall_avg:.2f} |")
    perfect_count = sum(1 for s in avg_scores if s >= 4.5)
    lines.append(f"| 优秀率 (≥4.5分) | {perfect_count/len(avg_scores)*100:.1f}% |")
    low_count = sum(1 for s in avg_scores if s <= 3)
    lines.append(f"| 低分率 (≤3分) | {low_count/len(avg_scores)*100:.1f}% |")
    lines.append("")
    
    # 维度得分
    lines.append("### 维度得分分布\n")
    lines.append("| 维度 | 平均分 | 评价 |")
    lines.append("|------|--------|------|")
    for dim, avg in sorted(dim_averages.items(), key=lambda x: x[1]):
        status = "✅ 良好" if avg >= 4 else ("➖ 一般" if avg >= 3 else "⚠️ 待改进")
        lines.append(f"| {dim} | {avg:.2f} | {status} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 会话详情
    lines.append("## 📋 会话详情\n")
    
    for sess in results:
        session_id = sess.get('session_id', 'unknown')
        evals = sess.get('evaluations', [])
        analyses = sess.get('low_score_analyses', [])
        
        if evals:
            sess_avg = sum(e.get('avg_score', 3) for e in evals) / len(evals)
        else:
            sess_avg = 0
        
        lines.append(f"### Session: {session_id}\n")
        lines.append(f"**综合得分**: {sess_avg:.2f} | **回复数**: {len(evals)} | **低分项**: {len(analyses)}")
        lines.append("")
        
        for ev in evals:
            turn_idx = ev.get('turn_index', 0)
            avg_score = ev.get('avg_score', 3)
            scores = ev.get('scores', {})
            analysis = ev.get('overall_analysis', '')
            
            # 分数状态
            status = "🟢" if avg_score >= 4 else ("🟡" if avg_score >= 3 else "🔴")
            
            lines.append(f"#### Turn {turn_idx} {status} {avg_score:.1f}分\n")
            
            # 各维度分数
            scores_str = " | ".join([f"{k[:10]}: {v}" for k, v in scores.items()])
            lines.append(f"**维度分数**: {scores_str}")
            lines.append("")
            lines.append(f"**综合分析**: {analysis}")
            lines.append("")
            
            # 回复片段
            response = ev.get('target_response', '')
            if len(response) > 150:
                response = response[:150] + "..."
            lines.append(f"> {response}")
            lines.append("")
            
            # 该 Turn 的深度分析
            turn_analyses = [a for a in analyses if a.get('turn_index') == turn_idx]
            if turn_analyses:
                for an in turn_analyses:
                    lines.append("**🔍 深度分析:**")
                    if an.get('root_cause'):
                        lines.append(f"- 根因: {an['root_cause']}")
                    if an.get('traced_node_title'):
                        lines.append(f"- 溯源节点: {an['traced_node_title']}")
                    if an.get('modification_suggestion'):
                        suggestion = an['modification_suggestion'][:200]
                        lines.append(f"- 修改建议: {suggestion}...")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def generate_json_report(results: List[Dict], rubrics: List[Dict] = None) -> Dict:
    """生成 JSON 格式的评测报告"""
    from datetime import datetime
    
    # 收集统计
    all_evals = []
    all_analyses = []
    for sess in results:
        all_evals.extend(sess.get('evaluations', []))
        all_analyses.extend(sess.get('low_score_analyses', []))
    
    if all_evals:
        avg_scores = [e.get('avg_score', 3) for e in all_evals]
        overall_avg = sum(avg_scores) / len(avg_scores)
    else:
        overall_avg = 0
    
    # 按维度统计
    dim_scores = {}
    for ev in all_evals:
        for dim, score in ev.get('scores', {}).items():
            if dim not in dim_scores:
                dim_scores[dim] = []
            dim_scores[dim].append(score)
    
    dim_averages = {d: round(sum(s)/len(s), 2) for d, s in dim_scores.items()}
    
    return {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "session_count": len(results),
            "turn_count": len(all_evals),
            "low_score_count": len(all_analyses)
        },
        "summary": {
            "avg_score": round(overall_avg, 2),
            "dimension_averages": dim_averages
        },
        "sessions": results,
        "low_score_analyses": all_analyses
    }


if __name__ == "__main__":
    # 测试代码
    try:
        with open('test_cases1.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)
        with open('rubric.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        workflow = None
        try:
            workflow = DifyWorkflowParser(workflow_path='Dify.yml')
            print("✅ 工作流已加载")
        except:
            print("⚠️ 未找到工作流文件")
        
        print("🚀 Starting Unified Evaluation...")
        results = run_log_evaluation(
            logs[:1],
            config['rubrics'],
            workflow_parser=workflow,
            low_score_threshold=config.get('low_score_threshold', 3)
        )
        
        print("\n=== 评测结果 ===")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")