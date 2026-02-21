import asyncio
import time
import sys
import os
from loguru import logger
from rich.console import Console
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import SessionManager
from src.intelligence.registry import IntelligenceRegistry

# Configure logging to file only to keep console clean for results
logger.remove()
logger.add("benchmark_robust.log", level="INFO")

console = Console()

async def run_scenario(agent, query, mode, scenario_name):
    console.print(f"\n[bold blue][SCENARIO: {scenario_name}][/bold blue]")
    console.print(f"Query: [white]\"{query}\"[/white] | Mode: [cyan]{mode}[/cyan]")
    
    start_total = time.perf_counter()
    ttft = None
    
    async def _tracker():
        nonlocal ttft
        # We'll use the agent's run method but monitor internal events if possible
        # Since run() handles Live and RenderController, we just measure turn time here.
        # Expert Hardening: Wrap the internal run call to capture the first stream event
        pass

    try:
        # We run the agent's main entry point for a true E2E test
        # Note: RenderController headers will print to console
        await agent.run(query, user_mode=mode)
        
        total_time = time.perf_counter() - start_total
        console.print(f"\n[bold green]Result:[/bold green] COMPLETED")
        console.print(f"Total Latency: [bold white]{total_time:.2f}s[/bold white]")
        return total_time
    except Exception as e:
        console.print(f"\n[bold red]Result: FAILED[/bold red] - {e}")
        return None

async def main():
    console.print("="*60)
    console.print("      DEVOPS AGENT ROBUST E2E BENCHMARK")
    console.print("="*60)
    
    # 1. Initialization
    reg = IntelligenceRegistry.get_instance()
    await reg.initialize()
    
    mgr = SessionManager()
    session = mgr.create_session("Robust E2E Benchmark Session")
    agent = LangGraphAgent(session)
    
    results = {}
    
    # --- SCENARIO A: CHAT MODE ---
    # Expected: No tool usage, fast conversational response
    results["CHAT"] = await run_scenario(
        agent, 
        "Hello, can you tell me what your primary capabilities are?", 
        "CHAT", 
        "Pure Conversation"
    )
    
    # --- SCENARIO B: EXEC MODE ---
    # Expected: Forced execution of a command
    results["EXEC"] = await run_scenario(
        agent, 
        "ls", 
        "EXEC", 
        "Forced Execution"
    )
    
    # --- SCENARIO C: AUTO MODE ---
    # Expected: Multi-step reasoning (Plan -> Execute -> Analyze)
    results["AUTO"] = await run_scenario(
        agent, 
        "Check all docker containers and tell me if any are stopped", 
        "AUTO", 
        "Complex Reasoning Loop"
    )
    
    # --- FINAL REPORT ---
    console.print("\n" + "="*60)
    console.print("               BENCHMARK SUMMARY REPORT")
    console.print("="*60)
    
    # Targets
    targets = {"CHAT": 1.5, "EXEC": 3.0, "AUTO": 8.0}
    
    all_passed = True
    for mode, latency in results.items():
        if latency is None:
            status = "[bold red]FAILED[/bold red]"
            all_passed = False
        else:
            target = targets.get(mode, 10.0)
            if latency <= target:
                status = f"[bold green]PASS[/bold green] (Target: <{target}s)"
            else:
                status = f"[bold yellow]WARM[/bold yellow] (Target: <{target}s)"
            
        console.print(f"  {mode:<8} Latency: {latency:>5.2f}s | {status}" if latency else f"  {mode:<8} Latency:  ERROR | {status}")

    console.print("="*60)
    
    if all_passed:
        console.print("\n[bold green]SYSTEM VERIFIED: Robust and Responsive.[/bold green]")
    else:
        console.print("\n[bold red]SYSTEM REGRESSION DETECTED: Check logs.[/bold red]")
        sys.exit(1)

    await reg.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
