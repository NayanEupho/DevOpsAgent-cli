import lancedb
import pyarrow as pa
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from src.config import config
from langchain_ollama import OllamaEmbeddings

class VectorService:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(config.agent.gcc_base_path) / "vector_store"
        self.embeddings = OllamaEmbeddings(
            model=config.ollama.embedding_model,
            base_url=config.ollama.host
        )
        self._db = None
        self._table = None
        self._embed_cache = {} # Simple memory cache for TTFT optimization

    def connect(self):
        """Connect to LanceDB and ensure the table exists."""
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        
        # BUG-09 FIX: Dynamically detect embedding dimension from the model
        try:
            sample = self.embeddings.embed_query("dimension probe")
            dim = len(sample)
        except Exception:
            dim = 768  # Fallback for offline/error scenarios
            logger.warning(f"VectorService: Could not probe embedding dim, defaulting to {dim}")

        # Schema: vector, text, metadata (json), session_id
        schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), dim)),
            pa.field("text", pa.string()),
            pa.field("metadata", pa.string()), # Stored as JSON string
            pa.field("session_id", pa.string()) # Expert Hardening Phase K: Dedicated indexed column
        ])
        
        if "memories" not in self._db.table_names():
            self._table = self._db.create_table("memories", schema=schema)
        else:
            self._table = self._db.open_table("memories")
            
            # Expert Hardening Phase Q: Schema Self-Healing
            # If the table exists but is missing columns (e.g. session_id), we recreate it
            existing_columns = self._table.schema.names
            required_columns = ["vector", "text", "metadata", "session_id"]
            
            missing = [c for c in required_columns if c not in existing_columns]
            if missing:
                logger.warning(f"VectorService: Schema mismatch (missing {missing}). Recreating memories table...")
                self._db.drop_table("memories")
                self._table = self._db.create_table("memories", schema=schema)
        
        logger.info(f"LanceDB initialized at {self.db_path} (dim={dim})")

    async def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """Embed and insert texts into the vector store."""
        if not texts:
            return

        # Generate embeddings
        vectors = self.embeddings.embed_documents(texts)
        
        import json
        data = []
        for text, vector, meta in zip(texts, vectors, metadatas):
            data.append({
                "vector": vector,
                "text": text,
                "metadata": json.dumps(meta),
                "session_id": meta.get("session_id", "N/A") # Expert Hardening Phase K
            })
        
        self._table.add(data)
        logger.debug(f"VectorService: Indexed {len(texts)} chunks.")

    async def search(self, query: str, limit: int = 3, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search for similar contexts."""
        if query in self._embed_cache:
            query_vec = self._embed_cache[query]
        else:
            query_vec = self.embeddings.embed_query(query)
            # Limit cache size
            if len(self._embed_cache) > 100:
                self._embed_cache.pop(next(iter(self._embed_cache)))
            self._embed_cache[query] = query_vec
        
        # LanceDB search
        results = (
            self._table.search(query_vec)
            .metric("cosine")
            .limit(limit)
            .to_pandas()
        )
        
        import json
        outputs = []
        for _, row in results.iterrows():
            # Distance in LanceDB is usually 1 - similarity for cosine
            # If distance is small, it matches
            score = 1 - row["_distance"]
            if score >= threshold:
                outputs.append({
                    "text": row["text"],
                    "metadata": json.loads(row["metadata"]),
                    "score": score
                })
        
        return outputs

    def delete_session_memories(self, session_id: str):
        """Remove all vector entries for a specific session."""
        # Expert Hardening Phase K: Direct column filter
        self._table.delete(f"session_id = '{session_id}'")
        logger.info(f"VectorService: Dropped memories for {session_id}")

    def reset_all(self):
        """Wipe the entire vector store."""
        # Simplest way is to drop and recreate
        self._db.drop_table("memories")
        self.connect()
        logger.warning("VectorService: Full reset complete.")
