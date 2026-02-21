import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from src.config import config
from src.gcc.storage import GCCStorage

class Session:
    def __init__(self, session_id: str, goal: str, created_at: str = None):
        self.id = session_id
        self.goal = goal
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.path = Path(config.agent.gcc_base_path) / "sessions" / self.id

    def get_metadata(self) -> dict:
        return {
            "session_id": self.id,
            "goal": self.goal,
            "created_at": self.created_at,
            "status": "active"
        }

    def update_metadata(self, new_data: dict):
        current_path = self.path / "metadata.yaml"
        if current_path.exists():
            with open(current_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            data = self.get_metadata()
        
        data.update(new_data)
        # Expert Hardening: Use safe_dump to avoid !!python/object tags that break subsequent loads
        GCCStorage.atomic_write(str(current_path), yaml.safe_dump(data))

class SessionManager:
    def __init__(self):
        self.base_path = Path(config.agent.gcc_base_path)
        self.sessions_path = self.base_path / "sessions"
        self.archived_path = self.base_path / "archived"
        self.main_md_path = self.base_path / "main.md"
        
        self.ensure_dirs()

    def ensure_dirs(self):
        self.sessions_path.mkdir(parents=True, exist_ok=True)
        self.archived_path.mkdir(parents=True, exist_ok=True)
        if not self.main_md_path.exists():
            self._init_main_md()

    def _init_main_md(self):
        content = "# DevOps Agent — Project Memory\n\n## Active Session\n→ None\n\n## Session History\n\n| Session | Date | Goal | Status | Commits | Key Finding |\n|---------|------|------|--------|---------|-------------|\n"
        GCCStorage.atomic_write(str(self.main_md_path), content)

    def create_session(self, goal: str) -> Session:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        slug = goal.lower().replace(" ", "-")[:30]
        
        # Determine next ID (BUG-10 FIX: parse max to avoid gaps from deletions)
        existing = list(self.sessions_path.glob("session_*"))
        if existing:
            import re
            ids = []
            for d in existing:
                m = re.match(r"session_(\d+)_", d.name)
                if m:
                    ids.append(int(m.group(1)))
            next_id = max(ids) + 1 if ids else 1
        else:
            next_id = 1
        session_id = f"session_{next_id:03d}_{timestamp}_{slug}"
        
        session = Session(session_id, goal)
        session.path.mkdir(parents=True, exist_ok=True)
        
        # Create initial files
        # Expert Hardening: Use safe_dump for consistency
        GCCStorage.atomic_write(str(session.path / "metadata.yaml"), yaml.safe_dump(session.get_metadata()))
        GCCStorage.atomic_write(str(session.path / "log.md"), f"# Log — {goal}\n\n")
        GCCStorage.atomic_write(str(session.path / "commit.md"), f"# Commits — {goal}\n\n")
        
        # Update main.md
        self.update_active_session(session)
        
        return session

    def update_active_session(self, session: Session):
        # This is a bit simplified; real implementation would parse and replace the "Active Session" section
        content = f"# DevOps Agent — Project Memory\n\n## Active Session\n→ {session.id} (in progress)\n   Started: {session.created_at}\n   Goal: {session.goal}\n\n## Session History\n"
        # In a real app, we'd append to history here instead of just overwriting.
        GCCStorage.atomic_write(str(self.main_md_path), content)

    def list_sessions(self) -> List[dict]:
        sessions = []
        for sdir in self.sessions_path.iterdir():
            if sdir.is_dir() and sdir.name.startswith("session_"):
                meta_path = sdir / "metadata.yaml"
                if meta_path.exists():
                    with open(meta_path, 'r') as f:
                        sessions.append(yaml.safe_load(f))
        return sessions

session_manager = SessionManager()
