import asyncio
import os
from pathlib import Path
from src.gcc.session import session_manager
from src.agent.graph_core import LangGraphAgent
from src.gcc.storage import GCCStorage
from rich.console import Console

console = Console()

async def test_gcc_ingestion():
    console.print("[bold cyan]Starting GCC History Ingestion Test...[/bold cyan]\n")

    # 1. Create a session
    session = session_manager.create_session("History Ingestion Verification")
    console.print(f"Created Session: {session.id}")

    # 2. Mock a log.md with history
    log_content = """## [10:00] HUMAN
Hello agent, what is the status of my docker containers?

---

## [10:01] AI
OBSERVATION: User asked for docker status.
THOUGHT: I should run 'docker ps'.
ACTION: run_command(cmd='docker ps')
OUTPUT: CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
INFERENCE: No containers are running.

---
"""
    GCCStorage.atomic_write(str(session.path / "log.md"), log_content)
    console.print("[green]Mocked log.md with previous history.[/green]")

    # 3. Initialize LangGraph Agent
    agent = LangGraphAgent(session)
    thread_config = {"configurable": {"thread_id": session.id}}

    # we want to verify the 'ingestion' node logic
    # We'll run the graph and check the internal state after the ingestion node
    
    initial_input = {
        "messages": [], # Empty start to trigger ingestion
        "session_id": session.id,
        "goal": session.goal
    }

    # Run only up to the planner to see the messages bootstrap
    # But for a simpler test, let's just use the ingestor directly and then verify the graph can handle it.
    
    from src.gcc.ingestor import GCCIngestor
    messages = GCCIngestor.parse_log(session.path / "log.md")
    
    console.print(f"\nParsed [bold]{len(messages)}[/bold] messages from GCC.")
    for msg in messages:
        console.print(f"  [{type(msg).__name__}] {msg.content[:50]}...")

    if len(messages) == 2:
        console.print("[green]SUCCESS: Correct number of messages parsed.[/green]")
    else:
        console.print("[red]FAILED: Incorrect number of messages parsed.[/red]")

    # Verify timestamps are preserved in content
    if "[10:00]" in messages[0].content and "[10:01]" in messages[1].content:
        console.print("[green]SUCCESS: Timestamps correctly preserved in message content.[/green]")
    else:
        console.print("[red]FAILED: Timestamps missing from message content.[/red]")

    console.print("\n[bold cyan]GCC Ingestion Verification Complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(test_gcc_ingestion())
