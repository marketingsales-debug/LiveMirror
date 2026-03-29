"""
Lesson Learnt Memory Tier.
Persistent SQLite-based storage for agent observations and reflections.
Extracted logic from Mem0 and Stanford Generative Agents.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class LessonLearntStore:
    """Handles persistent storage of agent lessons across sessions."""

    def __init__(self, db_path: str = "data/memory/lessons.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    topic TEXT,
                    content TEXT,
                    embedding_json TEXT, -- Placeholder for Phase 14
                    created_at TIMESTAMP,
                    relevance_score REAL
                )
            """)
            conn.commit()

    def save_lesson(self, agent_id: str, topic: str, content: str, relevance: float = 1.0):
        """Save a new lesson learned by an agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO lessons (agent_id, topic, content, created_at, relevance_score) VALUES (?, ?, ?, ?, ?)",
                (agent_id, topic, content, datetime.now().isoformat(), relevance)
            )
            conn.commit()

    def get_lessons(self, topic: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the most relevant lessons, optionally filtered by topic."""
        query = "SELECT agent_id, topic, content, created_at, relevance_score FROM lessons"
        params = []
        
        if topic:
            query += " WHERE topic = ?"
            params.append(topic)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                {
                    "agent_id": row[0],
                    "topic": row[1],
                    "content": row[2],
                    "ts": row[3],
                    "score": row[4]
                }
                for row in cursor.fetchall()
            ]

    def clear_all(self):
        """Wipe the memory."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM lessons")
            conn.commit()
