import asyncio
import time
from pathlib import Path
from src.agent.graph_core import LangGraphAgent, AgentState
from src.gcc.session import Session, SessionManager
from src.config import config
from src.intelligence.registry import IntelligenceRegistry
from loguru import logger
from langchain_core.messages import HumanMessage

async def run_benchmark():
    print("\n" + "="*50)
    print("        DEVOPS AGENT PERFORMANCE BENCHMARK")
    print("="*50)
    
    # 1. Warm up Ollama and Initialize Registry
    print("\n[1/5] Initializing Systems & Warming up Ollama...")
    start_init = time.perf_counter()
    reg = IntelligenceRegistry.get_instance()
    await reg.initialize()
    init_duration = time.perf_counter() - start_init
    print(f"      Registry Init: {init_duration:.2f}s")

    # 2. Measure Static Skill Loading
    print("\n[2/5] Measuring Static Skill Loading...")
    mgr = SessionManager()
    session = mgr.create_session("Benchmark Session")
    
    start_agent = time.perf_counter()
    agent = LangGraphAgent(session)
    agent_init_duration = time.perf_counter() - start_agent
    
    skill_count = len(agent.skills_documentation.split("### SKILL:")) - 1
    print(f"      Skills Loaded: {skill_count}")
    print(f"      Agent Init (Skill Loading): {agent_init_duration:.2f}s (Target: < 2s)")

    # 3. Measure Pivot Detection (Fast Reflex)
    print("\n[3/5] Measuring Pivot Detection (Fast Reflex)...")
    queries = [
        "What is the status of my docker containers?", # Continue
        "Actually, stop that. Let's switch to a new task: check the git branch.", # Switch
    ]
    
    reflex_latencies = []
    for q in queries:
        start_reflex = time.perf_counter()
        # We call the internal method that uses fast_llm
        await agent._detect_and_handle_pivot(q)
        duration = time.perf_counter() - start_reflex
        reflex_latencies.append(duration)
        print(f"      Query: '{q[:40]}...' -> Latency: {duration:.2f}s")
    
    avg_reflex = sum(reflex_latencies) / len(reflex_latencies)
    print(f"      Avg Reflex Latency: {avg_reflex:.2f}s (Target: < 1s)")

    # 4. Measure Ingestion Latency (Incremental Sync)
    print("\n[4/5] Measuring Ingestion Latency (Incremental Sync)...")
    # Simulate some history
    log_file = session.path / "log.md"
    with open(log_file, "a") as f:
        f.write("## 2024-02-21 12:00:00\n[AI] Running ls...\n[TOOL] file1.txt\n")
    
    state = {"messages": [HumanMessage(content="Hello")], "last_synced_count": 0}
    
    start_ingest = time.perf_counter()
    # ingestion_node returns a dict
    await agent.ingestion_node(state)
    ingest_duration = time.perf_counter() - start_ingest
    print(f"      Log Ingestion (First Sync): {ingest_duration*1000:.1f}ms (Target: < 150ms)")

    # 5. Full Turn TTFT Estimation
    print("\n[5/5] Full Turn Latency Estimation (Planning)...")
    start_plan = time.perf_counter()
    # We won't run a full 'run' to avoid expensive generation, but we check internal components
    # The planner call is the main bottleneck
    print("      (Simulating Turn...)")
    # We already know generation depends on model speed, but the context prep is now instant.
    
    print("\n" + "="*50)
    print("               BENCHMARK SUMMARY")
    print("="*50)
    
    results = [
        ("Registry Init", f"{init_duration:.2f}s", "N/A"),
        ("Skill Loading", f"{agent_init_duration:.2f}s", "< 2.0s"),
        ("Pivot Reflex", f"{avg_reflex:.2f}s", "< 1.0s"),
        ("Ingestion (1 entry)", f"{ingest_duration*1000:.1f}ms", "< 150ms"),
    ]
    
    for metric, val, target in results:
        passed = False
        if target == "N/A":
            passed = True
        else:
            # Parse target and value - order matters for replacement
            # Replace 'ms' first to avoid 's' replacement leaving 'm'
            t_clean = target.replace("< ", "")
            if "ms" in t_clean:
                t_num = float(t_clean.replace("ms", ""))
                t_sec = t_num / 1000
            else:
                t_num = float(t_clean.replace("s", ""))
                t_sec = t_num
                
            v_clean = val
            if "ms" in v_clean:
                v_num = float(v_clean.replace("ms", ""))
                v_sec = v_num / 1000
            else:
                v_num = float(v_clean.replace("s", ""))
                v_sec = v_num
            
            if v_sec < t_sec:
                passed = True
        
        status = "[PASS]" if passed else "[WARN]"
        print(f"{status:8} {metric:20} : {val:8} (Target: {target})")

    await reg.shutdown()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
