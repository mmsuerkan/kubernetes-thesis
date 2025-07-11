"""
Strategy Database - SQLite based persistent storage for learned strategies
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Strategy:
    """Learned strategy representation"""
    id: str
    error_type: str
    conditions: List[str]
    actions: List[Dict[str, Any]]
    confidence: float
    success_rate: float
    usage_count: int
    created_at: datetime
    updated_at: datetime
    source: str  # 'learned', 'manual', 'community'
    context: Dict[str, Any]
    last_used: Optional[datetime] = None

class StrategyDatabase:
    """SQLite-based strategy database for persistent learning"""
    
    def __init__(self, db_path: str = "reflexion_strategies.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Strategies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    error_type TEXT NOT NULL,
                    conditions TEXT NOT NULL,  -- JSON array
                    actions TEXT NOT NULL,     -- JSON array
                    confidence REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'learned',
                    context TEXT DEFAULT '{}'  -- JSON object
                )
            """)
            
            # Add last_used column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE strategies ADD COLUMN last_used TIMESTAMP NULL")
                logger.info("Added last_used column to strategies table")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Strategy usage history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    pod_name TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    feedback TEXT,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                )
            """)
            
            # Strategy evolution tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_evolution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    change_type TEXT NOT NULL,  -- 'created', 'modified', 'merged'
                    change_description TEXT,
                    old_confidence REAL,
                    new_confidence REAL,
                    trigger_event TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                )
            """)
            
            conn.commit()
            logger.info(f"Strategy database initialized at {self.db_path}")
    
    def add_strategy(self, strategy: Strategy) -> bool:
        """Add a new strategy to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO strategies 
                    (id, error_type, conditions, actions, confidence, success_rate, 
                     usage_count, source, context, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy.id,
                    strategy.error_type,
                    json.dumps(strategy.conditions),
                    json.dumps(strategy.actions),
                    strategy.confidence,
                    strategy.success_rate,
                    strategy.usage_count,
                    strategy.source,
                    json.dumps(strategy.context),
                    strategy.created_at.isoformat(),
                    strategy.updated_at.isoformat()
                ))
                
                # Log strategy creation
                cursor.execute("""
                    INSERT INTO strategy_evolution 
                    (strategy_id, version, change_type, change_description, new_confidence)
                    VALUES (?, 1, 'created', 'Initial strategy creation', ?)
                """, (strategy.id, strategy.confidence))
                
                conn.commit()
                logger.info(f"Added new strategy: {strategy.id} for {strategy.error_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add strategy {strategy.id}: {e}")
            return False
    
    def get_strategies_for_error(self, error_type: str, context: Dict[str, Any] = None) -> List[Strategy]:
        """Get relevant strategies for a specific error type and context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM strategies 
                    WHERE error_type = ? 
                    ORDER BY confidence DESC, success_rate DESC
                """, (error_type,))
                
                rows = cursor.fetchall()
                strategies = []
                
                for row in rows:
                    strategy = Strategy(
                        id=row[0],
                        error_type=row[1],
                        conditions=json.loads(row[2]),
                        actions=json.loads(row[3]),
                        confidence=row[4],
                        success_rate=row[5],
                        usage_count=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        updated_at=datetime.fromisoformat(row[8]),
                        source=row[9],
                        context=json.loads(row[10]),
                        last_used=datetime.fromisoformat(row[11]) if len(row) > 11 and row[11] else None
                    )
                    
                    # Check if strategy conditions match current context
                    if self._matches_context(strategy, context):
                        strategies.append(strategy)
                
                logger.info(f"Found {len(strategies)} strategies for {error_type}")
                return strategies
                
        except Exception as e:
            logger.error(f"Failed to get strategies for {error_type}: {e}")
            return []
    
    def update_strategy_performance(self, strategy_id: str, success: bool, execution_time: float,
                                   pod_name: str, namespace: str, feedback: str = None) -> bool:
        """Update strategy performance based on usage outcome"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Record usage
                cursor.execute("""
                    INSERT INTO strategy_usage 
                    (strategy_id, pod_name, namespace, success, execution_time, feedback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (strategy_id, pod_name, namespace, success, execution_time, feedback))
                
                # Update strategy statistics
                now = datetime.now()
                
                # Check if last_used column exists
                cursor.execute("PRAGMA table_info(strategies)")
                columns = [col[1] for col in cursor.fetchall()]
                has_last_used = 'last_used' in columns
                
                if has_last_used:
                    cursor.execute("""
                        UPDATE strategies 
                        SET usage_count = usage_count + 1,
                            success_rate = (
                                SELECT AVG(CAST(success AS FLOAT)) 
                                FROM strategy_usage 
                                WHERE strategy_id = ?
                            ),
                            updated_at = ?,
                            last_used = ?
                        WHERE id = ?
                    """, (strategy_id, now.isoformat(), now.isoformat(), strategy_id))
                else:
                    cursor.execute("""
                        UPDATE strategies 
                        SET usage_count = usage_count + 1,
                            success_rate = (
                                SELECT AVG(CAST(success AS FLOAT)) 
                                FROM strategy_usage 
                                WHERE strategy_id = ?
                            ),
                            updated_at = ?
                        WHERE id = ?
                    """, (strategy_id, now.isoformat(), strategy_id))
                
                # Update confidence based on recent performance
                cursor.execute("""
                    SELECT AVG(CAST(success AS FLOAT)) as recent_success
                    FROM strategy_usage 
                    WHERE strategy_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """, (strategy_id,))
                
                recent_success = cursor.fetchone()[0] or 0.0
                new_confidence = min(0.95, max(0.1, recent_success * 0.9 + 0.1))
                
                cursor.execute("""
                    UPDATE strategies 
                    SET confidence = ?
                    WHERE id = ?
                """, (new_confidence, strategy_id))
                
                # Log evolution
                cursor.execute("""
                    INSERT INTO strategy_evolution 
                    (strategy_id, version, change_type, change_description, new_confidence)
                    VALUES (?, 
                            (SELECT COUNT(*) FROM strategy_evolution WHERE strategy_id = ?) + 1,
                            'performance_update', 
                            'Updated based on usage outcome', 
                            ?)
                """, (strategy_id, strategy_id, new_confidence))
                
                conn.commit()
                logger.info(f"Updated performance for strategy {strategy_id}: success={success}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update strategy performance: {e}")
            return False
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Get overall strategy database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total strategies
                cursor.execute("SELECT COUNT(*) FROM strategies")
                total_strategies = cursor.fetchone()[0]
                
                # Success rate by error type
                cursor.execute("""
                    SELECT s.error_type, AVG(s.success_rate) as avg_success
                    FROM strategies s
                    GROUP BY s.error_type
                """)
                success_by_error = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Most used strategies
                cursor.execute("""
                    SELECT id, error_type, usage_count, success_rate
                    FROM strategies 
                    ORDER BY usage_count DESC 
                    LIMIT 5
                """)
                top_strategies = [
                    {
                        "id": row[0],
                        "error_type": row[1],
                        "usage_count": row[2],
                        "success_rate": row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) FROM strategy_usage 
                    WHERE timestamp > datetime('now', '-24 hours')
                """)
                recent_usage = cursor.fetchone()[0]
                
                return {
                    "total_strategies": total_strategies,
                    "success_by_error_type": success_by_error,
                    "top_strategies": top_strategies,
                    "recent_usage_24h": recent_usage,
                    "database_path": str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"Failed to get strategy statistics: {e}")
            return {}
    
    def _matches_context(self, strategy: Strategy, context: Dict[str, Any]) -> bool:
        """Check if strategy conditions match the current context"""
        if not context:
            return True
            
        for condition in strategy.conditions:
            # Simple condition matching - can be enhanced
            if "namespace" in condition and context.get("namespace"):
                if f"namespace == '{context['namespace']}'" in condition:
                    continue
                elif "namespace" in condition and context["namespace"] not in condition:
                    return False
            
            if "cluster_size" in condition and context.get("cluster_size"):
                # Add more sophisticated condition matching here
                pass
                
        return True
    
    def close(self):
        """Close database connection"""
        # SQLite connections are automatically closed when using context manager
        pass