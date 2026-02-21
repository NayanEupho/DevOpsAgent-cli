import asyncio
import os
from pathlib import Path
from src.intelligence.registry import IntelligenceRegistry
from langchain_core.messages import HumanMessage

async def test_intelligence_stack():
    print("[bold cyan]Starting Phase 6: Intelligence Stack Test...[/bold cyan]\n")
    
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # 1. Test SQLite Session Persistence
    session_id = "test_intel_session_001"
    await registry.db.insert_session(session_id, "Testing Intelligence", "./test_path")
    rows = await registry.db.execute("SELECT goal FROM sessions WHERE id = ?", (session_id,))
    if rows and rows[0][0] == "Testing Intelligence":
        print("[green]SUCCESS: SQLite Session persistence verified.[/green]")
    else:
        print("[red]FAILED: SQLite Session persistence.[/red]")

    # 2. Test Vector Storage (Semantic Memory)
    test_text = "To fix an OOM error on Kubernetes, you should increase the resource limits in the deployment spec."
    test_meta = {"session_id": session_id, "type": "fix"}
    
    print("Indexing test memory...")
    await registry.vector.add_texts([test_text], [test_meta])
    
    # Wait for a brief moment for LanceDB to commit
    await asyncio.sleep(1)
    
    print("Querying semantic memory...")
    hits = await registry.remember("How do I fix Kubernetes OOM?")
    if "OOM error" in hits:
        print("[green]SUCCESS: Semantic RAG recall verified.[/green]")
        print(f"Recall Content: {hits[:100]}...")
    else:
        print("[red]FAILED: Semantic memory recall.[/red]")

    # 3. Test Skill Sync
    await registry.metadata.sync_skills()
    skills = await registry.metadata.get_active_skills()
    if skills:
        print(f"[green]SUCCESS: Found {len(skills)} registered skills.[/green]")
        for s in skills:
            print(f" - Registered Skill: {s['name']}")
    else:
        print("[yellow]WARNING: No skills found to sync.[/yellow]")

    await registry.shutdown()
    print("\n[bold cyan]Phase 6 Verification Complete![/bold cyan]")

if __name__ == "__main__":
    from rich import print
    asyncio.run(test_intelligence_stack())
