import aiosqlite
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path
from loguru import logger
from src.config import config

class DatabaseService:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(config.agent.gcc_base_path) / "intelligence.db"
        self._conn = None

    async def connect(self):
        """Initialize connection and apply schema."""
        if self._conn:
            return
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        
        # Enable WAL mode for concurrency
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        
        await self._init_schema()
        logger.info(f"Intelligence DB initialized at {self.db_path}")

    async def _init_schema(self):
        """Create tables if they don't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            goal TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            path TEXT,
            parent_id TEXT,
            FOREIGN KEY (parent_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            root_path TEXT,
            last_scanned TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            skill_id TEXT,
            cmd TEXT,
            exit_code INTEGER,
            output_summary TEXT,
            env_os TEXT,
            env_release TEXT,
            env_shell TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_history_session ON command_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_history_skill ON command_history(skill_id);
        """
        await self._conn.executescript(schema)
        
        # Simple Migration: Add title if missing
        cursor = await self._conn.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "title" not in columns:
            await self._conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
            logger.info("Intelligence DB: Migrated sessions table (added title column)")
            
        if "parent_id" not in columns:
            await self._conn.execute("ALTER TABLE sessions ADD COLUMN parent_id TEXT")
            logger.info("Intelligence DB: Migrated sessions table (added parent_id column)")
            
        # Phase 16: Add cwd to command history for path-aware tracking
        cursor = await self._conn.execute("PRAGMA table_info(command_history)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "cwd" not in columns:
            await self._conn.execute("ALTER TABLE command_history ADD COLUMN cwd TEXT")
            logger.info("Intelligence DB: Migrated command_history table (added cwd column)")
            
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: tuple = ()):
        """Execute a write query (INSERT/UPDATE/DELETE) and commit."""
        async with self._conn.execute(query, params) as cursor:
            await self._conn.commit()
            return await cursor.fetchall()

    async def read_execute(self, query: str, params: tuple = ()):
        """Execute a read-only query (SELECT) without committing."""
        async with self._conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def insert_session(self, session_id: str, goal: str, path: str, title: Optional[str] = None, parent_id: Optional[str] = None):
        query = "INSERT OR IGNORE INTO sessions (id, title, goal, path, parent_id) VALUES (?, ?, ?, ?, ?)"
        await self.execute(query, (session_id, title or goal[:50], goal, path, parent_id))

    async def rename_session(self, session_id: str, new_title: str):
        query = "UPDATE sessions SET title = ? WHERE id = ?"
        await self.execute(query, (new_title, session_id))

    async def delete_session(self, session_id: str):
        # Cascades will handle command_history if foreign keys are enabled
        query = "DELETE FROM sessions WHERE id = ?"
        await self.execute(query, (session_id,))

    async def reset_all(self):
        """Wipe all session and history data."""
        await self.execute("DELETE FROM command_history")
        await self.execute("DELETE FROM sessions")
        await self._conn.commit()

    async def log_command(self, session_id: str, skill_id: str, cmd: str, exit_code: int, summary: str, env: dict):
        query = """
        INSERT INTO command_history 
        (session_id, skill_id, cmd, exit_code, output_summary, env_os, env_release, env_shell, cwd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.execute(query, (
            session_id, 
            skill_id, 
            cmd, 
            exit_code, 
            summary, 
            env.get("os"), 
            env.get("release"), 
            env.get("shell"),
            env.get("cwd")
        ))
