import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import base64
import time as time_module
from pathlib import Path
from run_eval import run_log_evaluation, generate_session_summary, generate_markdown_report, generate_json_report
from agent import RealAgent
from prompt_optimizer import OmegaPromptForge
from workflow_parser import DifyWorkflowParser
from database import get_database
from trace_store import TraceStore, init_db
from eval_dispatcher import run_evaluation_task  # 🆕 v0.8.0: 引入统一评测调度器 # 🆕 v0.3.0: Trace 追踪
from evaluator_store import EvaluatorStore  # 🆕 v1.0.0: 评估器存储
from evaluator_generator import EvaluatorGenerator  # 🆕 v1.0.0: 评估器生成器

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(
    page_title="KST Agent 评估系统 Pro", 
    layout="wide", 
    page_icon="🤖",
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
if 'demo_mode' not in st.session_state:
    st.session_state['demo_mode'] = {'active': False, 'step': 0}

# ==========================================
# 演示步骤定义
# ==========================================
DEMO_STEPS = [
    {"title": "👋 欢迎", "desc": "基于 LLM-as-a-Judge 的智能对话质量评测平台", "page": "dashboard"},
    {"title": "📊 工作台", "desc": "核心指标面板：会话数、评分维度、评测次数、低分警示", "page": "dashboard"},
    {"title": "📜 日志回放", "desc": "三栏布局 - 左侧会话列表 / 中间对话 / 右侧评测结果", "page": "logs"},
    {"title": "🚀 智能评测", "desc": "Phase1快速评分(1调用=6维度) + Phase2低分深度分析", "page": "eval"},
    {"title": "🔍 低分分析", "desc": "根因分析 + 工作流节点溯源 + Prompt优化建议", "page": "analysis"},
    {"title": "📚 历史记录", "desc": "SQLite持久化 - 批次查询/详情展开/删除管理", "page": "history"},
    {"title": "🎉 完成", "desc": "您已掌握核心功能！点击「完成」开始使用", "page": "dashboard"},
]

# ==========================================
# Logo 加载
# ==========================================
@st.cache_data
def get_logo_base64():
    logo_path = Path(__file__).parent / "assets/logo.png"
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
    font-size: 0.95rem;
    font-weight: 700;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    white-space: nowrap;
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

/* 透明演示横幅 */
.demo-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(26, 26, 46, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    padding: 12px 24px;
    z-index: 9999;
    border-top: 2px solid rgba(102, 126, 234, 0.6);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.demo-banner-content {
    display: flex;
    align-items: center;
    gap: 16px;
    flex: 1;
}

.demo-banner-step {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
}

.demo-banner-title {
    color: white;
    font-weight: 600;
    font-size: 1rem;
    margin: 0;
}

.demo-banner-desc {
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.85rem;
    margin: 0;
}

.demo-banner-progress {
    width: 120px;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    overflow: hidden;
}

.demo-banner-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 2px;
    transition: width 0.3s ease;
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
                <div class="logo-text">KST Agent 评估系统</div>
                <div class="logo-version">Pro v3.0</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="logo-container">
            <div style="font-size: 1.8rem;">🤖</div>
            <div>
                <div class="logo-text">KST Agent 评估系统</div>
                <div class="logo-version">Pro v3.0</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ==========================================
    # 🆕 v0.6.0: 简洁侧边栏导航 (4 入口)
    # ==========================================
    
    st.caption("导航")
    
    # 1. 首页看板 (含统计)
    if st.button("📊 首页看板", use_container_width=True, 
                 type="primary" if st.session_state['current_page'] == 'dashboard' else "secondary"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    # 2. 评测中心
    if st.button("🚀 评测中心", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'eval_center' else "secondary"):
        st.session_state['current_page'] = 'eval_center'
        st.rerun()
    
    # 🆕 3. Dify 管理
    if st.button("🔌 Dify 管理", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'dify_management' else "secondary"):
        st.session_state['current_page'] = 'dify_management'
        st.rerun()
    
    # 🆕 4. 评测管理
    if st.button("📋 评测管理", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'eval_dataset_management' else "secondary"):
        st.session_state['current_page'] = 'eval_dataset_management'
        st.rerun()
    
    # 🆕 5. 报告中心
    if st.button("📝 报告中心", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'report_center' else "secondary"):
        st.session_state['current_page'] = 'report_center'
        st.rerun()
    
    # 6. 数据浏览 (整合日志 + Trace + 历史 + 低分)
    if st.button("📜 数据浏览", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'data_explorer' else "secondary"):
        st.session_state['current_page'] = 'data_explorer'
        st.rerun()
    
    # 7. 系统设置 (整合 rubric + prompt)
    if st.button("⚙️ 系统设置", use_container_width=True,
                 type="primary" if st.session_state['current_page'] == 'settings' else "secondary"):
        st.session_state['current_page'] = 'settings'
        st.rerun()
    
    # 工作流状态指示
    if st.session_state.get('workflow_parser'):
        summary = st.session_state['workflow_parser'].get_workflow_summary()
        st.markdown(f"""
        <div class="workflow-status workflow-loaded">
            ✅ 工作流: {summary['name'][:20]}...<br/>
            📍 {summary['llm_nodes_count']} 个 LLM 节点
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
    
    # 演示教程入口
    st.divider()
    if st.button("🎬 演示教程", use_container_width=True, help="点击开始功能引导演示"):
        st.session_state['show_demo'] = True
        st.session_state['demo_step'] = 0
        st.session_state['current_page'] = 'dashboard'
        st.rerun()

# ==========================================
# 数据加载
# ==========================================
if 'logs_data' not in st.session_state:
    st.session_state['logs_data'] = load_json_path("data/test_cases1.json")
if 'rubric_data' not in st.session_state:
    st.session_state['rubric_data'] = load_json_path("config/rubric.json")

logs_data = st.session_state.get('logs_data')
rubric_data = st.session_state.get('rubric_data')
workflow_parser = st.session_state.get('workflow_parser')

# ==========================================
# 页面路由
# ==========================================
current_page = st.session_state['current_page']

# -----------------------------------------------------------------------------
# Dashboard - 🆕 v0.6.0: 首页看板 (模式切换 + 三图表)
# -----------------------------------------------------------------------------
if current_page == 'dashboard':
    st.markdown('<h1 class="main-title">📊 首页看板</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">AI 对话评测系统 Pro v3.0 | 评测数据可视化看板</p>', unsafe_allow_html=True)
    
    # 🆕 模式切换器
    if 'dashboard_mode' not in st.session_state:
        st.session_state['dashboard_mode'] = 'all'
    
    mode_col1, mode_col2, mode_col3, mode_col4 = st.columns(4)
    with mode_col1:
        if st.button("📊 全部", use_container_width=True, 
                     type="primary" if st.session_state['dashboard_mode'] == 'all' else "secondary"):
            st.session_state['dashboard_mode'] = 'all'
            st.rerun()
    with mode_col2:
        if st.button("💬 单轮对话", use_container_width=True,
                     type="primary" if st.session_state['dashboard_mode'] == 'single_turn' else "secondary"):
            st.session_state['dashboard_mode'] = 'single_turn'
            st.rerun()
    with mode_col3:
        if st.button("🔄 多轮对话", use_container_width=True,
                     type="primary" if st.session_state['dashboard_mode'] == 'multi_turn' else "secondary"):
            st.session_state['dashboard_mode'] = 'multi_turn'
            st.rerun()
    with mode_col4:
        if st.button("🤖 Agent", use_container_width=True,
                     type="primary" if st.session_state['dashboard_mode'] == 'agent' else "secondary"):
            st.session_state['dashboard_mode'] = 'agent'
            st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 获取当前模式的统计数据
    current_mode = st.session_state['dashboard_mode']
    mode_label = {'all': '全部', 'single_turn': '单轮对话', 'multi_turn': '多轮对话', 'agent': 'Agent'}[current_mode]
    
    stats = TraceStore.get_dashboard_stats(eval_type=current_mode if current_mode != 'all' else None)
    
    # 统计卡片
    st.markdown(f"### 📈 {mode_label}评测统计")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["trace_count"]}</div><div class="metric-label">评测记录</div></div>', unsafe_allow_html=True)
    with col2:
        avg_color = "🟢" if stats["avg_score"] >= 4 else ("🟡" if stats["avg_score"] >= 3 else "🔴")
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["avg_score"]}/5 {avg_color}</div><div class="metric-label">平均分</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["excellent_rate"]}%</div><div class="metric-label">优秀率(≥4分)</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["low_score_count"]}</div><div class="metric-label">低分项(<3分)</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 🆕 三个图表区域
    if stats['dimension_stats']:
        st.markdown("### 📊 数据可视化")
        # ===============================
        # 🆕 Dashboard Vis 2.0 (Plotly 高级图表)
        # ===============================
        
        # 获取用于可视化的高级数据 (Lightweight)
        eval_type_filter = current_mode if current_mode != 'all' else None
        viz_data = TraceStore.get_viz_data(eval_type=eval_type_filter, limit=500)
        
        if not viz_data:
            st.info("暂无足够数据生成高级图表。")
        else:
            viz_df = pd.DataFrame(viz_data)
            viz_df['created_at'] = pd.to_datetime(viz_df['created_at'])
            viz_df['date_hour'] = viz_df['created_at'].dt.strftime('%m-%d %H:00')
            
            # --- Row 1: 趋势与容量 (Combo Chart) ---
            st.markdown("##### 📈 评测趋势与质量波动 (Trend & Volume)")
            
            trend = viz_df.groupby('date_hour').agg(
                count=('trace_id', 'count'),
                avg_score=('avg_score', 'mean')
            ).reset_index().sort_values('date_hour')
            
            fig_combo = go.Figure()
            # Bar: Volume
            fig_combo.add_trace(go.Bar(
                x=trend['date_hour'], y=trend['count'], name='评测数量',
                marker_color='#3b82f6', opacity=0.3
            ))
            # Line: Score
            fig_combo.add_trace(go.Scatter(
                x=trend['date_hour'], y=trend['avg_score'], name='平均分',
                yaxis='y2', line=dict(color='#ef4444', width=3), mode='lines+markers'
            ))
            
            fig_combo.update_layout(
                yaxis=dict(title='评测数量'),
                yaxis2=dict(title='平均分', overlaying='y', side='right', range=[0, 5.2]),
                hovermode='x unified',
                height=300,
                margin=dict(l=20, r=20, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_combo, use_container_width=True)
            
            # --- Row 2: 关联分析 & 维度诊断 ---
            col_v1, col_v2 = st.columns(2)
            
            with col_v1:
                st.markdown("##### 🔬 性能与质量关联 (Performance)")
                # Prep scatter data
                scatter_data = []
                for d in viz_data:
                    metrics = d.get('metrics', {})
                    # 尝试不同字段
                    tokens = metrics.get('token_usage', {}).get('total_tokens', 0)
                    if tokens == 0:
                        # Fallback for simple structure
                        tokens = metrics.get('total_tokens', 0)
                        
                    scatter_data.append({
                        'score': d['avg_score'],
                        'latency': d['latency_ms'] or 0,
                        'tokens': tokens,
                        'type': d['eval_type']
                    })
                sdf = pd.DataFrame(scatter_data)
                
                if not sdf.empty and sdf['latency'].max() > 0:
                    fig_scatter = px.scatter(
                        sdf, x='latency', y='score', color='type',
                        size='tokens', size_max=15,
                        labels={'latency': '响应耗时 (ms)', 'score': '质量分', 'type': '模式', 'tokens': 'Tokens'},
                        color_discrete_map={'single_turn': '#6366f1', 'multi_turn': '#10b981', 'agent': '#f59e0b'}
                    )
                    # 及格线
                    fig_scatter.add_hline(y=3.0, line_dash="dash", line_color="red", opacity=0.5)
                    fig_scatter.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.caption("暂无足够的性能指标数据用于关联分析")

            with col_v2:
                st.markdown("##### 🎯 维度能力矩阵 (Heatmap)")
                # Prep heatmap data
                dim_rows = []
                for d in viz_data:
                    etype = d['eval_type']
                    # 获取 scores
                    for s_name, s_val in d.get('scores', {}).items():
                        dim_rows.append({'type': etype, 'dimension': s_name, 'score': s_val})
                
                ddf = pd.DataFrame(dim_rows)
                if not ddf.empty:
                    # Pivoting
                    hm = ddf.groupby(['type', 'dimension'])['score'].mean().reset_index()
                    pivot = hm.pivot(index='type', columns='dimension', values='score')
                    
                    if not pivot.empty:
                        fig_heat = px.imshow(
                            pivot,
                            labels=dict(x="维度", y="模式", color="得分"),
                            x=pivot.columns,
                            y=pivot.index,
                            color_continuous_scale='RdBu', range_color=[1, 5],
                            text_auto='.1f', aspect="auto"
                        )
                        fig_heat.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
                        st.plotly_chart(fig_heat, use_container_width=True)
                    else:
                        st.caption("数据不足以生成矩阵")
                else:
                    st.caption("暂无维度评分数据")
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 薄弱维度提示
        if stats['dimension_stats']:
            weakest = min(stats['dimension_stats'].items(), key=lambda x: x[1]['avg'])
            strongest = max(stats['dimension_stats'].items(), key=lambda x: x[1]['avg'])
            
            hint_col1, hint_col2 = st.columns(2)
            with hint_col1:
                if weakest[1]['avg'] < 4:
                    st.warning(f"⚠️ **薄弱维度**: {weakest[0]} ({weakest[1]['avg']}/5)")
                else:
                    st.success(f"✅ 所有维度表现良好 (均 ≥ 4分)")
            with hint_col2:
                st.info(f"🏆 **最强维度**: {strongest[0]} ({strongest[1]['avg']}/5)")
    else:
        # 无数据时的提示
        st.info(f"📊 当前模式「{mode_label}」暂无评测数据。完成评测后，这里将显示统计图表。")

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
# 智能评测 (🆕 v1.0.0: 集成评估器选择)
# -----------------------------------------------------------------------------
elif current_page == 'eval':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🚀 智能评测</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">两阶段评测：快速打分 + 低分深度分析</p>', unsafe_allow_html=True)
    
    if not logs_data:
        st.warning("⚠️ 请先加载对话数据")
        st.stop()
    
    # 🆕 v1.0.0: 评估器选择
    st.markdown("### 📋 评测配置")
    
    # 确保默认评估器存在
    EvaluatorStore.ensure_default_evaluator()
    
    # 获取所有评估器
    evaluators = EvaluatorStore.list_evaluators()
    
    col_eval, col_threshold = st.columns([3, 1])
    
    with col_eval:
        if evaluators:
            # 构建选项
            evaluator_options = {ev['evaluator_id']: ev for ev in evaluators}
            
            # 默认选中默认评估器
            default_evaluator = EvaluatorStore.get_default_evaluator()
            default_idx = 0
            if default_evaluator:
                for i, ev in enumerate(evaluators):
                    if ev['evaluator_id'] == default_evaluator['evaluator_id']:
                        default_idx = i
                        break
            
            selected_evaluator = st.selectbox(
                "选择评估器",
                options=evaluators,
                index=default_idx,
                format_func=lambda x: f"{'⭐ ' if x.get('is_default') else ''}{x['name']} v{x['version']} ({len(x.get('dimensions', []))}维度)",
                help="评估器决定使用哪些维度和权重来评测对话质量"
            )
            
            # 显示评估器摘要
            if selected_evaluator:
                dims = selected_evaluator.get('dimensions', [])
                dim_names = [f"{d['name']}({d.get('weight', 0)*100:.0f}%)" for d in dims[:4]]
                st.caption(f"维度: {', '.join(dim_names)}{'...' if len(dims) > 4 else ''}")
        else:
            st.error("❌ 未找到评估器，请先在系统设置中创建评估器")
            if st.button("前往创建"):
                st.session_state['current_page'] = 'settings'
                st.rerun()
            st.stop()
    
    with col_threshold:
        low_threshold = st.selectbox("低分阈值", [1, 2, 3, 4], index=2, help="综合分 ≤ 该值触发深度分析")
    
    # 工作流状态
    if workflow_parser:
        st.success("✅ 工作流已加载，低分项将自动进行节点溯源")
    else:
        st.info("ℹ️ 未加载工作流，低分项将不含节点溯源")
    
    # 开始评测按钮
    start_eval = st.button("▶️ 开始评测", type="primary", use_container_width=True)
    
    if start_eval:
        progress = st.progress(0)
        status = st.empty()
        
        def update_progress(current, total, desc):
            progress.progress(min(current / total, 1.0))
            status.text(f"评测中: {desc}")
        
        try:
            # 🆕 v1.0.0: 使用选中的评估器维度
            selected_dims = selected_evaluator.get('dimensions', [])
            
            results = run_log_evaluation(
                logs_data, 
                selected_dims,  # 使用评估器的维度而非 rubric_data
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
# 🆕 v0.3.0: Trace 追踪页面
# ==========================================
elif current_page == 'trace':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🔍 Trace 追踪</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">查看评测调用记录 - Langfuse 风格可观测性</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        session_filter = st.text_input("🔎 按 Session ID 筛选", "", placeholder="输入 session_id...")
    with col2:
        type_filter = st.selectbox("📋 评测类型", ["all", "single_turn", "multi_turn", "agent"])
    with col3:
        limit = st.slider("显示条数", 10, 100, 30)
    
    try:
        traces = TraceStore.list_traces(
            session_id=session_filter if session_filter else None,
            eval_type=type_filter if type_filter != "all" else None,
            limit=limit
        )
        trace_count = TraceStore.get_trace_count()
        st.markdown(f"### 📊 共 **{trace_count}** 条记录 (显示 {len(traces)} 条)")
        
        if not traces:
            st.info("暂无 Trace 记录。运行评测后，记录将自动保存到这里。")
        else:
            for trace in traces:
                avg_score = trace.get('avg_score') or 0
                color = "🟢" if avg_score >= 4 else "🟡" if avg_score >= 3 else "🔴"
                created = trace.get('created_at', '')[:16] if trace.get('created_at') else ''
                title = f"{color} {trace['trace_id']} | {trace['session_id'][:15]}... | {avg_score:.1f}/5 | {trace['eval_type']} | {created}"
                
                with st.expander(title):
                    detail = TraceStore.get_trace(trace['trace_id'])
                    if detail:
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.caption(f"🤖 模型: {detail.get('model', 'N/A')}")
                        with c2:
                            st.caption(f"⏱️ 耗时: {detail.get('latency_ms', 0)}ms")
                        with c3:
                            st.caption(f"📝 评分数: {len(detail.get('scores', []))}")
                        
                        io1, io2 = st.columns(2)
                        with io1:
                            st.markdown("**📥 输入**")
                            st.json(detail.get('input_data', {}))
                        with io2:
                            st.markdown("**📤 输出**")
                            st.json(detail.get('output_data', {}))
                        
                        st.markdown("**⭐ 评分**")
                        for score in detail.get('scores', []):
                            val = score['value']
                            icon = "🟢" if val >= 4 else "🟡" if val >= 3 else "🔴"
                            st.markdown(f"{icon} **{score['name']}**: {val}/5")
    except Exception as e:
        st.error(f"加载 Trace 数据失败: {str(e)}")

# ==========================================
# 🆕 v0.4.0: 统计看板页面
# ==========================================
elif current_page == 'stats':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">📊 统计看板</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">评测质量总览 - 维度分析 + Bad Case 追踪</p>', unsafe_allow_html=True)
    
    try:
        # 获取统计数据
        stats = TraceStore.get_dimension_stats()
        trace_count = TraceStore.get_trace_count()
        low_scores = TraceStore.get_low_score_traces(threshold=3, limit=10)
        
        # 顶部汇总
        st.markdown(f"### 📈 总体概览 (共 {trace_count} 条 Trace)")
        
        if not stats:
            st.info("暂无评分数据。运行评测后，统计将自动生成。")
        else:
            # 维度指标卡片
            cols = st.columns(len(stats))
            for i, (dim, data) in enumerate(stats.items()):
                with cols[i]:
                    avg = data['avg']
                    color = "🟢" if avg >= 4 else "🟡" if avg >= 3 else "🔴"
                    delta = "⚠️" if avg < 3 else ""
                    st.metric(
                        label=f"{color} {dim[:15]}",
                        value=f"{avg}/5",
                        delta=f"n={data['count']}"
                    )
            
            st.divider()
            
            # 图表区域
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 维度平均分")
                import pandas as pd
                df = pd.DataFrame([
                    {"维度": k[:12], "平均分": v['avg'], "样本数": v['count']}
                    for k, v in stats.items()
                ])
                fig = px.bar(df, x="维度", y="平均分", color="平均分",
                            color_continuous_scale=["red", "yellow", "green"],
                            range_color=[1, 5])
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 📈 雷达图分布")
                dimensions = list(stats.keys())[:6]  # 最多显示6个
                values = [stats[d]['avg'] for d in dimensions]
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=dimensions + [dimensions[0]],
                    fill='toself',
                    name='当前得分'
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # 薄弱维度警告
            weak = [k for k, v in stats.items() if v['avg'] < 3]
            if weak:
                st.warning(f"⚠️ **薄弱维度**: {', '.join(weak)} (平均分 < 3)")
            
            st.divider()
            
            # 低分记录列表
            st.markdown("#### 🔴 近期低分记录 (score < 3)")
            if low_scores:
                for item in low_scores:
                    created = item.get('created_at', '')[:16] if item.get('created_at') else ''
                    st.error(
                        f"**{item['trace_id']}** | {item['session_id'][:15]}... | "
                        f"**{item['dimension']}**: {item['score']}/5 | {created}"
                    )
                    if item.get('reasoning'):
                        st.caption(f"理由: {item['reasoning'][:80]}...")
            else:
                st.success("🎉 暂无低分记录，质量表现优秀！")
    
    except Exception as e:
        st.error(f"加载统计数据失败: {str(e)}")

# ==========================================
# 🆕 v0.6.0: 评测中心页面 (整合数据源 + 维度配置 + 评测)
# ==========================================
elif current_page == 'eval_center':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🚀 评测中心</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">一站式评测配置与执行</p>', unsafe_allow_html=True)
    
    # Step 1: 选择评测类型
    st.markdown("### Step 1: 选择评测类型")
    
    # 模型配置检查
    with st.expander("🛠️ 模型配置检查 (Debug)", expanded=False):
        try:
            temp_agent = RealAgent()
            st.info(f"当前使用的模型: **{temp_agent.model_name}**")
            # Mask API Key safely
            key_preview = "N/A"
            if temp_agent.client.api_key:
                key_str = str(temp_agent.client.api_key)
                if len(key_str) > 8:
                    key_preview = f"{key_str[:8]}...****"
                else:
                    key_preview = "****"
            
            st.code(f"Base URL: {temp_agent.client.base_url}\nAPI Key: {key_preview}")
        except Exception as e:
            st.error(f"模型初始化失败: {e}")
            
    eval_type = st.radio(
        "评测类型",
        ["🔄 自动识别", "💬 单轮评测", "🗣️ 多轮评测", "🤖 Agent 评测"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Step 2 + Step 3: 左右布局
    col_data, col_rubric = st.columns(2)
    
    with col_data:
        st.markdown("### Step 2: 数据源配置")
        
        source_type = st.radio(
            "数据来源",
            ["📤 上传 JSON 文件", "📂 选择历史日志", "🔗 输入 Session ID"],
            label_visibility="collapsed"
        )
        
        if source_type == "📤 上传 JSON 文件":
            uploaded = st.file_uploader("上传评测数据", type=['json'], key="eval_center_upload")
            if uploaded:
                try:
                    data = json.load(uploaded)
                    st.session_state['eval_center_data'] = data if isinstance(data, list) else [data]
                    st.success(f"✅ 已加载 {len(st.session_state['eval_center_data'])} 条数据")
                except Exception as e:
                    st.error(f"解析失败: {e}")
        
        elif source_type == "📂 选择历史日志":
            # 自动扫描 data 目录
            data_dir = Path("data")
            json_files = list(data_dir.glob("*.json")) if data_dir.exists() else []
            json_options = [str(f) for f in json_files]
            
            if not json_options:
                st.warning("⚠️ data/ 目录下未找到 JSON 文件")
                log_path = st.text_input("日志文件路径", "data/test_cases1.json")
            else:
                log_path = st.selectbox("选择日志文件", json_options, index=0 if json_options else None)
            
            if st.button("📂 加载日志", key="load_log_btn"):
                data = load_json_path(log_path)
                if data:
                    st.session_state['eval_center_data'] = data
                    # 提示已移至下方统一显示，避免重复
        
        elif source_type == "🔗 输入 Session ID":
            session_id = st.text_input("Session ID", placeholder="输入要评测的 Session ID...")
            if session_id:
                st.info(f"将评测 Session: {session_id}")
        
        # 显示已加载数据统计
        if st.session_state.get('eval_center_data'):
            data = st.session_state['eval_center_data']
            st.markdown(f"**📊 已加载: {len(data)} 条数据**")
    
    with col_rubric:
        st.markdown("### Step 3: 评估器选择")
        
        # 🆕 v1.0.0: 使用评估器替代维度选择
        EvaluatorStore.ensure_default_evaluator()
        evaluators = EvaluatorStore.list_evaluators()
        
        if evaluators:
            # 默认选中默认评估器
            default_evaluator = EvaluatorStore.get_default_evaluator()
            default_idx = 0
            if default_evaluator:
                for i, ev in enumerate(evaluators):
                    if ev['evaluator_id'] == default_evaluator['evaluator_id']:
                        default_idx = i
                        break
            
            selected_evaluator = st.selectbox(
                "选择评估器",
                options=evaluators,
                index=default_idx,
                format_func=lambda x: f"{'⭐ ' if x.get('is_default') else ''}{x['name']} v{x['version']}",
                key="eval_center_evaluator"
            )
            
            if selected_evaluator:
                dims = selected_evaluator.get('dimensions', [])
                selected_dims = dims  # 使用评估器的所有维度
                
                st.markdown("**评估维度:**")
                for dim in dims[:4]:
                    weight = dim.get('weight', 0)
                    st.markdown(f"- {dim['name']} ({weight*100:.0f}%)")
                if len(dims) > 4:
                    st.caption(f"... 还有 {len(dims)-4} 个维度")
                
                st.caption(f"共 {len(dims)} 个维度")
                
                # 存储选中的评估器到 session state
                st.session_state['eval_center_selected_evaluator'] = selected_evaluator
        else:
            st.warning("请先在系统设置中创建评估器")
            if st.button("前往创建评估器"):
                st.session_state['current_page'] = 'settings'
                st.rerun()
    
    st.divider()
    
    # Step 4: 开始评测
    st.markdown("### Step 4: 开始评测")
    
    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        start_eval = st.button("▶️ 开始评测", use_container_width=True, type="primary")
    
    with col_status:
        if st.session_state.get('eval_center_data'):
            dim_count = len(selected_dims) if 'selected_dims' in dir() and selected_dims else 6
            st.success(f"✅ 就绪: {len(st.session_state['eval_center_data'])} 条数据 | {dim_count} 个维度")
        else:
            st.info("请配置数据源并加载数据")
    
    # 评测执行区域
    if start_eval:
        if not st.session_state.get('eval_center_data'):
            st.warning("请先加载评测数据")
        else:
            st.divider()
            st.markdown("### 📊 评测结果")
            
            data = st.session_state['eval_center_data']
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 🆕 v0.9.0: 新版评测调用
            try:
                # 定义进度回调
                def update_progress(current, total, message):
                    progress = min(current / total, 1.0) if total > 0 else 0
                    progress_bar.progress(progress)
                    status_text.text(f"{message} ({current}/{total})")
                
                # 🆕 v1.0.0: 使用选中的评估器维度
                selected_evaluator = st.session_state.get('eval_center_selected_evaluator')
                if selected_evaluator:
                    rubrics = selected_evaluator.get('dimensions', [])
                else:
                    # 回退: 使用默认评估器
                    default_eval = EvaluatorStore.get_default_evaluator()
                    rubrics = default_eval.get('dimensions', []) if default_eval else []
                
                if not rubrics:
                    st.error("❌ 未找到评估维度，请先选择评估器")
                else:
                    # 执行评测 - 新版返回 (results, summary)
                    results, summary = run_evaluation_task(
                        data_list=data,
                        rubrics=rubrics,
                        progress_callback=update_progress
                    )
                
                status_text.text("✅ 评测完成!")
                progress_bar.progress(1.0)
                
                # 保存结果到 session state
                st.session_state['eval_center_last_results'] = results
                st.session_state['eval_center_last_summary'] = summary

            except Exception as e:
                st.error(f"❌ 评测执行失败: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # 如果有结果，显示结果概览 (支持持久化显示)
    if st.session_state.get('eval_center_last_results'):
        results = st.session_state['eval_center_last_results']
        summary = st.session_state.get('eval_center_last_summary', {})
        
        # 🆕 v0.9.0: 评测摘要卡片
        st.markdown("### 📈 评测摘要")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("📊 总计", summary.get('total', len(results)))
        with col2:
            st.metric("✅ 成功", summary.get('success', 0))
        with col3:
            st.metric("⚠️ 跳过", summary.get('skipped', 0))
        with col4:
            st.metric("❌ 失败", summary.get('error', 0))
        with col5:
            avg = summary.get('avg_score', 0)
            st.metric("⭐ 平均分", f"{avg:.1f}/5")
        
        # 耗时信息
        duration = summary.get('duration_ms', 0)
        if duration > 0:
            st.caption(f"⏱️ 总耗时: {duration/1000:.1f}s")
        
        st.divider()
        
        # 🆕 v0.9.0: 按状态分类显示结果
        st.markdown("### 📋 详细结果")
        
        # 状态筛选
        status_filter = st.selectbox(
            "筛选状态", 
            ["全部", "✅ 成功", "⚠️ 跳过", "❌ 失败"],
            key="eval_result_filter"
        )
        
        filtered_results = results
        if status_filter == "✅ 成功":
            filtered_results = [r for r in results if r.get('status') == 'success']
        elif status_filter == "⚠️ 跳过":
            filtered_results = [r for r in results if r.get('status') == 'skipped']
        elif status_filter == "❌ 失败":
            filtered_results = [r for r in results if r.get('status') == 'error']
        
        # 显示列表
        for r in filtered_results[:20]:  # 限制显示数量
            status = r.get('status', 'unknown')
            sess_id = r.get('session_id', 'unknown')
            eval_type = r.get('eval_type', 'unknown')
            avg_score = r.get('avg_score', 0)
            duration_ms = r.get('duration_ms', 0)
            error_msg = r.get('error_message', '')
            
            if status == 'success':
                st.success(f"✅ **{sess_id}** | {eval_type} | {avg_score:.1f}/5 | {duration_ms}ms")
            elif status == 'skipped':
                st.warning(f"⚠️ **{sess_id}** | 跳过: {error_msg}")
            else:
                st.error(f"❌ **{sess_id}** | 失败: {error_msg}")
        
        if len(filtered_results) > 20:
            st.caption(f"... 还有 {len(filtered_results) - 20} 条")
        
        st.divider()
        
        # 操作按钮
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🔄 重新评测", use_container_width=True):
                st.session_state['eval_center_last_results'] = None
                st.session_state['eval_center_last_summary'] = None
                st.rerun()
        with col_btn2:
            if st.button("📊 查看详情 (Trace)", type="primary", use_container_width=True):
                st.session_state['current_page'] = 'data_explorer'
                # 自动切换到对应的模式
                success_results = [r for r in results if r.get('status') == 'success']
                if success_results and 'eval_type' in success_results[0]:
                    etype = success_results[0]['eval_type']
                    if etype == 'single_turn':
                        st.session_state['data_explorer_mode'] = "💬 单轮"
                    elif etype == 'multi_turn':
                        st.session_state['data_explorer_mode'] = "🗣️ 多轮"
                    elif etype == 'agent':
                        st.session_state['data_explorer_mode'] = "🤖 Agent"
                st.rerun()

# ==========================================
# 🆕 v0.6.0: 追踪分析页面 (整合 Trace + 历史 + 低分)
# ==========================================
elif current_page == 'tracking':
    if st.button("← 返回工作台"):
        st.session_state['current_page'] = 'dashboard'
        st.rerun()
    
    st.markdown('<h1 class="main-title">🔍 追踪分析</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Trace 追踪 | 历史评测 | 低分分析</p>', unsafe_allow_html=True)
    
    # Tabs 整合
    tab_trace, tab_history, tab_lowscore = st.tabs(["📋 Trace 追踪", "📚 历史评测", "🔴 低分分析"])
    
    with tab_trace:
        # 筛选控件
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            session_filter = st.text_input("🔎 按 Session ID 筛选", "", placeholder="输入 session_id...", key="tracking_session")
        with col2:
            type_filter = st.selectbox("📋 评测类型", ["all", "single_turn", "multi_turn", "agent"], key="tracking_type")
        with col3:
            limit = st.slider("显示条数", 10, 100, 30, key="tracking_limit")
        
        try:
            traces = TraceStore.list_traces(
                session_id=session_filter if session_filter else None,
                eval_type=type_filter if type_filter != "all" else None,
                limit=limit
            )
            trace_count = TraceStore.get_trace_count()
            st.markdown(f"### 📊 共 **{trace_count}** 条记录 (显示 {len(traces)} 条)")
            
            if not traces:
                st.info("暂无 Trace 记录。运行评测后，记录将自动保存到这里。")
            else:
                for trace in traces:
                    avg_score = trace.get('avg_score') or 0
                    color = "🟢" if avg_score >= 4 else "🟡" if avg_score >= 3 else "🔴"
                    created = trace.get('created_at', '')[:16] if trace.get('created_at') else ''
                    title = f"{color} {trace['trace_id']} | {trace['session_id'][:15]}... | {avg_score:.1f}/5 | {trace['eval_type']} | {created}"
                    
                    with st.expander(title):
                        detail = TraceStore.get_trace(trace['trace_id'])
                        if detail:
                            # 元信息表格
                            st.markdown(f"""
                            | 模型 | 耗时 | Tokens | 创建时间 |
                            |------|------|--------|---------|
                            | {detail.get('model', 'N/A')} | {detail.get('latency_ms', 0)}ms | {detail.get('tokens_used', 'N/A')} | {detail.get('created_at', '')[:19]} |
                            """)
                            
                            # 输入输出
                            io1, io2 = st.columns(2)
                            with io1:
                                st.markdown("**📥 输入**")
                                st.json(detail.get('input_data', {}))
                            with io2:
                                st.markdown("**📤 输出**")
                                st.json(detail.get('output_data', {}))
                            
                            # 评分详情 (含 reasoning)
                            st.markdown("**⭐ 评分详情**")
                            for score in detail.get('scores', []):
                                val = score['value']
                                icon = "🟢" if val >= 4 else "🟡" if val >= 3 else "🔴"
                                turn_label = f"[Turn {score['turn_index']}]" if score.get('turn_index') is not None else ""
                                st.markdown(f"{icon} **{score['name']}**: {val}/5 {turn_label}")
                                if score.get('reasoning'):
                                    st.caption(f"  → {score['reasoning']}")
                            
                            # Metadata 展开
                            if detail.get('metadata') and detail['metadata'] != {}:
                                with st.expander("📋 扩展元数据"):
                                    st.json(detail['metadata'])
        except Exception as e:
            st.error(f"加载 Trace 数据失败: {str(e)}")
    
    with tab_history:
        st.markdown("### 📚 历史评测记录")
        try:
            # 使用 TraceStore 获取历史记录
            sessions = TraceStore.list_traces(limit=50)
            if sessions:
                # 按 session_id 分组
                from collections import defaultdict
                grouped = defaultdict(list)
                for s in sessions:
                    grouped[s['session_id']].append(s)
                
                for session_id, traces in list(grouped.items())[:20]:
                    avg = sum(t.get('avg_score') or 0 for t in traces) / len(traces) if traces else 0
                    with st.expander(f"📋 {session_id[:30]}... | {len(traces)} 条记录 | 平均: {avg:.1f}/5"):
                        for t in traces:
                            st.markdown(f"- **{t['trace_id']}** | {t['eval_type']} | {t.get('created_at', '')[:16]}")
            else:
                st.info("暂无历史评测记录")
        except Exception as e:
            st.warning(f"历史数据加载异常: {e}")
    
    with tab_lowscore:
        st.markdown("### 🔴 低分记录分析")
        
        threshold = st.slider("低分阈值", 1.0, 5.0, 3.0, 0.5, key="lowscore_threshold")
        
        try:
            low_scores = TraceStore.get_low_score_traces(threshold=threshold, limit=20)
            
            if low_scores:
                st.markdown(f"共 **{len(low_scores)}** 条低分记录 (score < {threshold})")
                
                for item in low_scores:
                    created = item.get('created_at', '')[:16] if item.get('created_at') else ''
                    st.error(
                        f"**{item['trace_id']}** | {item['session_id'][:15]}... | "
                        f"**{item['dimension']}**: {item['score']}/5 | {created}"
                    )
                    if item.get('reasoning'):
                        st.caption(f"  → {item['reasoning']}")
            else:
                st.success(f"🎉 暂无低分记录 (score < {threshold})，质量表现优秀！")
        except Exception as e:
            st.error(f"加载低分数据失败: {str(e)}")

# ==========================================
# 🆕 v0.7.0: 数据浏览页面 (按评测模式分类)
# ==========================================
elif current_page == 'data_explorer':
    st.markdown('<h1 class="main-title">📜 数据浏览</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">按评测模式浏览和分析数据</p>', unsafe_allow_html=True)
    
    # 模式选择器
    mode_options = ["📊 全部", "💬 单轮", "🗣️ 多轮", "🤖 Agent"]
    if 'data_explorer_mode' not in st.session_state:
        st.session_state['data_explorer_mode'] = "📊 全部"
    
    selected_mode = st.radio(
        "选择模式",
        mode_options,
        horizontal=True,
        index=mode_options.index(st.session_state.get('data_explorer_mode', "📊 全部")),
        label_visibility="collapsed",
        key="de_mode_selector"
    )
    st.session_state['data_explorer_mode'] = selected_mode
    
    st.divider()
    
    # 获取类型映射
    mode_type_map = {
        "💬 单轮": "single_turn",
        "🗣️ 多轮": "multi_turn", 
        "🤖 Agent": "agent",
        "📊 全部": None
    }
    current_eval_type = mode_type_map.get(selected_mode)
    
    try:
        # ========== 📊 全部模式 ==========
        if selected_mode == "📊 全部":
            # 统计卡片
            stats_by_type = TraceStore.get_stats_by_type()
            
            st.markdown("### 📈 评测类型概览")
            cols = st.columns(3)
            
            type_info = [
                ("💬 单轮", "single_turn", "#3b82f6"),
                ("🗣️ 多轮", "multi_turn", "#22c55e"),
                ("🤖 Agent", "agent", "#f59e0b")
            ]
            
            for i, (label, key, color) in enumerate(type_info):
                with cols[i]:
                    data = stats_by_type.get(key, {'count': 0, 'avg': 0, 'low_count': 0})
                    st.markdown(f'''
                    <div style="background:{color}20; border-left:4px solid {color}; padding:16px; border-radius:8px; margin-bottom:12px;">
                        <div style="font-size:24px; font-weight:bold; color:{color};">{data['count']}</div>
                        <div style="font-size:14px; color:#666;">{label}</div>
                        <div style="font-size:12px; color:#999; margin-top:8px;">
                            平均: {data['avg']}/5 | 低分: {data['low_count']}
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    # 快捷入口按钮
                    if st.button(f"查看详情", key=f"goto_{key}", use_container_width=True):
                        st.session_state['data_explorer_mode'] = label
                        st.rerun()
            
            st.divider()
            
            # 最近评测记录
            st.markdown("### 📋 最近评测记录")
            recent_traces = TraceStore.list_traces(limit=20)
            
            for trace in recent_traces:
                avg_score = trace.get('avg_score') or 0
                color = "🟢" if avg_score >= 4 else "🟡" if avg_score >= 3 else "🔴"
                eval_type = trace.get('eval_type', 'multi_turn')
                type_icon = "💬" if eval_type == "single_turn" else "🗣️" if eval_type == "multi_turn" else "🤖"
                created = trace.get('created_at', '')[:16] if trace.get('created_at') else ''
                
                st.markdown(f"""
                {color} **{trace['trace_id']}** | {type_icon} {eval_type} | {trace['session_id'][:20]}... | {avg_score:.1f}/5 | {created}
                """)
            
            # 全局低分预警
            st.divider()
            st.markdown("### 🔴 全局低分预警")
            low_scores = TraceStore.get_low_score_traces(threshold=3, limit=10)
            if low_scores:
                for item in low_scores:
                    type_icon = "💬" if item['eval_type'] == "single_turn" else "🗣️" if item['eval_type'] == "multi_turn" else "🤖"
                    st.error(f"{type_icon} **{item['trace_id']}** | {item['dimension']}: {item['score']}/5")
                    if item.get('reasoning'):
                        st.caption(f"→ {item['reasoning'][:80]}")
            else:
                st.success("🎉 暂无低分记录，质量表现优秀！")
        
        elif selected_mode in ["💬 单轮", "🗣️ 多轮", "🤖 Agent"]:
            # 1. 顶部统计
            stats = TraceStore.get_stats_by_type().get(current_eval_type, {'count': 0, 'avg': 0, 'low_count': 0})
            
            c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
            c1.metric("📊 总记录", stats['count'])
            c2.metric("⭐ 平均分", f"{stats['avg']}/5")
            c3.metric("🔴 低分", stats['low_count'])
            
            # 2. 筛选与列表
            with c4:
                limit = st.selectbox("显示条数", [50, 100, 200], index=0, key="list_limit")
            
            # 获取数据
            traces = TraceStore.get_traces_with_messages(eval_type=current_eval_type, limit=limit)
            
            if not traces:
                st.info(f"暂无 {selected_mode} 评测记录。")
            else:
                # 准备 DataFrame 数据
                import pandas as pd # Added import for pandas
                df_data = []
                for t in traces:
                    created_str = t.get('created_at', '')
                    # 尝试转为 datetime 对象以便 column_config 格式化
                    try:
                        created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        created_dt = created_str

                    # 提取更多信息 (Input/Output Preview)
                    input_data = t.get('input_data', {})
                    messages = input_data.get('messages', [])
                    
                    # 默认值
                    input_preview = "N/A"
                    output_preview = "N/A"
                    
                    # 提取性能指标 (Metrics)
                    metrics = {}
                    try:
                        meta_raw = t.get('metadata')
                        if meta_raw:
                            if isinstance(meta_raw, str):
                                meta = json.loads(meta_raw)
                            else:
                                meta = meta_raw
                            
                            # 兼容直接存储和嵌套 'metrics' 的情况
                            metrics = meta.get('metrics', meta)
                    except:
                        pass
                        
                    latency_val = t.get('latency_ms', 0) or 0
                    latency_display = f"{latency_val}ms"
                    
                    ttft_val = metrics.get('ttft_ms', 0)
                    ttft_display = f"{ttft_val}ms" if ttft_val else "-"
                    
                    usage = metrics.get('token_usage') or {}
                    total_tokens = usage.get('total_tokens', 0)
                    tokens_display = total_tokens if total_tokens else "-"
                    
                    if t['eval_type'] == 'agent':
                        input_preview = input_data.get('task', input_data.get('task_description', 'N/A'))
                        # 尝试从 output_data 获取结果，或者 fallback 到 input_data
                        output_data = t.get('output_data', {}) or {}
                        # output_data 可能是 string (JSON) 或 dict
                        if isinstance(output_data, str):
                            try:
                                output_data = json.loads(output_data)
                            except:
                                output_data = {}
                                
                        output_preview = str(output_data.get('result', output_data.get('output', input_data.get('final_output', 'N/A'))))
                    else: # single/multi
                        if messages:
                            # Input: User Message
                            user_msgs = [m['content'] for m in messages if m.get('role') == 'user']
                            if user_msgs: 
                                input_preview = user_msgs[0]
                            
                            # Output: Assistant Message
                            asst_msgs = [m['content'] for m in messages if m.get('role') == 'assistant']
                            if asst_msgs:
                                output_preview = asst_msgs[-1]
                    
                    # 截断预览
                    if len(input_preview) > 60: input_preview = input_preview[:60] + "..."
                    if len(output_preview) > 60: output_preview = output_preview[:60] + "..."
                    
                    # 格式化 Token 显示
                    tokens_display = "-"
                    if total_tokens > 0:
                        tokens_display = f"{total_tokens}" if total_tokens < 1000 else f"{total_tokens/1000:.1f}k"
                    
                    # Session ID Fallback (优化显示 'unknown')
                    session_display = t['session_id']
                    if not session_display or session_display == 'unknown':
                        if t['eval_type'] == 'single_turn':
                            session_display = "Single Turn Task"
                        elif t['eval_type'] == 'agent':
                            session_display = "Agent Task"
                        else:
                            session_display = "Session"
                            
                    df_data.append({
                        "id": t['trace_id'],
                        "name": session_display,
                        "type": t['eval_type'],
                        "score": t.get('avg_score', 0),
                        "input": input_preview,
                        "output": output_preview,
                        "time": created_dt,
                        "latency": latency_display,
                        "ttft": ttft_display,
                        "tokens": tokens_display,
                        "raw_trace": t
                    })
                
                df = pd.DataFrame(df_data)
                
                # 配置列显示 (仿 Langfuse)
                st.markdown("### 📋 记录列表")
                
                st.dataframe(
                    df,
                    column_order=["time", "name", "type", "score", "latency", "ttft", "tokens", "input", "output"],
                    column_config={
                        "time": st.column_config.DatetimeColumn("Time", format="MM-DD HH:mm", width="small"),
                        "name": st.column_config.TextColumn("Name / Session", width="medium"),
                        "type": st.column_config.TextColumn("Type", width="small"),
                        "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=5, format="%.1f"),
                        "latency": st.column_config.TextColumn("Latency", width="small"),
                        "ttft": st.column_config.TextColumn("TTFT", width="small"),
                        "tokens": st.column_config.TextColumn("Tokens", width="small"),
                        "input": st.column_config.TextColumn("Input Preview", width="medium"),
                        "output": st.column_config.TextColumn("Output Preview", width="medium"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )
                
                st.divider()
                
                # 3. 详情查看 (Master-Detail)
                st.markdown(f"### 🔍 {selected_mode} 详情")
                
                # 生成选项列表
                options = [t['raw_trace'] for t in df_data]
                selected_trace = st.selectbox(
                    "选择要查看的记录:", 
                    options, 
                    format_func=lambda x: f"[{x['created_at'][:16]}] {x['session_id']} (⭐{(x.get('avg_score') or 0):.1f})",
                    key="trace_selector"
                )
                
                if selected_trace:
                    trace = selected_trace
                    avg_score = trace.get('avg_score') or 0
                    color = "🟢" if avg_score >= 4 else "🟡" if avg_score >= 3 else "🔴"
                    
                    # 渲染不同模式的详情
                    # A. 单轮模式详情
                    if current_eval_type == 'single_turn':
                        st.markdown(f"#### {color} Session: {trace['session_id']}")
                        
                        # Input/Output
                        input_data = trace.get('input_data', {})
                        messages = input_data.get('messages', [])
                        
                        user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), '')
                        assistant_msg = next((m['content'] for m in messages if m.get('role') == 'assistant'), '')
                        
                        col_io1, col_io2 = st.columns(2)
                        with col_io1:
                            st.info(f"**User**: {user_msg}")
                        with col_io2:
                            st.success(f"**Assistant**: {assistant_msg}")
                        
                        # Scores
                        st.markdown("#### ⭐ 维度评分")
                        scores = trace.get('scores', [])
                        if scores:
                            cols = st.columns(min(len(scores), 4))
                            for i, s in enumerate(scores):
                                with cols[i % 4]:
                                    val = s['value']
                                    s_color = "🟢" if val >= 4 else "🟡" if val >= 3 else "🔴"
                                    st.markdown(f"**{s['name']}**")
                                    st.markdown(f"{s_color} {val}/5")
                                    if s.get('reasoning'):
                                        st.caption(f"{s['reasoning']}")
                                        
                    # B. 多轮模式详情
                    elif current_eval_type == 'multi_turn':
                        st.markdown(f"#### {color} Session: {trace['session_id']}")
                        messages = trace.get('input_data', {}).get('messages', [])
                        
                        # 聊天气泡
                        for i, msg in enumerate(messages):
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '')
                            if role == 'user':
                                st.markdown(f'''<div style="background:#f0f0f0;padding:10px;border-radius:10px;margin:5px 0;width:fit-content">👤 {content}</div>''', unsafe_allow_html=True)
                            elif role == 'assistant':
                                # 尝试找当前轮次的评分
                                turn_idx = i // 2
                                turn_scores = [s for s in trace.get('scores', []) if s.get('turn_index') == turn_idx]
                                turn_avg = sum(s['value'] for s in turn_scores)/len(turn_scores) if turn_scores else 0
                                score_badge = f"⭐{turn_avg:.1f}" if turn_scores else ""
                                st.markdown(f'''<div style="background:#e3f2fd;padding:10px;border-radius:10px;margin:5px 0;margin-left:auto;width:fit-content;text-align:right">🤖 {content} <br><small>{score_badge}</small></div>''', unsafe_allow_html=True)
                                
                                # 显示维度详情
                                if turn_scores:
                                    with st.expander(f"Turn {turn_idx} 评分详情"):
                                        for s in turn_scores:
                                            st.write(f"- **{s['name']}**: {s['value']}/5 ({s.get('reasoning','')})")

                    # C. Agent 模式详情
                    elif current_eval_type == 'agent':
                        input_data = trace.get('input_data', {})
                        task_desc = input_data.get('task', input_data.get('task_description', '未知任务'))
                        success = input_data.get('success', None)
                        status_icon = "✅" if success else "❌" if success is False else "⏳"
                        
                        st.markdown(f"#### {status_icon} Task: {task_desc}")
                        st.markdown(f"**最终输出**: {input_data.get('output', input_data.get('final_output', 'N/A'))}")
                        
                        # 工具链可视化
                        tool_calls = input_data.get('tool_calls', [])
                        if tool_calls:
                            st.markdown("---")
                            st.markdown(f"#### 🔧 工具调用链 ({len(tool_calls)} 次调用)")
                            
                            # 横向流程图
                            tool_cols = st.columns(min(len(tool_calls), 5))
                            for i, tool in enumerate(tool_calls[:5]):
                                with tool_cols[i]:
                                    tool_name = tool.get('name', 'unknown')
                                    tool_success = tool.get('success', True)
                                    t_color = "#22c55e" if tool_success else "#ef4444"
                                    st.markdown(f'''
                                    <div style="text-align:center; padding:12px; background:{t_color}20; border-radius:8px; border:2px solid {t_color};">
                                        <div style="font-size:12px; color:#666;">Step {i+1}</div>
                                        <div style="font-size:14px; font-weight:bold;">{tool_name[:12]}</div>
                                    </div>
                                    ''', unsafe_allow_html=True)
                        # 决策推理链
                        decisions = input_data.get('decisions', input_data.get('decision_steps', []))
                        if decisions:
                            st.markdown("---")
                            st.markdown("#### 🧠 决策推理链")
                            for i, dec in enumerate(decisions):
                                thought = dec.get('thought', dec.get('reasoning', str(dec)))
                                st.markdown(f"**Step {i+1}**: {thought}")
                        
                        # 评分详情
                        st.markdown("---")
                        st.markdown("#### ⭐ 评分详情")
                        scores = trace.get('scores', [])
                        for score in scores:
                            val = score['value']
                            s_color = "🟢" if val >= 4 else "🟡" if val >= 3 else "🔴"
                            st.markdown(f"{s_color} **{score['name']}**: {val}/5")
                            if score.get('reasoning'):
                                st.caption(f"→ {score['reasoning']}")
    
    except Exception as e:
        st.error(f"加载数据失败: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ==========================================
# 🆕 v1.0.0: 系统设置页面 (整合 evaluator + rubric + prompt)
# ==========================================
elif current_page == 'settings':
    st.markdown('<h1 class="main-title">⚙️ 系统设置</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">评估器管理 | 评分维度 | Prompt 模板</p>', unsafe_allow_html=True)
    
    # 确保默认评估器存在
    EvaluatorStore.ensure_default_evaluator()
    
    tab_evaluator, tab_rubric, tab_prompt, tab_langfuse = st.tabs(["🧪 评估器管理", "🛠️ 评分维度", "🎨 Prompt 模板", "🔌 Langfuse 集成"])
    
    # ==========================================
    # Tab 1: 评估器管理 (🆕 v1.0.0)
    # ==========================================
    with tab_evaluator:
        st.markdown("### 🧪 评估器管理")
        st.caption("评估器是可复用的评估配置模板，包含评估维度、权重和评分标准。")
        
        # 操作按钮行
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
        with btn_col1:
            if st.button("➕ 创建评估器", use_container_width=True):
                st.session_state['evaluator_mode'] = 'create'
                st.rerun()
        with btn_col2:
            if st.button("🤖 LLM 生成", use_container_width=True):
                st.session_state['evaluator_mode'] = 'llm_generate'
                st.rerun()
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 获取当前模式
        evaluator_mode = st.session_state.get('evaluator_mode', 'list')
        
        # ==========================================
        # 模式: 列表视图
        # ==========================================
        if evaluator_mode == 'list':
            evaluators = EvaluatorStore.list_evaluators()
            
            if not evaluators:
                st.info("暂无评估器，请创建一个新的评估器。")
            else:
                st.markdown(f"**共 {len(evaluators)} 个评估器:**")
                
                for ev in evaluators:
                    is_default = ev.get('is_default', False)
                    is_system = ev.get('is_system', False)
                    
                    # 图标
                    default_icon = "⭐" if is_default else ""
                    system_icon = "🔒" if is_system else ""
                    
                    # 评测类型标签
                    eval_types = ev.get('eval_types', [])
                    type_labels = {'single_turn': '单轮', 'multi_turn': '多轮', 'agent': 'Agent'}
                    types_str = ", ".join([type_labels.get(t, t) for t in eval_types])
                    
                    with st.expander(f"{default_icon}{system_icon} {ev['name']} v{ev['version']} ({len(ev.get('dimensions', []))}维度)"):
                        st.markdown(f"**ID**: `{ev['evaluator_id']}`")
                        st.markdown(f"**描述**: {ev.get('description', '无描述')}")
                        st.markdown(f"**适用类型**: {types_str}")
                        st.markdown(f"**创建方式**: {ev.get('created_by', 'manual')}")
                        st.markdown(f"**创建时间**: {ev.get('created_at', 'N/A')}")
                        
                        # 维度列表
                        st.markdown("**评估维度:**")
                        dims = ev.get('dimensions', [])
                        for dim in dims:
                            weight_pct = f"{dim.get('weight', 0) * 100:.0f}%"
                            st.markdown(f"- **{dim['name']}** (权重: {weight_pct})")
                        
                        # 操作按钮
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if not is_default:
                                if st.button("⭐ 设为默认", key=f"default_{ev['evaluator_id']}"):
                                    EvaluatorStore.set_default_evaluator(ev['evaluator_id'])
                                    st.success("已设为默认评估器")
                                    st.rerun()
                        with col_b:
                            if not is_system:
                                if st.button("✏️ 编辑", key=f"edit_{ev['evaluator_id']}"):
                                    st.session_state['evaluator_mode'] = 'edit'
                                    st.session_state['edit_evaluator_id'] = ev['evaluator_id']
                                    st.rerun()
                        with col_c:
                            if not is_system:
                                if st.button("🗑️ 删除", key=f"delete_{ev['evaluator_id']}"):
                                    try:
                                        EvaluatorStore.delete_evaluator(ev['evaluator_id'])
                                        st.success("已删除")
                                        st.rerun()
                                    except ValueError as e:
                                        st.error(str(e))
        
        # ==========================================
        # 模式: 创建评估器
        # ==========================================
        elif evaluator_mode == 'create':
            st.markdown("### ➕ 创建新评估器")
            
            if st.button("← 返回列表"):
                st.session_state['evaluator_mode'] = 'list'
                st.rerun()
            
            with st.form("create_evaluator_form"):
                name = st.text_input("评估器名称", placeholder="例如: 客服质量评估")
                description = st.text_area("描述", placeholder="描述评估器的用途和适用场景")
                version = st.text_input("版本", value="1.0")
                
                eval_types = st.multiselect(
                    "适用评测类型",
                    options=["single_turn", "multi_turn", "agent"],
                    default=["multi_turn"],
                    format_func=lambda x: {"single_turn": "单轮对话", "multi_turn": "多轮对话", "agent": "Agent 评测"}[x]
                )
                
                st.markdown("**评估维度** (JSON 格式):")
                default_dims = json.dumps([
                    {
                        "name": "维度1",
                        "weight": 0.5,
                        "description": "维度描述",
                        "criteria": {"1": "差", "3": "中", "5": "优"},
                        "low_score_checklist": ["检查项1"]
                    },
                    {
                        "name": "维度2",
                        "weight": 0.5,
                        "description": "维度描述",
                        "criteria": {"1": "差", "3": "中", "5": "优"},
                        "low_score_checklist": ["检查项1"]
                    }
                ], ensure_ascii=False, indent=2)
                
                dimensions_json = st.text_area("维度配置", value=default_dims, height=300)
                
                submitted = st.form_submit_button("💾 保存评估器", type="primary")
                
                if submitted:
                    try:
                        dimensions = json.loads(dimensions_json)
                        
                        # 验证维度
                        errors = EvaluatorGenerator.validate_dimensions(dimensions)
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            evaluator_id = EvaluatorStore.create_evaluator(
                                name=name,
                                dimensions=dimensions,
                                eval_types=eval_types,
                                version=version,
                                description=description,
                                created_by="manual"
                            )
                            st.success(f"✅ 评估器创建成功! ID: {evaluator_id}")
                            st.session_state['evaluator_mode'] = 'list'
                            st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"JSON 解析错误: {e}")
        
        # ==========================================
        # 模式: LLM 生成评估器
        # ==========================================
        elif evaluator_mode == 'llm_generate':
            st.markdown("### 🤖 LLM 生成评估器")
            st.caption("输入自然语言描述或上传文档，AI 将自动生成评估器配置。")
            
            if st.button("← 返回列表"):
                st.session_state['evaluator_mode'] = 'list'
                st.rerun()
            
            input_method = st.radio("输入方式", ["自然语言描述", "上传文档"], horizontal=True)
            
            user_input = ""
            
            if input_method == "自然语言描述":
                user_input = st.text_area(
                    "描述您的评估需求",
                    placeholder="例如：我需要一个评估客服对话的评估器，重点关注：\n1. 情绪管理能力 (30%)\n2. 问题解决率 (40%)\n3. 沟通专业度 (30%)",
                    height=200
                )
            else:
                uploaded_file = st.file_uploader("上传评估标准文档", type=["txt", "md", "json"])
                if uploaded_file:
                    user_input = uploaded_file.read().decode('utf-8')
                    st.text_area("文档内容预览", user_input[:1000] + "..." if len(user_input) > 1000 else user_input, height=150, disabled=True)
            
            if st.button("🔮 生成预览", type="primary", disabled=not user_input):
                with st.spinner("AI 正在生成评估器配置..."):
                    try:
                        generator = EvaluatorGenerator()
                        if input_method == "自然语言描述":
                            result = generator.generate_from_text(user_input)
                        else:
                            result = generator.generate_from_document(user_input)
                        
                        if 'error' in result and not result.get('dimensions'):
                            st.error(f"生成失败: {result['error']}")
                        else:
                            st.session_state['generated_evaluator'] = result
                            st.success("✅ 生成成功!")
                    except Exception as e:
                        st.error(f"生成失败: {e}")
            
            # 显示生成结果
            if 'generated_evaluator' in st.session_state:
                result = st.session_state['generated_evaluator']
                
                st.markdown("---")
                st.markdown("### 📋 生成预览")
                
                # Markdown 预览
                markdown_preview = EvaluatorGenerator.render_as_markdown(result)
                st.markdown(markdown_preview)
                
                # JSON 编辑
                with st.expander("✏️ 编辑 JSON"):
                    edited_json = st.text_area(
                        "JSON 配置",
                        value=json.dumps(result, ensure_ascii=False, indent=2),
                        height=400
                    )
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 保存评估器", type="primary", use_container_width=True):
                        try:
                            final_config = json.loads(edited_json) if 'edited_json' in dir() else result
                            
                            evaluator_id = EvaluatorStore.create_evaluator(
                                name=final_config.get('name', '未命名评估器'),
                                dimensions=final_config.get('dimensions', []),
                                eval_types=final_config.get('eval_types', ['multi_turn']),
                                version=final_config.get('version', '1.0'),
                                description=final_config.get('description', ''),
                                created_by="llm_generated"
                            )
                            st.success(f"✅ 评估器已保存! ID: {evaluator_id}")
                            del st.session_state['generated_evaluator']
                            st.session_state['evaluator_mode'] = 'list'
                            st.rerun()
                        except Exception as e:
                            st.error(f"保存失败: {e}")
                
                with col_cancel:
                    if st.button("🔄 重新生成", use_container_width=True):
                        del st.session_state['generated_evaluator']
                        st.rerun()
        
        # ==========================================
        # 模式: 编辑评估器
        # ==========================================
        elif evaluator_mode == 'edit':
            evaluator_id = st.session_state.get('edit_evaluator_id')
            ev = EvaluatorStore.get_evaluator(evaluator_id)
            
            if not ev:
                st.error("评估器不存在")
                st.session_state['evaluator_mode'] = 'list'
                st.rerun()
            
            st.markdown(f"### ✏️ 编辑评估器: {ev['name']}")
            
            if st.button("← 返回列表"):
                st.session_state['evaluator_mode'] = 'list'
                st.rerun()
            
            with st.form("edit_evaluator_form"):
                name = st.text_input("评估器名称", value=ev['name'])
                description = st.text_area("描述", value=ev.get('description', ''))
                version = st.text_input("版本", value=ev['version'])
                
                eval_types = st.multiselect(
                    "适用评测类型",
                    options=["single_turn", "multi_turn", "agent"],
                    default=ev.get('eval_types', ['multi_turn']),
                    format_func=lambda x: {"single_turn": "单轮对话", "multi_turn": "多轮对话", "agent": "Agent 评测"}[x]
                )
                
                st.markdown("**评估维度** (JSON 格式):")
                dimensions_json = st.text_area(
                    "维度配置",
                    value=json.dumps(ev.get('dimensions', []), ensure_ascii=False, indent=2),
                    height=300
                )
                
                submitted = st.form_submit_button("💾 保存修改", type="primary")
                
                if submitted:
                    try:
                        dimensions = json.loads(dimensions_json)
                        
                        # 验证维度
                        errors = EvaluatorGenerator.validate_dimensions(dimensions)
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            EvaluatorStore.update_evaluator(
                                evaluator_id=evaluator_id,
                                name=name,
                                dimensions=dimensions,
                                eval_types=eval_types,
                                version=version,
                                description=description
                            )
                            st.success("✅ 评估器已更新!")
                            st.session_state['evaluator_mode'] = 'list'
                            st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"JSON 解析错误: {e}")
    
    # ==========================================
    # Tab 2: 评分维度 (原有功能)
    # ==========================================
    with tab_rubric:
        st.markdown("### 🛠️ 评分维度配置 (旧版 - 建议使用评估器)")
        st.warning("⚠️ 此功能将被评估器管理替代，建议迁移到评估器。")
        
        rubric_path = st.text_input("配置文件路径", "config/rubric.json", key="settings_rubric_path")
        
        if st.button("📂 加载配置", key="settings_load_rubric"):
            st.session_state['rubric_data'] = load_json_path(rubric_path)
            st.rerun()
        
        rubric_data = st.session_state.get('rubric_data') or load_json_path(rubric_path)
        
        if rubric_data:
            if isinstance(rubric_data, dict) and 'rubrics' in rubric_data:
                dims = rubric_data['rubrics']
            elif isinstance(rubric_data, list):
                dims = rubric_data
            else:
                dims = []
            
            st.markdown(f"**共 {len(dims)} 个评测维度:**")
            for dim in dims:
                name = dim.get('name', 'unknown') if isinstance(dim, dict) else str(dim)
                desc = dim.get('description', '')[:50] if isinstance(dim, dict) else ''
                with st.expander(f"📌 {name}"):
                    st.markdown(f"**描述**: {desc}...")
                    if isinstance(dim, dict):
                        st.json(dim.get('criteria', {}))
        else:
            st.warning("未加载配置文件")
    
    # ==========================================
    # Tab 3: Prompt 模板 (原有功能)
    # ==========================================
    with tab_prompt:
        st.markdown("### 🎨 Prompt 模板")
        
        st.markdown("**评测 Prompt 预览:**")
        st.code("""
你是一个专业的对话质量评测专家。请对以下对话进行评分。

评分维度:
1. clarity (清晰度): 1-5分
2. proactivity (主动性): 1-5分
3. accuracy (准确性): 1-5分
...

输出格式: JSON
{"scores": {"clarity": 4, ...}, "reasoning": "..."}
        """, language="text")
        
        st.info("Prompt 模板编辑功能开发中...")

    # ==========================================
    # Tab 4: Langfuse 集成配置 (🆕 Dify 集成)
    # ==========================================
    with tab_langfuse:
        st.markdown("### 🔌 Langfuse 兼容 API 配置")
        st.caption("通过 Langfuse 兼容 API，将 Dify 或其他 LLM 平台的 trace 数据接入评测系统。")
        
        # 导入 langfuse_adapter 模块
        try:
            import sys
            import os
            # 确保当前目录在 Python 路径中（解决 Zeabur 部署环境问题）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from langfuse_adapter import API_KEYS, add_api_key, remove_api_key, list_api_keys
            adapter_available = True
        except ImportError as e:
            adapter_available = False
            st.error(f"⚠️ langfuse_adapter 模块未找到: {e}")
        
        if adapter_available:
            # 服务状态
            st.markdown("#### 📡 服务状态")
            
            status_col1, status_col2, status_col3 = st.columns(3)
            with status_col1:
                st.markdown('''
                <div class="metric-card">
                    <div class="metric-value">🟢</div>
                    <div class="metric-label">API 就绪</div>
                </div>
                ''', unsafe_allow_html=True)
            with status_col2:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{len(list_api_keys())}</div>
                    <div class="metric-label">活跃密钥</div>
                </div>
                ''', unsafe_allow_html=True)
            with status_col3:
                st.markdown('''
                <div class="metric-card">
                    <div class="metric-value">5000</div>
                    <div class="metric-label">监听端口</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            # API 密钥管理
            st.markdown("#### 🔑 API 密钥管理")
            
            # 当前密钥列表
            current_keys = list_api_keys()
            if current_keys:
                st.markdown("**已配置的密钥:**")
                for pk in current_keys:
                    key_col1, key_col2 = st.columns([4, 1])
                    with key_col1:
                        st.code(f"公钥: {pk}", language=None)
                    with key_col2:
                        if pk != "pk-eval-platform":  # 保护默认密钥
                            if st.button("🗑️", key=f"del_{pk}", help="删除此密钥"):
                                remove_api_key(pk)
                                st.success(f"已删除密钥: {pk}")
                                st.rerun()
            else:
                st.info("暂无配置的 API 密钥")
            
            # 添加新密钥
            with st.expander("➕ 添加新密钥"):
                new_pk = st.text_input("公钥 (Public Key)", placeholder="pk-your-project")
                new_sk = st.text_input("密钥 (Secret Key)", placeholder="sk-your-secret-key", type="password")
                
                if st.button("添加密钥", type="primary"):
                    if new_pk and new_sk:
                        if new_pk.startswith("pk-") and new_sk.startswith("sk-"):
                            add_api_key(new_pk, new_sk)
                            st.success(f"✅ 密钥已添加: {new_pk}")
                            st.rerun()
                        else:
                            st.error("公钥应以 'pk-' 开头，密钥应以 'sk-' 开头")
                    else:
                        st.warning("请填写公钥和密钥")
            
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            # Dify 配置指南
            st.markdown("#### 📋 Dify 配置指南")
            
            with st.expander("🔧 如何在 Dify 中配置", expanded=True):
                st.markdown("""
**步骤 1: 打开 Dify 应用设置**
- 进入您的 Dify 应用 → 监控 (Tracing)

**步骤 2: 添加 Langfuse 提供者**
- 选择 Langfuse 作为追踪提供者

**步骤 3: 填写配置**
""")
                st.code(f"""
Secret Key: sk-eval-platform-secret-key-2024
Public Key: pk-eval-platform
Host: http://your-server-ip:5000
""", language="text")
                
                st.info("💡 将 `your-server-ip` 替换为运行此服务的机器 IP 地址")
            
            # 连接测试
            st.markdown("#### 🧪 连接测试")
            
            test_col1, test_col2 = st.columns([2, 1])
            with test_col1:
                test_host = st.text_input("测试地址", value="http://localhost:5000", key="test_host")
            with test_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 测试连接", use_container_width=True):
                    import requests
                    try:
                        resp = requests.get(f"{test_host}/api/public/health", timeout=5)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(f"✅ 连接成功! 版本: {data.get('version', 'unknown')}")
                        else:
                            st.error(f"❌ 连接失败: HTTP {resp.status_code}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ 无法连接到服务，请确认 API Server 已启动")
                    except Exception as e:
                        st.error(f"❌ 连接错误: {e}")
            
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            # API 端点参考
            st.markdown("#### 📚 API 端点参考")
            
            st.markdown("""
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/public/ingestion` | POST | Langfuse 兼容数据摄入 |
| `/api/public/health` | GET | 健康检查 |
| `/api/v1/traces` | GET | 查询 Trace 记录 |
| `/api/v1/stats` | GET | 获取统计数据 |
""")
            
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            # 🆕 远程 Traces 查看
            st.markdown("#### 📊 Dify Traces 数据")
            
            api_url = st.text_input("API 服务地址", value="https://ai-dialogue-eval-api.zeabur.app", key="traces_api_url")
            
            col_fetch, col_limit = st.columns([1, 1])
            with col_limit:
                trace_limit = st.selectbox("显示条数", [10, 20, 50, 100], index=0)
            with col_fetch:
                st.markdown("<br>", unsafe_allow_html=True)
                fetch_traces = st.button("🔄 获取 Traces", use_container_width=True)
            
            if fetch_traces:
                import requests
                try:
                    resp = requests.get(f"{api_url}/api/v1/traces", params={"limit": trace_limit}, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        traces = data.get('traces', [])
                        if traces:
                            st.success(f"✅ 获取到 {len(traces)} 条 Traces (共 {data.get('total', '?')} 条)")
                            
                            # 显示 traces 表格
                            import pandas as pd
                            trace_rows = []
                            for t in traces:
                                trace_rows.append({
                                    "ID": t.get('id', '')[:8],
                                    "会话ID": (t.get('session_id') or '')[:20],
                                    "输入": (t.get('input') or '')[:50] + "...",
                                    "输出": (t.get('output') or '')[:50] + "...",
                                    "评分": t.get('avg_score', '-'),
                                    "时间": t.get('created_at', '')[:19]
                                })
                            
                            df = pd.DataFrame(trace_rows)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            # 详情展开
                            with st.expander("📄 查看完整 JSON"):
                                st.json(traces)
                        else:
                            st.info("暂无 Traces 数据")
                    else:
                        st.error(f"❌ 获取失败: HTTP {resp.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ 无法连接到 API 服务")
                except Exception as e:
                    st.error(f"❌ 错误: {e}")
            
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            # 🆕 可观测性数据 - Langfuse Events
            st.markdown("#### 🔍 可观测性数据 (Langfuse Events)")
            st.caption("展示原始 LLM 调用信息：模型、Token 使用、延迟等")
            
            col_events, col_type = st.columns([2, 1])
            with col_type:
                event_type_filter = st.selectbox("事件类型", ["全部", "generation-create", "span-create", "trace-create"], index=0)
            with col_events:
                st.markdown("<br>", unsafe_allow_html=True)
                fetch_events = st.button("🔄 获取 Events", use_container_width=True)
            
            if fetch_events:
                import requests
                try:
                    params = {"limit": 20}
                    if event_type_filter != "全部":
                        params["event_type"] = event_type_filter
                    
                    resp = requests.get(f"{api_url}/api/v1/langfuse/events", params=params, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        events = data.get('events', [])
                        if events:
                            st.success(f"✅ 获取到 {len(events)} 条 Events")
                            
                            # Token 统计
                            total_input = sum(e.get('input_tokens') or 0 for e in events)
                            total_output = sum(e.get('output_tokens') or 0 for e in events)
                            total_latency = sum(e.get('latency_ms') or 0 for e in events)
                            models = list(set(e.get('model') for e in events if e.get('model')))
                            
                            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                            with stat_col1:
                                st.metric("输入 Tokens", f"{total_input:,}")
                            with stat_col2:
                                st.metric("输出 Tokens", f"{total_output:,}")
                            with stat_col3:
                                st.metric("总延迟", f"{total_latency:,} ms")
                            with stat_col4:
                                st.metric("使用模型", ", ".join(models[:2]) if models else "-")
                            
                            # Events 表格
                            import pandas as pd
                            event_rows = []
                            for e in events:
                                event_rows.append({
                                    "类型": e.get('event_type', '')[:20],
                                    "名称": (e.get('name') or '')[:25],
                                    "模型": e.get('model') or '-',
                                    "输入 Tokens": e.get('input_tokens') or 0,
                                    "输出 Tokens": e.get('output_tokens') or 0,
                                    "延迟(ms)": e.get('latency_ms') or 0,
                                    "时间": (e.get('created_at') or '')[:19]
                                })
                            
                            df_events = pd.DataFrame(event_rows)
                            st.dataframe(df_events, use_container_width=True, hide_index=True)
                            
                            with st.expander("📄 查看完整 Events JSON"):
                                st.json(events)
                        else:
                            st.info("暂无 Events 数据。请先在 Dify 中发起对话，数据会自动记录。")
                    else:
                        st.error(f"❌ 获取失败: HTTP {resp.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ 无法连接到 API 服务")
                except Exception as e:
                    st.error(f"❌ 错误: {e}")



# ==========================================
# 透明演示横幅（底部固定）
# ==========================================
import time as time_module

if st.session_state.get('show_demo', False):
    step_idx = st.session_state.get('demo_step', 0)
    total_steps = len(DEMO_STEPS)
    
    if step_idx >= total_steps:
        step_idx = total_steps - 1
    
    step = DEMO_STEPS[step_idx]
    progress_pct = ((step_idx + 1) / total_steps) * 100
    
    # 在sidebar显示演示控制面板
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🎬 演示模式")
        st.progress((step_idx + 1) / total_steps, text=f"步骤 {step_idx + 1}/{total_steps}")
        st.markdown(f"**{step['title']}**")
        st.caption(step['desc'])
        
        # 控制按钮
        col_prev, col_next = st.columns(2)
        with col_prev:
            if step_idx > 0:
                if st.button("⬅️ 上一步", key="demo_prev_btn", use_container_width=True):
                    st.session_state['demo_step'] = step_idx - 1
                    prev_step = DEMO_STEPS[step_idx - 1]
                    st.session_state['current_page'] = prev_step['page']
                    st.rerun()
        
        with col_next:
            if step_idx < total_steps - 1:
                if st.button("➡️ 下一步", key="demo_next_btn", use_container_width=True, type="primary"):
                    st.session_state['demo_step'] = step_idx + 1
                    next_step = DEMO_STEPS[step_idx + 1]
                    st.session_state['current_page'] = next_step['page']
                    st.rerun()
            else:
                if st.button("🎉 完成", key="demo_finish_btn", use_container_width=True, type="primary"):
                    st.session_state['show_demo'] = False
                    st.session_state['demo_step'] = 0
                    st.rerun()
        
        # 自动播放和退出
        col_auto, col_exit = st.columns(2)
        with col_auto:
            if step_idx < total_steps - 1:
                auto_play = st.checkbox("🔄 自动", key="demo_auto_chk", value=False)
        with col_exit:
            if st.button("✖️ 退出", key="demo_exit_btn", use_container_width=True):
                st.session_state['show_demo'] = False
                st.session_state['demo_step'] = 0
                st.rerun()
        
        # 自动播放逻辑
        if step_idx < total_steps - 1 and st.session_state.get('demo_auto_chk', False):
            countdown = st.empty()
            for i in range(3, 0, -1):
                countdown.caption(f"⏱️ {i}秒后下一步...")
                time_module.sleep(1)
            countdown.empty()
            st.session_state['demo_step'] = step_idx + 1
            next_step = DEMO_STEPS[step_idx + 1]
            st.session_state['current_page'] = next_step['page']
            st.rerun()
    
    # 页面顶部也显示当前步骤提示
    st.info(f"🎬 **演示模式** [{step_idx + 1}/{total_steps}] {step['title']} - {step['desc']}")

# ==========================================
# 🆕 Dify 管理页面
# ==========================================
elif current_page == 'dify_management':
    st.markdown('<h1 class="main-title">🔌 Dify 管理</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">管理 Dify 工作流应用 | 在线测试 | 批量测试</p>', unsafe_allow_html=True)
    
    from dify_store import DifyStore
    from dify_client import DifyClient
    
    tab_apps, tab_playground, tab_batch = st.tabs(["📱 App 列表", "🎮 Playground", "📦 批量测试"])
    
    # ========== Tab 1: App 列表 ==========
    with tab_apps:
        st.markdown("### 📱 Dify App 管理")
        
        # 操作按钮
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("➕ 添加 App", use_container_width=True, type="primary"):
                st.session_state['dify_app_mode'] = 'create'
                st.rerun()
        
        app_mode = st.session_state.get('dify_app_mode', 'list')
        
        # 创建模式
        if app_mode == 'create':
            st.markdown("---")
            st.markdown("#### ➕ 添加新 App")
            
            with st.form("create_app_form"):
                name = st.text_input("App 名称", placeholder="如：客服质量检测工作流")
                dify_host = st.text_input("Dify Host", value="https://api.dify.ai", placeholder="https://api.dify.ai")
                api_key = st.text_input("API Key", type="password", placeholder="app-xxx")
                app_type = st.selectbox("App 类型", ["chat", "workflow"])
                description = st.text_area("描述", placeholder="描述此工作流的用途")
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("取消", use_container_width=True):
                        st.session_state['dify_app_mode'] = 'list'
                        st.rerun()
                
                if submitted:
                    if name and api_key:
                        app_id = DifyStore.create_app(
                            name=name,
                            dify_host=dify_host,
                            api_key=api_key,
                            app_type=app_type,
                            description=description
                        )
                        st.success(f"✅ App 创建成功! ID: {app_id}")
                        st.session_state['dify_app_mode'] = 'list'
                        st.rerun()
                    else:
                        st.error("请填写 App 名称和 API Key")
        
        # 列表模式
        else:
            apps = DifyStore.list_apps()
            
            if not apps:
                st.info("暂无 Dify App，请点击「添加 App」创建")
            else:
                st.markdown(f"**共 {len(apps)} 个 App:**")
                
                for app in apps:
                    with st.expander(f"📱 {app['name']} ({app['app_type']})"):
                        st.markdown(f"**ID**: `{app['id']}`")
                        st.markdown(f"**Host**: {app['dify_host']}")
                        st.markdown(f"**描述**: {app.get('description', '无')}")
                        st.markdown(f"**创建时间**: {app.get('created_at', 'N/A')}")
                        
                        # 🆕 显示统一静态凭证（供配置到 Dify）
                        st.markdown("---")
                        st.markdown("#### 🔑 Dify Langfuse 配置")
                        st.caption("所有工作流统一使用以下凭证，数据将按工作流名称自动区分")
                        
                        # 获取当前 Host
                        import os
                        api_host = os.environ.get('API_HOST', 'https://ai-dialogue-eval-api.zeabur.app')
                        
                        st.code("Public Key: pk-eval-platform", language="text")
                        st.code("Secret Key: sk-eval-platform-secret-key-2024", language="text")
                        st.code(f"Host: {api_host}", language="text")
                        
                        # 操作按钮
                        col_dataset, col_test, col_del = st.columns(3)
                        
                        # 🆕 打开评测集按钮
                        with col_dataset:
                            datasets = DifyStore.list_datasets(app_id=app['id'])
                            if datasets:
                                if st.button("📋 打开评测集", key=f"dataset_{app['id']}", type="primary"):
                                    st.session_state['selected_dataset'] = datasets[0]['id']
                                    st.session_state['current_page'] = 'eval_dataset_management'
                                    st.rerun()
                            else:
                                st.caption("暂无评测集")
                        
                        with col_test:
                            if st.button("🔗 测试Dify", key=f"test_{app['id']}"):
                                client = DifyClient(app['dify_host'], app['api_key'])
                                result = client.test_connection()
                                if result['success']:
                                    st.success("→ Dify 连接正常")
                                else:
                                    st.error(result['message'])
                        with col_del:
                            if st.button("🗑️ 删除", key=f"del_{app['id']}"):
                                DifyStore.delete_app(app['id'])
                                st.success("已删除")
                                st.rerun()
                        
                        # 🆕 测试回传按钮（单独一行）
                        if app.get('public_key') and app.get('secret_key'):
                            if st.button("📡 测试回传", key=f"test_callback_{app['id']}", help="模拟 Dify 发送数据到平台"):
                                import requests
                                import base64
                                import os
                                
                                # 构造认证头
                                credentials = f"{app['public_key']}:{app['secret_key']}"
                                auth_header = base64.b64encode(credentials.encode()).decode()
                                
                                # 平台 API 地址
                                api_host = os.environ.get('API_HOST', 'http://localhost:5000')
                                
                                # 模拟 Dify 发送的数据
                                test_payload = {
                                    "batch": [{
                                        "id": f"test-{app['id']}-{int(time_module.time())}",
                                        "type": "trace-create",
                                        "timestamp": datetime.now().isoformat(),
                                        "body": {
                                            "id": f"dify-test-{int(time_module.time())}",
                                            "name": f"测试回传 - {app['name']}",
                                            "input": "这是一条测试消息",
                                            "output": "这是测试回复，用于验证回传链路是否正常。",
                                            "userId": "test_user"
                                        }
                                    }]
                                }
                                
                                try:
                                    response = requests.post(
                                        f"{api_host}/api/public/ingestion",
                                        json=test_payload,
                                        headers={
                                            "Authorization": f"Basic {auth_header}",
                                            "Content-Type": "application/json"
                                        },
                                        timeout=10
                                    )
                                    
                                    if response.status_code in [200, 207]:
                                        st.success("✅ 回传测试成功！数据已存入评测集")
                                        st.json(response.json())
                                    else:
                                        st.error(f"❌ 回传失败: {response.status_code} - {response.text}")
                                except requests.exceptions.ConnectionError:
                                    st.error("❌ 无法连接到 API 服务器，请确保 Flask 服务已启动")
                                except Exception as e:
                                    st.error(f"❌ 测试失败: {str(e)}")
    
    # ========== Tab 2: Playground ==========
    with tab_playground:
        st.markdown("### 🎮 Playground 在线测试")
        st.caption("选择一个 App，填写入参，实时调用 Dify 并查看结果")
        
        apps = DifyStore.list_apps()
        if not apps:
            st.warning("请先在「App 列表」中添加 Dify App")
        else:
            selected_app = st.selectbox(
                "选择 App",
                apps,
                format_func=lambda x: f"{x['name']} ({x['app_type']})"
            )
            
            if selected_app:
                client = DifyClient(selected_app['dify_host'], selected_app['api_key'])
                
                # 获取入参定义
                with st.spinner("加载入参定义..."):
                    fields = client.get_input_form_fields()
                
                if not fields:
                    st.info("此 App 无需额外输入参数，直接发送查询即可")
                    fields = []
                
                st.markdown("---")
                st.markdown("#### 📝 输入参数")
                
                # 动态生成表单
                inputs = {}
                for field in fields:
                    label = f"{field['label']} {'*' if field.get('required') else ''}"
                    var = field['variable']
                    
                    if field['type'] == 'paragraph':
                        inputs[var] = st.text_area(label, value=field.get('default', ''), key=f"input_{var}")
                    elif field['type'] == 'select' and field.get('options'):
                        inputs[var] = st.selectbox(label, field['options'], key=f"input_{var}")
                    elif field['type'] == 'number':
                        inputs[var] = st.number_input(label, value=field.get('default', 0), key=f"input_{var}")
                    else:
                        inputs[var] = st.text_input(label, value=field.get('default', ''), key=f"input_{var}")
                
                # 查询输入
                query = st.text_area("用户问题 / Query", placeholder="输入您的问题...", key="playground_query")
                
                # 发送按钮
                if st.button("🚀 发送", type="primary", use_container_width=True):
                    if query or inputs:
                        with st.spinner("调用 Dify API..."):
                            if selected_app['app_type'] == 'workflow':
                                # 工作流模式
                                all_inputs = {**inputs}
                                if query:
                                    all_inputs['query'] = query
                                result = client.run_workflow(all_inputs)
                            else:
                                # 对话模式
                                result = client.chat(query, inputs)
                        
                        if 'error' in result:
                            st.error(f"调用失败: {result['error']}")
                        else:
                            st.markdown("---")
                            st.markdown("#### 📤 响应结果")
                            
                            # 提取输出
                            if selected_app['app_type'] == 'workflow':
                                output = result.get('data', {}).get('outputs', {})
                                st.json(output)
                            else:
                                answer = result.get('answer', '')
                                st.success(answer)
                            
                            # 保存到评测集
                            with st.expander("💾 保存到评测集"):
                                datasets = DifyStore.list_datasets(app_id=selected_app['id'])
                                if datasets:
                                    ds = st.selectbox("选择评测集", datasets, format_func=lambda x: x['name'])
                                    if st.button("保存"):
                                        DifyStore.add_record(
                                            dataset_id=ds['id'],
                                            inputs=json.dumps(inputs, ensure_ascii=False),
                                            query=query,
                                            output=str(result.get('answer', result.get('data', {}).get('outputs', ''))),
                                            source="playground"
                                        )
                                        st.success("已保存到评测集")
                                else:
                                    st.info("请先在「评测管理」中创建评测集")
                    else:
                        st.warning("请输入问题或填写参数")
    
    # ========== Tab 3: 批量测试 ==========
    with tab_batch:
        st.markdown("### 📦 批量测试")
        st.caption("上传 Excel 批量调用 Dify 工作流，自动保存结果到评测集")
        
        apps = DifyStore.list_apps()
        if not apps:
            st.warning("请先在「App 列表」中添加 Dify App")
        else:
            selected_app = st.selectbox(
                "选择 App",
                apps,
                format_func=lambda x: f"{x['name']} ({x['app_type']})",
                key="batch_app_select"
            )
            
            if selected_app:
                client = DifyClient(selected_app['dify_host'], selected_app['api_key'])
                
                # 获取入参定义
                fields = client.get_input_form_fields()
                
                st.markdown("---")
                
                # Step 1: 生成模板
                st.markdown("#### 📥 Step 1: 下载模板")
                
                if fields:
                    st.markdown(f"此 App 共有 **{len(fields)}** 个输入参数")
                    
                    # 生成模板
                    import pandas as pd
                    template_data = {}
                    for field in fields:
                        template_data[field['variable']] = [f"示例_{field.get('label', field['variable'])}"]
                    template_data['query'] = ["您的问题"]
                    
                    template_df = pd.DataFrame(template_data)
                    
                    # 显示模板预览
                    st.dataframe(template_df, use_container_width=True)
                    
                    # 下载按钮
                    csv_data = template_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 下载 CSV 模板",
                        data=csv_data,
                        file_name=f"batch_template_{selected_app['name']}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("此 App 无需额外参数，只需提供 query 列")
                    template_df = pd.DataFrame({"query": ["问题1", "问题2"]})
                    st.dataframe(template_df)
                    csv_data = template_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button("📥 下载模板", csv_data, "batch_template.csv", "text/csv")
                
                st.markdown("---")
                
                # Step 2: 上传文件
                st.markdown("#### 📤 Step 2: 上传测试数据")
                
                uploaded_file = st.file_uploader(
                    "上传 CSV 或 Excel 文件",
                    type=['csv', 'xlsx', 'xls'],
                    key="batch_file_upload"
                )
                
                if uploaded_file:
                    # 解析文件
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df = pd.read_csv(uploaded_file)
                        else:
                            df = pd.read_excel(uploaded_file)
                        
                        st.success(f"✅ 文件解析成功！共 {len(df)} 行数据")
                        st.dataframe(df.head(5), use_container_width=True)
                        
                        st.markdown("---")
                        
                        # Step 3: 配置执行
                        st.markdown("#### ⚙️ Step 3: 配置执行")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            concurrency = st.slider("并发数", min_value=1, max_value=10, value=3)
                        with col2:
                            auto_eval = st.checkbox("执行后自动评测", value=False)
                        
                        # 选择或创建评测集
                        datasets = DifyStore.list_datasets(app_id=selected_app['id'])
                        create_new = st.checkbox("创建新评测集", value=not datasets)
                        
                        if create_new:
                            new_ds_name = st.text_input(
                                "新评测集名称",
                                value=f"{selected_app['name']}-批量测试-{datetime.now().strftime('%m%d%H%M')}"
                            )
                        else:
                            if datasets:
                                target_ds = st.selectbox(
                                    "保存到评测集",
                                    datasets,
                                    format_func=lambda x: x['name']
                                )
                        
                        st.markdown("---")
                        
                        # Step 4: 执行
                        st.markdown("#### 🚀 Step 4: 执行批量测试")
                        
                        if st.button("🚀 开始执行", type="primary", use_container_width=True):
                            # 创建或获取评测集
                            if create_new:
                                dataset_id = DifyStore.create_dataset(
                                    name=new_ds_name,
                                    app_id=selected_app['id'],
                                    source_type='batch'
                                )
                                st.info(f"已创建评测集: {new_ds_name}")
                            else:
                                dataset_id = target_ds['id']
                            
                            # 执行批量测试
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            results_container = st.empty()
                            
                            success_count = 0
                            error_count = 0
                            results_list = []
                            
                            from datetime import datetime
                            
                            for idx, row in df.iterrows():
                                # 更新进度
                                progress = (idx + 1) / len(df)
                                progress_bar.progress(progress)
                                status_text.text(f"执行中: {idx + 1}/{len(df)}")
                                
                                # 构建输入
                                inputs = {}
                                for col in df.columns:
                                    if col != 'query':
                                        inputs[col] = str(row[col]) if pd.notna(row[col]) else ""
                                
                                query = str(row.get('query', '')) if pd.notna(row.get('query', '')) else ''
                                
                                # 调用 Dify
                                try:
                                    if selected_app['app_type'] == 'workflow':
                                        all_inputs = {**inputs}
                                        if query:
                                            all_inputs['query'] = query
                                        result = client.run_workflow(all_inputs)
                                        output = str(result.get('data', {}).get('outputs', ''))
                                    else:
                                        result = client.chat(query, inputs)
                                        output = result.get('answer', '')
                                    
                                    if 'error' not in result:
                                        # 保存记录
                                        DifyStore.add_record(
                                            dataset_id=dataset_id,
                                            inputs=json.dumps(inputs, ensure_ascii=False),
                                            query=query,
                                            output=output,
                                            source='batch',
                                            total_tokens=result.get('data', {}).get('total_tokens', 0),
                                            latency_ms=int(result.get('data', {}).get('elapsed_time', 0) * 1000)
                                        )
                                        success_count += 1
                                        results_list.append({"row": idx + 1, "status": "✅", "output": output[:50]})
                                    else:
                                        error_count += 1
                                        results_list.append({"row": idx + 1, "status": "❌", "output": result['error'][:50]})
                                        
                                except Exception as e:
                                    error_count += 1
                                    results_list.append({"row": idx + 1, "status": "❌", "output": str(e)[:50]})
                            
                            # 完成
                            progress_bar.progress(1.0)
                            status_text.empty()
                            
                            st.success(f"✅ 批量测试完成! 成功: {success_count}, 失败: {error_count}")
                            
                            # 显示结果
                            results_df = pd.DataFrame(results_list)
                            st.dataframe(results_df, use_container_width=True)
                            
                            # 自动评测
                            if auto_eval and success_count > 0:
                                st.info("正在执行自动评测...")
                                from dify_eval_adapter import DifyEvalAdapter
                                records = DifyStore.list_records(dataset_id, status='pending')
                                record_ids = [r['id'] for r in records]
                                if record_ids:
                                    eval_results, eval_summary = DifyEvalAdapter.batch_evaluate(record_ids)
                                    st.success(f"评测完成! 平均分: {eval_summary['avg_score']:.2f}")
                                    
                    except Exception as e:
                        st.error(f"文件解析失败: {str(e)}")

# ==========================================
# 🆕 评测管理页面
# ==========================================
elif current_page == 'eval_dataset_management':
    st.markdown('<h1 class="main-title">📋 评测管理</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">评测集管理 | 评测任务 | 重新评测</p>', unsafe_allow_html=True)
    
    from dify_store import DifyStore
    
    tab_datasets, tab_evaluate, tab_reevaluate = st.tabs(["📁 评测集", "⚡ 评测任务", "🔄 重新评测"])
    
    # ========== Tab 1: 评测集列表 ==========
    with tab_datasets:
        st.markdown("### 📁 评测集管理")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("➕ 创建评测集", use_container_width=True, type="primary"):
                st.session_state['dataset_mode'] = 'create'
                st.rerun()
        
        dataset_mode = st.session_state.get('dataset_mode', 'list')
        
        # 创建模式
        if dataset_mode == 'create':
            st.markdown("---")
            st.markdown("#### ➕ 创建评测集")
            
            with st.form("create_dataset_form"):
                name = st.text_input("评测集名称", placeholder="如：客服话术v2.1 - 2026年1月")
                
                # 关联 App
                apps = DifyStore.list_apps()
                app_options = [{"id": None, "name": "不关联 App"}] + apps
                selected_app = st.selectbox(
                    "关联 Dify App (可选)",
                    app_options,
                    format_func=lambda x: x['name']
                )
                
                source_type = st.selectbox("来源类型", ["dify", "json_upload", "builtin"])
                description = st.text_area("描述")
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("取消", use_container_width=True):
                        st.session_state['dataset_mode'] = 'list'
                        st.rerun()
                
                if submitted:
                    if name:
                        dataset_id = DifyStore.create_dataset(
                            name=name,
                            app_id=selected_app.get('id') if selected_app else None,
                            source_type=source_type,
                            description=description
                        )
                        st.success(f"✅ 评测集创建成功! ID: {dataset_id}")
                        st.session_state['dataset_mode'] = 'list'
                        st.rerun()
                    else:
                        st.error("请填写评测集名称")
        
        # 列表模式
        else:
            datasets = DifyStore.list_datasets()
            
            if not datasets:
                st.info("暂无评测集，请点击「创建评测集」添加")
            else:
                st.markdown(f"**共 {len(datasets)} 个评测集:**")
                
                for ds in datasets:
                    record_count = ds.get('record_count', 0)
                    evaluated_count = ds.get('evaluated_count', 0)
                    avg_score = ds.get('avg_score', 0) or 0
                    
                    with st.expander(f"📁 {ds['name']} ({record_count} 条记录)"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("记录数", record_count)
                        with col2:
                            st.metric("已评测", evaluated_count)
                        with col3:
                            st.metric("平均分", f"{avg_score:.1f}/5" if avg_score else "-")
                        
                        st.markdown(f"**ID**: `{ds['id']}`")
                        st.markdown(f"**来源**: {ds.get('source_type', 'dify')}")
                        st.markdown(f"**创建时间**: {ds.get('created_at', 'N/A')}")
                        
                        # 查看记录
                        if st.button("📜 查看记录", key=f"view_{ds['id']}"):
                            st.session_state['selected_dataset'] = ds['id']
                            st.session_state['current_page'] = 'eval_dataset_management'
                            # 切换到评测任务 Tab
                        
                        # 删除按钮
                        if st.button("🗑️ 删除", key=f"del_ds_{ds['id']}"):
                            DifyStore.delete_dataset(ds['id'])
                            st.success("评测集及其记录已删除")
                            st.rerun()
    
    # ========== Tab 2: 评测任务 ==========
    with tab_evaluate:
        st.markdown("### ⚡ 评测任务")
        st.caption("选择评测集 → 筛选记录 → 执行评测")
        
        datasets = DifyStore.list_datasets()
        if not datasets:
            st.warning("请先创建评测集")
        else:
            selected_ds = st.selectbox(
                "选择评测集",
                datasets,
                format_func=lambda x: f"{x['name']} ({x.get('record_count', 0)} 条)",
                key="eval_dataset_select"
            )
            
            if selected_ds:
                # 筛选条件
                col1, col2, col3 = st.columns(3)
                with col1:
                    status_filter = st.selectbox("评测状态", ["全部", "pending", "completed", "failed"])
                with col2:
                    limit = st.number_input("显示条数", min_value=10, max_value=500, value=50)
                
                # 获取记录
                records = DifyStore.list_records(
                    selected_ds['id'],
                    status=status_filter if status_filter != "全部" else None,
                    limit=limit
                )
                
                if not records:
                    st.info("该评测集暂无记录")
                else:
                    st.markdown(f"**共 {len(records)} 条记录:**")
                    
                    # 显示记录表格
                    import pandas as pd
                    df_data = []
                    for r in records:
                        df_data.append({
                            "ID": r['id'],
                            "Query": (r.get('query', '') or '')[:50],
                            "Output": (r.get('output', '') or '')[:50],
                            "状态": r.get('eval_status', 'pending'),
                            "评测次数": r.get('eval_count', 0),
                            "创建时间": r.get('created_at', '')[:16]
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 批量评测按钮
                    st.markdown("---")
                    
                    # 选择评估器
                    from evaluator_store import EvaluatorStore
                    evaluators = EvaluatorStore.list_evaluators()
                    selected_evaluator = st.selectbox(
                        "选择评估器",
                        evaluators,
                        format_func=lambda x: f"{'⭐ ' if x.get('is_default') else ''}{x['name']} v{x['version']}",
                        key="eval_evaluator_select"
                    )
                    
                    col_eval, col_pending = st.columns(2)
                    with col_eval:
                        if st.button("🚀 执行批量评测", type="primary", use_container_width=True):
                            from dify_eval_adapter import DifyEvalAdapter
                            
                            record_ids = [r['id'] for r in records]
                            evaluator_id = selected_evaluator['evaluator_id'] if selected_evaluator else None
                            
                            # 显示进度
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            def update_progress(current, total):
                                progress_bar.progress(current / total)
                                status_text.text(f"评测进度: {current}/{total}")
                            
                            # 执行评测
                            results, summary = DifyEvalAdapter.batch_evaluate(
                                record_ids, 
                                evaluator_id,
                                progress_callback=update_progress
                            )
                            
                            progress_bar.progress(1.0)
                            status_text.empty()
                            
                            # 显示结果
                            st.success(f"✅ 评测完成! 成功: {summary['success']}, 失败: {summary['error']}, 平均分: {summary['avg_score']:.2f}")
                            
                            # 刷新页面
                            st.rerun()
                    
                    with col_pending:
                        pending_count = len([r for r in records if r.get('eval_status') == 'pending'])
                        st.info(f"待评测: {pending_count} 条")
    
    # ========== Tab 3: 重新评测 ==========
    with tab_reevaluate:
        st.markdown("### 🔄 重新评测")
        st.caption("选择已评测的记录，使用新评估器重新评测")
        
        datasets = DifyStore.list_datasets()
        if not datasets:
            st.warning("请先创建评测集")
        else:
            selected_ds = st.selectbox(
                "选择评测集",
                datasets,
                format_func=lambda x: f"{x['name']}",
                key="reevaluate_dataset_select"
            )
            
            if selected_ds:
                # 只显示已评测的记录
                completed_records = DifyStore.list_records(
                    selected_ds['id'],
                    status='completed',
                    limit=100
                )
                
                if not completed_records:
                    st.info("暂无已评测的记录")
                else:
                    st.markdown(f"**共 {len(completed_records)} 条已评测记录:**")
                    
                    # 显示记录
                    for r in completed_records[:10]:
                        latest = DifyStore.get_latest_evaluation(r['id']) if hasattr(DifyStore, 'get_latest_evaluation') else None
                        score_display = f"⭐{latest['avg_score']:.1f}" if latest else "-"
                        
                        with st.expander(f"{r['id']} | {(r.get('query', '')[:30] or 'N/A')}... | {score_display}"):
                            st.markdown(f"**评测次数**: {r.get('eval_count', 0)}")
                            if latest:
                                st.json(json.loads(latest.get('scores', '{}')))
                            
                            if st.button("🔄 重新评测", key=f"re_{r['id']}"):
                                from dify_eval_adapter import DifyEvalAdapter
                                result = DifyEvalAdapter.run_evaluation(r['id'])
                                if result['status'] == 'success':
                                    st.success(f"重新评测完成! 新分数: {result['avg_score']:.2f}")
                                else:
                                    st.error(f"评测失败: {result.get('error_message', '未知错误')}")

# ==========================================
# 🆕 报告中心页面
# ==========================================
elif current_page == 'report_center':
    st.markdown('<h1 class="main-title">📝 报告中心</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">可配置字段导出 | 多格式支持</p>', unsafe_allow_html=True)
    
    from dify_store import DifyStore
    import pandas as pd
    
    st.markdown("### 📊 导出评测报告")
    
    # 选择评测集
    datasets = DifyStore.list_datasets()
    if not datasets:
        st.warning("请先创建评测集并添加记录")
    else:
        selected_ds = st.selectbox(
            "选择评测集",
            datasets,
            format_func=lambda x: f"{x['name']} ({x.get('record_count', 0)} 条)",
            key="report_dataset_select"
        )
        
        if selected_ds:
            st.markdown("---")
            
            # 配置导出字段
            st.markdown("#### 📋 选择导出字段")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**基础信息**")
                include_id = st.checkbox("记录 ID", value=True)
                include_query = st.checkbox("用户问题 (Query)", value=True)
                include_output = st.checkbox("AI 回答 (Output)", value=True)
                include_inputs = st.checkbox("输入参数 (Inputs)", value=False)
                include_source = st.checkbox("来源", value=False)
                include_created = st.checkbox("创建时间", value=True)
            
            with col2:
                st.markdown("**评测信息**")
                include_status = st.checkbox("评测状态", value=True)
                include_eval_count = st.checkbox("评测次数", value=False)
                include_scores = st.checkbox("各维度分数", value=True)
                include_avg_score = st.checkbox("平均分", value=True)
                include_reasonings = st.checkbox("评测理由", value=False)
            
            st.markdown("---")
            
            # 筛选条件
            st.markdown("#### 🔍 筛选条件")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("评测状态", ["全部", "pending", "completed", "failed"], key="report_status")
            with col2:
                limit = st.number_input("最大记录数", min_value=10, max_value=1000, value=100, key="report_limit")
            
            st.markdown("---")
            
            # 导出格式
            st.markdown("#### 📁 导出格式")
            
            export_format = st.radio(
                "选择格式",
                ["CSV", "Excel", "JSON"],
                horizontal=True
            )
            
            # 预览和导出
            st.markdown("---")
            
            if st.button("📊 生成报告", type="primary", use_container_width=True):
                # 获取数据
                records = DifyStore.list_records(
                    selected_ds['id'],
                    status=status_filter if status_filter != "全部" else None,
                    limit=limit
                )
                
                if not records:
                    st.warning("暂无匹配的记录")
                else:
                    # 构建导出数据
                    export_data = []
                    
                    for r in records:
                        row = {}
                        
                        if include_id:
                            row['ID'] = r['id']
                        if include_query:
                            row['Query'] = r.get('query', '')
                        if include_output:
                            row['Output'] = r.get('output', '')
                        if include_inputs:
                            row['Inputs'] = r.get('inputs', '')
                        if include_source:
                            row['Source'] = r.get('source', '')
                        if include_created:
                            row['Created'] = r.get('created_at', '')
                        if include_status:
                            row['Status'] = r.get('eval_status', '')
                        if include_eval_count:
                            row['EvalCount'] = r.get('eval_count', 0)
                        
                        # 获取评测结果
                        if include_scores or include_avg_score or include_reasonings:
                            latest = DifyStore.get_latest_evaluation(r['id'])
                            if latest:
                                if include_avg_score:
                                    row['AvgScore'] = latest.get('avg_score', 0)
                                if include_scores:
                                    row['Scores'] = latest.get('scores', '{}')
                                if include_reasonings:
                                    row['Reasonings'] = latest.get('reasonings', '{}')
                            else:
                                if include_avg_score:
                                    row['AvgScore'] = None
                                if include_scores:
                                    row['Scores'] = None
                                if include_reasonings:
                                    row['Reasonings'] = None
                        
                        export_data.append(row)
                    
                    # 转换为 DataFrame
                    df = pd.DataFrame(export_data)
                    
                    # 显示预览
                    st.markdown("#### 📋 预览")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    st.markdown(f"**共 {len(df)} 条记录**")
                    
                    # 导出按钮
                    st.markdown("---")
                    
                    filename = f"report_{selected_ds['name']}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                    
                    if export_format == "CSV":
                        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 下载 CSV",
                            data=csv_data,
                            file_name=f"{filename}.csv",
                            mime="text/csv"
                        )
                    elif export_format == "Excel":
                        # 使用 BytesIO 生成 Excel
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Report')
                        excel_data = output.getvalue()
                        st.download_button(
                            label="📥 下载 Excel",
                            data=excel_data,
                            file_name=f"{filename}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:  # JSON
                        json_data = df.to_json(orient='records', force_ascii=False, indent=2)
                        st.download_button(
                            label="📥 下载 JSON",
                            data=json_data,
                            file_name=f"{filename}.json",
                            mime="application/json"
                        )

# ==========================================
# 页脚
# ==========================================
if not st.session_state.get('show_demo', False):
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.caption("AI 对话评测系统 Pro v3.0 | 支持工作流节点溯源 | Powered by LLM-as-a-Judge")
