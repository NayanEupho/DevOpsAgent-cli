import re
from typing import List, Any
from loguru import logger

class MarkdownAwareChunker:
    @staticmethod
    def chunk_text(text: str, max_chars: int = 4000) -> List[str]:
        """Split markdown by headings (H2, H3) with size guards."""
        # Split by ## or ### headings
        sections = re.split(r'\n(?=##+ )', text)
        
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Expert Hardening Phase K: Size Guard
            # If a section is too large, sliding window split
            if len(section) > max_chars:
                logger.debug(f"Chunker: Splitting large section ({len(section)} chars)")
                for i in range(0, len(section), max_chars - 200): # 200 char overlap
                    chunks.append(section[i:i + max_chars])
            else:
                chunks.append(section)
            
        return chunks

class PlatinumEnvelope:
    @staticmethod
    def wrap(source: str, content: str, metadata: dict) -> str:
        """Wraps content in a high-fidelity 'Platinum Envelope' for LLM clarity."""
        meta_str = "\n".join([f"  - {k}: {v}" for k, v in metadata.items()])
        return f"""
[PLATINUM_ENVELOPE: {source}]
--------------------------------------------------
METADATA:
{meta_str}
--------------------------------------------------
CONTENT:
{content}
--------------------------------------------------
[/PLATINUM_ENVELOPE]
"""

class ContextManager:
    @staticmethod
    def trim_messages(messages: list, max_len: int = 15) -> list:
        """Prunes message history to stay within context window limits."""
        if len(messages) <= max_len:
            return messages
        
        # Keep the head (if needed) and the tail
        # Standard implementation for this agent: Keep last N
        logger.debug(f"ContextManager: Pruning history from {len(messages)} to {max_len}")
        return messages[-max_len:]
    
    @staticmethod
    async def get_condensed_history(agent, query: str) -> str:
        """Wrapper for RAG retrieval to avoid cluttering nodes."""
        return await agent.intelligence.remember(query)
