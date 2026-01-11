"""
评估器存储模块 - v1.0.0

功能:
- 评估器 CRUD 操作
- 版本管理
- 默认评估器设置
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class EvaluatorStore:
    """评估器存储管理器"""
    
    DB_PATH = "data/eval_results.db"
    
    @classmethod
    def _get_conn(cls):
        """获取数据库连接"""
        conn = sqlite3.connect(cls.DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    @classmethod
    def create_evaluator(cls,
                        name: str,
                        dimensions: List[Dict],
                        eval_types: List[str] = None,
                        version: str = "1.0",
                        description: str = "",
                        is_default: bool = False,
                        is_system: bool = False,
                        created_by: str = "manual",
                        parent_version: str = None) -> str:
        """
        创建评估器
        
        Args:
            name: 评估器名称
            dimensions: 评估维度列表
            eval_types: 适用的评测类型 ["single_turn", "multi_turn", "agent"]
            version: 版本号
            description: 描述
            is_default: 是否设为默认
            is_system: 是否为系统评估器 (不可删除)
            created_by: 创建来源 (manual/llm_generated/imported/migrated)
            parent_version: 父版本 ID (用于版本追溯)
        
        Returns:
            evaluator_id: 新创建的评估器 ID
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        evaluator_id = f"eval_{str(uuid.uuid4())[:8]}"
        
        if eval_types is None:
            eval_types = ["single_turn", "multi_turn", "agent"]
        
        # 如果设为默认，先清除其他默认评估器
        if is_default:
            cursor.execute("UPDATE evaluators SET is_default = 0 WHERE is_default = 1")
        
        cursor.execute("""
            INSERT INTO evaluators 
            (evaluator_id, name, version, description, eval_types, dimensions, 
             is_default, is_system, created_by, parent_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evaluator_id,
            name,
            version,
            description,
            json.dumps(eval_types, ensure_ascii=False),
            json.dumps(dimensions, ensure_ascii=False),
            1 if is_default else 0,
            1 if is_system else 0,
            created_by,
            parent_version
        ))
        
        conn.commit()
        conn.close()
        
        return evaluator_id
    
    @classmethod
    def get_evaluator(cls, evaluator_id: str) -> Optional[Dict]:
        """
        获取评估器详情
        
        Args:
            evaluator_id: 评估器 ID
        
        Returns:
            评估器详情字典，未找到返回 None
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM evaluators WHERE evaluator_id = ?", (evaluator_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return cls._row_to_dict(row)
        return None
    
    @classmethod
    def list_evaluators(cls, include_system: bool = True, eval_type: str = None) -> List[Dict]:
        """
        列出所有评估器
        
        Args:
            include_system: 是否包含系统评估器
            eval_type: 筛选适用的评测类型
        
        Returns:
            评估器列表
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        query = "SELECT * FROM evaluators"
        conditions = []
        params = []
        
        if not include_system:
            conditions.append("is_system = 0")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY is_default DESC, created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        evaluators = [cls._row_to_dict(row) for row in rows]
        
        # 筛选 eval_type
        if eval_type:
            evaluators = [
                e for e in evaluators 
                if eval_type in e.get('eval_types', [])
            ]
        
        return evaluators
    
    @classmethod
    def update_evaluator(cls,
                        evaluator_id: str,
                        name: str = None,
                        dimensions: List[Dict] = None,
                        eval_types: List[str] = None,
                        description: str = None,
                        version: str = None) -> bool:
        """
        更新评估器
        
        Args:
            evaluator_id: 评估器 ID
            其他参数: 需要更新的字段
        
        Returns:
            是否更新成功
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        # 检查是否为系统评估器
        cursor.execute("SELECT is_system FROM evaluators WHERE evaluator_id = ?", (evaluator_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        if row['is_system']:
            conn.close()
            raise ValueError("系统评估器不可修改")
        
        # 构建更新语句
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if dimensions is not None:
            updates.append("dimensions = ?")
            params.append(json.dumps(dimensions, ensure_ascii=False))
        if eval_types is not None:
            updates.append("eval_types = ?")
            params.append(json.dumps(eval_types, ensure_ascii=False))
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if version is not None:
            updates.append("version = ?")
            params.append(version)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(evaluator_id)
            
            query = f"UPDATE evaluators SET {', '.join(updates)} WHERE evaluator_id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return True
    
    @classmethod
    def delete_evaluator(cls, evaluator_id: str) -> bool:
        """
        删除评估器
        
        Args:
            evaluator_id: 评估器 ID
        
        Returns:
            是否删除成功
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        # 检查是否为系统评估器
        cursor.execute("SELECT is_system, is_default FROM evaluators WHERE evaluator_id = ?", (evaluator_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        if row['is_system']:
            conn.close()
            raise ValueError("系统评估器不可删除")
        
        cursor.execute("DELETE FROM evaluators WHERE evaluator_id = ?", (evaluator_id,))
        conn.commit()
        conn.close()
        
        return True
    
    @classmethod
    def set_default_evaluator(cls, evaluator_id: str) -> bool:
        """
        设置默认评估器
        
        Args:
            evaluator_id: 评估器 ID
        
        Returns:
            是否设置成功
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        # 检查评估器是否存在
        cursor.execute("SELECT id FROM evaluators WHERE evaluator_id = ?", (evaluator_id,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # 清除所有默认标记
        cursor.execute("UPDATE evaluators SET is_default = 0")
        
        # 设置新的默认
        cursor.execute("UPDATE evaluators SET is_default = 1 WHERE evaluator_id = ?", (evaluator_id,))
        
        conn.commit()
        conn.close()
        return True
    
    @classmethod
    def get_default_evaluator(cls) -> Optional[Dict]:
        """
        获取默认评估器
        
        Returns:
            默认评估器详情，未找到返回 None
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM evaluators WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return cls._row_to_dict(row)
        return None
    
    @classmethod
    def create_version(cls, evaluator_id: str, new_version: str = None) -> Optional[str]:
        """
        基于现有评估器创建新版本
        
        Args:
            evaluator_id: 源评估器 ID
            new_version: 新版本号 (可选，自动递增)
        
        Returns:
            新评估器 ID
        """
        # 获取原评估器
        original = cls.get_evaluator(evaluator_id)
        if not original:
            return None
        
        # 自动递增版本号
        if new_version is None:
            try:
                parts = original['version'].split('.')
                parts[-1] = str(int(parts[-1]) + 1)
                new_version = '.'.join(parts)
            except:
                new_version = original['version'] + ".1"
        
        # 创建新版本
        new_id = cls.create_evaluator(
            name=original['name'],
            dimensions=original['dimensions'],
            eval_types=original['eval_types'],
            version=new_version,
            description=original.get('description', ''),
            is_default=False,
            is_system=False,
            created_by="versioned",
            parent_version=evaluator_id
        )
        
        return new_id
    
    @classmethod
    def get_version_history(cls, evaluator_id: str) -> List[Dict]:
        """
        获取评估器的版本历史
        
        Args:
            evaluator_id: 评估器 ID
        
        Returns:
            版本历史列表
        """
        conn = cls._get_conn()
        cursor = conn.cursor()
        
        # 获取当前评估器
        current = cls.get_evaluator(evaluator_id)
        if not current:
            return []
        
        history = [current]
        
        # 向上追溯父版本
        parent_id = current.get('parent_version')
        while parent_id:
            cursor.execute("SELECT * FROM evaluators WHERE evaluator_id = ?", (parent_id,))
            row = cursor.fetchone()
            if row:
                parent = cls._row_to_dict(row)
                history.append(parent)
                parent_id = parent.get('parent_version')
            else:
                break
        
        conn.close()
        return history
    
    @classmethod
    def _row_to_dict(cls, row) -> Dict:
        """将数据库行转换为字典"""
        d = dict(row)
        
        # 解析 JSON 字段
        if d.get('dimensions'):
            try:
                d['dimensions'] = json.loads(d['dimensions'])
            except:
                d['dimensions'] = []
        
        if d.get('eval_types'):
            try:
                d['eval_types'] = json.loads(d['eval_types'])
            except:
                d['eval_types'] = []
        
        # 转换布尔值
        d['is_default'] = bool(d.get('is_default', 0))
        d['is_system'] = bool(d.get('is_system', 0))
        
        return d
    
    @classmethod
    def ensure_default_evaluator(cls):
        """
        确保存在默认评估器
        如果不存在，则从 rubric.json 迁移创建
        """
        default = cls.get_default_evaluator()
        if default:
            return default['evaluator_id']
        
        # 尝试从 rubric.json 迁移
        rubric_path = Path("config/rubric.json")
        if rubric_path.exists():
            with open(rubric_path, 'r', encoding='utf-8') as f:
                rubric = json.load(f)
            
            # 为每个维度添加默认权重
            dimensions = rubric.get('rubrics', [])
            weight_per_dim = 1.0 / len(dimensions) if dimensions else 0
            for dim in dimensions:
                if 'weight' not in dim:
                    dim['weight'] = round(weight_per_dim, 2)
            
            evaluator_id = cls.create_evaluator(
                name="系统默认评估器",
                version="1.0",
                description="从 rubric.json 迁移的默认评估维度 (6维度客服质量评估)",
                eval_types=["single_turn", "multi_turn", "agent"],
                dimensions=dimensions,
                is_default=True,
                is_system=True,
                created_by="migrated"
            )
            
            return evaluator_id
        
        return None


# 测试代码
if __name__ == "__main__":
    # 确保数据库表存在
    from database import get_database
    db = get_database()
    
    print("🧪 测试评估器存储模块")
    print("=" * 50)
    
    # 1. 确保默认评估器
    print("\n1. 确保默认评估器...")
    default_id = EvaluatorStore.ensure_default_evaluator()
    print(f"   默认评估器 ID: {default_id}")
    
    # 2. 列出所有评估器
    print("\n2. 列出所有评估器...")
    evaluators = EvaluatorStore.list_evaluators()
    for e in evaluators:
        default_mark = "⭐" if e['is_default'] else ""
        system_mark = "🔒" if e['is_system'] else ""
        print(f"   - {e['name']} v{e['version']} {default_mark}{system_mark}")
        print(f"     ID: {e['evaluator_id']}, 维度数: {len(e['dimensions'])}")
    
    # 3. 创建测试评估器
    print("\n3. 创建测试评估器...")
    test_dims = [
        {
            "name": "测试维度1",
            "weight": 0.5,
            "description": "测试描述1",
            "criteria": {"1": "差", "5": "好"}
        },
        {
            "name": "测试维度2",
            "weight": 0.5,
            "description": "测试描述2",
            "criteria": {"1": "差", "5": "好"}
        }
    ]
    test_id = EvaluatorStore.create_evaluator(
        name="测试评估器",
        dimensions=test_dims,
        eval_types=["multi_turn"],
        description="这是一个测试评估器"
    )
    print(f"   创建成功，ID: {test_id}")
    
    # 4. 获取评估器详情
    print("\n4. 获取评估器详情...")
    detail = EvaluatorStore.get_evaluator(test_id)
    print(f"   名称: {detail['name']}")
    print(f"   版本: {detail['version']}")
    print(f"   维度: {[d['name'] for d in detail['dimensions']]}")
    
    # 5. 创建新版本
    print("\n5. 创建新版本...")
    new_version_id = EvaluatorStore.create_version(test_id)
    new_detail = EvaluatorStore.get_evaluator(new_version_id)
    print(f"   新版本 ID: {new_version_id}")
    print(f"   新版本号: {new_detail['version']}")
    
    # 6. 删除测试评估器
    print("\n6. 清理测试数据...")
    EvaluatorStore.delete_evaluator(test_id)
    EvaluatorStore.delete_evaluator(new_version_id)
    print("   已删除测试评估器")
    
    print("\n✅ 测试完成!")
