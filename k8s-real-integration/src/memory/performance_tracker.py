"""
Performance Tracker - Dynamic confidence scoring and performance analysis
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    strategy_id: str
    error_type: str
    success_rate: float
    avg_resolution_time: float
    confidence_score: float
    usage_count: int
    last_used: datetime
    trend: str  # 'improving', 'declining', 'stable'

class PerformanceTracker:
    """Dynamic performance tracking and confidence scoring"""
    
    def __init__(self, db_path: str = "reflexion_performance.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize performance tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_resolution_time REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    usage_count INTEGER NOT NULL,
                    last_used TIMESTAMP NOT NULL,
                    trend TEXT NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self._init_remaining_tables()
            conn.commit()
    
    def clear_all_metrics(self) -> bool:
        """Clear all performance metrics and history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear all metrics
                cursor.execute("DELETE FROM performance_metrics")
                deleted_metrics = cursor.rowcount
                
                # Clear performance history
                cursor.execute("DELETE FROM performance_history")
                deleted_history = cursor.rowcount
                
                # Clear system performance
                cursor.execute("DELETE FROM system_performance")
                deleted_system = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Cleared {deleted_metrics} performance metrics, {deleted_history} history records, {deleted_system} system records")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear performance metrics: {e}")
            return False
    
    def _init_remaining_tables(self):
        """Initialize remaining database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Performance history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    resolution_time REAL,
                    confidence_before REAL,
                    confidence_after REAL,
                    context TEXT,  -- JSON
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    overall_success_rate REAL,
                    avg_resolution_time REAL,
                    total_processed INTEGER,
                    unique_error_types INTEGER,
                    active_strategies INTEGER,
                    learning_velocity REAL,  -- strategies learned per day
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info(f"Performance tracker database initialized at {self.db_path}")
    
    def calculate_dynamic_confidence(self, strategy_id: str, recent_window: int = 10) -> float:
        """Calculate dynamic confidence based on recent performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get recent performance data
                cursor.execute("""
                    SELECT success, resolution_time, timestamp 
                    FROM performance_history 
                    WHERE strategy_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (strategy_id, recent_window))
                
                recent_data = cursor.fetchall()
                
                if not recent_data:
                    return 0.5  # Neutral confidence for new strategies
                
                # Calculate base success rate
                success_count = sum(1 for row in recent_data if row[0])
                base_success_rate = success_count / len(recent_data)
                
                # Calculate recency weight (more recent = higher weight)
                weighted_success = 0
                total_weight = 0
                now = datetime.now()
                
                for i, (success, res_time, timestamp_str) in enumerate(recent_data):
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_hours = (now - timestamp).total_seconds() / 3600
                    weight = max(0.1, 1.0 - (age_hours / 168))  # 1 week decay
                    
                    weighted_success += success * weight
                    total_weight += weight
                
                weighted_success_rate = weighted_success / total_weight if total_weight > 0 else base_success_rate
                
                # Calculate trend factor
                if len(recent_data) >= 5:
                    recent_half = recent_data[:len(recent_data)//2]
                    older_half = recent_data[len(recent_data)//2:]
                    
                    recent_success = sum(1 for row in recent_half if row[0]) / len(recent_half)
                    older_success = sum(1 for row in older_half if row[0]) / len(older_half)
                    
                    trend_factor = min(0.2, max(-0.2, (recent_success - older_success)))
                else:
                    trend_factor = 0
                
                # Calculate resolution time factor
                resolution_times = [row[1] for row in recent_data if row[1] is not None]
                if resolution_times:
                    avg_resolution = sum(resolution_times) / len(resolution_times)
                    # Lower resolution time = higher confidence
                    time_factor = max(-0.1, min(0.1, (60 - avg_resolution) / 600))  # 60s baseline
                else:
                    time_factor = 0
                
                # Final confidence calculation
                confidence = min(0.95, max(0.05, 
                    weighted_success_rate + trend_factor + time_factor
                ))
                
                logger.info(f"Dynamic confidence for {strategy_id}: {confidence:.3f}")
                return confidence
                
        except Exception as e:
            logger.error(f"Failed to calculate dynamic confidence: {e}")
            return 0.5
    
    def record_performance(self, strategy_id: str, success: bool, resolution_time: float = None,
                          confidence_before: float = 0.5, context: Dict[str, Any] = None) -> float:
        """Record performance data and return updated confidence"""
        try:
            # Calculate new confidence
            new_confidence = self.calculate_dynamic_confidence(strategy_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Record performance history
                cursor.execute("""
                    INSERT INTO performance_history 
                    (strategy_id, success, resolution_time, confidence_before, confidence_after, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id, 
                    success, 
                    resolution_time, 
                    confidence_before, 
                    new_confidence,
                    json.dumps(context) if context else "{}"
                ))
                
                conn.commit()
                logger.info(f"Recorded performance for {strategy_id}: success={success}, new_confidence={new_confidence:.3f}")
                return new_confidence
                
        except Exception as e:
            logger.error(f"Failed to record performance: {e}")
            return confidence_before
    
    def update_strategy_metrics(self, strategy_id: str, error_type: str) -> PerformanceMetric:
        """Update and return current performance metrics for a strategy"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate current metrics
                cursor.execute("""
                    SELECT 
                        AVG(CAST(success AS FLOAT)) as success_rate,
                        AVG(resolution_time) as avg_resolution_time,
                        COUNT(*) as usage_count,
                        MAX(timestamp) as last_used
                    FROM performance_history 
                    WHERE strategy_id = ?
                """, (strategy_id,))
                
                row = cursor.fetchone()
                if not row or row[0] is None:
                    return None
                
                success_rate = row[0]
                avg_resolution_time = row[1] or 0.0
                usage_count = row[2]
                last_used = datetime.fromisoformat(row[3])
                
                # Calculate confidence
                confidence_score = self.calculate_dynamic_confidence(strategy_id)
                
                # Determine trend
                cursor.execute("""
                    SELECT success FROM performance_history 
                    WHERE strategy_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 6
                """, (strategy_id,))
                
                recent_results = [row[0] for row in cursor.fetchall()]
                if len(recent_results) >= 6:
                    recent_avg = sum(recent_results[:3]) / 3
                    older_avg = sum(recent_results[3:6]) / 3
                    
                    if recent_avg > older_avg + 0.1:
                        trend = "improving"
                    elif recent_avg < older_avg - 0.1:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"
                
                # Store/update metrics
                cursor.execute("""
                    INSERT OR REPLACE INTO performance_metrics 
                    (strategy_id, error_type, success_rate, avg_resolution_time, 
                     confidence_score, usage_count, last_used, trend)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id, error_type, success_rate, avg_resolution_time,
                    confidence_score, usage_count, last_used.isoformat(), trend
                ))
                
                conn.commit()
                
                metric = PerformanceMetric(
                    strategy_id=strategy_id,
                    error_type=error_type,
                    success_rate=success_rate,
                    avg_resolution_time=avg_resolution_time,
                    confidence_score=confidence_score,
                    usage_count=usage_count,
                    last_used=last_used,
                    trend=trend
                )
                
                logger.info(f"Updated metrics for {strategy_id}: {trend} trend, {confidence_score:.3f} confidence")
                return metric
                
        except Exception as e:
            logger.error(f"Failed to update strategy metrics: {e}")
            return None
    
    def get_performance_insights(self, days: int = 7) -> Dict[str, Any]:
        """Get performance insights for the specified period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since_date = datetime.now() - timedelta(days=days)
                
                # Overall performance
                cursor.execute("""
                    SELECT 
                        AVG(CAST(success AS FLOAT)) as overall_success_rate,
                        AVG(resolution_time) as avg_resolution_time,
                        COUNT(*) as total_processed,
                        COUNT(DISTINCT strategy_id) as strategies_used
                    FROM performance_history 
                    WHERE timestamp > ?
                """, (since_date.isoformat(),))
                
                overall = cursor.fetchone()
                
                # Top performing strategies
                cursor.execute("""
                    SELECT 
                        strategy_id,
                        AVG(CAST(success AS FLOAT)) as success_rate,
                        COUNT(*) as usage_count,
                        AVG(resolution_time) as avg_time
                    FROM performance_history 
                    WHERE timestamp > ?
                    GROUP BY strategy_id
                    HAVING COUNT(*) >= 3
                    ORDER BY success_rate DESC, usage_count DESC
                    LIMIT 5
                """, (since_date.isoformat(),))
                
                top_strategies = [
                    {
                        "strategy_id": row[0],
                        "success_rate": row[1],
                        "usage_count": row[2],
                        "avg_resolution_time": row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Performance trends
                cursor.execute("""
                    SELECT 
                        DATE(timestamp) as date,
                        AVG(CAST(success AS FLOAT)) as daily_success_rate,
                        COUNT(*) as daily_count
                    FROM performance_history 
                    WHERE timestamp > ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (since_date.isoformat(),))
                
                daily_trends = [
                    {
                        "date": row[0],
                        "success_rate": row[1],
                        "count": row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    "period_days": days,
                    "overall_performance": {
                        "success_rate": overall[0] or 0.0,
                        "avg_resolution_time": overall[1] or 0.0,
                        "total_processed": overall[2] or 0,
                        "strategies_used": overall[3] or 0
                    },
                    "top_strategies": top_strategies,
                    "daily_trends": daily_trends,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get performance insights: {e}")
            return {}
    
    def get_strategy_ranking(self, error_type: str = None) -> List[Dict[str, Any]]:
        """Get strategies ranked by performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if error_type:
                    cursor.execute("""
                        SELECT * FROM performance_metrics 
                        WHERE error_type = ?
                        ORDER BY confidence_score DESC, success_rate DESC
                    """, (error_type,))
                else:
                    cursor.execute("""
                        SELECT * FROM performance_metrics 
                        ORDER BY confidence_score DESC, success_rate DESC
                    """)
                
                rankings = []
                for i, row in enumerate(cursor.fetchall(), 1):
                    rankings.append({
                        "rank": i,
                        "strategy_id": row[1],
                        "error_type": row[2],
                        "success_rate": row[3],
                        "avg_resolution_time": row[4],
                        "confidence_score": row[5],
                        "usage_count": row[6],
                        "last_used": row[7],
                        "trend": row[8]
                    })
                
                return rankings
                
        except Exception as e:
            logger.error(f"Failed to get strategy ranking: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        # SQLite connections are automatically closed when using context manager
        pass