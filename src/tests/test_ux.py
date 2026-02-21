import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import Session
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

async def test_streaming_ux():
    print("Testing Phase 12: Advanced CLI UX & Streaming...")
    
    # Setup mock session
    session_id = "test-streaming-123"
    session = Session(session_id, "Test UX", "2026-02-20T00:00:00")
    
    # Mock dependencies to avoid real Ollama calls
    with patch('src.agent.graph_core.ChatOllama'), \
         patch('src.agent.graph_core.ObservabilityService'), \
         patch('src.agent.graph_core.IntelligenceRegistry'), \
         patch('langgraph.graph.StateGraph.compile') as mock_compile:
        
        # Setup mock app with astream_events simulator
        mock_app = AsyncMock()
        mock_compile.return_value = mock_app
        
        async def mock_astream_events(*args, **kwargs):
            # Phase 1: Planning
            yield {"event": "on_node_start", "name": "planner", "metadata": {"langgraph_node": "planner"}, "data": {}}
            await asyncio.sleep(0.1)
            
            # Phase 2: Streaming tokens
            yield {"event": "on_chat_model_stream", "name": "ChatOllama", "data": {"chunk": AIMessage(content="I am thinking ")}}
            yield {"event": "on_chat_model_stream", "name": "ChatOllama", "data": {"chunk": AIMessage(content="about the status...")}}
            await asyncio.sleep(0.1)
            
            # Phase 3: Tool Start
            yield {"event": "on_node_start", "name": "executor", "metadata": {"langgraph_node": "executor"}, "data": {}}
            yield {"event": "on_tool_start", "name": "run_command", "data": {"input": {"command": "ls -la"}}}
            await asyncio.sleep(0.1)
            
            # Phase 4: End
            yield {"event": "on_chain_end", "name": "LangGraph", "data": {}}

        mock_app.astream_events = mock_astream_events
        mock_app.aget_state = AsyncMock(return_value=MagicMock(next=None)) # No interrupt for this test
        
        agent = LangGraphAgent(session)
        await agent.run("Show me the files")

    print("\n[OK] Streaming and HUD simulation finished.")

async def test_nl_safety_gate():
    print("\nTesting Intelligent Safety Gate (Natural Language)...")
    
    session = Session("test-nl-safety", "Test NL", "2026-02-20T00:00:00")
    
    with patch('src.agent.graph_core.ChatOllama'), \
         patch('src.agent.graph_core.IntelligenceRegistry'):
        
        agent = LangGraphAgent(session)
        
        # 1. Mock a safety interrupt snapshot
        mock_ai_msg = AIMessage(content="I will delete X", tool_calls=[{"name": "run_command", "args": {"command": "rm -rf /"}, "id": "1"}])
        mock_snapshot = MagicMock()
        mock_snapshot.values = {"messages": [mock_ai_msg]}
        mock_snapshot.next = ["executor"]
        
        # 2. Test Approval strings
        with patch('rich.console.Console.input', side_effect=["Yes, do it", "Try another way instead"]):
            # Fix: mock astream to return an empty async iterator
            async def empty_iterator(*args, **kwargs):
                if False: yield None
            
            agent.app.astream = empty_iterator
            agent.app.aupdate_state = AsyncMock()
            
            # Test approval
            print("Running approval test...")
            await agent._handle_safety_interrupt(mock_snapshot, {})
            
            # Test denial/feedback
            print("Running denial/feedback test...")
            await agent._handle_safety_interrupt(mock_snapshot, {})
            
            # Verify update_state was called for the second input
            agent.app.aupdate_state.assert_called_once()
            args, _ = agent.app.aupdate_state.call_args
            # args[1] is the state update dictionary
            assert "another way" in args[1]["denial_reason"]

    print("[OK] Intelligent Safety Gate logic verified.")

if __name__ == "__main__":
    asyncio.run(test_streaming_ux())
    asyncio.run(test_nl_safety_gate())
