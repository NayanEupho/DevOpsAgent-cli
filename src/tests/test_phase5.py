import asyncio
import os
from pathlib import Path
from src.gcc.session import session_manager
from src.agent.graph_core import LangGraphAgent
from src.gcc.storage import GCCStorage
from langchain_core.messages import HumanMessage
from rich.console import Console

console = Console()

async def test_negotiation_and_sync():
    console.print("[bold cyan]Starting Phase 5: Negotiation & Sync Test...[/bold cyan]\n")

    # 1. Create a session
    session = session_manager.create_session("Phase 5 Verification")
    console.print(f"Created Session: {session.id}")

    # 2. Mock initial history
    initial_log = "## [22:00] HUMAN\nHello\n\n---\n"
    GCCStorage.atomic_write(str(session.path / "log.md"), initial_log)

    # 3. Initialize Agent
    agent = LangGraphAgent(session)
    thread_config = {"configurable": {"thread_id": session.id}}

    # 4. Trigger ingestion and first turn
    console.print("\n[bold green]Case 1: Initial Ingestion[/bold green]")
    async for event in agent.app.astream({"messages": [HumanMessage(content="What did we do so far?")]}, thread_config, stream_mode="values"):
        pass
    
    state = await agent.app.aget_state(thread_config)
    # We expect messages from log + the new human message + AI response
    console.print(f"Message count after turn 1: {len(state.values['messages'])}")

    # 5. Simulate Manual Mode (Externally add to log)
    console.print("\n[bold green]Case 2: Manual Sync Detection[/bold green]")
    manual_entry = "## [22:05] HUMAN\ndocker ps\n\nOUTPUT:\nCONTAINER ID IMAGE ...\n\n---\n"
    GCCStorage.atomic_append(str(session.path / "log.md"), manual_entry)
    
    # Run another turn - the ingestion node should pick up the delta
    async for event in agent.app.astream({"messages": [HumanMessage(content="Did you see the docker command?")]}, thread_config, stream_mode="values"):
        pass
    
    final_state = await agent.app.aget_state(thread_config)
    console.print(f"Message count after sync turn: {len(final_state.values['messages'])}")
    
    # Verify the manual entry exists in state
    found_sync = any("docker ps" in m.content for m in final_state.values['messages'])
    if found_sync:
        console.print("[green]SUCCESS: Manual command correctly synced into reasoning state.[/green]")
    else:
        console.print("[red]FAILED: Manual command missing from state.[/red]")

    console.print("\n[bold cyan]Phase 5 Verification Complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(test_negotiation_and_sync())
