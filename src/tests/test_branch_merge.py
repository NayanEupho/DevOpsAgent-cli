import asyncio
from pathlib import Path
from src.intelligence.registry import IntelligenceRegistry

async def test_branch_merge():
    print("Starting Phase 7: Branch & Merge Test...")
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # 1. Setup Parent
    parent_id = "parent_001"
    parent_path = Path(".GCC/sessions") / parent_id
    parent_path.mkdir(parents=True, exist_ok=True)
    with open(parent_path / "log.md", 'w') as f:
        f.write("# Parent Session Log\nInitial state.")
    
    await registry.db.insert_session(parent_id, "Main Goal", str(parent_path))
    
    # 2. Branch
    print("Testing Branching...")
    branch_id = await registry.branch_session(parent_id, "Hypothesis A")
    
    # Verify file copy
    branch_log = Path(".GCC/sessions") / branch_id / "log.md"
    if branch_log.exists():
        print(f"[green]SUCCESS: Branch directory and log created: {branch_id}[/green]")
    
    # 3. Simulate work in branch (Add finding)
    with open(Path(".GCC/sessions") / branch_id / "commit.md", 'w') as f:
        f.write("- Verified that port 8080 is blocked by firewall.\n- Proposed fix: Open port 8080.")
    
    # 4. Merge
    print("Testing Merging...")
    await registry.merge_session(branch_id)
    
    # Verify merge in parent log
    with open(parent_path / "log.md", 'r') as f:
        content = f.read()
        if "MERGED FROM BRANCH" in content and "firewall" in content:
            print("[green]SUCCESS: Findings merged back to parent log.[/green]")
    
    # Verify status change
    rows = await registry.db.execute("SELECT status FROM sessions WHERE id = ?", (branch_id,))
    if rows and rows[0][0] == "merged":
        print("[green]SUCCESS: Branch status updated to 'merged'.[/green]")

    await registry.shutdown()
    print("Branch & Merge Verification Complete.")

if __name__ == "__main__":
    asyncio.run(test_branch_merge())
