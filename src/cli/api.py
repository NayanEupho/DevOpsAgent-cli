from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from src.intelligence.registry import IntelligenceRegistry
from src.config import config
import os

app = FastAPI(title="DevOps Agent GCC Visualizer API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/sessions/tree")
async def get_session_tree():
    """Returns the full DAG of sessions for visualization."""
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    query = """
    SELECT id, title, goal, parent_id, status, created_at, path 
    FROM sessions 
    ORDER BY created_at ASC
    """
    rows = await registry.db.read_execute(query)
    
    # Get active session from main.md (simplified)
    # In a full impl, we'd have a 'settings' table or similar
    
    nodes = []
    for row in rows:
        nodes.append({
            "id": row[0],
            "title": row[1],
            "goal": row[2],
            "parentId": row[3],
            "status": row[4],
            "createdAt": row[5],
            "path": row[6],
            "isActive": row[4] == "active"
        })
    
    return nodes

@app.post("/sessions/{session_id}/activate")
async def activate_session(session_id: str):
    """Switches the active session for the agent."""
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # 1. Verify existence
    rows = await registry.db.read_execute("SELECT id, title, goal, created_at FROM sessions WHERE id = ?", (session_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Update DB status (simplified deactivate others)
    await registry.db.execute("UPDATE sessions SET status = 'archived' WHERE status = 'active'")
    await registry.db.execute("UPDATE sessions SET status = 'active' WHERE id = ?", (session_id,))
    
    # 3. Update local session manager (main.md context)
    from src.gcc.session import Session, session_manager
    session_data = rows[0]
    new_active = Session(session_data[0], session_data[2], session_data[3])
    session_manager.update_active_session(new_active)
    
    return {"status": "success", "active_session": session_id}

@app.get("/sessions/{session_id}/content")
async def get_session_content(session_id: str):
    """Returns the log.md and commit.md content for a specific session."""
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    rows = await registry.db.read_execute("SELECT path FROM sessions WHERE id = ?", (session_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_path = Path(rows[0][0])
    log_path = session_path / "log.md"
    commit_path = session_path / "commit.md"
    
    content = {
        "log": "",
        "commit": ""
    }
    
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8') as f:
            content["log"] = f.read()
            
    if commit_path.exists():
        with open(commit_path, 'r', encoding='utf-8') as f:
            content["commit"] = f.read()
            
    return content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
