import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from .database import DatabaseService
from .metadata import MetadataService
class IntelligenceRegistry:
    _instance = None

    def __init__(self):
        self.db = DatabaseService()
        self.metadata = MetadataService(self.db)
        self._initialized = False
        self._background_tasks = set() # Phase O: Track orphans for graceful exit

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self):
        """Warm up all services in parallel."""
        if self._initialized:
            return
            
        # Connect to DB first as metadata sync depends on it
        await self.db.connect()
        
        # Sync metadata
        await self.metadata.sync_all()
        
        self._initialized = True
        logger.info("IntelligenceRegistry: Orchestration layer active.")

    async def shutdown(self):
        """Phase O: Graceful Shutdown - Cancel all background tasks and close DB."""
        if self._background_tasks:
            logger.info(f"Registry: Cleaning up {len(self._background_tasks)} background tasks...")
            for task in self._background_tasks:
                task.cancel()
            
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

        await self.db.close()
        logger.info("IntelligenceRegistry: Shutdown complete.")

    def track_task(self, coro):
        """Phase O: Helper to fire-and-forget but keep track for shutdown."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def list_sessions(self, query: Optional[str] = None) -> str:
        """Search or list sessions from SQLite."""
        if query:
            sql = "SELECT id, title, goal FROM sessions WHERE title LIKE ? OR goal LIKE ?"
            rows = await self.db.execute(sql, (f"%{query}%", f"%{query}%"))
        else:
            sql = "SELECT id, title, goal FROM sessions LIMIT 10"
            rows = await self.db.execute(sql)
            
        if not rows: return "No sessions found."
        return "\n".join([f"- [{r[0]}] {r[1]}: {r[2][:50]}..." for r in rows])

    async def get_session_details(self, session_id: str) -> str:
        """Fetch full details for a session."""
        rows = await self.db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not rows: return "Session not found."
        r = rows[0]
        return f"ID: {r[0]}\nTitle: {r[1]}\nGoal: {r[2]}\nStatus: {r[3]}\nCreated: {r[4]}\nGCC Path: {r[5]}"

    async def rename_session(self, session_id: str, new_title: str):
        """Rename a session in the index."""
        await self.db.rename_session(session_id, new_title)

    async def branch_session(self, parent_id: str, branch_name: str) -> str:
        """Forks a session into a child branch."""
        # 1. Resolve parent path
        rows = await self.db.execute("SELECT path, goal FROM sessions WHERE id = ?", (parent_id,))
        if not rows: raise ValueError(f"Parent session {parent_id} not found.")
        parent_path, parent_goal = rows[0]
        
        # 2. Create branch ID and path
        from datetime import datetime
        import re
        branch_name_safe = re.sub(r'[^a-z0-9_-]', '', branch_name.lower().replace(' ', '-'))
        branch_id = f"branch_{branch_name_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        branch_path = Path(parent_path).parent / branch_id
        
        # 3. Clone physical GCC state (Harden: Use thread for blocking I/O)
        if Path(parent_path).exists():
            def _clone():
                shutil.copytree(parent_path, branch_path)
                with open(branch_path / "log.md", 'a') as f:
                    f.write(f"\n\n## BRANCH FORKED: {datetime.now()}\nForked from {parent_id}\n")
            
            await asyncio.to_thread(_clone)
        
        # 4. Insert into SQLite
        await self.db.insert_session(
            session_id=branch_id,
            goal=f"Branch for: {parent_goal}",
            path=str(branch_path),
            title=branch_name,
            parent_id=parent_id
        )
        
        logger.info(f"IntelligenceRegistry: Branched {parent_id} -> {branch_id}")
        return branch_id

    async def merge_session(self, branch_id: str):
        """Merges a branch's findings back into its parent."""
        # 1. Resolve lineage
        rows = await self.db.execute("SELECT parent_id, path, title FROM sessions WHERE id = ?", (branch_id,))
        if not rows or not rows[0][0]: raise ValueError(f"Session {branch_id} is not a branch.")
        parent_id, branch_path, branch_title = rows[0]
        
        parent_rows = await self.db.execute("SELECT path FROM sessions WHERE id = ?", (parent_id,))
        if not parent_rows: raise ValueError(f"Parent {parent_id} not found.")
        parent_path = parent_rows[0][0]
        
        # 2. Extract 'Findings' (Commits)
        branch_commit_path = Path(branch_path) / "commit.md"
        if branch_commit_path.exists():
            with open(branch_commit_path, 'r') as f:
                findings = f.read()
            
            # 3. Append to Parent log.md
            with open(Path(parent_path) / "log.md", 'a') as f:
                f.write(f"\n\n## MERGED FROM BRANCH: {branch_title} ({branch_id})\n")
                f.write(findings)
                
            logger.info(f"IntelligenceRegistry: Merged findings from {branch_id} to {parent_id}")
        
        # 4. Close branch
        await self.db.execute("UPDATE sessions SET status = 'merged' WHERE id = ?", (branch_id,))

    async def delete_session(self, session_id: str):
        """Full purge of a session from intelligence."""
        await self.db.delete_session(session_id)
        logger.warning(f"IntelligenceRegistry: Purged session {session_id}")

    async def reset_intelligence(self, include_gcc: bool = False):
        """Base reset to fresh state. If include_gcc is True, deletes all session files."""
        await self.db.reset_all()
        
        if include_gcc:
            gcc_sessions_path = Path(self.db.db_path).parent / "sessions"
            if gcc_sessions_path.exists():
                shutil.rmtree(gcc_sessions_path)
                gcc_sessions_path.mkdir(parents=True, exist_ok=True)
                logger.warning(f"IntelligenceRegistry: PURGED GCC directory at {gcc_sessions_path}")
                
        logger.critical("IntelligenceRegistry: FULL SYSTEM RESET PERFORMED.")
