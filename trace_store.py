"""
Trace 存储模块 - Langfuse 风格的本地 Trace 追踪

功能:
- 记录每次评测调用 (Trace)
- 存储各维度评分 (Score)
- 支持按 session_id / eval_type 筛选
- 提供统计分析 API
"""

import sqlite3
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "data" / "traces.db"


def init_db():
    """初始化数据库表结构"""
    # 确保目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        -- Trace 表: 记录每次评测调用
        CREATE TABLE IF NOT EXISTS traces (
            trace_id TEXT PRIMARY KEY,
            session_id TEXT,
            eval_type TEXT DEFAULT 'multi_turn',
            name TEXT DEFAULT 'evaluation',
            input_data TEXT,
            output_data TEXT,
            model TEXT,
            latency_ms INTEGER,
            tokens_used INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Scores 表: 评分记录
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            reasoning TEXT,
            turn_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);
        CREATE INDEX IF NOT EXISTS idx_traces_type ON traces(eval_type);
        CREATE INDEX IF NOT EXISTS idx_scores_trace ON scores(trace_id);
        CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
    """)
    conn.commit()
    return conn


@contextmanager
def get_db():
    """获取数据库连接 (上下文管理器)"""
    conn = init_db()
    try:
        yield conn
    finally:
        conn.close()


class TraceStore:
    """Trace 存储管理器 (Langfuse 风格)"""
    
    @staticmethod
    def create_trace(
        session_id: str,
        name: str = "evaluation",
        eval_type: str = "multi_turn",
        input_data: dict = None,
        output_data: dict = None,
        model: str = None,
        latency_ms: int = None,
        metadata: dict = None
    ) -> str:
        """
        创建新的 Trace 记录
        
        Args:
            session_id: 会话 ID
            name: Trace 名称
            eval_type: 评测类型 (single_turn / multi_turn / agent)
            input_data: 输入数据
            output_data: 输出数据
            model: 使用的模型
            latency_ms: 执行耗时 (毫秒)
            metadata: 扩展元数据
        
        Returns:
            trace_id: 新创建的 Trace ID
        """
        trace_id = str(uuid.uuid4())[:8]
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO traces 
                (trace_id, session_id, eval_type, name, input_data, output_data, model, latency_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace_id,
                session_id,
                eval_type,
                name,
                json.dumps(input_data or {}, ensure_ascii=False),
                json.dumps(output_data or {}, ensure_ascii=False),
                model,
                latency_ms,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            conn.commit()
        
        return trace_id
    
    @staticmethod
    def update_trace(
        trace_id: str,
        output_data: dict = None,
        latency_ms: int = None
    ):
        """更新 Trace 输出数据"""
        with get_db() as conn:
            if output_data is not None:
                conn.execute(
                    "UPDATE traces SET output_data = ? WHERE trace_id = ?",
                    (json.dumps(output_data, ensure_ascii=False), trace_id)
                )
            if latency_ms is not None:
                conn.execute(
                    "UPDATE traces SET latency_ms = ? WHERE trace_id = ?",
                    (latency_ms, trace_id)
                )
            conn.commit()
    
    @staticmethod
    def add_score(
        trace_id: str,
        name: str,
        value: float,
        reasoning: str = "",
        turn_index: int = None
    ):
        """
        为 Trace 添加评分
        
        Args:
            trace_id: 关联的 Trace ID
            name: 维度名称
            value: 评分值 (1-5)
            reasoning: 评分理由
            turn_index: Turn 索引 (多轮场景)
        """
        with get_db() as conn:
            conn.execute("""
                INSERT INTO scores (trace_id, name, value, reasoning, turn_index)
                VALUES (?, ?, ?, ?, ?)
            """, (trace_id, name, value, reasoning, turn_index))
            conn.commit()
    
    @staticmethod
    def get_trace(trace_id: str) -> Optional[Dict]:
        """获取单个 Trace 详情"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()
            
            if not row:
                return None
            
            trace = dict(row)
            trace['input_data'] = json.loads(trace['input_data'] or '{}')
            trace['output_data'] = json.loads(trace['output_data'] or '{}')
            trace['metadata'] = json.loads(trace['metadata'] or '{}')
            
            # 获取关联的评分
            scores = conn.execute(
                "SELECT name, value, reasoning, turn_index FROM scores WHERE trace_id = ? ORDER BY turn_index, id",
                (trace_id,)
            ).fetchall()
            trace['scores'] = [dict(s) for s in scores]
            
            return trace
    
    @staticmethod
    def list_traces(
        session_id: str = None,
        eval_type: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        列出 Trace 记录
        
        Args:
            session_id: 按会话 ID 筛选
            eval_type: 按评测类型筛选
            limit: 返回条数
            offset: 偏移量
        """
        with get_db() as conn:
            query = """
                SELECT t.*, 
                       COUNT(s.id) as score_count,
                       AVG(s.value) as avg_score
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                WHERE 1=1
            """
            params = []
            
            if session_id:
                query += " AND t.session_id = ?"
                params.append(session_id)
            if eval_type:
                query += " AND t.eval_type = ?"
                params.append(eval_type)
            
            query += " GROUP BY t.trace_id ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
    
    @staticmethod
    def get_dimension_stats() -> Dict[str, Dict]:
        """
        获取各维度平均分统计
        
        Returns:
            {"clarity": {"avg": 4.2, "count": 150}, ...}
        """
        with get_db() as conn:
            rows = conn.execute("""
                SELECT name, AVG(value) as avg_score, COUNT(*) as count
                FROM scores
                GROUP BY name
                ORDER BY avg_score ASC
            """).fetchall()
            return {r['name']: {'avg': round(r['avg_score'], 2), 'count': r['count']} for r in rows}
    
    @staticmethod
    def get_low_score_traces(threshold: float = 3, limit: int = 20) -> List[Dict]:
        """获取低分 Trace 列表"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT t.trace_id, t.session_id, t.eval_type, t.created_at,
                       s.name as dimension, s.value as score, s.reasoning
                FROM scores s
                JOIN traces t ON s.trace_id = t.trace_id
                WHERE s.value < ?
                ORDER BY t.created_at DESC
                LIMIT ?
            """, (threshold, limit)).fetchall()
            return [dict(r) for r in rows]
    
    @staticmethod
    def get_session_summary(session_id: str) -> Dict:
        """获取会话汇总"""
        with get_db() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(DISTINCT t.trace_id) as trace_count,
                    AVG(s.value) as avg_score
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                WHERE t.session_id = ?
            """, (session_id,)).fetchone()
            
            dim_scores = conn.execute("""
                SELECT s.name, AVG(s.value) as avg_score
                FROM scores s
                JOIN traces t ON s.trace_id = t.trace_id
                WHERE t.session_id = ?
                GROUP BY s.name
            """, (session_id,)).fetchall()
            
            dim_dict = {r['name']: round(r['avg_score'], 2) for r in dim_scores}
            weak = [d for d, s in dim_dict.items() if s < 3]
            strong = [d for d, s in dim_dict.items() if s >= 4]
            
            return {
                'session_id': session_id,
                'trace_count': stats['trace_count'] or 0,
                'avg_score': round(stats['avg_score'] or 0, 2),
                'dimension_scores': dim_dict,
                'weak_points': weak,
                'strong_points': strong
            }
    
    @staticmethod
    def get_trace_count(eval_type: str = None) -> int:
        """获取 Trace 总数，支持按类型筛选"""
        with get_db() as conn:
            if eval_type and eval_type != 'all':
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM traces WHERE eval_type = ?", 
                    (eval_type,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM traces").fetchone()
            return row['cnt']
    
    @staticmethod
    def get_dashboard_stats(eval_type: str = None) -> Dict:
        """
        获取看板统计数据，支持按评测类型筛选
        
        Args:
            eval_type: 评测类型 (single_turn / multi_turn / agent / None=全部)
        
        Returns:
            {
                'trace_count': 总记录数,
                'avg_score': 平均分,
                'excellent_rate': 优秀率,
                'low_score_count': 低分项数,
                'dimension_stats': {维度: {'avg': x, 'count': n}},
                'score_distribution': [分数分布],
                'recent_trends': [近期趋势]
            }
        """
        with get_db() as conn:
            # 构建筛选条件
            type_filter = ""
            params = []
            if eval_type and eval_type != 'all':
                type_filter = "WHERE t.eval_type = ?"
                params.append(eval_type)
            
            # 1. 基础统计
            basic_sql = f"""
                SELECT 
                    COUNT(DISTINCT t.trace_id) as trace_count,
                    AVG(s.value) as avg_score,
                    SUM(CASE WHEN s.value >= 4 THEN 1 ELSE 0 END) * 100.0 / 
                        NULLIF(COUNT(s.id), 0) as excellent_rate,
                    SUM(CASE WHEN s.value < 3 THEN 1 ELSE 0 END) as low_score_count
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                {type_filter}
            """
            basic = conn.execute(basic_sql, params).fetchone()
            
            # 2. 维度统计
            dim_sql = f"""
                SELECT s.name, AVG(s.value) as avg_score, COUNT(*) as count
                FROM scores s
                JOIN traces t ON s.trace_id = t.trace_id
                {type_filter}
                GROUP BY s.name
                ORDER BY avg_score ASC
            """
            dim_rows = conn.execute(dim_sql, params).fetchall()
            dimension_stats = {r['name']: {'avg': round(r['avg_score'], 2), 'count': r['count']} for r in dim_rows}
            
            # 3. 分数分布 (1-5分各有多少)
            dist_sql = f"""
                SELECT 
                    CASE 
                        WHEN s.value >= 4.5 THEN '5分'
                        WHEN s.value >= 3.5 THEN '4分'
                        WHEN s.value >= 2.5 THEN '3分'
                        WHEN s.value >= 1.5 THEN '2分'
                        ELSE '1分'
                    END as score_level,
                    COUNT(*) as count
                FROM scores s
                JOIN traces t ON s.trace_id = t.trace_id
                {type_filter}
                GROUP BY score_level
                ORDER BY score_level DESC
            """
            dist_rows = conn.execute(dist_sql, params).fetchall()
            score_distribution = {r['score_level']: r['count'] for r in dist_rows}
            
            # 4. 近7天趋势
            trend_sql = f"""
                SELECT 
                    DATE(t.created_at) as date,
                    AVG(s.value) as avg_score,
                    COUNT(DISTINCT t.trace_id) as trace_count
                FROM traces t
                JOIN scores s ON t.trace_id = s.trace_id
                {type_filter}
                {"AND" if type_filter else "WHERE"} t.created_at >= datetime('now', '-7 days')
                GROUP BY DATE(t.created_at)
                ORDER BY date
            """
            trend_params = params.copy()
            trend_rows = conn.execute(trend_sql, trend_params).fetchall()
            recent_trends = [{'date': r['date'], 'avg_score': round(r['avg_score'], 2), 'count': r['trace_count']} for r in trend_rows]
            
            return {
                'trace_count': basic['trace_count'] or 0,
                'avg_score': round(basic['avg_score'] or 0, 2),
                'excellent_rate': round(basic['excellent_rate'] or 0, 1),
                'low_score_count': basic['low_score_count'] or 0,
                'dimension_stats': dimension_stats,
                'score_distribution': score_distribution,
                'recent_trends': recent_trends
            }
    
    @staticmethod
    def get_stats_by_type() -> Dict[str, Dict]:
        """
        按评测类型分组统计
        
        Returns:
            {
                "single_turn": {"count": 156, "avg": 4.2, "low_count": 12},
                "multi_turn": {"count": 23, "avg": 4.1, "low_count": 5},
                "agent": {"count": 45, "avg": 4.3, "low_count": 8}
            }
        """
        with get_db() as conn:
            # 按类型统计基本信息
            rows = conn.execute("""
                SELECT 
                    t.eval_type,
                    COUNT(DISTINCT t.trace_id) as count,
                    AVG(s.value) as avg_score
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                GROUP BY t.eval_type
            """).fetchall()
            
            result = {}
            for r in rows:
                eval_type = r['eval_type'] or 'multi_turn'
                result[eval_type] = {
                    'count': r['count'],
                    'avg': round(r['avg_score'] or 0, 2),
                    'low_count': 0
                }
            
            # 获取低分数量 (< 3)
            low_rows = conn.execute("""
                SELECT t.eval_type, COUNT(DISTINCT t.trace_id) as low_count
                FROM traces t
                JOIN scores s ON t.trace_id = s.trace_id
                WHERE s.value < 3
                GROUP BY t.eval_type
            """).fetchall()
            
            for r in low_rows:
                eval_type = r['eval_type'] or 'multi_turn'
                if eval_type in result:
                    result[eval_type]['low_count'] = r['low_count']
            
            return result
    
    @staticmethod
    def get_turn_scores(trace_id: str) -> List[Dict]:
        """
        获取多轮对话每个 Turn 的评分
        
        Args:
            trace_id: Trace ID
            
        Returns:
            [{"turn_index": 0, "avg_score": 4.2, "scores": {...}}, ...]
        """
        with get_db() as conn:
            rows = conn.execute("""
                SELECT turn_index, name, value, reasoning
                FROM scores
                WHERE trace_id = ? AND turn_index IS NOT NULL
                ORDER BY turn_index, name
            """, (trace_id,)).fetchall()
            
            # 按 turn_index 分组
            turns = {}
            for r in rows:
                idx = r['turn_index']
                if idx not in turns:
                    turns[idx] = {'turn_index': idx, 'scores': {}, 'total': 0, 'count': 0}
                turns[idx]['scores'][r['name']] = {
                    'value': r['value'],
                    'reasoning': r['reasoning']
                }
                turns[idx]['total'] += r['value']
                turns[idx]['count'] += 1
            
            # 计算每个 Turn 的平均分
            result = []
            for idx in sorted(turns.keys()):
                t = turns[idx]
                t['avg_score'] = round(t['total'] / t['count'], 2) if t['count'] > 0 else 0
                del t['total']
                del t['count']
                result.append(t)
            
            return result
    
    @staticmethod
    def get_traces_with_messages(
        eval_type: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        获取 Trace 列表，包含输入输出消息内容
        
        Args:
            eval_type: 按评测类型筛选
            limit: 返回条数
        """
        with get_db() as conn:
            query = """
                SELECT t.*, 
                       COUNT(s.id) as score_count,
                       AVG(s.value) as avg_score
                FROM traces t
                LEFT JOIN scores s ON t.trace_id = s.trace_id
                WHERE 1=1
            """
            params = []
            
            if eval_type:
                query += " AND t.eval_type = ?"
                params.append(eval_type)
            
            query += " GROUP BY t.trace_id ORDER BY t.created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            traces = []
            for r in rows:
                trace = dict(r)
                trace['input_data'] = json.loads(trace['input_data'] or '{}')
                trace['output_data'] = json.loads(trace['output_data'] or '{}')
                trace['metadata'] = json.loads(trace['metadata'] or '{}')
                
                # 获取关联的评分
                scores = conn.execute(
                    "SELECT name, value, reasoning, turn_index FROM scores WHERE trace_id = ? ORDER BY turn_index, id",
                    (trace['trace_id'],)
                ).fetchall()
                trace['scores'] = [dict(s) for s in scores]
                
                traces.append(trace)
            
            return traces



    @staticmethod
    def get_viz_data(eval_type: str = None, limit: int = 1000) -> List[Dict]:
        """
        获取用于可视化的轻量级 Trace 数据
        
        只提取: trace_id, eval_type, avg_score, latency_ms, metadata, created_at, 以及详细 scores
        """
        with get_db() as conn:
            # 1. 查询 Traces
            params = []
            where_clause = ""
            if eval_type and eval_type != 'all':
                where_clause = "WHERE eval_type = ?"
                params.append(eval_type)
                
            sql = f"""
                SELECT trace_id, eval_type, latency_ms, metadata, created_at, 
                       (SELECT AVG(value) FROM scores WHERE trace_id = traces.trace_id) as avg_score
                FROM traces
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            
            # 2. 获取所有 Scores (为了画 Heatmap)
            # 为了性能，可以一次性拉取这些 Traces 的所有 Scores
            trace_ids = [r['trace_id'] for r in rows]
            if not trace_ids:
                return []
                
            placeholders = ','.join(['?'] * len(trace_ids))
            score_sql = f"""
                SELECT trace_id, name, value 
                FROM scores 
                WHERE trace_id IN ({placeholders})
            """
            score_rows = conn.execute(score_sql, trace_ids).fetchall()
            
            # 组装 Scores
            scores_map = {}
            for sr in score_rows:
                tid = sr['trace_id']
                if tid not in scores_map:
                    scores_map[tid] = {}
                scores_map[tid][sr['name']] = sr['value']
                
            # 组装结果
            results = []
            for r in rows:
                meta = {}
                try:
                    if r['metadata']:
                        meta = json.loads(r['metadata']) if isinstance(r['metadata'], str) else r['metadata']
                except:
                    pass
                
                results.append({
                    'trace_id': r['trace_id'],
                    'eval_type': r['eval_type'],
                    'latency_ms': r['latency_ms'],
                    'created_at': r['created_at'],
                    'avg_score': r['avg_score'] or 0,
                    'metrics': meta.get('metrics', {}), # 提取 metrics (tokens等)
                    'scores': scores_map.get(r['trace_id'], {})
                })
                
            return results


# 便捷函数
def create_trace(**kwargs) -> str:
    return TraceStore.create_trace(**kwargs)

def add_score(**kwargs):
    return TraceStore.add_score(**kwargs)

def list_traces(**kwargs) -> List[Dict]:
    return TraceStore.list_traces(**kwargs)

def get_trace(trace_id: str) -> Optional[Dict]:
    return TraceStore.get_trace(trace_id)


if __name__ == "__main__":
    # 测试代码
    print("🧪 Testing TraceStore...")
    
    # 初始化数据库
    init_db()
    print("✅ Database initialized")
    
    # 创建测试 Trace
    trace_id = TraceStore.create_trace(
        session_id="test_session_001",
        eval_type="multi_turn",
        input_data={"messages": [{"role": "user", "content": "Hello"}]},
        model="gpt-4o-mini"
    )
    print(f"✅ Created trace: {trace_id}")
    
    # 添加评分
    TraceStore.add_score(trace_id, "clarity", 4.5, "表达清晰", turn_index=0)
    TraceStore.add_score(trace_id, "accuracy", 5.0, "信息准确", turn_index=0)
    TraceStore.add_score(trace_id, "proactivity", 3.5, "略显被动", turn_index=0)
    print("✅ Added scores")
    
    # 获取 Trace 详情
    detail = TraceStore.get_trace(trace_id)
    print(f"✅ Trace detail: {detail['trace_id']}, scores: {len(detail['scores'])}")
    
    # 列表查询
    traces = TraceStore.list_traces(limit=5)
    print(f"✅ Listed {len(traces)} traces")
    
    # 维度统计
    stats = TraceStore.get_dimension_stats()
    print(f"✅ Dimension stats: {stats}")
    
    print("\n🎉 All tests passed!")
