import asyncio
from pathlib import Path
from src.cli.export import ExportService
from src.intelligence.registry import IntelligenceRegistry

async def test_export():
    print("Starting Phase 7: Export Service Test...")
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # 1. Setup Test Data
    session_id = "export_test_001"
    session_path = Path(".GCC/sessions") / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    
    with open(session_path / "log.md", 'w') as f:
        f.write("AI: Running docker ps\nCMD: docker ps\nOUT: [list of containers]")
    with open(session_path / "commit.md", 'w') as f:
        f.write("- Milestone: Staging environment verified.")
        
    await registry.db.insert_session(session_id, "Test Export logic", str(session_path))
    
    # 2. Trigger Export
    print("Generating Report...")
    report_path = await ExportService.export_session(session_id)
    
    # 3. Verify
    if Path(report_path).exists():
        print(f"[green]SUCCESS: Report generated at {report_path}[/green]")
        with open(report_path, 'r') as f:
            content = f.read()
            if "EXECUTIVE SUMMARY" in content and "MILESTONES" in content:
                print("[green]SUCCESS: Content structure verified.[/green]")
                
    await registry.shutdown()
    print("Export Verification Complete.")

if __name__ == "__main__":
    asyncio.run(test_export())
