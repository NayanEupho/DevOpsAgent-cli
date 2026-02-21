import pickle
from typing import Any, Dict, Optional, Tuple, Sequence, List
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from pathlib import Path
from src.gcc.storage import GCCStorage

class GCCCheckpointer(BaseCheckpointSaver):
    def __init__(self, session_path: Path):
        super().__init__()
        self.session_path = session_path
        self.checkpoint_dir = session_path / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        
        path = self.checkpoint_dir / f"{thread_id}.pkl"
        if not path.exists():
            return None
            
        with open(path, "rb") as f:
            data = pickle.load(f)
            
        checkpoint = data["checkpoint"]
        metadata = data["metadata"]
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=data.get("parent_config")
        )

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        return self.get_tuple(config)

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: Any) -> Dict[str, Any]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        
        data = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "parent_config": config.get("parent_config")
        }
        
        path = self.checkpoint_dir / f"{thread_id}.pkl"
        # Expert Hardening Phase K: Atomic write for checkpoints
        GCCStorage.atomic_write(str(path), pickle.dumps(data), mode='wb')
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }

    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: Any) -> Dict[str, Any]:
        return self.put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config: Dict[str, Any], writes: Sequence[Tuple[str, Any]], task_id: str) -> None:
        """Persist pending writes (e.g., tool calls during HITL interrupt)."""
        thread_id = config["configurable"]["thread_id"]
        writes_path = self.checkpoint_dir / f"{thread_id}_writes_{task_id}.pkl"
        with open(writes_path, "wb") as f:
            pickle.dump(writes, f)

    async def aput_writes(self, config: Dict[str, Any], writes: Sequence[Tuple[str, Any]], task_id: str) -> None:
        self.put_writes(config, writes, task_id)

    def list(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[CheckpointTuple] = None, limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        """Scan checkpoint directory and return stored checkpoints."""
        results = []
        for path in sorted(self.checkpoint_dir.glob("*.pkl")):
            if "_writes_" in path.name:
                continue  # Skip write files
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                thread_id = path.stem
                cp_config = {"configurable": {"thread_id": thread_id}}
                results.append(CheckpointTuple(
                    config=cp_config,
                    checkpoint=data["checkpoint"],
                    metadata=data["metadata"],
                    parent_config=data.get("parent_config")
                ))
            except Exception:
                continue
        if limit:
            results = results[:limit]
        return results

    async def alist(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[CheckpointTuple] = None, limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        return self.list(config, filter=filter, before=before, limit=limit)
