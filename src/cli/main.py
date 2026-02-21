import typer
from typing import Optional
from src.gcc.session import session_manager
from src.agent.core import AgentCore
from src.ollama_client import ollama_client
from loguru import logger
import asyncio

app = typer.Typer(help="DevOps Agent — Terminal-native AI for Docker, K8s, and Git.")

async def start_agent(goal: Optional[str] = None, session_id: Optional[str] = None, debug: bool = False):
    # Health check
    if not await ollama_client.check_health():
        typer.echo("Error: Ollama is not ready. Please check OLLAMA_HOST and OLLAMA_MODEL in .env")
        raise typer.Exit(code=1)

    if goal:
        session = session_manager.create_session(goal)
    elif session_id:
        # BUG-17 FIX: resolve specific session by ID
        sessions = session_manager.list_sessions()
        match = [s for s in sessions if s['session_id'] == session_id or session_id in s['session_id']]
        if not match:
            typer.echo(f"Session '{session_id}' not found.")
            raise typer.Exit(code=1)
        session_info = match[0]
        from src.gcc.session import Session
        session = Session(session_info['session_id'], session_info['goal'], session_info['created_at'])
    else:
        # Try to resume or list
        sessions = session_manager.list_sessions()
        if not sessions:
            typer.echo("No active sessions. Create one with: devops-agent new 'goal'")
            raise typer.Exit()
        
        # Resume the latest for foundation
        session_info = sessions[-1]
        from src.gcc.session import Session
        session = Session(session_info['session_id'], session_info['goal'], session_info['created_at'])

    agent = AgentCore(session, debug_mode=debug)
    await agent.run_loop()

@app.command()
def new(goal: str, debug: bool = typer.Option(False, "--debug", help="Enable verbose debug logging")):
    """Start a new session with a specific goal."""
    asyncio.run(start_agent(goal, debug=debug))

@app.command()
def continue_session(session_id: Optional[str] = typer.Argument(None), debug: bool = typer.Option(False, "--debug", help="Enable verbose debug logging")):
    """Resume an existing session."""
    asyncio.run(start_agent(session_id=session_id, debug=debug))

@app.command()
def list_sessions():
    """List all recent sessions."""
    sessions = session_manager.list_sessions()
    if not sessions:
        typer.echo("No sessions found.")
        return

    typer.echo("\nSESSION HISTORY")
    typer.echo("─" * 60)
    for s in sessions:
        typer.echo(f"{s['session_id']} | {s['created_at']} | {s['goal']}")

@app.command()
def reset(nuclear: bool = typer.Option(False, "--nuclear", help="Purge ALL session history and intellectual memory")):
    """Resets the agent state. Use --nuclear for a complete wipe."""
    if nuclear:
        confirmed = typer.confirm("⚠️ DANGER: This will delete ALL session logs, history, and AI memory. Continue?", abort=True)
        if confirmed:
            typer.echo("🚀 Performing Nuclear Reset...")
            from src.intelligence.registry import IntelligenceRegistry
            registry = IntelligenceRegistry.get_instance()
            
            async def _do_reset():
                await registry.initialize()
                await registry.reset_intelligence(include_gcc=True)
                session_manager.reset_all()
            
            asyncio.run(_do_reset())
            typer.echo("✅ System Purged. You have a fresh slate.")
    else:
        typer.echo("Standard reset not implemented. Use 'reset --nuclear' for a full wipe.")

@app.callback(invoke_without_command=True)
def cli_callback(ctx: typer.Context, debug: bool = typer.Option(False, "--debug", help="Enable verbose debug logging")):
    if ctx.invoked_subcommand is None:
        asyncio.run(start_agent(debug=debug))

if __name__ == "__main__":
    app()
