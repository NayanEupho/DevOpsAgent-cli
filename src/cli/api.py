from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
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
    """Returns the full DAG of sessions for visualization with rich metadata."""
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    query = """
    SELECT id, title, goal, parent_id, status, created_at, path, session_type 
    FROM sessions 
    ORDER BY created_at ASC
    """
    rows = await registry.db.read_execute(query)
    
    nodes = []
    for row in rows:
        session_id = row[0]
        metrics = await registry.db.get_session_metrics(session_id)
        
        nodes.append({
            "id": session_id,
            "title": row[1],
            "goal": row[2],
            "parentId": row[3],
            "status": row[4],
            "createdAt": row[5],
            "path": row[6],
            "type": row[7],
            "isActive": row[4] == "active",
            "commandCount": metrics["commandCount"]
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
    
    # Fetch real metrics from DB
    metrics = await registry.db.get_session_metrics(session_id)
    
    content = {
        "log": "",
        "commit": "",
        "os": metrics["os"],
        "shell": metrics["shell"]
    }
    
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8') as f:
            content["log"] = f.read()
            
    if commit_path.exists():
        with open(commit_path, 'r', encoding='utf-8') as f:
            content["commit"] = f.read()
            
    return content

@app.get("/sessions/{session_id}/export/{file_type}")
async def export_session_file(session_id: str, file_type: str):
    """Securely exports log.md or commit.md as a file download."""
    if file_type not in ["log", "commit"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    rows = await registry.db.read_execute("SELECT path FROM sessions WHERE id = ?", (session_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session_path = Path(rows[0][0]).resolve()
    # Edge Case Hardening: Ensure path is within GCC base to prevent traversal
    gcc_base = Path(config.agent.gcc_base_path).resolve()
    if not str(session_path).startswith(str(gcc_base)):
         raise HTTPException(status_code=403, detail="Access denied")

    filename = f"{file_type}.md"
    target_file = session_path / filename
    
    if not target_file.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found on disk")
        
    return FileResponse(
        path=target_file,
        filename=f"{session_id}_{filename}",
        media_type="text/markdown"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
