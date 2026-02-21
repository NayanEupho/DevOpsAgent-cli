import json
from typing import Optional, Dict, Any
from loguru import logger
from src.intelligence.registry import IntelligenceRegistry

class SemanticCache:
    """Caches LLM responses based on query similarity to reduce latency."""
    
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
        self.registry = IntelligenceRegistry.get_instance()

    async def get(self, query: str) -> Optional[str]:
        """Check if a similar query exists in the cache (Vector DB)."""
        # We leverage the existing memories table but with a dedicated 'cache' namespace
        hits = await self.registry.vector.search(query, limit=1, threshold=self.threshold)
        if hits:
            hit = hits[0]
            meta = hit["metadata"]
            if isinstance(meta, str):
                 import json
                 meta = json.loads(meta)
            
            if meta.get("context_type") == "semantic_cache":
                logger.info(f"Semantic Cache: HIT for '{query[:30]}...' (Score: {hit['score']:.2f})")
                return meta.get("cached_response")
        return None

    async def set(self, query: str, response: str):
        """Store a new query-response pair in the semantic cache."""
        if not query or not response:
            return
            
        metadata = {
            "context_type": "semantic_cache",
            "query": query,
            "session_id": "global_cache"
        }
        
        # We store the response as the 'text' to be retrieved, but embed the query
        # Since VectorService.add_texts embeds the input 'texts', we use a trick:
        # We'll use a specific method or ensure the query is what gets indexed.
        # Implementation note: VectorService indexes the 'texts' list.
        # So we index the query text but point the result to the response.
        # Actually, standard semantic cache: Index(Query) -> Return(Response).
        
        # Refactoring VectorService to support distinct indexing vs storage would be ideal,
        # but for now we store the query as text and response in metadata.
        metadata["cached_response"] = response
        # Expert Hardening Phase O: Use track_task for shutdown safety
        self.registry.track_task(self.registry.vector.add_texts([query], [metadata]))
        logger.debug(f"Semantic Cache: SET for '{query[:30]}...'")
