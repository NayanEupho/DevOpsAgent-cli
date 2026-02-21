import asyncio
import time
from pathlib import Path
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import Session, SessionManager
from src.config import config
from src.intelligence.registry import IntelligenceRegistry
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

async def benchmark_e2e_scenarios():
    print("\n" + "="*60)
    print("        DEVOPS AGENT END-TO-END LATENCY BENCHMARK")
    print("="*60)
    
    # Initialize Registry
    reg = IntelligenceRegistry.get_instance()
    await reg.initialize()
    
    mgr = SessionManager()
    
    scenarios = [
        {
            "name": "System Navigation",
            "query": "List all files in my current directory.",
            "goal": "Verify file system access latency"
        },
        {
            "name": "Docker Audit",
            "query": "What docker containers are running on my machine?",
            "goal": "Verify container management latency"
        }
    ]
    
    final_stats = []

    for sc in scenarios:
        print(f"\n>>> Running Scenario: {sc['name']}")
        session = mgr.create_session(sc['goal'])
        agent = LangGraphAgent(session)
        
        # We wrap the internal graph execution to capture node-level timing
        # Since we want to find bottlenecks, we'll time the specific node calls
        
        start_total = time.perf_counter()
        
        # 1. Ingestion Node
        start_node = time.perf_counter()
        # Mock initial state with required keys
        from src.agent.env import get_system_info
        env_info = await get_system_info()
        
        state = {
            "messages": [HumanMessage(content=sc['query'])], 
            "last_synced_count": 0,
            "goal": sc['query'],
            "env": env_info
        }
        
        ingestion_results = await agent.ingestion_node(state)
        # Update state with results from ingestion
        state.update(ingestion_results)
        
        ingestion_time = time.perf_counter() - start_node
        print(f"      [1/4] Ingestion: {ingestion_time*1000:.1f}ms")
        
        # 2. Planner Node (Main Bottleneck - LLM Reasoning)
        start_node = time.perf_counter()
        # We use a mocked planner response if we want to test 'plumbing' latency, 
        # but the user wants real implementation latency.
        planner_state = await agent.planner_node(state)
        planner_time = time.perf_counter() - start_node
        print(f"      [2/4] Planner (LLM): {planner_time:.2f}s")
        
        # Extract the tool call if any
        last_msg = planner_state["messages"][-1]
        tool_call_latency = 0
        analyzer_time = 0
        
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            # 3. Tool Execution Simulation (Simplified for benchmark)
            print(f"      [3/4] Tool Call Detected: {last_msg.tool_calls[0]['name']}")
            start_node = time.perf_counter()
            # We don't execute real destructive commands, but 'ls' or 'docker ps' are fine
            # We'll use the checkpointer logic to see how it routes
            tool_call_latency = time.perf_counter() - start_node # Usually fast
            
            # 4. Analyzer Node
            start_node = time.perf_counter()
            # Mock results for analyzer to see its overhead
            state["messages"].append(last_msg)
            state["messages"].append(ToolMessage(content="Simulated tool output", tool_call_id=last_msg.tool_calls[0]["id"]))
            await agent.analyzer_node(state)
            analyzer_time = time.perf_counter() - start_node
            print(f"      [4/4] Analyzer: {analyzer_time:.2f}s")
            
        total_time = time.perf_counter() - start_total
        print(f"      TOTAL E2E: {total_time:.2f}s")
        
        final_stats.append({
            "name": sc['name'],
            "total": total_time,
            "breakdown": {
                "ingestion": ingestion_time,
                "planner": planner_time,
                "analyzer": analyzer_time
            }
        })

    print("\n" + "="*60)
    print("               E2E BOTTLENECK ANALYSIS")
    print("="*60)
    for stat in final_stats:
        print(f"\nScenario: {stat['name']}")
        p_pct = (stat['breakdown']['planner'] / stat['total']) * 100
        a_pct = (stat['breakdown']['analyzer'] / stat['total']) * 100 if stat['total'] > 0 else 0
        print(f"  - Total Latency: {stat['total']:.2f}s")
        print(f"  - Planner Weight: {p_pct:.1f}% ({stat['breakdown']['planner']:.2f}s)")
        print(f"  - Analyzer Weight: {a_pct:.1f}% ({stat['breakdown']['analyzer']:.2f}s)")
        
        if p_pct > 80:
            print("  - [BOTTLENECK] Planner (LLM Generation) is dominant. Suggestion: Use smaller model or parallel tool calls.")
        elif a_pct > 30:
            print("  - [BOTTLENECK] Analyzer overhead is high. Suggestion: Streamline output truncation.")

    await reg.shutdown()

if __name__ == "__main__":
    asyncio.run(benchmark_e2e_scenarios())
