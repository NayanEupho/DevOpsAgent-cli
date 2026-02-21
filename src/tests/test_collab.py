import asyncio
from pathlib import Path
from src.agent.graph_core import LangGraphAgent
from src.gcc.session import Session
from langchain_core.messages import HumanMessage

async def test_phase_10():
    print("Testing Phase 10: Seamless Collaboration...")
    
    from src.config import config
    # Setup mock session
    session_id = "test-collab-123"
    # Matches Session.path: config.agent.gcc_base_path / "sessions" / self.id
    path = Path(config.agent.gcc_base_path) / "sessions" / session_id
    path.mkdir(parents=True, exist_ok=True)
    
    # 1. Test last milestones
    with open(path / "commit.md", "w", encoding="utf-8") as f:
        f.write("## 2026-02-19 23:00\n")
        f.write("- Milestone A: Setup Docker\n")
        f.write("## 2026-02-19 23:10\n")
        f.write("- Milestone B: Configured K8s\n")
        f.write("- Milestone C: Deployed App\n")
        
    session = Session(session_id, "Test Phase 10", "2026-02-19T00:00:00")
    
    # We test the method directly without full init if possible, 
    # but LangGraphAgent calls it in __init__
    # To avoid Ollama connection errors, we can mock ChatOllama
    from unittest.mock import MagicMock, patch
    with patch('src.agent.graph_core.ChatOllama'), \
         patch('src.agent.graph_core.ObservabilityService'), \
         patch('src.agent.graph_core.IntelligenceRegistry'):
        
        agent = LangGraphAgent(session)
        print(f"Captured Milestones: {agent.context_recap}")
        assert "Milestone C" in agent.context_recap
    
    # 2. Test Ingestion Handover
    with open(path / "log.md", "w", encoding="utf-8") as f:
        f.write("## [23:00] AI\nI am starting task X.\n\n")
        f.write("## [23:05] HUMAN [MANUAL]\nls -la\ndocker ps\n\n")
        
    from src.gcc.ingestor import GCCIngestor
    history = GCCIngestor.parse_log(path / "log.md")
    print(f"Parsed History Items: {len(history)}")
    
    manual_entries = [m.content for m in history if isinstance(m, HumanMessage) and "[MANUAL]" in m.content]
    print(f"Manual Entries Detected: {len(manual_entries)}")
    assert len(manual_entries) > 0
    
    print("Phase 10 Logic Verified Successfully!")

if __name__ == "__main__":
    asyncio.run(test_phase_10())
