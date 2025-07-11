"""
Episodic Memory Manager - Long-term storage for experiences and learning episodes
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class EpisodicMemory:
    """Represents a single learning episode"""
    id: str
    pod_name: str
    namespace: str
    error_type: str
    context: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    outcome: Dict[str, Any]
    lessons_learned: List[str]
    confidence_before: float
    confidence_after: float
    resolution_time: float
    timestamp: datetime
    reflection_quality: float
    insights_generated: int

class EpisodicMemoryManager:
    """Manages episodic memory storage and retrieval"""
    
    def __init__(self, db_path: str = "reflexion_episodes.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for episodic memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Episodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    pod_name TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    context TEXT NOT NULL,          -- JSON
                    actions_taken TEXT NOT NULL,    -- JSON
                    outcome TEXT NOT NULL,          -- JSON
                    lessons_learned TEXT NOT NULL,  -- JSON
                    confidence_before REAL,
                    confidence_after REAL,
                    resolution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reflection_quality REAL,
                    insights_generated INTEGER
                )
            """)
            
            # Memory patterns table for pattern recognition
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,     -- 'temporal', 'contextual', 'causal'
                    pattern_data TEXT NOT NULL,     -- JSON
                    strength REAL NOT NULL,         -- How strong this pattern is
                    frequency INTEGER DEFAULT 1,   -- How often seen
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Memory associations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id_1 TEXT NOT NULL,
                    episode_id_2 TEXT NOT NULL,
                    association_type TEXT NOT NULL,  -- 'similar_context', 'similar_outcome', 'causal'
                    strength REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (episode_id_1) REFERENCES episodes (id),
                    FOREIGN KEY (episode_id_2) REFERENCES episodes (id)
                )
            """)
            
            conn.commit()
            logger.info(f"Episodic memory database initialized at {self.db_path}")
    
    def store_episode(self, episode: EpisodicMemory) -> bool:
        """Store a new learning episode"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO episodes 
                    (id, pod_name, namespace, error_type, context, actions_taken, 
                     outcome, lessons_learned, confidence_before, confidence_after,
                     resolution_time, timestamp, reflection_quality, insights_generated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    episode.id,
                    episode.pod_name,
                    episode.namespace,
                    episode.error_type,
                    json.dumps(episode.context),
                    json.dumps(episode.actions_taken),
                    json.dumps(episode.outcome),
                    json.dumps(episode.lessons_learned),
                    episode.confidence_before,
                    episode.confidence_after,
                    episode.resolution_time,
                    episode.timestamp.isoformat(),
                    episode.reflection_quality,
                    episode.insights_generated
                ))
                conn.commit()
                
                # Analyze and store patterns
                self._analyze_patterns(episode)
                
                # Create associations with similar episodes
                self._create_associations(episode)
                
                logger.info(f"Stored episode: {episode.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store episode {episode.id}: {e}")
            return False
    
    def get_similar_episodes(self, error_type: str, context: Dict[str, Any], 
                           limit: int = 10) -> List[EpisodicMemory]:
        """Retrieve similar episodes for learning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get episodes with same error type
                cursor.execute("""
                    SELECT * FROM episodes 
                    WHERE error_type = ? 
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (error_type, limit * 2))  # Get more to filter
                
                episodes = []
                for row in cursor.fetchall():
                    episode_context = json.loads(row[4])
                    
                    # Calculate similarity score
                    similarity = self._calculate_context_similarity(context, episode_context)
                    
                    # Lower threshold for better matching + always include same error type
                    if similarity > 0.1 or True:  # Accept all same error_type episodes for now
                        episode = EpisodicMemory(
                            id=row[0],
                            pod_name=row[1],
                            namespace=row[2],
                            error_type=row[3],
                            context=episode_context,
                            actions_taken=json.loads(row[5]),
                            outcome=json.loads(row[6]),
                            lessons_learned=json.loads(row[7]),
                            confidence_before=row[8],
                            confidence_after=row[9],
                            resolution_time=row[10],
                            timestamp=datetime.fromisoformat(row[11]),
                            reflection_quality=row[12],
                            insights_generated=row[13]
                        )
                        episodes.append((episode, similarity))
                
                # Sort by similarity and return top results
                episodes.sort(key=lambda x: x[1], reverse=True)
                return [ep[0] for ep in episodes[:limit]]
                
        except Exception as e:
            logger.error(f"Failed to get similar episodes: {e}")
            return []
    
    def get_learning_progression(self, days: int = 30) -> Dict[str, Any]:
        """Analyze learning progression over time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since_date = datetime.now() - timedelta(days=days)
                
                # Overall progression
                cursor.execute("""
                    SELECT 
                        DATE(timestamp) as date,
                        AVG(confidence_after - confidence_before) as confidence_gain,
                        AVG(reflection_quality) as avg_reflection_quality,
                        AVG(insights_generated) as avg_insights,
                        COUNT(*) as episode_count
                    FROM episodes 
                    WHERE timestamp > ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (since_date.isoformat(),))
                
                daily_progression = []
                for row in cursor.fetchall():
                    daily_progression.append({
                        "date": row[0],
                        "confidence_gain": row[1],
                        "reflection_quality": row[2],
                        "avg_insights": row[3],
                        "episode_count": row[4]
                    })
                
                # Error type breakdown
                cursor.execute("""
                    SELECT 
                        error_type,
                        COUNT(*) as count,
                        AVG(confidence_after - confidence_before) as avg_improvement,
                        AVG(resolution_time) as avg_resolution_time
                    FROM episodes 
                    WHERE timestamp > ?
                    GROUP BY error_type
                """, (since_date.isoformat(),))
                
                error_type_stats = []
                for row in cursor.fetchall():
                    error_type_stats.append({
                        "error_type": row[0],
                        "count": row[1],
                        "avg_improvement": row[2],
                        "avg_resolution_time": row[3]
                    })
                
                return {
                    "daily_progression": daily_progression,
                    "error_type_stats": error_type_stats,
                    "analysis_period_days": days
                }
                
        except Exception as e:
            logger.error(f"Failed to get learning progression: {e}")
            return {}
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get overall memory statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total episodes
                cursor.execute("SELECT COUNT(*) FROM episodes")
                total_episodes = cursor.fetchone()[0]
                
                # Average metrics
                cursor.execute("""
                    SELECT 
                        AVG(reflection_quality) as avg_reflection_quality,
                        AVG(insights_generated) as avg_insights,
                        AVG(confidence_after - confidence_before) as avg_confidence_gain,
                        AVG(resolution_time) as avg_resolution_time
                    FROM episodes
                """)
                row = cursor.fetchone()
                
                # Pattern count
                cursor.execute("SELECT COUNT(*) FROM memory_patterns")
                pattern_count = cursor.fetchone()[0]
                
                # Association count
                cursor.execute("SELECT COUNT(*) FROM memory_associations")
                association_count = cursor.fetchone()[0]
                
                return {
                    "total_episodes": total_episodes,
                    "avg_reflection_quality": row[0] or 0.0,
                    "avg_insights_generated": row[1] or 0.0,
                    "avg_confidence_gain": row[2] or 0.0,
                    "avg_resolution_time": row[3] or 0.0,
                    "patterns_discovered": pattern_count,
                    "associations_formed": association_count
                }
                
        except Exception as e:
            logger.error(f"Failed to get memory statistics: {e}")
            return {}
    
    def _calculate_context_similarity(self, context1: Dict[str, Any], 
                                    context2: Dict[str, Any]) -> float:
        """Calculate similarity between two contexts"""
        if not context1 or not context2:
            return 0.0
        
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
        
        matches = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                matches += 1
        
        return matches / len(common_keys)
    
    def _analyze_patterns(self, episode: EpisodicMemory):
        """Analyze and store patterns from the episode"""
        # This is a simplified pattern analysis
        # In a full implementation, this would use more sophisticated ML techniques
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Temporal pattern (time of day when errors occur)
            hour = episode.timestamp.hour
            temporal_pattern = {
                "type": "temporal",
                "hour": hour,
                "error_type": episode.error_type
            }
            
            # Check if pattern exists first to avoid NULL constraint
            pattern_json = json.dumps(temporal_pattern)
            cursor.execute("""
                SELECT strength, frequency FROM memory_patterns 
                WHERE pattern_type = 'temporal' AND pattern_data = ?
            """, (pattern_json,))
            
            existing = cursor.fetchone()
            if existing:
                # Update existing pattern
                new_strength = existing[0] + 1
                new_frequency = existing[1] + 1
            else:
                # Create new pattern
                new_strength = 1
                new_frequency = 1
            
            cursor.execute("""
                INSERT OR REPLACE INTO memory_patterns 
                (pattern_type, pattern_data, strength, frequency)
                VALUES ('temporal', ?, ?, ?)
            """, (pattern_json, new_strength, new_frequency))
            
            conn.commit()
    
    def _create_associations(self, episode: EpisodicMemory):
        """Create associations with similar episodes"""
        similar_episodes = self.get_similar_episodes(
            episode.error_type, 
            episode.context, 
            limit=5
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for similar_ep in similar_episodes:
                if similar_ep.id != episode.id:
                    similarity = self._calculate_context_similarity(
                        episode.context, 
                        similar_ep.context
                    )
                    
                    cursor.execute("""
                        INSERT INTO memory_associations 
                        (episode_id_1, episode_id_2, association_type, strength)
                        VALUES (?, ?, 'similar_context', ?)
                    """, (episode.id, similar_ep.id, similarity))
            
            conn.commit()
    
    def close(self):
        """Close database connection"""
        # SQLite connections are automatically closed when using context manager
        pass