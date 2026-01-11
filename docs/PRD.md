# AI Dialogue Evaluation System - Product Requirements Document (v0.9.0)

**Version:** v0.9.0  
**Status:** Active / Implemented  
**Date:** 2026-01-03  
**Author:** AI Dialogue Evaluation Team

---

## 1. Introduction

### 1.1 Purpose
The purpose of this document is to define the product requirements and technical specifications for **Version 0.9.0** of the AI Dialogue Evaluation System. This release focuses on "All-in-One Observability," unifying the evaluation of Single-turn, Multi-turn, and Agent interactions under a single architecture, introducing a comprehensive Trace system, and enhancing visual analytics via Dashboard 2.0.

### 1.2 Scope
*   **Unified Evaluation:** Support for three distinct evaluation modes (Single-turn, Multi-turn, Agent).
*   **Traceability:** Implementation of a local `TraceStore` to record granular execution details (Langfuse-style).
*   **Dashboard 2.0:** A multi-mode visualization panel using Plotly for high-fidelity analytics.
*   **Agent Evaluation:** Capabilities to assess tool calling, decision reasoning, and task success.
*   **Deep Analysis:** Automated root cause analysis for low-performing interactions.

### 1.3 Definitions
*   **Session:** A complete interaction session (chat or task) between a user and the AI.
*   **Turn:** A single exchange (User input -> AI response) within a session.
*   **Trace:** A detailed record of a single execution unit (session or turn), capturing inputs, outputs, latency, tokens, and scores.
*   **Agent:** An AI system capable of using tools and making multi-step decisions to complete a task.

---

## 2. User Requirements Analysis

### 2.1 Target Users
1.  **AI Engineers:** Focus on debugging, prompt optimization, and latency/token analysis.
2.  **Product Managers:** Focus on overall quality trends, pass rates, and identifying weak dimensions.
3.  **QA Engineers:** Focus on batch testing, regression testing, and validating bad cases.

### 2.2 User Stories

| ID | User Persona | Requirement | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **US-01** | AI Engineer | I want to evaluate Single-turn, Multi-turn, and Agent tasks using a single tool. | The system accepts all 3 formats and routes them correctly. |
| **US-02** | AI Engineer | I want to see detailed logs (latency, tokens) for each evaluation to debug performance. | Trace details show `latency_ms` and `token_usage` for every record. |
| **US-03** | PM | I want to view quality trends over time to see if the model is improving. | Dashboard displays a generic trend chart (Time vs. Score/Volume). |
| **US-04** | PM | I want to know which dimensions (e.g., Accuracy, Empathy) are the weakest. | Dashboard highlights "Weakest Dimension" and shows a heatmap. |
| **US-05** | QA | I want to filter and analyze only the "failed" or "low score" cases. | "Low Score Analysis" section lists all cases with score < Threshold. |
| **US-06** | All | I want to create a persistent local record of evaluations without setting up external servers. | All data is stored in a local SQLite database (`traces.db`). |

---

## 3. Functional Specifications

### 3.1 Unified Evaluation Dispatcher
**Core Logic:** `eval_dispatcher.py`
*   **Input Handling:** Accepts a uniform list of dictionaries.
*   **Auto-Detection:** Automatically detects evaluation type based on input keys (`messages` vs `task`).
*   **Validation:** Validates required fields (`session_id`, `messages`/`task`) before processing.
*   **Routing:**
    *   `single_turn`/`multi_turn` -> `Evaluate Turn Unified` (LLM Judge).
    *   `agent` -> `Evaluate Agent` (Tool/Reasoning Judge).

### 3.2 Traceability System (TraceStore)
**Core Logic:** `trace_store.py`
*   **Storage:** Persists every evaluation as a "Trace".
*   **Schema:** `trace_id` (UUID), `session_id`, `eval_type`, `input_data` (JSON), `output_data` (JSON), `metadata` (JSON), `latency`, `model`.
*   **Retrieval:** Supports filtering by `session_id`, `eval_type`, and `date`.
*   **Stats API:** Provides aggregated statistics for the dashboard (Average scores, P90 latency, etc.).

### 3.3 Dashboard 2.0
**Frontend:** `app.py` (Streamlit + Plotly)
*   **Mode Switcher:**
    *   **All:** Aggregated view of all system traffic.
    *   **Single/Multi/Agent:** Specialized views for specific modes.
*   **Visualizations:**
    *   **Trend Combo Chart:** Bar (Volume) + Line (Avg Score) over time.
    *   **Performance Scatter:** X=Latency, Y=Score, Size=Tokens, Color=Type.
    *   **Dimension Heatmap:** X=Dimensions, Y=Eval Modes, Color=Score.
*   **Key Metrics:** Total Traces, Average Score, Excellent Rate (≥4), Low Score Count (<3).

### 3.4 Evaluation Center
*   **Data Sources:**
    *   Upload JSON File.
    *   Select from `data/` directory.
    *   Specify Session ID.
*   **Execution:**
    *   Real-time progress bar.
    *   Live status updates (Success/Skipped/Error).
*   **Results Display:**
    *   Summary Cards (Total, Success, Error, Avg Score).
    *   Detailed list with Expanders.
    *   Export to CSV, JSON, Markdown.

### 3.5 Deep Analysis Module
*   **Low Score Triggers:** Configurable threshold (default ≤ 3.0).
*   **Analysis Logic:**
    *   **Root Cause:** Why did the model fail? (e.g., Logic error, Hallucination, Format error).
    *   **Node Tracing:** (Agent only) Which workflow node caused the failure?
    *   **Suggestions:** Specific prompt or code modifications to fix the issue.

---

## 4. System Architecture & Data Flow

### 4.1 Architecture Diagram

```mermaid
graph TD
    User[User / QA] -->|1. Load Data| FE[Frontend (Streamlit)]
    FE -->|2. Dispatch Config| Dispatcher[Eval Dispatcher]
    
    subgraph Core Engine
        Dispatcher -->|Route| Validator[Input Validator]
        Validator -->|Chat| ChatEval[Chat Evaluator]
        Validator -->|Agent| AgentEval[Agent Evaluator]
        
        ChatEval -->|Prompt| LLM[LLM Judge]
        AgentEval -->|Prompt| LLM
    end
    
    subgraph Storage Layer (Local SQLite)
        LLM -->|Result| DB[(TraceStore DB)]
        DB -->|Tables| T_Traces[Traces Table]
        DB -->|Tables| T_Scores[Scores Table]
        DB -->|Tables| T_Analyses[Analysis Table]
    end
    
    subgraph Analytics Layer
        DB -->|Query Stats| Dashboard[Dashboard 2.0]
        Dashboard -->|Viz| Plotly[Plotly Charts]
        DB -->|Query Traces| Explorer[Data Explorer]
    end
```

### 4.2 Data Flow
1.  **Ingestion:** User loads JSON data -> `app.py` parses it.
2.  **Dispatch:** `run_evaluation_task()` receives data list -> Normalizes format.
3.  **Evaluation:**
    *   System constructs prompts based on `rubric.json`.
    *   Invokes `RealAgent` to get unified JSON response from LLM.
4.  **Persistence:**
    *   `TraceStore.create_trace()` saves execution metadata.
    *   `TraceStore.add_score()` saves dimension scores.
5.  **Visualization:** `app.py` queries `TraceStore` to render charts and tables.

---

## 5. Technical Details

### 5.1 Technology Stack
*   **Language:** Python 3.9+
*   **Frontend:** Streamlit 1.30+
*   **Charts:** Plotly Express / Graph Objects
*   **Database:** SQLite 3 (Standard Library)
*   **LLM Integration:** OpenAI SDK / Custom `RealAgent` Wrapper

### 5.2 Database Schema
**Table: `traces`**
*   `trace_id` (TEXT PK): UUID
*   `session_id` (TEXT): Associated session
*   `eval_type` (TEXT): 'single_turn', 'multi_turn', 'agent'
*   `input_data` (JSON): Messages, Task, Context
*   `output_data` (JSON): Response, Tool Calls, Result
*   `metadata` (JSON): Token usage, Metrics, Tags
*   `latency_ms` (INT): Execution time
*   `created_at` (DATETIME)

**Table: `scores`**
*   `id` (INTEGER PK)
*   `trace_id` (TEXT FK)
*   `name` (TEXT): Dimension name (e.g., 'accuracy')
*   `value` (FLOAT): Score 1-5
*   `reasoning` (TEXT): Justification
*   `turn_index` (INTEGER): For multi-turn chats

### 5.3 Interface Contracts (DTOs)
**EvalResultDTO:**
```json
{
  "trace_id": "uuid",
  "status": "success",
  "scores": {"accuracy": 5, "clarity": 4},
  "avg_score": 4.5,
  "analysis": "Response was clear and accurate...",
  "meta": {"latency": 1200}
}
```

---

## 6. Evaluation Metrics & Standards

### 6.1 Scoring Dimensions (Configurable via `rubric.json`)
*   **Single/Multi-Turn:**
    *   **Accuracy:** Correctness of information.
    *   **Clarity:** Readability and structure.
    *   **Completeness:** Addressing all parts of the user query.
    *   **Safety:** Compliance with safety guidelines.
*   **Agent:**
    *   **Task Success:** Did it achieve the goal?
    *   **Tool Usage:** Correct tool selection and parameters.
    *   **Reasoning:** Logical decision-making process.

### 6.2 Scoring Algorithm
*   **Scale:** 1.0 to 5.0 (Float).
*   **Aggregation:** Arithmetical Mean of active dimensions.
*   **Minimum Score Penalty:**
    *   *Formula:* `Final Score = min(Average Score, Minimum Dimension Score + 1.5)`
    *   *Purpose:* Prevents a severe failure in one dimension (e.g., Safety=1) from being masked by high scores in others.

---

## 7. Future Roadmap (Post v0.9.0)
*   **v1.0.0:** Production Release.
*   **v1.1.0:** Remote Database Support (PostgreSQL).
*   **v1.2.0:** A/B Testing Framework (Side-by-side comparison).
*   **v1.5.0:** Automated Dataset Generation via LLM.
