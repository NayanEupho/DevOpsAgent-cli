import re
from pathlib import Path
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class GCCIngestor:
    @staticmethod
    def parse_log(log_path: Path, start_offset: int = 0) -> List[BaseMessage]:
        """Parse log.md into LangChain messages, optionally starting from an offset.
        The offset refers to the number of top-level headers (## [HH:MM]) previously processed.
        """
        if not log_path.exists():
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        messages = []
        # Split by sections starting with ## [HH:MM]
        sections = re.split(r'\n(?=## \[\d{2}:\d{2}\])', content)

        # Apply offset to skip already processed sections
        effective_sections = sections[start_offset:] if start_offset < len(sections) else []

        for section in effective_sections:
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
                messages.append(AIMessage(content=f"[{timestamp}] {body}"))
            else:
                messages.append(HumanMessage(content=f"[{timestamp}] {body}"))

        return messages

    @staticmethod
    def get_new_entries(log_path: Path, processed_count: int) -> List[BaseMessage]:
        """Get only the entries that haven't been processed yet."""
        # Use the offset directly in parse_log to avoid re-parsing the head
        return GCCIngestor.parse_log(log_path, start_offset=processed_count)
