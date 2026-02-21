import asyncio
from pathlib import Path
from loguru import logger
from src.config import config
from .database import DatabaseService

class MetadataService:
    def __init__(self, db: DatabaseService):
        self.db = db
        self.skills_path = Path("skills")

    async def sync_all(self):
        """Perform a full sync of sessions and skills in parallel."""
        await asyncio.gather(
            self.sync_sessions(),
            self.sync_skills()
        )

    async def sync_sessions(self):
        """Sync GCC sessions from filesystem to DB in parallel."""
        sessions_dir = Path(config.agent.gcc_base_path) / "sessions"
        if not sessions_dir.exists():
            return

        tasks = []
        for sdir in sessions_dir.iterdir():
            if sdir.is_dir() and sdir.name.startswith("session_"):
                tasks.append(self._sync_single_session(sdir))
        
        if tasks:
            await asyncio.gather(*tasks)
        
        logger.info("MetadataService: Sessions synced.")

    async def _sync_single_session(self, sdir: Path):
        """Internal helper to sync one session directory."""
        meta_path = sdir / "metadata.yaml"
        title = "Recovered Session"
        goal = "Unknown Goal"
        
        if meta_path.exists():
            try:
                import yaml
                # Use to_thread for blocking file I/O
                def _read_meta():
                    with open(meta_path, 'r') as f:
                        return yaml.safe_load(f)
                
                m = await asyncio.to_thread(_read_meta)
                if m:
                    title = m.get("title") or m.get("session_id")
                    goal = m.get("goal", "Recovered Goal")
            except Exception as e:
                logger.warning(f"MetadataService: Failed to parse {meta_path}: {e}")
        
        await self.db.insert_session(sdir.name, goal, str(sdir), title=title)

    async def sync_skills(self):
        """Discover and index skills in the skills/ directory."""
        if not self.skills_path.exists():
            return

        for sdir in self.skills_path.iterdir():
            if sdir.is_dir():
                skill_id = sdir.name
                skill_file = sdir / "SKILL.md"
                if skill_file.exists():
                    query = "INSERT OR REPLACE INTO skills (id, name, root_path, last_scanned) VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
                    await self.db.execute(query, (skill_id, skill_id, str(sdir)))
                    
        logger.info("MetadataService: Skills synced.")

    async def get_active_skills(self) -> list:
        """Return a list of all registered skills."""
        rows = await self.db.execute("SELECT id, name, root_path FROM skills")
        return [{"id": r[0], "name": r[1], "path": r[2]} for r in rows]
