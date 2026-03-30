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
                    embedding_json TEXT,
                    created_at TIMESTAMP,
                    relevance_score REAL
                )
            """)
            # Relational Graph Table (Phase 8)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    predicate TEXT,
                    object TEXT,
                    confidence REAL,
                    source_id TEXT
                )
            """)
            # Dynamic Secrets Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    key_name TEXT PRIMARY KEY,
                    key_value TEXT,
                    updated_at TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.commit()

    def set_secret(self, name: str, value: str):
        """Upsert a secret key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO secrets (key_name, key_value, updated_at) VALUES (?, ?, ?)",
                (name.upper(), value, datetime.now().isoformat())
            )
            conn.commit()

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a specific secret."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key_value FROM secrets WHERE key_name = ?", (name.upper(),))
            row = cursor.fetchone()
            return row[0] if row else None

    def list_secrets(self) -> List[Dict[str, Any]]:
        """List all secret names and their status (not values)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key_name, updated_at, status FROM secrets")
            return [{"name": row[0], "updated_at": row[1], "status": row[2]} for row in cursor.fetchall()]

    def delete_secret(self, name: str):
        """Remove a secret."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM secrets WHERE key_name = ?", (name.upper(),))
            conn.commit()

    def save_triple(self, subject: str, predicate: str, obj: str, confidence: float = 1.0):
        """Save a knowledge graph triple."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO triples (subject, predicate, object, confidence) VALUES (?, ?, ?, ?)",
                (subject, predicate, obj, confidence)
            )
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
