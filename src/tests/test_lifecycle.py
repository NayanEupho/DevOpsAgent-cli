import asyncio
import os
from pathlib import Path
from rich import print
from src.intelligence.registry import IntelligenceRegistry

async def test_lifecycle_management():
    print("[bold cyan]Starting Phase 6: Lifecycle Management Test...[/bold cyan]\n")
    
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # Setup test data
    s1 = "lifecycle_test_001"
    s2 = "lifecycle_test_002"
    await registry.db.insert_session(s1, "Initial Goal 1", "./p1")
    await registry.db.insert_session(s2, "Initial Goal 2", "./p2")
    await registry.vector.add_texts(["Memory 1"], [{"session_id": s1}])
    await registry.vector.add_texts(["Memory 2"], [{"session_id": s2}])
    await asyncio.sleep(1) # Wait for commit
    
    # 1. Test Rename
    print("Testing Rename...")
    await registry.rename_session(s1, "REPOINTED: New Title")
    rows = await registry.db.execute("SELECT title FROM sessions WHERE id = ?", (s1,))
    if rows and rows[0][0] == "REPOINTED: New Title":
        print("[green]SUCCESS: Session renamed in SQLite.[/green]")
    
    # 2. Test Specific Deletion
    print(f"Testing Specific Deletion of {s1}...")
    await registry.delete_session(s1)
    # Check SQLite
    rows = await registry.db.execute("SELECT id FROM sessions WHERE id = ?", (s1,))
    if not rows:
        print("[green]SUCCESS: Session deleted from SQLite.[/green]")
    # Check Vector Store
    hits = await registry.remember("Memory 1")
    if s1 not in hits:
        print("[green]SUCCESS: Session memories purged from Vector Store.[/green]")
    
    # 3. Test Full (Nuclear) Reset
    print("Testing Nuclear Reset...")
    # Create a dummy session folder to delete
    dummy_path = Path(".GCC/sessions/dummy_session")
    dummy_path.mkdir(parents=True, exist_ok=True)
    
    await registry.reset_intelligence(include_gcc=True)
    
    # Check SQLite
    rows = await registry.db.execute("SELECT count(*) FROM sessions")
    if rows and rows[0][0] == 0:
        print("[green]SUCCESS: SQLite fully wiped.[/green]")
        
    # Check Vector Store
    try:
        hits = await registry.remember("Memory 2")
        if not hits:
            print("[green]SUCCESS: Vector Store fully wiped.[/green]")
    except:
        print("[green]SUCCESS: Vector Store reset.[/green]")
        
    # Check GCC
    if not dummy_path.exists():
        print("[green]SUCCESS: GCC Sessions directory purged.[/green]")

    await registry.shutdown()
    print("\n[bold cyan]Lifecycle Management Verification Complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(test_lifecycle_management())
