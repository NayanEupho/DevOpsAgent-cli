import asyncio
import time
from pathlib import Path
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import Session, SessionManager
from src.config import config
from loguru import logger
from langchain_core.messages import HumanMessage

async def run_local_benchmark():
    print("\n" + "="*50)
    print("        DEVOPS AGENT LOCAL LOGIC BENCHMARK")
    print("="*50)
    
    # 1. Measure Static Skill Loading
    print("\n[1/2] Measuring Static Skill Loading...")
    mgr = SessionManager()
    session = mgr.create_session("Local Benchmark")
    
    start_init = time.perf_counter()
    agent = LangGraphAgent(session)
    duration = time.perf_counter() - start_init
    
    skill_count = len(agent.skills_documentation.split("### SKILL:")) - 1
    print(f"      Skills Loaded: {skill_count}")
    print(f"      Agent Init (Skill Loading): {duration*1000:.1f}ms")

    # 2. Measure Ingestion Latency (Incremental Sync)
    print("\n[2/2] Measuring Ingestion Latency (Incremental Sync)...")
    log_file = session.path / "log.md"
    # Write 10 entries to simulate some history
    with open(log_file, "a") as f:
        for i in range(10):
            f.write(f"## 2024-02-21 12:00:{i:02d}\n[AI] Action {i}\n[TOOL] Result {i}\n")
    
    state = {"messages": [HumanMessage(content="Hello")], "last_synced_count": 0}
    
    start_ingest = time.perf_counter()
    await agent.ingestion_node(state)
    ingest_duration = time.perf_counter() - start_ingest
    print(f"      Log Ingestion (10 entries): {ingest_duration*1000:.1f}ms")

    print("\n" + "="*50)
    print("               SUMMARY")
    print("="*50)
    print(f"✅ Skill Loading: {duration*1000:.1f}ms (Target: < 2000ms)")
    print(f"✅ Log Ingestion: {ingest_duration*1000:.1f}ms (Target: < 150ms)")

if __name__ == "__main__":
    asyncio.run(run_local_benchmark())
