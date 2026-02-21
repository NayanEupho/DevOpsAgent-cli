import asyncio
import os
from pathlib import Path
from src.gcc.session import session_manager
from src.agent.graph_core import LangGraphAgent
from langchain_core.messages import HumanMessage
from rich.console import Console

console = Console()

async def test_langgraph_safety_and_persistence():
    console.print("[bold cyan]Starting LangGraph Safety & Persistence Test...[/bold cyan]\n")

    # 1. Create a session
    session = session_manager.create_session("LangGraph Verification")
    console.print(f"Created Session: {session.id}")

    # 2. Initialize LangGraph Agent
    agent = LangGraphAgent(session)
    thread_config = {"configurable": {"thread_id": session.id}}

    # 3. Simulate a command that needs approval (e.g., delete)
    # Note: We need to mock the LLM or provide a prompt that triggers a tool call
    console.print("\n[bold green]Case 1: Triggering Safety Interrupt[/bold green]")
    user_msg = "Please run 'kubectl delete pod nginx' to cleanup."
    
    # We run the agent. Since it's interactive in LangGraphAgent.run, 
    # we'll test the internal components if we want to automate, 
    # or just run it and expect the prompt.
    
    # For automated verification, let's check if the graph 'interrupts' correctly
    initial_input = {"messages": [HumanMessage(content=user_msg)]}
    
    # First turn
    async for event in agent.app.astream(initial_input, thread_config, stream_mode="values"):
        pass # Stream AI messages
        
    snapshot = await agent.app.aget_state(thread_config)
    console.print(f"Graph State: [yellow]{snapshot.next}[/yellow]")
    
    if "executor" in snapshot.next:
        console.print("[green]SUCCESS: Graph correctly interrupted before executor for destructive command.[/green]")
    else:
        console.print("[red]FAILED: Graph did not interrupt before executor.[/red]")

    # 4. Verify GCC Checkpointer & Metadata
    checkpoint_file = session.path / "checkpoints" / f"{session.id}.pkl"
    if checkpoint_file.exists():
        console.print(f"[green]SUCCESS: GCC Checkpointer persisted state to {checkpoint_file.name}[/green]")
    else:
        console.print("[red]FAILED: GCC Checkpointer did not persist state.[/red]")

    import yaml
    with open(session.path / "metadata.yaml", "r") as f:
        meta = yaml.safe_load(f)
        if "env" in meta:
            console.print(f"[green]SUCCESS: Metadata contains environment info: {meta['env']}[/green]")
        else:
            console.print("[red]FAILED: Metadata missing environment info.[/red]")

    console.print("\n[bold cyan]LangGraph Verification Complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(test_langgraph_safety_and_persistence())
