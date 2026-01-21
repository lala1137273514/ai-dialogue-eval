"""
Dify 数据存储管理器 - v1.0.0

功能:
- Dify App 配置管理 (CRUD)
- 评测集管理 (CRUD)
- 对话记录管理 (CRUD + 筛选)
- 评测结果存储 (支持重新评测)
"""

import sqlite3
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path

# 数据库路径 (与 trace_store.py 共用)
DB_PATH = str(Path(__file__).parent / "data" / "traces.db")


def init_dify_tables():
    """初始化 Dify 相关数据表"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        -- Dify App 配置表
        CREATE TABLE IF NOT EXISTS dify_apps (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dify_host TEXT DEFAULT 'https://api.dify.ai',
            api_key TEXT NOT NULL,
            app_type TEXT DEFAULT 'chat',
            description TEXT,
            public_key TEXT UNIQUE,
            secret_key TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 评测集表
        CREATE TABLE IF NOT EXISTS eval_datasets (
            id TEXT PRIMARY KEY,
            app_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            evaluator_id TEXT,
            source_type TEXT DEFAULT 'dify',
            record_count INTEGER DEFAULT 0,
            evaluated_count INTEGER DEFAULT 0,
            avg_score REAL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 对话记录表
        CREATE TABLE IF NOT EXISTS dataset_records (
            id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            dify_trace_id TEXT,
            dify_conversation_id TEXT,
            inputs TEXT,
            query TEXT,
            output TEXT,
            model TEXT,
            total_tokens INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            latency_ms INTEGER,
            total_cost REAL,
            source TEXT DEFAULT 'offline',
            eval_status TEXT DEFAULT 'pending',
            eval_count INTEGER DEFAULT 0,
            last_eval_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 评测结果表
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            evaluator_id TEXT,
            eval_version INTEGER DEFAULT 1,
            scores TEXT,
            avg_score REAL,
            reasonings TEXT,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration_ms INTEGER
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_datasets_app ON eval_datasets(app_id);
        CREATE INDEX IF NOT EXISTS idx_records_dataset ON dataset_records(dataset_id);
        CREATE INDEX IF NOT EXISTS idx_records_status ON dataset_records(eval_status);
        CREATE INDEX IF NOT EXISTS idx_records_created ON dataset_records(created_at);
        CREATE INDEX IF NOT EXISTS idx_results_record ON evaluation_results(record_id);
    """)
    conn.commit()
    
    # 🆕 迁移：为旧表添加新列（如果不存在）
    try:
        # 检查 public_key 列是否存在
        cursor = conn.execute("PRAGMA table_info(dify_apps)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'public_key' not in columns:
            conn.execute("ALTER TABLE dify_apps ADD COLUMN public_key TEXT")
            print("[DifyStore] 迁移: 添加 public_key 列")
        
        if 'secret_key' not in columns:
            conn.execute("ALTER TABLE dify_apps ADD COLUMN secret_key TEXT")
            print("[DifyStore] 迁移: 添加 secret_key 列")
        
        conn.commit()
    except Exception as e:
        print(f"[DifyStore] 迁移警告: {e}")
    
    conn.close()


@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DifyStore:
    """Dify 数据存储管理器"""
    
    # ========== dify_apps 表操作 ==========
    
    @classmethod
    def create_app(cls, name: str, dify_host: str, api_key: str, 
                   app_type: str = "chat", description: str = "") -> str:
        """创建 Dify App 配置，自动生成独立凭证，并创建关联评测集"""
        import secrets
        
        app_id = str(uuid.uuid4())[:8]
        # 生成独立凭证
        public_key = f"pk-{secrets.token_hex(16)}"
        secret_key = f"sk-{secrets.token_hex(32)}"
        
        with get_db() as conn:
            # 创建 App
            conn.execute("""
                INSERT INTO dify_apps (id, name, dify_host, api_key, app_type, description, public_key, secret_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (app_id, name, dify_host, api_key, app_type, description, public_key, secret_key))
            
            # 🆕 自动创建关联的评测集
            dataset_id = str(uuid.uuid4())[:8]
            dataset_name = f"{name}-评测集"
            conn.execute("""
                INSERT INTO eval_datasets (id, app_id, name, source_type, description)
                VALUES (?, ?, ?, 'dify', '自动创建的App评测集，所有回传数据存入此表')
            """, (dataset_id, app_id, dataset_name))
            
            conn.commit()
        
        print(f"[DifyStore] ✅ App 创建成功: {app_id}, 评测集: {dataset_id}")
        return app_id
    
    @classmethod
    def get_app(cls, app_id: str) -> Optional[Dict]:
        """获取 App 详情"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM dify_apps WHERE id = ? AND is_active = 1",
                (app_id,)
            ).fetchone()
            
            if row:
                return dict(row)
            return None
    
    @classmethod
    def list_apps(cls, include_inactive: bool = False) -> List[Dict]:
        """列出所有 App"""
        with get_db() as conn:
            if include_inactive:
                rows = conn.execute("SELECT * FROM dify_apps ORDER BY created_at DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM dify_apps WHERE is_active = 1 ORDER BY created_at DESC"
                ).fetchall()
            
            return [dict(row) for row in rows]
    
    @classmethod
    def update_app(cls, app_id: str, **kwargs) -> bool:
        """更新 App 配置"""
        allowed_fields = ['name', 'dify_host', 'api_key', 'app_type', 'description', 'is_active']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [app_id]
        
        with get_db() as conn:
            conn.execute(f"UPDATE dify_apps SET {set_clause} WHERE id = ?", values)
            conn.commit()
        
        return True
    
    @classmethod
    def delete_app(cls, app_id: str) -> bool:
        """删除 App (软删除)"""
        with get_db() as conn:
            conn.execute("UPDATE dify_apps SET is_active = 0 WHERE id = ?", (app_id,))
            conn.commit()
        return True
    
    @classmethod
    def get_app_by_credentials(cls, public_key: str, secret_key: str = None) -> Optional[Dict]:
        """根据凭证查找 App"""
        with get_db() as conn:
            if secret_key:
                row = conn.execute(
                    "SELECT * FROM dify_apps WHERE public_key = ? AND secret_key = ? AND is_active = 1",
                    (public_key, secret_key)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM dify_apps WHERE public_key = ? AND is_active = 1",
                    (public_key,)
                ).fetchone()
            
            if row:
                return dict(row)
            return None
    
    @classmethod
    def get_or_create_daily_dataset(cls, app_id: str, app_name: str) -> str:
        """获取或创建当日评测集"""
        today = datetime.now().strftime('%Y-%m-%d')
        dataset_name = f"{app_name}-{today}"
        
        with get_db() as conn:
            # 查找今日评测集
            row = conn.execute(
                "SELECT id FROM eval_datasets WHERE app_id = ? AND name = ?",
                (app_id, dataset_name)
            ).fetchone()
            
            if row:
                return row['id']
            
            # 创建新评测集
            dataset_id = str(uuid.uuid4())[:8]
            conn.execute("""
                INSERT INTO eval_datasets (id, app_id, name, source_type, description)
                VALUES (?, ?, ?, 'dify', '自动创建的每日评测集')
            """, (dataset_id, app_id, dataset_name))
            conn.commit()
            
            return dataset_id
    
    # ========== eval_datasets 表操作 ==========
    
    @classmethod
    def create_dataset(cls, name: str, app_id: str = None, 
                       evaluator_id: str = None, source_type: str = "dify",
                       description: str = "") -> str:
        """创建评测集"""
        dataset_id = str(uuid.uuid4())[:8]
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO eval_datasets (id, app_id, name, evaluator_id, source_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dataset_id, app_id, name, evaluator_id, source_type, description))
            conn.commit()
        
        return dataset_id
    
    @classmethod
    def get_dataset(cls, dataset_id: str) -> Optional[Dict]:
        """获取评测集详情"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM eval_datasets WHERE id = ?",
                (dataset_id,)
            ).fetchone()
            
            if row:
                return dict(row)
            return None
    
    @classmethod
    def list_datasets(cls, app_id: str = None) -> List[Dict]:
        """列出评测集"""
        with get_db() as conn:
            if app_id:
                rows = conn.execute(
                    "SELECT * FROM eval_datasets WHERE app_id = ? ORDER BY created_at DESC",
                    (app_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM eval_datasets ORDER BY created_at DESC"
                ).fetchall()
            
            return [dict(row) for row in rows]
    
    @classmethod
    def delete_dataset(cls, dataset_id: str) -> bool:
        """删除评测集及其所有记录"""
        with get_db() as conn:
            # 删除评测结果
            conn.execute("""
                DELETE FROM evaluation_results 
                WHERE record_id IN (SELECT id FROM dataset_records WHERE dataset_id = ?)
            """, (dataset_id,))
            
            # 删除记录
            conn.execute("DELETE FROM dataset_records WHERE dataset_id = ?", (dataset_id,))
            
            # 删除评测集
            conn.execute("DELETE FROM eval_datasets WHERE id = ?", (dataset_id,))
            conn.commit()
        
        return True
    
    # ========== dataset_records 表操作 ==========
    
    @classmethod
    def add_record(cls, dataset_id: str, inputs: str, query: str, output: str,
                   source: str = "offline", **kwargs) -> str:
        """添加对话记录"""
        record_id = str(uuid.uuid4())[:8]
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO dataset_records 
                (id, dataset_id, inputs, query, output, source, 
                 model, total_tokens, prompt_tokens, completion_tokens, 
                 latency_ms, total_cost, dify_trace_id, dify_conversation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, dataset_id, inputs, query, output, source,
                kwargs.get('model'), kwargs.get('total_tokens'), 
                kwargs.get('prompt_tokens'), kwargs.get('completion_tokens'),
                kwargs.get('latency_ms'), kwargs.get('total_cost'),
                kwargs.get('dify_trace_id'), kwargs.get('dify_conversation_id')
            ))
            
            # 更新评测集记录数
            conn.execute("""
                UPDATE eval_datasets SET record_count = record_count + 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), dataset_id))
            
            conn.commit()
        
        return record_id
    
    @classmethod
    def get_record(cls, record_id: str) -> Optional[Dict]:
        """获取记录详情"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM dataset_records WHERE id = ?",
                (record_id,)
            ).fetchone()
            
            if row:
                return dict(row)
            return None
    
    @classmethod
    def list_records(cls, dataset_id: str, status: str = None,
                     start_date: str = None, end_date: str = None,
                     limit: int = 100) -> List[Dict]:
        """列出记录（支持筛选）"""
        with get_db() as conn:
            sql = "SELECT * FROM dataset_records WHERE dataset_id = ?"
            params = [dataset_id]
            
            if status:
                sql += " AND eval_status = ?"
                params.append(status)
            
            if start_date:
                sql += " AND created_at >= ?"
                params.append(start_date)
            
            if end_date:
                sql += " AND created_at <= ?"
                params.append(end_date)
            
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
    
    @classmethod
    def update_record_status(cls, record_id: str, status: str, 
                             eval_count: int = None) -> bool:
        """更新记录评测状态"""
        with get_db() as conn:
            if eval_count is not None:
                conn.execute("""
                    UPDATE dataset_records 
                    SET eval_status = ?, eval_count = ?, last_eval_at = ?
                    WHERE id = ?
                """, (status, eval_count, datetime.now().isoformat(), record_id))
            else:
                conn.execute("""
                    UPDATE dataset_records 
                    SET eval_status = ?, last_eval_at = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), record_id))
            conn.commit()
        
        return True
    
    # ========== evaluation_results 表操作 ==========
    
    @classmethod
    def save_evaluation_result(cls, record_id: str, evaluator_id: str,
                               scores: str, avg_score: float, reasonings: str,
                               duration_ms: int) -> int:
        """保存评测结果"""
        with get_db() as conn:
            # 获取当前版本号
            row = conn.execute("""
                SELECT MAX(eval_version) as max_version 
                FROM evaluation_results WHERE record_id = ?
            """, (record_id,)).fetchone()
            
            next_version = (row['max_version'] or 0) + 1
            
            cursor = conn.execute("""
                INSERT INTO evaluation_results 
                (record_id, evaluator_id, eval_version, scores, avg_score, reasonings, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (record_id, evaluator_id, next_version, scores, avg_score, reasonings, duration_ms))
            
            result_id = cursor.lastrowid
            conn.commit()
        
        return result_id
    
    @classmethod
    def get_record_evaluations(cls, record_id: str) -> List[Dict]:
        """获取记录的所有评测历史"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM evaluation_results 
                WHERE record_id = ? 
                ORDER BY eval_version ASC
            """, (record_id,)).fetchall()
            
            return [dict(row) for row in rows]
    
    @classmethod
    def get_latest_evaluation(cls, record_id: str) -> Optional[Dict]:
        """获取最新评测结果"""
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM evaluation_results 
                WHERE record_id = ? 
                ORDER BY eval_version DESC 
                LIMIT 1
            """, (record_id,)).fetchone()
            
            if row:
                return dict(row)
            return None


# 模块初始化时创建表
if __name__ != "__main__":
    try:
        init_dify_tables()
    except Exception as e:
        print(f"[DifyStore] 初始化表结构时出错: {e}")
