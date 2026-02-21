from datetime import datetime
from pathlib import Path
from src.gcc.storage import GCCStorage

class OTAEntry:
    def __init__(self, observation: str = "", thought: str = "", action: str = "", output: str = "", inference: str = ""):
        self.timestamp = datetime.now().strftime("%H:%M")
        self.observation = observation
        self.thought = thought
        self.action = action
        self.output = output
        self.inference = inference

    def to_markdown(self) -> str:
        return f"""
## [{self.timestamp}] AI
OBSERVATION: {self.observation}

THOUGHT: {self.thought}

ACTION: {self.action}

OUTPUT:
{self.output}

INFERENCE: {self.inference}

---
"""

class HumanEntry:
    def __init__(self, command: str, output: str):
        self.timestamp = datetime.now().strftime("%H:%M")
        self.command = command
        self.output = output

    def to_markdown(self) -> str:
        return f"""
## [{self.timestamp}] HUMAN
{self.command}

OUTPUT:
{self.output}

---
"""

class GCCLogger:
    def __init__(self, session_path: Path):
        self.log_path = session_path / "log.md"
        self.commit_path = session_path / "commit.md"

    def log_ai_action(self, **kwargs):
        entry = OTAEntry(**kwargs)
        GCCStorage.atomic_append(str(self.log_path), entry.to_markdown())

    def log_human_action(self, command: str, output: str):
        entry = HumanEntry(command, output)
        GCCStorage.atomic_append(str(self.log_path), entry.to_markdown())

    def log_commit(self, summary: str, finding: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"### [{timestamp}] COMMIT\n**Summary:** {summary}\n**Finding:** {finding}\n\n---\n"
        GCCStorage.atomic_append(str(self.commit_path), content)
