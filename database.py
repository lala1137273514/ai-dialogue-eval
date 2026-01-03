"""
数据库模块 - SQLite 存储评测结果

表结构：
- eval_batches: 评测批次
- session_results: 会话评测结果
- turn_evaluations: Turn 级评测详情
- low_score_analyses: 低分深度分析
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class EvalDatabase:
    """评测结果数据库"""
    
    def __init__(self, db_path: str = "data/eval_results.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """创建表结构"""
        cursor = self.conn.cursor()
        
        # 评测批次
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_count INTEGER,
                turn_count INTEGER,
                avg_score REAL,
                low_score_count INTEGER,
                workflow_file TEXT,
                rubric_file TEXT,
                log_file TEXT
            )
        """)
        
        # 会话评测结果
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER REFERENCES eval_batches(id),
                session_id TEXT,
                domain TEXT,
                avg_score REAL,
                turn_count INTEGER,
                low_score_count INTEGER
            )
        """)
        
        # Turn 级评测详情
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turn_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_result_id INTEGER REFERENCES session_results(id),
                turn_index INTEGER,
                target_response TEXT,
                avg_score REAL,
                min_score INTEGER,
                combined_score REAL,
                overall_analysis TEXT,
                scores_json TEXT
            )
        """)
        
        # 低分深度分析
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS low_score_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_evaluation_id INTEGER REFERENCES turn_evaluations(id),
                session_id TEXT,
                turn_index INTEGER,
                combined_score REAL,
                scores_json TEXT,
                overall_analysis TEXT,
                target_response TEXT,
                root_cause TEXT,
                traced_node_id TEXT,
                traced_node_title TEXT,
                prompt_issue TEXT,
                modification_suggestion TEXT
            )
        """)
        
        self.conn.commit()
    
    def save_evaluation_results(self, 
                                 results: List[Dict], 
                                 workflow_file: str = None,
                                 rubric_file: str = None,
                                 log_file: str = None) -> int:
        """
        保存评测结果到数据库
        
        Args:
            results: 评测结果列表
            workflow_file: 工作流文件路径
            rubric_file: 评分标准文件路径
            log_file: 日志文件路径
        
        Returns:
            批次 ID
        """
        cursor = self.conn.cursor()
        
        # 统计数据
        total_turns = sum(len(s.get('evaluations', [])) for s in results)
        total_low_score = sum(len(s.get('low_score_analyses', [])) for s in results)
        
        # 计算平均分
        all_scores = []
        for sess in results:
            for ev in sess.get('evaluations', []):
                all_scores.append(ev.get('combined_score', ev.get('avg_score', 3)))
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # 创建批次
        cursor.execute("""
            INSERT INTO eval_batches 
            (session_count, turn_count, avg_score, low_score_count, workflow_file, rubric_file, log_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (len(results), total_turns, round(avg_score, 2), total_low_score, 
              workflow_file, rubric_file, log_file))
        
        batch_id = cursor.lastrowid
        
        # 保存每个会话
        for sess in results:
            session_id = sess.get('session_id', 'unknown')
            evals = sess.get('evaluations', [])
            analyses = sess.get('low_score_analyses', [])
            
            # 会话平均分
            if evals:
                sess_avg = sum(e.get('combined_score', e.get('avg_score', 3)) for e in evals) / len(evals)
            else:
                sess_avg = 0
            
            cursor.execute("""
                INSERT INTO session_results 
                (batch_id, session_id, domain, avg_score, turn_count, low_score_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (batch_id, session_id, sess.get('domain', 'general'), 
                  round(sess_avg, 2), len(evals), len(analyses)))
            
            session_result_id = cursor.lastrowid
            
            # 保存每个 Turn 评测
            for ev in evals:
                scores = ev.get('scores', {})
                min_score = min(scores.values()) if scores else 3
                
                cursor.execute("""
                    INSERT INTO turn_evaluations 
                    (session_result_id, turn_index, target_response, avg_score, 
                     min_score, combined_score, overall_analysis, scores_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_result_id, ev.get('turn_index', 0),
                      ev.get('target_response', '')[:1000],
                      ev.get('avg_score', 3), min_score,
                      ev.get('combined_score', ev.get('avg_score', 3)),
                      ev.get('overall_analysis', ''),
                      json.dumps(scores, ensure_ascii=False)))
                
                turn_eval_id = cursor.lastrowid
                
                # 检查是否有对应的低分分析
                for an in analyses:
                    if an.get('turn_index') == ev.get('turn_index'):
                        cursor.execute("""
                            INSERT INTO low_score_analyses 
                            (turn_evaluation_id, session_id, turn_index, combined_score,
                             scores_json, overall_analysis, target_response,
                             root_cause, traced_node_id, traced_node_title, 
                             prompt_issue, modification_suggestion)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (turn_eval_id, session_id, an.get('turn_index', 0),
                              an.get('combined_score', an.get('avg_score', 0)),
                              json.dumps(an.get('scores', {}), ensure_ascii=False),
                              an.get('overall_analysis', ''),
                              an.get('target_response', '')[:1000],
                              an.get('root_cause', ''),
                              an.get('traced_node_id', ''),
                              an.get('traced_node_title', ''),
                              an.get('prompt_issue', ''),
                              an.get('modification_suggestion', '')))
        
        self.conn.commit()
        return batch_id
    
    def get_all_batches(self) -> List[Dict]:
        """获取所有评测批次"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, created_at, session_count, turn_count, avg_score, 
                   low_score_count, workflow_file, rubric_file, log_file
            FROM eval_batches
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_batch_details(self, batch_id: int) -> Dict:
        """获取批次详细信息"""
        cursor = self.conn.cursor()
        
        # 批次信息
        cursor.execute("SELECT * FROM eval_batches WHERE id = ?", (batch_id,))
        batch = dict(cursor.fetchone() or {})
        
        # 会话列表
        cursor.execute("""
            SELECT * FROM session_results WHERE batch_id = ?
        """, (batch_id,))
        sessions = [dict(row) for row in cursor.fetchall()]
        
        batch['sessions'] = sessions
        return batch
    
    def get_session_turns(self, session_result_id: int) -> List[Dict]:
        """获取会话的所有 Turn 评测"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM turn_evaluations WHERE session_result_id = ?
            ORDER BY turn_index
        """, (session_result_id,))
        
        turns = []
        for row in cursor.fetchall():
            turn = dict(row)
            turn['scores'] = json.loads(turn.get('scores_json', '{}'))
            turns.append(turn)
        
        return turns
    
    def get_low_score_analyses(self, batch_id: int = None) -> List[Dict]:
        """获取低分分析列表"""
        cursor = self.conn.cursor()
        
        if batch_id:
            cursor.execute("""
                SELECT lsa.* 
                FROM low_score_analyses lsa
                JOIN turn_evaluations te ON lsa.turn_evaluation_id = te.id
                JOIN session_results sr ON te.session_result_id = sr.id
                WHERE sr.batch_id = ?
            """, (batch_id,))
        else:
            cursor.execute("SELECT * FROM low_score_analyses ORDER BY id DESC LIMIT 100")
        
        analyses = []
        for row in cursor.fetchall():
            an = dict(row)
            an['scores'] = json.loads(an.get('scores_json', '{}'))
            analyses.append(an)
        
        return analyses
    
    def get_statistics(self) -> Dict:
        """获取整体统计信息"""
        cursor = self.conn.cursor()
        
        # 批次总数
        cursor.execute("SELECT COUNT(*) FROM eval_batches")
        batch_count = cursor.fetchone()[0]
        
        # 评测总数
        cursor.execute("SELECT COUNT(*) FROM turn_evaluations")
        eval_count = cursor.fetchone()[0]
        
        # 低分分析总数
        cursor.execute("SELECT COUNT(*) FROM low_score_analyses")
        low_score_count = cursor.fetchone()[0]
        
        # 平均分
        cursor.execute("SELECT AVG(combined_score) FROM turn_evaluations")
        avg_score = cursor.fetchone()[0] or 0
        
        return {
            "batch_count": batch_count,
            "eval_count": eval_count,
            "low_score_count": low_score_count,
            "avg_score": round(avg_score, 2)
        }
    
    def delete_batch(self, batch_id: int) -> bool:
        """删除评测批次及其关联数据"""
        cursor = self.conn.cursor()
        
        try:
            # 获取所有关联的 session_result_id
            cursor.execute("SELECT id FROM session_results WHERE batch_id = ?", (batch_id,))
            session_ids = [row[0] for row in cursor.fetchall()]
            
            # 获取所有关联的 turn_evaluation_id
            turn_ids = []
            for sid in session_ids:
                cursor.execute("SELECT id FROM turn_evaluations WHERE session_result_id = ?", (sid,))
                turn_ids.extend([row[0] for row in cursor.fetchall()])
            
            # 删除低分分析
            for tid in turn_ids:
                cursor.execute("DELETE FROM low_score_analyses WHERE turn_evaluation_id = ?", (tid,))
            
            # 删除 turn 评测
            for sid in session_ids:
                cursor.execute("DELETE FROM turn_evaluations WHERE session_result_id = ?", (sid,))
            
            # 删除会话结果
            cursor.execute("DELETE FROM session_results WHERE batch_id = ?", (batch_id,))
            
            # 删除批次
            cursor.execute("DELETE FROM eval_batches WHERE id = ?", (batch_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            return False
    
    def update_batch_note(self, batch_id: int, note: str) -> bool:
        """更新批次备注"""
        cursor = self.conn.cursor()
        try:
            # 先检查是否有 note 列，没有则添加
            cursor.execute("PRAGMA table_info(eval_batches)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'note' not in columns:
                cursor.execute("ALTER TABLE eval_batches ADD COLUMN note TEXT")
            
            cursor.execute("UPDATE eval_batches SET note = ? WHERE id = ?", (note, batch_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


# 全局数据库实例
_db_instance = None

def get_database(db_path: str = "data/eval_results.db") -> EvalDatabase:
    """获取数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = EvalDatabase(db_path)
    return _db_instance
