import asyncio
import os
import yaml
from pathlib import Path
from src.config import config
from src.skills.parser import PermissionClassifier
from src.gcc.session import session_manager
from src.gcc.log import GCCLogger, OTAEntry
from src.gcc.graph import GCCGraph
from src.ollama_client import ollama_client
from rich.console import Console

console = Console()

async def run_robust_test():
    console.print("[bold cyan]Starting Robust Integration Test...[/bold cyan]\n")

    # 1. Configuration & Ollama Health
    console.print("[bold green]1. Checking Ollama Health...[/bold green]")
    health = await ollama_client.check_health()
    if not health:
        console.print("[bold red]FAILED: Ollama health check failed. Ensure the model is pulled.[/bold red]")
        return
    console.print(f"Ollama Model: {config.ollama.model} [dim green]PASSED[/dim green]\n")

    # 2. Permission Classifier
    console.print("[bold green]2. Testing Permission Classifier (Safety Gates)...[/bold green]")
    classifier = PermissionClassifier(config.agent.skills_path)
    
    test_cases = [
        ("kubectl get pods", "auto_execute"),
        ("kubectl delete pod foo", "destructive"),
        ("docker run ubuntu", "requires_approval"),
        ("git push --force", "destructive"),
        ("ls -la", "auto_execute"),
        ("rm -rf /", "destructive"),
        ("unknown_command", "requires_approval")
    ]
    
    for cmd, expected in test_cases:
        actual = classifier.classify(cmd)
        status = "[green]OK[/green]" if actual == expected else f"[red]FAIL (Got {actual})[/red]"
        console.print(f"  '{cmd}' -> {actual} {status}")
    console.print("")

    # 3. Session & GCC Logging
    console.print("[bold green]3. Testing Session & GCC Logging...[/bold green]")
    session = session_manager.create_session("Robust Integration Test Session")
    console.print(f"  Created Session: [blue]{session.id}[/blue]")
    
    logger = GCCLogger(session.path)
    logger.log_ai_action(
        observation="Testing logging functionality",
        thought="Verifying that all parts of the OTA entry are preserved",
        action="echo 'test'",
        output="test",
        inference="Logging works as expected"
    )
    logger.log_commit("Test Commit", "Confirmed logging integrity")
    
    log_file = session.path / "log.md"
    if log_file.exists() and "OBSERVATION" in log_file.read_text():
        console.print("  OTA Log Entry [dim green]PASSED[/dim green]")
    else:
        console.print("  OTA Log Entry [dim red]FAILED[/dim red]")
        
    commit_file = session.path / "commit.md"
    if commit_file.exists() and "Test Commit" in commit_file.read_text():
        console.print("  Commit Entry [dim green]PASSED[/dim green]")
    else:
        console.print("  Commit Entry [dim red]FAILED[/dim red]")
    console.print("")

    # 4. Visual Graph
    console.print("[bold green]4. Testing Visual GCC Graph...[/bold green]")
    graph = GCCGraph(session.path)
    tree = graph.render()
    if tree:
        console.print("  Graph Rendering [dim green]PASSED[/dim green]")
        graph.show()
    else:
        console.print("  Graph Rendering [dim red]FAILED[/dim red]")
    console.print("")

    # 5. External Environment Check
    console.print("[bold green]5. Verifying Host Environment (Docker/K8s)...[/bold green]")
    try:
        import subprocess
        docker_v = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip()
        console.print(f"  Docker: {docker_v or 'Not found'}")
        
        k8s_v = subprocess.run(["kubectl", "version", "--client"], capture_output=True, text=True).stdout.strip()
        console.print(f"  K8s: {k8s_v or 'Not found'}")
    except Exception as e:
        console.print(f"  Environment probe error: {e}")
    
    console.print("\n[bold cyan]Tests Complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(run_robust_test())
