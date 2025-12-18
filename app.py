import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import base64
from pathlib import Path
from run_eval import run_log_evaluation, generate_session_summary, generate_markdown_report, generate_json_report
from agent import RealAgent
from prompt_optimizer import OmegaPromptForge
from workflow_parser import DifyWorkflowParser
from database import get_database

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(
    page_title="AI 对话评测系统 Pro", 
    layout="wide", 
    page_icon="⚖️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 初始化状态
# ==========================================
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'dashboard'
if 'workflow_parser' not in st.session_state:
    st.session_state['workflow_parser'] = None

# ==========================================
# Logo 加载
# ==========================================
@st.cache_data
def get_logo_base64():
    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

LOGO_BASE64 = get_logo_base64()

# ==========================================
# CSS 样式
# ==========================================
def get_css():
    if st.session_state['theme'] == 'dark':
        theme_vars = """
        --bg-card: rgba(255, 255, 255, 0.03);
        --text-primary: rgba(255, 255, 255, 0.95);
        --text-secondary: rgba(255, 255, 255, 0.6);
        --text-muted: rgba(255, 255, 255, 0.4);
        --border-color: rgba(255, 255, 255, 0.08);
        --glow-color: rgba(102, 126, 234, 0.4);
        --danger-bg: rgba(244, 67, 54, 0.1);
        --danger-border: rgba(244, 67, 54, 0.3);
        """
    else:
        theme_vars = """
        --bg-card: rgba(0, 0, 0, 0.02);
        --text-primary: rgba(0, 0, 0, 0.87);
        --text-secondary: rgba(0, 0, 0, 0.6);
        --text-muted: rgba(0, 0, 0, 0.38);
        --border-color: rgba(0, 0, 0, 0.08);
        --glow-color: rgba(102, 126, 234, 0.3);
        --danger-bg: rgba(244, 67, 54, 0.05);
        --danger-border: rgba(244, 67, 54, 0.2);
        """
    
    return """
<style>
:root {
    """ + theme_vars + """
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.logo-container {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1rem 0.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.logo-container img {
    width: 40px;
    height: 40px;
    border-radius: 8px;
}

.logo-text {
    font-size: 1rem;
    font-weight: 700;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.logo-version {
    font-size: 0.7rem;
    color: var(--text-muted);
}

.main-title {
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.8rem;
    font-weight: 800;
    margin-bottom: 0.25rem;
}

.sub-title {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    transition: all 0.3s ease;
}

.metric-card:hover {
    border-color: var(--glow-color);
    transform: translateY(-2px);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-label {
    color: var(--text-secondary);
    font-size: 0.85rem;
    margin-top: 0.25rem;
}

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--glow-color), transparent);
    margin: 1.5rem 0;
}

.low-score-card {
    background: var(--danger-bg);
    border: 1px solid var(--danger-border);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.low-score-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

.analysis-section {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 0.75rem;
    margin-top: 0.5rem;
}

.analysis-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
}

.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
}

.badge-success {
    background: linear-gradient(135deg, #00c853, #b2ff59);
    color: #1a1a2e;
}

.badge-warning {
    background: linear-gradient(135deg, #ff9800, #ffc107);
    color: #1a1a2e;
}

.badge-danger {
    background: linear-gradient(135deg, #f44336, #ff5722);
    color: white;
}

.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

.workflow-status {
    padding: 0.5rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-top: 0.5rem;
}

.workflow-loaded {
    background: rgba(76, 175, 80, 0.1);
    border: 1px solid rgba(76, 175, 80, 0.3);
    color: #4caf50;
}

.workflow-not-loaded {
    background: rgba(255, 152, 0, 0.1);
    border: 1px solid rgba(255, 152, 0, 0.3);
    color: #ff9800;
}
</style>
"""

st.markdown(get_css(), unsafe_allow_html=True)

# ==========================================
# 工具函数
# ==========================================
def load_json_file(uploaded_file):
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            st.error(f"文件解析错误: {e}")
            return None
    return None

def load_json_path(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def create_radar_chart(dimension_scores: dict, title="维度得分雷达图"):
    categories = list(dimension_scores.keys())
    values = list(dimension_scores.values())
    if not categories:
        return None
    values.append(values[0])
    categories.append(categories[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.3)',
        line=dict(color='#667eea', width=2),
        name='得分'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5]),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=False,
        title=dict(text=title, font=dict(size=14)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=60, t=50, b=30),
        height=350
    )
    return fig

def export_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def export_to_json(df):
    return df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')

def get_score_badge(score):
    if score >= 4:
        return "badge-success", "优秀"
    elif score >= 3:
        return "badge-warning", "一般"
    else:
        return "badge-danger", "待改进"

# ==========================================
# 侧边栏
# ==========================================
with st.sidebar:
    # Logo
    if LOGO_BASE64:
        st.markdown(f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{LOGO_BASE64}" alt="Logo"/>
            <div>
                <div class="logo-text">AI 对话评测系统</div>
                <div class="logo-version">Pro v2.0</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="logo-container">
            <div style="font-size: 1.8rem;">⚖️</div>
            <div>
                <div class="logo-text">AI 对话评测系统</div>
                <div class="logo-version">Pro v2.0</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 导航
    st.caption("主要功能")
    
    if st.button("📊 工作台", use_container_width=True, 
                 type="primary" if st.session_state['current_page'] == 'dashboard' else "secondary"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    if st.button("📜 日志回放", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'logs' else "secondary"):
        st.session_state['current_page'] = 'logs'
        st.rerun()
    
    if st.button("🚀 智能评测", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'eval' else "secondary"):
        st.session_state['current_page'] = 'eval'
        st.rerun()
    
    if st.button("🔍 低分分析", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'analysis' else "secondary"):
        st.session_state['current_page'] = 'analysis'
        st.rerun()
    
    if st.button("📚 历史评测", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'history' else "secondary"):
        st.session_state['current_page'] = 'history'
        st.rerun()
    
    st.caption("系统设置")
    
    if st.button("🛠️ 评分标准配置", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'rubric' else "secondary"):
        st.session_state['current_page'] = 'rubric'
        st.rerun()
    
    if st.button("🎨 Prompt 工坊", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'prompt' else "secondary"):
        st.session_state['current_page'] = 'prompt'
        st.rerun()
    
    st.divider()
    
    # 数据源配置
    with st.expander("📁 数据源配置", expanded=False):
        st.caption("日志文件")
        log_file = st.text_input("日志路径", "test_cases1.json", label_visibility="collapsed")
        
        st.caption("评分标准")
        rubric_file = st.text_input("标准路径", "rubric.json", label_visibility="collapsed")
        
        st.caption("工作流文件 (可选)")
        workflow_file = st.text_input("工作流路径", "Dify.yml", label_visibility="collapsed")
        
        if st.button("📂 加载全部", use_container_width=True):
            st.session_state['logs_data'] = load_json_path(log_file)
            st.session_state['rubric_data'] = load_json_path(rubric_file)
            
            # 加载工作流
            try:
                st.session_state['workflow_parser'] = DifyWorkflowParser(workflow_path=workflow_file)
                st.success("✅ 工作流已加载")
            except Exception as e:
                st.session_state['workflow_parser'] = None
                st.warning(f"⚠️ 工作流加载失败: {e}")
            
            st.rerun()
    
    # 工作流状态
    if st.session_state.get('workflow_parser'):
        summary = st.session_state['workflow_parser'].get_workflow_summary()
        st.markdown(f"""
        <div class="workflow-status workflow-loaded">
            ✅ 工作流: {summary['name'][:20]}...<br/>
            📍 {summary['llm_nodes_count']} 个 LLM 节点
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="workflow-status workflow-not-loaded">
            ⚠️ 未加载工作流<br/>
            低分分析将不含节点溯源
        </div>
        """, unsafe_allow_html=True)
    
    # 主题切换
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        theme_label = "深色" if st.session_state['theme'] == 'dark' else "浅色"
        st.caption(f"当前主题: {theme_label}")
    with col2:
        theme_icon = "🌙" if st.session_state['theme'] == 'dark' else "☀️"
        if st.button(theme_icon):
            st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'
            st.rerun()

# ==========================================
# 数据加载
# ==========================================
if 'logs_data' not in st.session_state:
    st.session_state['logs_data'] = load_json_path("test_cases1.json")
if 'rubric_data' not in st.session_state:
    st.session_state['rubric_data'] = load_json_path("rubric.json")

logs_data = st.session_state.get('logs_data')
rubric_data = st.session_state.get('rubric_data')
workflow_parser = st.session_state.get('workflow_parser')

# ==========================================
# 页面路由
# ==========================================
current_page = st.session_state['current_page']

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
if current_page == 'dashboard':
    st.markdown('<h1 class="main-title">📊 工作台</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">欢迎使用 AI 对话评测系统 v2.0 - 支持工作流溯源</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    session_count = len(logs_data) if logs_data else 0
    rubric_count = len(rubric_data.get('rubrics', [])) if rubric_data else 0
    eval_count = len(st.session_state.get('eval_results', []))
    low_score_count = sum(len(r.get('low_score_analyses', [])) for r in st.session_state.get('eval_results', []))
    
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{session_count}</div><div class="metric-label">已加载会话</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{rubric_count}</div><div class="metric-label">评分维度</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{eval_count}</div><div class="metric-label">已完成评测</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{low_score_count}</div><div class="metric-label">低分警示</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 快捷操作
    st.markdown("### ⚡ 快捷操作")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🚀 开始评测", use_container_width=True, type="primary"):
            st.session_state['current_page'] = 'eval'
            st.rerun()
    with c2:
        if st.button("🔍 查看低分分析", use_container_width=True):
            st.session_state['current_page'] = 'analysis'
            st.rerun()
    with c3:
        if st.button("📜 查看日志", use_container_width=True):
            st.session_state['current_page'] = 'logs'
            st.rerun()
    with c4:
        if st.button("🎨 Prompt 工坊", use_container_width=True):
            st.session_state['current_page'] = 'prompt'
            st.rerun()
    
    # 状态
    if logs_data and rubric_data:
        if workflow_parser:
            st.success("✅ 数据和工作流已就绪，可以开始评测 (含节点溯源)")
        else:
            st.info("ℹ️ 数据已就绪。若需节点溯源，请加载工作流 YML")
    else:
        st.warning("⚠️ 请先在侧边栏加载数据")

# -----------------------------------------------------------------------------
# 日志回放 (增强版：三栏布局 + 评测结果对比)
# -----------------------------------------------------------------------------
elif current_page == 'logs':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">📜 日志回放</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">对话内容与评测结果对比展示</p>', unsafe_allow_html=True)
    
    if not logs_data:
        st.warning("⚠️ 请先加载日志数据")
        st.stop()
    
    # 获取当前会话的评测结果
    eval_results = st.session_state.get('eval_results', [])
    has_eval = len(eval_results) > 0
    
    # 三栏布局：会话列表 | 对话内容 | 评测结果
    col_list, col_chat, col_eval = st.columns([1, 2.5, 1.5])
    
    with col_list:
        st.markdown("#### 会话列表")
        if 'selected_session' not in st.session_state:
            st.session_state['selected_session'] = 0
        
        for i, session in enumerate(logs_data):
            sess_id = session.get('session_id', f'Session {i}')
            # 检查该会话是否有评测结果
            has_sess_eval = any(r['session_id'] == sess_id for r in eval_results)
            icon = "✅" if has_sess_eval else "📁"
            if st.button(f"{icon} {sess_id}", key=f"sess_{i}", use_container_width=True,
                        type="primary" if i == st.session_state['selected_session'] else "secondary"):
                st.session_state['selected_session'] = i
                st.session_state['selected_turn'] = None  # 重置选中的 turn
                st.rerun()
    
    # 获取当前选中的会话
    session = logs_data[st.session_state['selected_session']]
    session_id = session.get('session_id', 'unknown')
    
    # 获取该会话的评测结果
    session_eval = None
    for r in eval_results:
        if r['session_id'] == session_id:
            session_eval = r
            break
    
    with col_chat:
        st.markdown(f"#### 会话: {session_id}")
        st.caption(f"领域: {session.get('domain', 'general')}")
        
        messages = session.get('messages', [])
        assistant_turn_idx = 0  # 用于追踪 assistant 消息的索引
        
        for msg_idx, msg in enumerate(messages):
            is_assistant = msg['role'] == 'assistant'
            
            # 获取该 turn 的评测结果（新结构：每条回复只有一个评测记录）
            turn_eval = None
            if is_assistant and session_eval:
                for ev in session_eval.get('evaluations', []):
                    if ev.get('turn_index') == msg_idx:
                        turn_eval = ev
                        break
            
            # 渲染消息
            with st.chat_message(msg['role']):
                # 如果是 assistant 且有评分，添加点击功能
                if is_assistant and turn_eval:
                    # 使用综合分（combined_score）而非平均分
                    combined = turn_eval.get('combined_score', turn_eval.get('avg_score', 3))
                    min_s = turn_eval.get('min_score', 3)
                    # 颜色根据综合分和最低分综合判断
                    if combined <= 2 or min_s <= 1:
                        score_color = "🔴"
                    elif combined <= 3 or min_s <= 2:
                        score_color = "🟡"
                    else:
                        score_color = "🟢"
                    
                    # 消息头部显示综合分
                    col_msg, col_score = st.columns([4, 1])
                    with col_msg:
                        st.write(msg['content'])
                    with col_score:
                        if st.button(f"{score_color} {combined:.1f}", key=f"turn_{msg_idx}", help=f"综合分 {combined:.1f} | 最低分 {min_s}"):
                            st.session_state['selected_turn'] = msg_idx
                            st.rerun()
                else:
                    st.write(msg['content'])
            
            if is_assistant:
                assistant_turn_idx += 1
    
    with col_eval:
        st.markdown("#### 评测结果")
        
        if not has_eval:
            st.info("暂无评测数据\n\n请先执行智能评测")
            if st.button("🚀 去评测", use_container_width=True):
                st.session_state['current_page'] = 'eval'
                st.rerun()
        elif not session_eval:
            st.warning("当前会话暂无评测结果")
        else:
            # 显示会话综合评分（使用 combined_score）
            evals = session_eval.get('evaluations', [])
            if evals:
                avg = sum(e.get('combined_score', e.get('avg_score', 3)) for e in evals) / len(evals)
                st.metric("会话综合分", f"{avg:.2f}")
            
            # 显示选中 turn 的详细评分，或显示概览
            selected_turn = st.session_state.get('selected_turn')
            
            if selected_turn is not None:
                st.markdown(f"##### Turn {selected_turn} 详情")
                # 找到该 turn 的评测记录
                turn_eval = None
                for e in evals:
                    if e.get('turn_index') == selected_turn:
                        turn_eval = e
                        break
                
                if turn_eval:
                    # 显示综合分和最低分
                    combined = turn_eval.get('combined_score', turn_eval.get('avg_score', 3))
                    min_s = turn_eval.get('min_score', 3)
                    col_c, col_m = st.columns(2)
                    with col_c:
                        st.metric("综合分", f"{combined:.1f}")
                    with col_m:
                        st.metric("最低分", f"{min_s}")
                    
                    # 显示各维度分数
                    scores = turn_eval.get('scores', {})
                    for dim, score in scores.items():
                        icon = "✅" if score >= 4 else ("⚠️" if score <= 2 else "➖")
                        st.markdown(f"**{dim[:25]}** {icon}")
                        st.progress(score / 5)
                    
                    # 综合分析
                    analysis = turn_eval.get('overall_analysis', '')
                    if analysis:
                        st.markdown("---")
                        st.markdown(f"**综合分析**: {analysis}")
                
                # 低分深度分析
                analyses = session_eval.get('low_score_analyses', [])
                turn_analyses = [a for a in analyses if a.get('turn_index') == selected_turn]
                if turn_analyses:
                    st.markdown("---")
                    st.markdown("##### 🔍 深度分析")
                    for an in turn_analyses:
                        if an.get('root_cause'):
                            st.info(f"**根因**: {an['root_cause']}")
                        if an.get('traced_node_title'):
                            st.markdown(f"**溯源节点**: `{an['traced_node_title']}`")
                        if an.get('modification_suggestion'):
                            st.success(f"**修改建议**: {an['modification_suggestion'][:300]}")
                
                if st.button("返回概览", use_container_width=True):
                    st.session_state['selected_turn'] = None
                    st.rerun()
            else:
                # 显示所有维度的平均分概览
                st.markdown("##### 维度概览")
                dim_scores = {}
                for ev in evals:
                    for dim, score in ev.get('scores', {}).items():
                        if dim not in dim_scores:
                            dim_scores[dim] = []
                        dim_scores[dim].append(score)
                
                for dim, scores in dim_scores.items():
                    avg = sum(scores) / len(scores)
                    icon = "✅" if avg >= 4 else ("⚠️" if avg < 3 else "➖")
                    st.markdown(f"{icon} **{dim[:20]}**: {avg:.1f}")
                
                # 低分项数量提示
                low_count = len(session_eval.get('low_score_analyses', []))
                if low_count > 0:
                    st.markdown("---")
                    st.warning(f"发现 {low_count} 个低分回复需深度分析")

# -----------------------------------------------------------------------------
# 智能评测
# -----------------------------------------------------------------------------
elif current_page == 'eval':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🚀 智能评测</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">两阶段评测：快速打分 + 低分深度分析</p>', unsafe_allow_html=True)
    
    if not logs_data or not rubric_data:
        st.warning("⚠️ 请先加载数据")
        st.stop()
    
    # 配置选项
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if workflow_parser:
            st.success("✅ 工作流已加载，低分项将自动进行节点溯源")
        else:
            st.info("ℹ️ 未加载工作流，低分项将不含节点溯源")
    with col2:
        low_threshold = st.selectbox("低分阈值", [1, 2, 3, 4], index=2, help="综合分 ≤ 该值触发深度分析")
    with col3:
        start_eval = st.button("▶️ 开始评测", type="primary", use_container_width=True)
    
    if start_eval:
        progress = st.progress(0)
        status = st.empty()
        
        def update_progress(current, total, desc):
            progress.progress(min(current / total, 1.0))
            status.text(f"评测中: {desc}")
        
        try:
            results = run_log_evaluation(
                logs_data, 
                rubric_data['rubrics'],
                workflow_parser=workflow_parser,
                low_score_threshold=low_threshold,
                progress_callback=update_progress
            )
            st.session_state['eval_results'] = results
            progress.progress(1.0)
            
            # 统计低分数量
            low_count = sum(len(r.get('low_score_analyses', [])) for r in results)
            
            # 保存到数据库
            try:
                db = get_database()
                batch_id = db.save_evaluation_results(
                    results,
                    workflow_file=st.session_state.get('workflow_file', ''),
                    rubric_file=st.session_state.get('rubric_file', 'rubric.json'),
                    log_file=st.session_state.get('log_file', 'test_cases1.json')
                )
                status.success(f"✅ 评测完成！发现 {low_count} 个低分项 | 已保存到数据库 (批次 #{batch_id})")
            except Exception as db_err:
                status.success(f"✅ 评测完成！发现 {low_count} 个低分项 (数据库保存失败: {str(db_err)[:30]})")
            
        except Exception as e:
            status.error(f"❌ 评测失败: {str(e)}")
    
    # 显示结果
    if 'eval_results' in st.session_state and st.session_state['eval_results']:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 新数据结构：使用 combined_score（综合分）
        all_evals = []
        dim_scores_agg = {}
        
        for sess in st.session_state['eval_results']:
            for item in sess['evaluations']:
                combined = item.get('combined_score', item.get('avg_score', 3))
                min_s = item.get('min_score', 3)
                all_evals.append({
                    "Session": sess['session_id'],
                    "Turn": item['turn_index'],
                    "综合分": combined,
                    "最低分": min_s,
                    "分析": item.get('overall_analysis', '')[:60] + "..."
                })
                # 收集各维度分数
                for dim, score in item.get('scores', {}).items():
                    if dim not in dim_scores_agg:
                        dim_scores_agg[dim] = []
                    dim_scores_agg[dim].append(score)
        
        df = pd.DataFrame(all_evals)
        
        if not df.empty:
            col1, col2, col3, col4 = st.columns(4)
            avg_combined = df['综合分'].mean()
            with col1:
                st.metric("综合平均分", f"{avg_combined:.2f}")
            with col2:
                excellent = (df['综合分'] >= 4).sum()
                st.metric("优秀率 (≥4分)", f"{excellent/len(df)*100:.1f}%")
            with col3:
                low = (df['综合分'] <= 3).sum()
                st.metric("低分率 (≤3分)", f"{low/len(df)*100:.1f}%")
            with col4:
                low_count = sum(len(r.get('low_score_analyses', [])) for r in st.session_state['eval_results'])
                st.metric("深度分析数", low_count)
            
            # 雷达图（使用各维度平均分）
            dim_avg = {d: sum(s)/len(s) for d, s in dim_scores_agg.items()}
            chart = create_radar_chart(dim_avg)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # 数据表
            st.dataframe(df, use_container_width=True)
            
            # 导出功能
            st.markdown("#### 📥 导出报告")
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 1.5, 2])
            
            with col1:
                st.download_button("CSV", export_to_csv(df), "eval_results.csv", "text/csv", use_container_width=True)
            with col2:
                st.download_button("JSON", export_to_json(df), "eval_results.json", "application/json", use_container_width=True)
            with col3:
                # Markdown 报告
                md_report = generate_markdown_report(st.session_state['eval_results'])
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                st.download_button(
                    "📄 Markdown 报告",
                    md_report.encode('utf-8'),
                    f"eval_report_{timestamp}.md",
                    "text/markdown",
                    use_container_width=True
                )
            with col4:
                # JSON 完整报告
                json_report = generate_json_report(st.session_state['eval_results'])
                st.download_button(
                    "📊 JSON 完整报告",
                    json.dumps(json_report, ensure_ascii=False, indent=2).encode('utf-8'),
                    f"eval_report_{timestamp}.json",
                    "application/json",
                    use_container_width=True
                )
            with col5:
                if sum(len(r.get('low_score_analyses', [])) for r in st.session_state['eval_results']) > 0:
                    if st.button("🔍 查看低分分析详情", use_container_width=True):
                        st.session_state['current_page'] = 'analysis'
                        st.rerun()

# -----------------------------------------------------------------------------
# 低分分析面板 (更新适配合并评测结构)
# -----------------------------------------------------------------------------
elif current_page == 'analysis':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🔍 低分分析</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">根因分析 + 节点溯源 + 修改建议</p>', unsafe_allow_html=True)
    
    if 'eval_results' not in st.session_state or not st.session_state['eval_results']:
        st.warning("⚠️ 请先进行评测")
        st.stop()
    
    # 收集所有低分分析
    all_analyses = []
    for sess in st.session_state['eval_results']:
        for analysis in sess.get('low_score_analyses', []):
            analysis['session_id'] = sess['session_id']
            all_analyses.append(analysis)
    
    if not all_analyses:
        st.info("🎉 没有发现低分回复！所有回复质量良好。")
        st.stop()
    
    st.markdown(f"### 🚩 共发现 {len(all_analyses)} 个低分回复需要关注")
    
    # 展示每个低分项
    for i, analysis in enumerate(all_analyses):
        avg_score = analysis.get('avg_score', 0)
        scores = analysis.get('scores', {})
        
        # 标题：会话+Turn+平均分
        with st.expander(f"🔴 [{analysis['session_id']}] Turn {analysis['turn_index']} - 综合分 {avg_score:.1f}", expanded=i==0):
            
            # 问题回复
            st.markdown("**📝 问题回复:**")
            response = analysis.get('target_response', '')
            st.code(response[:500] + ("..." if len(response) > 500 else ""), language=None)
            
            # 各维度分数
            st.markdown("**📊 各维度得分:**")
            scores_text = " | ".join([f"{k[:15]}: {v}分" for k, v in scores.items()])
            st.caption(scores_text)
            
            # 综合分析
            st.markdown("**💭 综合分析:**")
            st.info(analysis.get('overall_analysis', '无'))
            
            st.markdown("---")
            
            # 根因分析
            if analysis.get('root_cause'):
                st.markdown("**🔍 根因分析:**")
                st.warning(analysis['root_cause'])
            
            # 节点溯源
            if analysis.get('traced_node_title'):
                st.markdown("**📍 溯源节点:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**节点名称:** `{analysis['traced_node_title']}`")
                with col2:
                    st.markdown(f"**节点 ID:** `{analysis.get('traced_node_id', 'N/A')}`")
            
            # Prompt 问题
            if analysis.get('prompt_issue'):
                st.markdown("**⚠️ Prompt 问题:**")
                st.error(analysis['prompt_issue'])
            
            # 修改建议
            if analysis.get('modification_suggestion'):
                st.markdown("**✏️ 修改建议:**")
                st.success(analysis['modification_suggestion'])

# -----------------------------------------------------------------------------
# 评分标准配置
# -----------------------------------------------------------------------------
elif current_page == 'rubric':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🛠️ 评分标准配置</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">五档评分标准 + 低分检查清单</p>', unsafe_allow_html=True)
    
    if not rubric_data:
        st.warning("⚠️ 请先加载评分标准")
        st.stop()
    
    # 版本和阈值
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📋 版本: {rubric_data.get('version', '1.0')}")
    with col2:
        st.info(f"🎯 低分阈值: ≤{rubric_data.get('low_score_threshold', 3)} 分触发深度分析")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 维度概览
    st.markdown("#### 当前维度")
    for rubric in rubric_data.get('rubrics', []):
        with st.expander(f"📊 {rubric['name']}"):
            st.markdown(f"**描述:** {rubric['description']}")
            
            st.markdown("**评分标准:**")
            for level, desc in rubric.get('criteria', {}).items():
                color = "🟢" if int(level) >= 4 else ("🟡" if int(level) >= 3 else "🔴")
                st.markdown(f"{color} **{level}分:** {desc}")
            
            if rubric.get('low_score_checklist'):
                st.markdown("**低分检查清单:**")
                for item in rubric['low_score_checklist']:
                    st.markdown(f"- {item}")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 编辑器
    st.markdown("#### JSON 编辑器")
    current_str = json.dumps(rubric_data, indent=2, ensure_ascii=False)
    new_str = st.text_area("编辑", current_str, height=400, label_visibility="collapsed")
    
    if st.button("💾 保存配置", type="primary"):
        try:
            new_json = json.loads(new_str)
            with open('rubric.json', 'w', encoding='utf-8') as f:
                json.dump(new_json, f, indent=2, ensure_ascii=False)
            st.session_state['rubric_data'] = new_json
            st.success("✅ 已保存")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 错误: {e}")

# -----------------------------------------------------------------------------
# Prompt 工坊
# -----------------------------------------------------------------------------
elif current_page == 'prompt':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🎨 Prompt 工坊</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">使用 ΩPromptForge 生成或优化 Prompts</p>', unsafe_allow_html=True)
    
    # 初始化
    if 'prompt_output' not in st.session_state:
        st.session_state['prompt_output'] = ""
    
    # 布局
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.markdown("#### 📥 输入")
        user_input = st.text_area(
            "输入主题或原始 Prompt",
            height=300,
            placeholder="例如：帮我生成一个职业规划助手的 Prompt...",
            key="prompt_input",
            label_visibility="collapsed"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            generate_btn = st.button("🪄 生成", type="primary", use_container_width=True)
        with col2:
            optimize_btn = st.button("✨ 优化", use_container_width=True)
        with col3:
            clear_btn = st.button("🗑️ 清空", use_container_width=True)
        
        if clear_btn:
            st.session_state['prompt_output'] = ""
            st.rerun()
    
    with right_col:
        st.markdown("#### 📤 输出")
        output_area = st.empty()
        
        # 处理生成/优化
        if generate_btn or optimize_btn:
            if not user_input.strip():
                st.warning("请先输入内容")
            else:
                with st.spinner("正在处理..."):
                    try:
                        agent = RealAgent()
                        optimizer = OmegaPromptForge(agent)
                        
                        if generate_btn:
                            stream = optimizer.generate(user_input)
                        else:
                            stream = optimizer.optimize(user_input)
                        
                        full_response = ""
                        for chunk in stream:
                            full_response += chunk
                            output_area.code(full_response, language="markdown")
                        
                        st.session_state['prompt_output'] = full_response
                        st.success("✅ 完成！")
                        
                    except Exception as e:
                        st.error(f"❌ 失败: {str(e)}")
        
        # 显示已有输出
        elif st.session_state['prompt_output']:
            output_area.code(st.session_state['prompt_output'], language="markdown")

# ==========================================
# 历史评测页面
# ==========================================
elif current_page == 'history':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">📚 历史评测</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">查看和管理历史评测记录</p>', unsafe_allow_html=True)
    
    try:
        db = get_database()
        batches = db.get_all_batches()
        stats = db.get_statistics()
        
        # 统计卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("评测批次", stats['batch_count'])
        with col2:
            st.metric("评测总数", stats['eval_count'])
        with col3:
            st.metric("低分分析", stats['low_score_count'])
        with col4:
            st.metric("历史平均分", stats['avg_score'])
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        if not batches:
            st.info("📭 暂无历史评测记录\n\n请先进行智能评测")
        else:
            # 批次列表
            st.markdown("### 📋 评测记录列表")
            
            for batch in batches:
                batch_id = batch['id']
                created = batch['created_at'][:19] if batch['created_at'] else '未知'
                avg_score = batch['avg_score'] or 0
                
                # 评分颜色
                if avg_score >= 4:
                    score_badge = f'<span style="background:#22c55e;color:white;padding:2px 8px;border-radius:10px;">{avg_score:.1f}</span>'
                elif avg_score >= 3:
                    score_badge = f'<span style="background:#eab308;color:white;padding:2px 8px;border-radius:10px;">{avg_score:.1f}</span>'
                else:
                    score_badge = f'<span style="background:#ef4444;color:white;padding:2px 8px;border-radius:10px;">{avg_score:.1f}</span>'
                
                with st.expander(f"📁 批次 #{batch_id} | {created} | {score_badge}", expanded=False):
                    # 基本信息
                    col_info, col_actions = st.columns([3, 1])
                    
                    with col_info:
                        st.markdown(f"""
                        | 项目 | 数值 |
                        |------|------|
                        | **会话数** | {batch['session_count']} |
                        | **回复数** | {batch['turn_count']} |
                        | **低分项** | {batch['low_score_count']} |
                        | **综合分** | {batch['avg_score']:.2f} |
                        """)
                        
                        # 文件信息
                        st.markdown("**📂 关联文件**")
                        log_file = batch.get('log_file', '未记录')
                        workflow_file = batch.get('workflow_file', '未记录')
                        rubric_file = batch.get('rubric_file', '未记录')
                        
                        st.caption(f"📝 日志: `{log_file}`")
                        st.caption(f"🔧 工作流: `{workflow_file}`")
                        st.caption(f"📏 评分标准: `{rubric_file}`")
                    
                    with col_actions:
                        # 查看详情
                        if st.button("📊 查看详情", key=f"view_{batch_id}", use_container_width=True):
                            st.session_state['view_batch_id'] = batch_id
                            st.rerun()
                        
                        # 删除按钮
                        if st.button("🗑️ 删除", key=f"del_{batch_id}", use_container_width=True, type="secondary"):
                            st.session_state['confirm_delete'] = batch_id
                            st.rerun()
                    
                    # 删除确认
                    if st.session_state.get('confirm_delete') == batch_id:
                        st.warning("⚠️ 确定要删除此批次吗？此操作不可撤销！")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ 确认删除", key=f"confirm_yes_{batch_id}", type="primary"):
                                if db.delete_batch(batch_id):
                                    st.session_state['confirm_delete'] = None
                                    st.success("已删除")
                                    st.rerun()
                                else:
                                    st.error("删除失败")
                        with col_no:
                            if st.button("❌ 取消", key=f"confirm_no_{batch_id}"):
                                st.session_state['confirm_delete'] = None
                                st.rerun()
                    
                    # 会话详情（如果选择了查看）
                    if st.session_state.get('view_batch_id') == batch_id:
                        st.markdown("---")
                        st.markdown("#### 📋 会话评测详情")
                        
                        batch_details = db.get_batch_details(batch_id)
                        sessions = batch_details.get('sessions', [])
                        
                        for sess in sessions:
                            sess_score = sess['avg_score'] or 0
                            sess_icon = "🟢" if sess_score >= 4 else ("🟡" if sess_score >= 3 else "🔴")
                            
                            with st.container():
                                st.markdown(f"**{sess_icon} {sess['session_id']}** - 综合分: {sess_score:.2f}")
                                
                                # 获取 Turn 详情
                                turns = db.get_session_turns(sess['id'])
                                if turns:
                                    turn_data = []
                                    for t in turns:
                                        turn_data.append({
                                            "Turn": t['turn_index'],
                                            "综合分": t['combined_score'],
                                            "最低分": t['min_score'],
                                            "分析": (t.get('overall_analysis') or '')[:50] + "..."
                                        })
                                    
                                    st.dataframe(pd.DataFrame(turn_data), use_container_width=True, hide_index=True)
                        
                        # 低分分析
                        low_analyses = db.get_low_score_analyses(batch_id)
                        if low_analyses:
                            st.markdown("#### 🔍 低分分析汇总")
                            for an in low_analyses:
                                st.markdown(f"**[{an['session_id']}] Turn {an['turn_index']}** - 综合分 {an['combined_score']:.1f}")
                                if an.get('root_cause'):
                                    st.info(f"根因: {an['root_cause'][:100]}...")
                                if an.get('traced_node_title'):
                                    st.caption(f"溯源节点: `{an['traced_node_title']}`")
    
    except Exception as e:
        st.error(f"数据库访问失败: {str(e)}")

# ==========================================
# 页脚
# ==========================================
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption("AI 对话评测系统 Pro v2.0 | 支持工作流节点溯源 | Powered by LLM-as-a-Judge")

