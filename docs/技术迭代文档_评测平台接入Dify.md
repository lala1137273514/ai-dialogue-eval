# 技术迭代文档：评测平台接入 Dify 工作流

> **项目**: AI 对话评测平台 (ai-dialogue-eval)
> **目标**: 让评测平台像 Langfuse 一样接收 Dify 发送的 LLM 调用数据，实现自动化评测
> **时间**: 2026-01-20

---

## 一、整体思路

### 1.1 背景

Dify 原生支持将 LLM 调用数据发送到 Langfuse（一个开源的 LLM 可观测性平台）。我们的评测平台需要接收同样的数据来实现自动化评测。

### 1.2 核心思路：模拟 Langfuse API

**不修改 Dify，而是让评测平台"伪装"成 Langfuse。**

```
┌─────────┐      Langfuse 协议      ┌─────────────────┐
│  Dify   │  ──────────────────────▶  │  评测平台 API   │
│ 工作流  │   POST /api/public/     │  (伪装成 Langfuse)│
└─────────┘      ingestion          └─────────────────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │  评测引擎     │
                                    │  + 数据存储   │
                                    └───────────────┘
```

### 1.3 关键实现点

1. **实现 Langfuse 兼容的 `/api/public/ingestion` 端点**
2. **支持 HTTP Basic Auth 认证**（Public Key + Secret Key）
3. **解析 Langfuse 事件格式**（trace-create, generation-create, span-create 等）
4. **将数据转换为评测平台格式并触发自动评测**

---

## 二、遇到的卡点及解决方案

### 卡点 1: Dify 配置验证失败 (404 错误)

**问题**: Dify 配置 Langfuse 后点击保存，报 `404 Not Found`。

**排查过程**:
1. 在 API Server 添加请求日志：
   ```python
   @app.before_request
   def log_request_info():
       print(f"📡 [Request] {request.method} {request.url}")
   ```
2. 发现 Dify 在验证时请求了 `/api/public/projects`，但我们只实现了 `/api/public/ingestion`。

**解决方案**: 添加 `/api/public/projects` 端点，返回模拟的项目列表：
```python
@app.route('/api/public/projects', methods=['GET'])
def list_projects():
    return jsonify({
        "data": [{"id": "default_project", "name": "Eval Platform"}]
    })
```

---

### 卡点 2: Zeabur 部署后 API 服务未启动

**问题**: 部署到 Zeabur 后，访问 API 地址返回的是 Streamlit 页面而非 Flask API。

**原因**: Zeabur 自动检测到 `streamlit` 命令并优先启动前端，忽略了 Flask API Server。

**解决方案**: 
1. 在 Zeabur 创建**两个独立服务**（指向同一 Git 仓库）
2. API 服务手动设置启动命令为 `python api_server.py`
3. 修改 [api_server.py](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/api_server.py) 读取 `PORT` 环境变量：
   ```python
   port = int(os.environ.get('PORT', 5000))
   app.run(host='0.0.0.0', port=port)
   ```

---

### 卡点 3: 前端看不到 Dify 发送的数据

**问题**: Dify 成功发送数据，API 服务日志显示接收成功，但 Streamlit 前端看不到数据。

**原因**: API 服务和 Streamlit 前端是**两个独立容器**，各自有独立的 SQLite 数据库文件，数据无法共享。

**解决方案**: 让 Streamlit 通过 HTTP 调用 API 服务获取数据：
```python
# 在 Streamlit 中
resp = requests.get(f"{api_url}/api/v1/traces")
traces = resp.json()['traces']
```

---

### 卡点 4: 原始 Langfuse 数据丢失

**问题**: 评测平台只保存了评测结果，但丢失了 Langfuse 原始的可观测性数据（Token 使用、延迟、模型信息等）。

**解决方案**: 按 TDD 流程新增数据存储：

1. **新增 [langfuse_events](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/langfuse_adapter.py#515-559) 表**：保存原始事件
   ```sql
   CREATE TABLE langfuse_events (
       event_id TEXT,
       event_type TEXT,
       model TEXT,
       input_tokens INTEGER,
       output_tokens INTEGER,
       latency_ms INTEGER,
       raw_body TEXT,
       ...
   );
   ```

2. **在事件处理中同时保存原始数据**：
   ```python
   def handle_generation_create(body, timestamp):
       # 1. 创建评测 Trace
       trace_id = TraceStore.create_trace(...)
       
       # 2. 保存原始 Langfuse 事件
       save_raw_event(
           event_id=gen_id,
           event_type='generation-create',
           model=model,
           input_tokens=usage.get('input'),
           ...
       )
   ```

3. **前端增加可观测性数据展示**

---

## 三、最终架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Dify 工作流                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ POST /api/public/ingestion
                          │ (Langfuse 协议, Basic Auth)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask API Server                          │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ langfuse_bp     │  │ /api/v1/...     │                   │
│  │ (Langfuse 兼容) │  │ (内部 API)      │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           ▼                    ▼                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  langfuse_adapter.py                     ││
│  │  • 解析事件 (trace/generation/span)                      ││
│  │  • 保存原始事件 → langfuse_events 表                     ││
│  │  • 转换为评测格式 → traces 表                            ││
│  │  • 触发自动评测 → scores 表                              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite 数据库                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ traces       │  │ scores       │  │ langfuse_events  │   │
│  │ (评测记录)   │  │ (评分)       │  │ (原始可观测数据) │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP API
┌─────────────────────────────────────────────────────────────┐
│                  Streamlit 前端                              │
│  • 📊 Traces 列表 + 评分                                     │
│  • 🔍 可观测性数据 (Token, 延迟, 模型)                       │
│  • ⚙️ 配置管理                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、核心代码文件

| 文件 | 作用 |
|------|------|
| [langfuse_adapter.py](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/langfuse_adapter.py) | Langfuse 协议解析、事件处理、数据转换 |
| [api_server.py](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/api_server.py) | Flask API 服务，注册 Langfuse 兼容端点 |
| [trace_store.py](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/trace_store.py) | SQLite 数据存储 (traces, scores, langfuse_events) |
| [app.py](file:///c:/Users/11372/Desktop/langfuse-main/ai-dialogue-eval/app.py) | Streamlit 前端，Langfuse 集成 Tab |

---

## 五、Dify 配置方式

在 Dify 应用中：**监控** → **追踪** → **Langfuse**

| 配置项 | 值 |
|--------|-----|
| Host | `https://ai-dialogue-eval-api.zeabur.app` |
| Public Key | `pk-eval-platform` |
| Secret Key | `sk-eval-platform-secret-key-2024` |

---

## 六、总结

### 成功关键

1. **协议模拟**：完整实现 Langfuse API 协议，让 Dify 无需修改即可对接
2. **日志排查**：通过添加请求日志，快速定位 Dify 验证时访问的接口
3. **分离部署**：API 和前端独立部署，通过 HTTP 通信
4. **数据融合**：同时保留可观测性数据和评测数据，实现两种视角

### 学到的经验

- Dify 配置 Langfuse 时会调用 `/api/public/projects` 验证连接
- Zeabur 自动检测启动命令可能不准确，需要手动设置
- 容器间无法共享 SQLite 文件，需要通过 API 通信
