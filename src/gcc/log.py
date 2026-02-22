from datetime import datetime
from pathlib import Path
from src.gcc.storage import GCCStorage
from src.intelligence.observability import Redactor

class OTAEntry:
    def __init__(self, observation: str = "", thought: str = "", action: str = "", output: str = "", inference: str = ""):
        self.timestamp = datetime.now().strftime("%H:%M")
        
        # Redact and truncate inputs
        self.observation = Redactor.redact_text(observation)
        self.thought = Redactor.redact_text(thought)
        self.action = Redactor.redact_text(action)
        
        # Truncate large outputs to 5000 chars for log sustainability
        raw_output = Redactor.redact_text(output)
        if len(raw_output) > 5000:
            self.output = raw_output[:5000] + "\n... (truncated for log brevity)"
        else:
            self.output = raw_output
            
        self.inference = Redactor.redact_text(inference)

    def to_markdown(self) -> str:
        # User requested AI: <cmd> format
        return f"""
## [{self.timestamp}] AI: {self.action}
**OBSERVATION:** {self.observation if self.observation else "N/A"}

**THOUGHT:** {self.thought if self.thought else "N/A"}

**OUTPUT:**
```bash
{self.output if self.output else "(No output)"}
```

**INFERENCE:** {self.inference if self.inference else "N/A"}

---
"""

class HumanEntry:
    def __init__(self, command: str, output: str):
        self.timestamp = datetime.now().strftime("%H:%M")
        self.command = Redactor.redact_text(command)
        
        raw_output = Redactor.redact_text(output)
        if len(raw_output) > 5000:
            self.output = raw_output[:5000] + "\n... (truncated for log brevity)"
        else:
            self.output = raw_output

    def to_markdown(self) -> str:
        # User requested Human: <cmd> format
        return f"""
## [{self.timestamp}] Human: {self.command}
**OUTPUT:**
```bash
{self.output if self.output else "(No output)"}
```

---
"""

class GCCLogger:
    def __init__(self, session_path: Path):
        self.session_path = session_path
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
        summary = Redactor.redact_text(summary)
        finding = Redactor.redact_text(finding)
        
        content = f"### [{timestamp}] COMMIT\n**Summary:** {summary}\n**Finding:** {finding}\n\n---\n"
        GCCStorage.atomic_append(str(self.commit_path), content)
