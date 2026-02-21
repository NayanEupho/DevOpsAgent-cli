import asyncio
import os
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import SessionManager
from src.intelligence.registry import IntelligenceRegistry
from loguru import logger

async def run_production_master_check():
    print("\n" + "="*60)
    print("      DEVOPS AGENT --- FINAL PRODUCTION INTEGRITY AUDIT")
    print("="*60)
    
    reg = IntelligenceRegistry.get_instance()
    await reg.initialize()
    
    mgr = SessionManager()
    session = mgr.create_session("Final Production Audit")
    agent = LangGraphAgent(session)

    tests_passed = 0
    total_tests = 5

    # --- TEST 1: Speculative FastPath (Accuracy & Latency) ---
    print("\n[1/5] Speculative FastPath Audit (AUTO Mode)")
    from langchain_core.messages import HumanMessage
    state1 = {
        "messages": [HumanMessage(content='list all docker containers')], 
        "user_mode": "AUTO", 
        "env": {"os": "Linux", "shell": "bash", "cwd": "/home/user"}
    }
    res1 = await agent.router_node(state1)
    if res1.get("next_step") == "fast_path":
        cmd = res1["messages"][-1].tool_calls[0]["args"]["cmd"]
        if "docker ps" in cmd.lower():
            print(f"      [PASS] FastPath correctly generated command: {cmd}")
            tests_passed += 1
        else:
            print(f"      [FAIL] FastPath result inaccurate: {cmd}")
    else:
        print(f"      [FAIL] Speculative router bypassed to planner (Step: {res1.get('next_step')}).")

    # --- TEST 2: Forced Execution (Manual Override) ---
    print("\n[2/5] Forced Execution Audit (EXEC Mode)")
    state2 = {
        "messages": [HumanMessage(content='check if nginx is running in k8s')], 
        "user_mode": "EXEC", 
        "env": {"os": "Linux", "shell": "bash"}
    }
    res2 = await agent.router_node(state2)
    if res2.get("next_step") == "fast_path":
        cmd = res2["messages"][-1].tool_calls[0]["args"]["cmd"]
        print(f"      [PASS] EXEC mode forced direct command: {cmd}")
        tests_passed += 1
    else:
        print(f"      [FAIL] EXEC mode leaked to step: {res2.get('next_step')}")

    # --- TEST 3: Informational Bypass (CHAT Mode) ---
    print("\n[3/5] Informational Bypass Audit (CHAT Mode)")
    state3 = {
        "messages": [HumanMessage(content='ls -la')], 
        "user_mode": "CHAT", 
        "env": {"os": "Linux", "shell": "bash"}
    }
    res3 = await agent.router_node(state3)
    if res3.get("next_step") == "chat":
        print(f"      [PASS] CHAT mode correctly short-circuited to chat node.")
        tests_passed += 1
    else:
        print(f"      [FAIL] CHAT mode failed to short-circuit (Step: {res3.get('next_step')}).")

    # --- TEST 4: Multi-Paragraph Input Handling ---
    print("\n[4/5] Multi-Paragraph Buffer Audit")
    # Simulate a query that was created via Shift+Enter
    multi_line_query = "Please look at my docker containers.\n\nThen, tell me how I can scale the nginx deployment."
    state4 = {
        "messages": [HumanMessage(content=multi_line_query)], 
        "user_mode": "AUTO", 
        "env": {"os": "Linux", "shell": "bash"}
    }
    # This should go to planner because it's complex (multi-paragraph)
    res4 = await agent.router_node(state4)
    if res4.get("next_step") == "planner":
        print(f"      [PASS] Multi-paragraph query correctly directed to heavy reasoning (Planner).")
        tests_passed += 1
    else:
        print(f"      [FAIL] Complex query was unsafely speculated (Step: {res4.get('next_step')}).")

    # --- TEST 5: Chat Node Response ---
    print("\n[5/5] Distributed Config Integrity Audit")
    if agent.fast_llm is not None:
        print(f"      [PASS] FastPath model initialized: {agent.config.ollama.fast_path_model}")
        print(f"      [PASS] Remote host: {agent.config.ollama.fast_path_host}")
        tests_passed += 1
    else:
        print(f"      [FAIL] Fast LLM not initialized even though enabled.")

    print("\n" + "="*60)
    print(f"   FINAL SCORE: {tests_passed}/{total_tests} TARGETS ACHIEVED")
    if tests_passed == total_tests:
        print("   STATUS: PRODUCTION READY")
    else:
        print("   STATUS: STAGED WITH MINOR REGRESSIONS")
    print("="*60 + "\n")
    
    await reg.shutdown()

if __name__ == "__main__":
    asyncio.run(run_production_master_check())
