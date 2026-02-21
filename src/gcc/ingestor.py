import re
from pathlib import Path
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class GCCIngestor:
    @staticmethod
    def parse_log(log_path: Path) -> List[BaseMessage]:
        """Parse log.md into LangChain messages."""
        if not log_path.exists():
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        messages = []
        # Split by sections starting with ## [HH:MM]
        sections = re.split(r'\n(?=## \[\d{2}:\d{2}\])', content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Detect if it's AI or HUMAN
            header_match = re.search(r'## \[(\d{2}:\d{2})\]\s+(AI|HUMAN)', section)
            if not header_match:
                continue

            timestamp = header_match.group(1)
            role = header_match.group(2)

            # Strip header
            body = re.sub(r'## \[\d{2}:\d{2}\]\s+(AI|HUMAN)', '', section, count=1).strip()

            if role == "AI":
                # Convert OTA trace back to a readable thought/action summary
                # We prefix with timestamp to keep the agent aware of 'when'
                messages.append(AIMessage(content=f"[{timestamp}] {body}"))
            else:
                messages.append(HumanMessage(content=f"[{timestamp}] {body}"))

        return messages

    @staticmethod
    def get_new_entries(log_path: Path, processed_count: int) -> List[BaseMessage]:
        """Get only the entries that haven't been processed yet."""
        all_messages = GCCIngestor.parse_log(log_path)
        if len(all_messages) > processed_count:
            return all_messages[processed_count:]
        return []
