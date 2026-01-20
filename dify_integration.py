"""
Dify 集成配置模块 - Streamlit UI 组件

提供:
- API 密钥管理界面
- 连接测试功能
- 配置信息展示
"""

import streamlit as st
from typing import Dict, List
import requests

# 默认配置
DEFAULT_CONFIG = {
    "public_key": "pk-eval-platform",
    "secret_key": "sk-eval-platform-secret-key-2024",
    "host": "http://localhost:5000"
}


def render_dify_integration_settings():
    """
    渲染 Dify 集成配置页面
    
    在 app.py 的系统设置中调用此函数
    """
    st.markdown("### 🔌 Dify 集成配置")
    
    st.markdown("""
    将此评测平台作为 Langfuse 的替代品接入 Dify，自动评测所有对话。
    """)
    
    # 配置信息展示
    st.markdown("#### 📋 Dify 配置信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input(
            "公钥 (Public Key)",
            value=DEFAULT_CONFIG["public_key"],
            key="dify_public_key",
            disabled=True
        )
        
    with col2:
        st.text_input(
            "密钥 (Secret Key)",
            value=DEFAULT_CONFIG["secret_key"],
            key="dify_secret_key",
            type="password",
            disabled=True
        )
    
    host = st.text_input(
        "Host (API 服务地址)",
        value=DEFAULT_CONFIG["host"],
        key="dify_host",
        placeholder="http://your-server:5000"
    )
    
    # 配置复制区域
    st.markdown("#### 📝 复制到 Dify")
    
    config_text = f"""
公钥: {DEFAULT_CONFIG['public_key']}
密钥: {DEFAULT_CONFIG['secret_key']}
Host: {host}
    """.strip()
    
    st.code(config_text, language="text")
    
    # 连接测试
    st.markdown("#### 🧪 连接测试")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("测试连接", type="primary"):
            test_connection(host)
    
    with col2:
        st.caption("测试 API 服务是否正常运行")
    
    # 使用说明
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        **步骤 1**: 启动 API 服务器
        ```bash
        python api_server.py
        ```
        
        **步骤 2**: 在 Dify 应用中配置 Langfuse
        1. 进入 Dify 应用 → 监控设置
        2. 选择「第三方 LLMOps 提供商」
        3. 选择「Langfuse」
        4. 填入上方的配置信息
        
        **步骤 3**: 测试
        在 Dify 应用中发送一条消息，然后在本系统的「数据浏览」中查看自动生成的 Trace 和评测分数。
        
        ---
        
        **工作原理**:
        - Dify 将所有对话数据发送到本系统的 `/api/public/ingestion` 端点
        - 系统自动创建 Trace 记录并触发评测
        - 评测结果保存到 `traces.db`，可在 Dashboard 实时查看
        """)
    
    # 最近的 Dify 数据
    st.markdown("#### 📊 最近的 Dify 数据")
    show_recent_dify_traces()


def test_connection(host: str):
    """测试与 API 服务的连接"""
    try:
        response = requests.get(f"{host}/api/public/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ 连接成功! 适配器版本: {data.get('version', 'unknown')}")
        else:
            st.error(f"❌ 连接失败: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("❌ 无法连接到服务器，请确保 API 服务已启动")
    except requests.exceptions.Timeout:
        st.error("❌ 连接超时")
    except Exception as e:
        st.error(f"❌ 连接错误: {str(e)}")


def show_recent_dify_traces():
    """显示最近来自 Dify 的 Trace 数据"""
    try:
        from trace_store import TraceStore
        
        # 获取最近的 Trace
        traces = TraceStore.list_traces(limit=10)
        
        # 过滤出 Dify 来源的数据
        dify_traces = []
        for trace in traces:
            metadata = trace.get('metadata', {})
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            if metadata.get('source') == 'dify':
                dify_traces.append(trace)
        
        if dify_traces:
            for trace in dify_traces[:5]:
                metadata = trace.get('metadata', {})
                if isinstance(metadata, str):
                    import json
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                with st.container():
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.caption(f"🔗 {trace.get('trace_id', 'N/A')}")
                    with cols[1]:
                        avg_score = trace.get('avg_score', 0)
                        if avg_score:
                            st.caption(f"⭐ {avg_score:.1f}")
                    with cols[2]:
                        st.caption(f"📅 {trace.get('created_at', 'N/A')[:10]}")
        else:
            st.info("暂无来自 Dify 的数据。配置 Dify 后，发送消息即可看到数据。")
            
    except Exception as e:
        st.warning(f"无法加载数据: {str(e)}")


# 简化版组件，可直接嵌入现有 Tab
def render_dify_config_card():
    """渲染简化版的 Dify 配置卡片"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0;">🔌 Dify 集成</h3>
        <p style="margin: 0; opacity: 0.9;">一键将评测平台接入 Dify，自动评测所有对话</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**公钥**")
        st.code("pk-eval-platform")
    
    with col2:
        st.markdown("**密钥**")
        st.code("sk-eval-platform-secret-key-2024")
    
    with col3:
        st.markdown("**Host**")
        st.code("http://localhost:5000")


if __name__ == "__main__":
    # 测试页面
    st.set_page_config(page_title="Dify 集成配置", layout="wide")
    render_dify_integration_settings()
