import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.gcc.session import session_manager
from src.agent.core import AgentCore

async def test_logging():
    print("--- Final GCC Logging Verification ---")
    goal = "final verification of logging fix"
    session = session_manager.create_session(goal)
    print(f"Created session: {session.id}")
    
    agent = AgentCore(session)
    
    print("Sending message to agent...")
    await agent.chat("Say 'Logging works!' and stop.")
    
    print("Shutting down agent...")
    await agent.shutdown()
    
    log_path = session.path / "log.md"
    commit_path = session.path / "commit.md"
    
    print(f"\nVerifying logs...")
    log_content = log_path.read_text(encoding="utf-8")
    commit_content = commit_path.read_text(encoding="utf-8")
    
    if "Logging works!" in log_content and "## [" in log_content:
        print("✓ log.md: SUCCESS")
    else:
        print("✗ log.md: FAILED")
        print(f"Content: {log_content}")

    if "Final response to: Say 'Logging works!'" in commit_content:
        print("✓ commit.md: SUCCESS")
    else:
        print("✗ commit.md: FAILED")
        print(f"Content: {commit_content}")

if __name__ == "__main__":
    asyncio.run(test_logging())
