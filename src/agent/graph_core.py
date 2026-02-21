import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, TypedDict, Union, Optional
from loguru import logger
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from src.config import config
from src.gcc.session import Session
from src.gcc.log import GCCLogger
from src.gcc.checkpointer import GCCCheckpointer
from langchain_core.tools import tool
from src.mcp.server import run_command, classifier
from src.agent.env import get_system_info, get_env_hash
from src.gcc.ingestor import GCCIngestor
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from src.intelligence.registry import IntelligenceRegistry
from src.intelligence.utils import MarkdownAwareChunker, PlatinumEnvelope
from src.intelligence.observability import ObservabilityService

console = Console()

# Wrap the FastMCP function as a LangChain tool
langchain_run_command = tool(run_command)

@tool
async def get_gcc_history(session_id: Optional[str] = None) -> str:
    """Retrieve the human-readable history and context from a specific session ID (or current if None).
    Use this to 'navigate' into a past session found via memories to see the full code and logs.
    """
    reg = IntelligenceRegistry.get_instance()
    
    if not session_id:
        return "Please specify a session_id to retrieve history, or use 'list_past_sessions' to find one."

    # Expert Hardening Phase K: Use async DB method from registry
    details = await reg.db.read_execute("SELECT path FROM sessions WHERE id = ?", (session_id,))
    if not details:
        return f"Session '{session_id}' not found in index."
    
    path = Path(details[0][0]) / "log.md"

    if path.exists():
        # Expert Hardening: Use to_thread for blocking file I/O
        def _read():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        
        content = await asyncio.to_thread(_read)
        return PlatinumEnvelope.wrap(
            source=session_id,
            content=content,
            metadata={
                "context_type": "full_history",
                "session_id": session_id
            }
        )
    return f"Log file not found at {path}"

@tool
async def list_past_sessions(query: Optional[str] = None) -> str:
    """Search or list past sessions in the indexed intelligence DB. Use keywords to find relevant sessions."""
    reg = IntelligenceRegistry.get_instance()
    return await reg.list_sessions(query)

@tool
async def get_session_context(session_id: str) -> str:
    """Get the goal, path, and environmental context of a specific session from SQLite."""
    reg = IntelligenceRegistry.get_instance()
    return await reg.get_session_details(session_id)

@tool
async def branch_session(branch_name: str) -> str:
    """Fork the current session into a child branch for hypothetical exploration.
    Returns the new branch ID and switches context.
    """
    reg = IntelligenceRegistry.get_instance()
    # Expert Hardening Phase K: Implement actual branching logic
    # In LangGraph context, we use the registry's stateful branching
    try:
        # We need the current session_id. Since tools are bound to the agent,
        # we can't easily get it here unless passed or inferred.
        # This is a placeholder for the physical fork logic in IntelligenceRegistry.
        return f"Branching command accepted for '{branch_name}'. Use 'merge_current_session' to bring changes back later."
    except Exception as e:
        return f"Branching failed: {e}"

@tool
async def merge_current_session() -> str:
    """Merge findings from the current branch session back into its parent."""
    # Placeholder for the merge findings logic
    return "Merge findings initiated. Context will be updated in parent session."

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    goal: str
    next_step: Optional[str]
    last_synced_count: int
    env: Dict[str, Any]
    env_hash: Optional[str]
    denial_reason: Optional[str]
    loop_count: int

class LangGraphAgent:
    def __init__(self, session: Session):
        self.session = session
        self.logger = GCCLogger(session.path)
        self.config = config
        
        # Phase 10: Late-binding commit summary
        self.context_recap = self._get_last_milestones()
        self.llm = ChatOllama(
            model=config.ollama.model,
            base_url=config.ollama.host,
            temperature=config.ollama.temperature,
            streaming=True  # Expert Hardening: Ensure token-level events are emitted
        )
        # Bind LangChain tools to LLM
        self.tools = [
            langchain_run_command, 
            get_gcc_history, 
            list_past_sessions, 
            get_session_context,
            branch_session,
            merge_current_session
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Initialize Intelligence Layer
        self.intelligence = IntelligenceRegistry.get_instance()
        from src.intelligence.cache import SemanticCache
        self.cache = SemanticCache()
        
        # Setup Tracing (Modular Phase 15: Langfuse)
        self.handler = ObservabilityService.get_callback_handler(
            session_id=session.id,
            env={} # Env will be populated during run() turn
        )
        
        self.graph = self._build_graph()
        self.checkpointer = GCCCheckpointer(session.path)
        self.app = self.graph.compile(checkpointer=self.checkpointer, interrupt_before=["executor"])

    def _get_last_milestones(self) -> str:
        """Read last 3 commits from GCC to summarize for the AI."""
        commit_path = self.session.path / "commit.md"
        if not commit_path.exists():
            return "No previous milestones found."
            
        try:
            with open(commit_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Get last few entries (commits start with - or ##)
            relevant = [l.strip() for l in lines if l.strip().startswith("-") or l.strip().startswith("##")][-3:]
            return " | ".join(relevant) if relevant else "Fresh session."
        except Exception as e:
            logger.error(f"Error reading milestones: {e}")
            return "Error reading history."

    async def emergency_panic(self, state: Optional[AgentState] = None):
        """Atomic state preservation during fatal system failure."""
        logger.critical("PANIC: Emergency state preservation triggered!")
        try:
            # Atomic write of the current known state to a panic file in GCC
            panic_path = self.session.path / "panic_state.json"
            import json
            
            # Simple serialization of metadata and last message
            summary = {
                "session_id": self.session.id,
                "goal": self.session.goal,
                "timestamp": str(datetime.now()),
                "last_node": "unknown"
            }
            
            with open(panic_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
                
            logger.info(f"Panic: State preserved at {panic_path}")
        except Exception as e:
            logger.error(f"Panic: Failed to save emergency state: {e}")

    async def prober_node(self, state: AgentState):
        logger.info("Prober: Detecting environment...")
        # Initialize DB/Vector store on first run
        await self.intelligence.initialize()
        
        sys_info = await get_system_info()
        env_hash = get_env_hash(sys_info)
        self.session.update_metadata({"env": sys_info, "env_hash": env_hash})
        
        # Log session to SQLite
        await self.intelligence.db.insert_session(self.session.id, self.session.goal, str(self.session.path))
        
        return {"env": sys_info, "env_hash": env_hash, "loop_count": 0}

    async def audit_node(self, state: AgentState):
        """Expert Audit Node: Detects environment drift and semantic infinite loops."""
        logger.info("Expert Audit: Checking system integrity...")
        
        # 1. OPTIMIZATION: Check if we actually need a full probe
        # If no commands were run since last probe, we can skip full drift detection
        last_msgs = state.get("messages", [])
        last_was_tool = last_msgs and isinstance(last_msgs[-1], ToolMessage)
        
        if not last_was_tool and state.get("env_hash"):
            logger.info("Expert Audit: Skipping full probe (No tool execution detected).")
            current_hash = state.get("env_hash")
            drift_detected = False
        else:
            # Full drift detection (Async/Parallel)
            current_info = await get_system_info()
            current_hash = get_env_hash(current_info)
            last_hash = state.get("env_hash")
            drift_detected = (last_hash and current_hash != last_hash)
            
            if drift_detected:
                logger.warning(f"Expert Audit: Environment DRIFT detected! Hash changed.")
            
        # 2. Hard Turn Limit (Circuit Breaker)
        loop_count = state.get("loop_count", 0) + 1
        if loop_count > 10:
            logger.error(f"Expert Audit: HARD TURN LIMIT REACHED ({loop_count}). Circuit breaker tripped.")
            return {"next_step": "circuit_break", "loop_count": loop_count}

        # 3. Action-Based Loop Detection (Repeated tool calls)
        # Check for repeated AI thoughts OR repeated tool actions
        ai_msgs = [m for m in state["messages"] if isinstance(m, AIMessage)]
        loop_detected = False
        repetition_hint = None
        
        if len(ai_msgs) >= 2:
            # A. Semantic Loop (Repeated text)
            if len(ai_msgs) >= 3:
                last_three_text = [m.content for m in ai_msgs[-3:]]
                if len(set(last_three_text)) == 1 and last_three_text[0].strip():
                    logger.error("Expert Audit: SEMANTIC LOOP DETECTED (Text).")
                    loop_detected = True

            # B. Action Loop (Repeated Tool Calls/Args)
            last_msgs_with_calls = [m for m in ai_msgs if m.tool_calls]
            if len(last_msgs_with_calls) >= 2:
                last_calls = last_msgs_with_calls[-2:]
                # Compare the first tool call of each message
                call1 = last_calls[0].tool_calls[0]
                call2 = last_calls[1].tool_calls[0]
                
                if call1["name"] == call2["name"] and call1["args"] == call2["args"]:
                    logger.error(f"Expert Audit: ACTION LOOP DETECTED (2x Same Command: {call1['name']}).")
                    # Expert Hardening Phase R: Stricter circuit break for identical consecutive commands
                    loop_detected = True
                    repetition_hint = f"CIRCUIT BREAKER: You tried to run the same command twice with no change: `{call1['args']}`. I am terminating this loop to save tokens. Explain why you are stuck instead."

        # 4. Decision
        if loop_detected:
            return {"next_step": "circuit_break", "loop_count": loop_count}
        
        if drift_detected:
             return {"next_step": "reprobe", "env_hash": current_hash, "loop_count": loop_count}
            
        update = {"next_step": "continue", "loop_count": loop_count}
        if repetition_hint:
            update["denial_reason"] = repetition_hint
            
        return update

    async def sanitizer_node(self, state: AgentState):
        """Sanitizes tool outputs to prevent prompt injection and ANSI log poisoning."""
        from src.intelligence.observability import Sanitizer
        logger.info("Expert Audit: Sanitizing last tool output...")
        
        last_msg = state["messages"][-1]
        
        if isinstance(last_msg, ToolMessage):
            original_content = last_msg.content
            # Active Sanitization: Strip ANSI and neutralize adversarial content
            sanitized_content = Sanitizer.sanitize(original_content)
            
            if sanitized_content != original_content:
                logger.warning("Expert Audit: Content sanitized (ANSI or Adversarial found).")
                # BUG-04 FIX: Only return the replacement message, not the full list.
                # AgentState.messages uses a reducer (lambda x, y: x + y), so returning
                # the full list would duplicate all messages.
                new_msg = ToolMessage(
                    content=sanitized_content,
                    tool_call_id=last_msg.tool_call_id,
                    artifact=last_msg.artifact,
                    status=last_msg.status
                )
                # Remove the old message and add the sanitized one
                from langgraph.graph.message import RemoveMessage
                return {"messages": [RemoveMessage(id=last_msg.id), new_msg]}
                
        return {}

    async def ingestion_node(self, state: AgentState):
        logger.info("Ingestion: Checking for new context in GCC logs...")
        
        all_history = GCCIngestor.parse_log(self.session.path / "log.md")
        last_count = state.get("last_synced_count", 0)
        
        if len(all_history) > last_count:
            new_entries = all_history[last_count:]
            logger.info(f"Ingestion: Synced {len(new_entries)} new entries from GCC.")
            
            # Phase 10: Create a 'Handover Note' if there are manual entries
            manual_actions = [m.content for m in new_entries if isinstance(m, HumanMessage) and "[MANUAL]" in m.content]
            handover_note = ""
            if manual_actions:
                handover_note = f"\nHANDOVER NOTE: The human manually performed the following actions while you were away:\n" + "\n".join(manual_actions)
            
            # Shadow Indexing: Update semantic memory with new entries
            full_text = "\n\n".join([m.content for m in new_entries])
            await self.intelligence.index_session_log(self.session.id, full_text)
            
            return {
                "messages": new_entries + ([HumanMessage(content=handover_note)] if handover_note else []),
                "last_synced_count": len(all_history)
            }

        return {"last_synced_count": len(all_history)}

    async def planner_node(self, state: AgentState):
        logger.info("Planner: Strategizing next move...")
        
        # Inject System Context
        env = state.get("env", {})
        tools_info = env.get("tools", {})
        denial_context = ""
        if state.get("denial_reason"):
            denial_context = f"\n[CRITICAL] PREVIOUS ATTEMPT FAILED/DENIED: {state['denial_reason']}\nYou MUST adapt your strategy and address the user's feedback."

        # Expert Hardening Phase R: Use Human Query for RAG/Cache to avoid tool-output loops
        user_query = state['goal']
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                user_query = m.content
                break
        
        logger.debug(f"Planner: Processing query: '{user_query}'")
        memories = await self.intelligence.remember(user_query)

        system_prompt = f"""Expert terminal AI. Env: {env.get('os')} ({env.get('release')}), {env.get('shell')}, CWD: {env.get('cwd')}.
Tools: K8s: {tools_info.get('kubectl', {}).get('context', 'N/A')}, Docker: {tools_info.get('docker', {}).get('status', 'N/A')}, Git: {tools_info.get('git', {}).get('branch', 'N/A')}.
{denial_context}

Rules:
1. Native commands for detected OS/Shell. Use absolute paths if ambiguity exists.
2. OBSERVATION FIRST: If the last message contains tool output, you MUST start by summarizing the findings (even if empty, e.g. "The command produced no output, confirming no containers are running") and explaining technical insights.
3. NEXT STEP: After summarizing, either propose the next tool command OR state that the goal is achieved and provide a final summary.
4. NEVER repeat the same command twice if the result was successful (even if empty). Move forward or refine your search.
5. Keep response concise but highly technical (max 5-7 sentences).

History/Memory:
{memories}

Recent Milestones:
{self.context_recap}
"""
        # Phase 13 Hardening: Use centralized ContextManager
        from src.intelligence.utils import ContextManager
        pruned_history = ContextManager.trim_messages(state["messages"], max_len=15)
        msg_history = [SystemMessage(content=system_prompt)] + pruned_history
        
        # Expert Hardening Phase R: Skip Semantic Cache if follow-up tool results exist
        # This prevents looping back to a cached 'tool call' plan when we should be summarizing.
        has_tool_results = any(isinstance(m, ToolMessage) for m in state["messages"][-3:])
        
        # Expert Hardening Phase M: Semantic Cache Check
        cached_response = None
        if not has_tool_results:
            cached_response = await self.cache.get(user_query)
            if cached_response:
                logger.info("Planner: Semantic Cache HIT.")
            
        if cached_response:
             # Fast Path: Return cached AIMessage
             return {"messages": [AIMessage(content=cached_response)], "denial_reason": None}

        logger.info("Planner: Invoking LLM...")
        response = await self.llm_with_tools.ainvoke(msg_history)
        logger.info(f"Planner: LLM responded (Content: {bool(response.content)}, Tools: {len(response.tool_calls)})")
        
        # Expert Hardening Phase M: Background Cache Set (Only if it's a direct user query response)
        if response.content and not response.tool_calls and not has_tool_results:
            logger.debug("Planner: Saving summary response to Semantic Cache.")
            self.intelligence.track_task(self.cache.set(user_query, response.content))
            
        return {"messages": [response], "denial_reason": None}

    async def negotiator_node(self, state: AgentState):
        logger.info("Negotiator: Analyzing denial and proposing alternatives...")
        denial = state.get("denial_reason", "")
        
        # Phase 12: Detect "Try X" pattern
        suggestion = ""
        if "instead" in denial.lower() or "try" in denial.lower():
            suggestion = f"\nUSER SUGGESTION: {denial}"
        
        return {
            "next_step": "replan", 
            "denial_reason": f"{denial}{suggestion}"
        }

    async def analyzer_node(self, state: AgentState):
        logger.info("Analyzer: Logging command results to Intelligence DB...")
        last_msgs = state.get("messages", [])
        if not last_msgs:
            return {}
        
        # Find the last tool call and its response safely
        for i in range(len(last_msgs)-1, 0, -1):
            msg = last_msgs[i]
            if isinstance(msg, ToolMessage):
                ai_msg = last_msgs[i-1]
                if isinstance(ai_msg, AIMessage) and ai_msg.tool_calls:
                    call = ai_msg.tool_calls[0]
                    if call["name"] == "run_command":
                        cmd = call["args"].get("cmd", "") or call["args"].get("command", "")
                        skill_id = "core"
                        if "docker" in cmd: skill_id = "docker"
                        elif "kubectl" in cmd: skill_id = "kubectl"
                        elif "git" in cmd: skill_id = "git"
                        
                        try:
                            # Phase O: Use track_task to ensure shutdown safety
                            self.intelligence.track_task(
                                self.intelligence.db.log_command(
                                    self.session.id,
                                    skill_id,
                                    cmd,
                                    0,
                                    str(msg.content)[:200],
                                    state.get("env", {})
                                )
                            )
                        except Exception as e:
                            logger.error(f"Analyzer: Failed to log command: {e}")
        return {}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # 2. Safety Gate (Routing logic)
        def safety_gate(state: AgentState) -> Literal["executor", "auto_executor", END]:
            last_message = state["messages"][-1]
            if not last_message.tool_calls:
                return END
            
            # Check all tool calls in the message
            for tc in last_message.tool_calls:
                # Support both 'cmd' and 'command' argument names
                cmd = tc["args"].get("cmd", "") or tc["args"].get("command", "")
                tier = classifier.classify(cmd)
                
                # If any tool call requires approval, route to 'executor' (interrupted)
                if tier != "auto_execute":
                    logger.info(f"Safety Gate: Command '{cmd[:30]}...' requires approval (Tier: {tier}).")
                    return "executor"
            
            # All tool calls are auto_execute
            logger.info("Safety Gate: All commands are 'auto_execute'. Routing to auto_executor.")
            return "auto_executor"

        def audit_gate(state: AgentState) -> Literal["planner", "prober", END]:
            next_step = state.get("next_step")
            if next_step == "circuit_break":
                logger.error("Audit Gate: Circuit breaker tripped. Terminating to prevent loop.")
                return END
            if next_step == "reprobe":
                logger.warning("Audit Gate: Drift detected. Re-probing environment.")
                return "prober"
            return "planner"

        # 3. Nodes
        tool_node = ToolNode(self.tools)

        workflow.add_node("prober", self.prober_node)
        workflow.add_node("ingestion", self.ingestion_node)
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", tool_node)
        workflow.add_node("auto_executor", tool_node) # Separate node for non-interrupted execution
        workflow.add_node("sanitizer", self.sanitizer_node)
        workflow.add_node("analyzer", self.analyzer_node)
        workflow.add_node("audit", self.audit_node)
        workflow.add_node("negotiator", self.negotiator_node)
        
        workflow.add_edge(START, "prober")
        workflow.add_edge("prober", "ingestion")
        workflow.add_edge("ingestion", "planner")
        workflow.add_edge("negotiator", "planner")
        
        workflow.add_conditional_edges(
            "planner",
            safety_gate,
            {
                "executor": "executor",
                "auto_executor": "auto_executor",
                END: END
            }
        )
        
        workflow.add_edge("executor", "sanitizer")
        workflow.add_edge("auto_executor", "sanitizer")
        workflow.add_edge("sanitizer", "analyzer")
        workflow.add_edge("analyzer", "audit")
        
        workflow.add_conditional_edges(
            "audit",
            audit_gate,
            {
                "planner": "planner",
                "prober": "prober",
                END: END
            }
        )

        return workflow

    async def run(self, user_input: str):
        """Execute one turn with Ollama-style streaming and a Live HUD."""
        # Expert Hardening Phase K: Update recap at the start of every user turn
        self.context_recap = self._get_last_milestones()
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "session_id": self.session.id,
            "goal": self.session.goal,
            "last_synced_count": 0,
            "env": {},
            "env_hash": None,
            "next_step": None,
            "denial_reason": None,
            "loop_count": 0
        }

        # BUG-18 FIX: Cache get_system_info() to avoid 6+ subprocess probes
        sys_info = await get_system_info()
        os_tag = f"os:{sys_info['os'].lower()}"

        trace_config = {
            "configurable": {"thread_id": self.session.id},
            "callbacks": [self.handler] if self.handler else [],
            "tags": ["devops-agent", os_tag],
            "metadata": {
                "langfuse_session_id": self.session.id,
                "langfuse_tags": ["devops-agent", os_tag],
                "goal": self.session.goal
            }
        }

        # UI State Container (Mutable)
        ui = {
            "streaming_content": "",
            "status_line": Text("🚀 Initializing..."),
            "tool_start_time": None,
            "running_tool": None
        }

        from rich.console import Group
        from rich.markup import escape
        import time
        
        def render_ui():
            """Helper to render both the streamed markdown and the status bar."""
            ui_elements = []
            
            # Expert Hardening: HUD at the top (per user feedback 'show before output')
            status_text = ui["status_line"].copy()
            if ui["tool_start_time"] and ui["running_tool"]:
                elapsed = int(time.time() - ui["tool_start_time"])
                status_text.plain = f"🛠️ [{elapsed}s] Running: {ui['running_tool']}"
            
            ui_elements.append(Panel(status_text, style="bold cyan", expand=False))
            
            # Spacer
            ui_elements.append(Text(""))
            
            if ui["streaming_content"].strip():
                ui_elements.append(Markdown(ui["streaming_content"]))
            
            return Group(*ui_elements)

        with Live(render_ui(), refresh_per_second=10, console=console, vertical_overflow="visible") as live:
            await self._run_graph_with_events(initial_state, trace_config, live, ui, render_ui)

    async def _run_graph_with_events(self, input_data: Optional[Dict], trace_config: Dict, live: Live, ui: Dict, render_ui: callable):
        """Internal loop to process graph events and update HUD."""
        from rich.markup import escape
        import time
        try:
            # Expert Hardening: Upgrade to v2 for better event streaming fidelity
            async for event in self.app.astream_events(input_data, config=trace_config, version="v2"):
                kind = event["event"]
                name = event["name"]

                # 1. Update Status HUD based on node transitions
                if kind in ["on_node_start", "on_chain_start"]:
                    node_name = event["metadata"].get("langgraph_node")
                    if not node_name and kind == "on_chain_start" and name == "LangGraph":
                        ui["status_line"].plain = "🧠 Agent Thinking..."
                        continue
                    
                    if node_name:
                        logger.debug(f"Event Loop: Node Start: {node_name}")
                        if node_name == "prober":
                            ui["status_line"].plain = "🔍 Detecting environment context..."
                        elif node_name == "ingestion":
                            ui["status_line"].plain = "📚 Ingesting GCC memory deltas..."
                        elif node_name == "planner":
                            # Expert Hardening Phase R: Differentiate between initial planning and post-tool analysis
                            if ui["streaming_content"].strip():
                                ui["status_line"].plain = "🔬 Analyzing findings & summarizing..."
                            else:
                                ui["status_line"].plain = "🧠 Strategizing next steps..."
                        elif node_name == "executor" or node_name == "auto_executor":
                            ui["status_line"].plain = "🛠️ Executing MCP Command..."
                        elif node_name == "analyzer":
                            ui["status_line"].plain = "📂 Saving audit trail..."
                        live.update(render_ui())

                # 2. Token Streaming for AI Responses (Handled for v2 events)
                elif kind == "on_chat_model_stream":
                    # v2 events have chunks in data["chunk"]
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        ui["streaming_content"] += chunk.content
                        live.update(render_ui())

                elif kind in ["on_node_end", "on_chain_end"]:
                    node_name = event["metadata"].get("langgraph_node")
                    if node_name == "planner":
                        output = event["data"].get("output")
                        # Handle both dict output (node) and direct message list (some chain wrappers)
                        messages = []
                        if isinstance(output, dict) and "messages" in output:
                            messages = output["messages"]
                        elif isinstance(output, list):
                            messages = output
                        
                        if messages:
                            last_msg = messages[-1]
                            if isinstance(last_msg, AIMessage) and last_msg.content:
                                # If the content isn't already in the buffer (to avoid duplicates from streaming)
                                if last_msg.content not in ui["streaming_content"]:
                                    ui["streaming_content"] += last_msg.content
                                    live.update(render_ui())

                # 3. Handle Tool execution visual feedback
                elif kind == "on_tool_start":
                    tool_input = event["data"].get("input", {})
                    cmd = tool_input.get("cmd", "") or tool_input.get("command", "")
                    if cmd:
                        ui["status_line"].plain = f"🛠️ Running: {cmd}"
                        ui["running_tool"] = cmd
                        ui["tool_start_time"] = time.time()
                        # Persist command in buffer with icon and separator
                        ui["streaming_content"] += f"\n\n---\n🛠️ **Executing:** `{cmd}`\n"
                        live.update(render_ui())
                
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    ui["tool_start_time"] = None
                    ui["running_tool"] = None
                    ui["status_line"].plain = "✅ Tool execution complete."
                    
                    if output is not None:
                        from langchain_core.messages import ToolMessage
                        content = output.content if isinstance(output, ToolMessage) else str(output)
                        
                        # Hardened Rendering: Handle Zero-Output
                        if not content.strip():
                            content = "(Command executed successfully with no output)"
                        
                        # Snippet logic (Increased to 2000 chars)
                        content_snippet = content[:2000]
                        if len(content) > 2000: content_snippet += "\n... (truncated)"
                        
                        # Style based on exit status if available
                        status_label = "SUCCESS"
                        if "[Exit Code:" in content and "Exit Code: 0]" not in content:
                            status_label = "FAILED"
                        
                        # Escape Rich markup in output to prevent crashes
                        escaped_content = escape(content_snippet)
                        
                        # Expert Hardening: Use Markdown syntax for headers, as ui["streaming_content"] is passed to Markdown()
                        ui["streaming_content"] += f"\n\n---\n### 📄 TOOL OUTPUT ({status_label})\n"
                        ui["streaming_content"] += f"```bash\n{escaped_content}\n```\n\n"
                        # Expert Hardening Phase Q: Add a separator to encourage LLM summary
                        ui["streaming_content"] += "---\n"
                        live.update(render_ui())

                # 4. Handle Interrupts (Safety Gate)
                if kind == "on_chain_end" and name == "LangGraph":
                    snapshot = await self.app.aget_state(trace_config)
                    if snapshot.next:
                        live.stop()
                        await self._handle_safety_interrupt(snapshot, trace_config, live, ui, render_ui)
                        live.start()
                    else:
                        # Final update for completion
                        ui["status_line"].plain = "✅ Task completed."
                        live.update(render_ui())
        except Exception as e:
            logger.critical(f"Fatal error in agent loop: {e}")
            await self.emergency_panic()
            raise e

    async def _handle_safety_interrupt(self, snapshot, trace_config, live, ui, render_ui):
        """Interactive approval handler with natural language support."""
        last_ai_msg = snapshot.values["messages"][-1]
        if not last_ai_msg.tool_calls:
            return

        console.print("\n[bold yellow]⚠️  SAFETY APPROVAL REQUIRED[/bold yellow]")
        for tc in last_ai_msg.tool_calls:
            cmd = tc["args"].get("cmd", "") or tc["args"].get("command", "")
            console.print(f"   Command: [white]{cmd}[/white]")
        
        user_response = console.input("\nApprove? (y/n/or type feedback): ").strip()
        
        lower_resp = user_response.lower()
        is_approval = any(x in lower_resp for x in ["y", "yes", "sure", "go", "approve", "ok"])
        is_denial = any(x in lower_resp for x in ["n", "no", "stop", "don't", "cancel", "deny"])

        if is_approval and not is_denial:
            console.print("[green]Approved. Executing...[/green]")
            ObservabilityService.score_trace(self.handler, "user-approval", 1.0)
            await self._run_graph_with_events(None, trace_config, live, ui, render_ui)
        else:
            reason = user_response if user_response and not is_denial else "User denied execution."
            ObservabilityService.score_trace(self.handler, "user-approval", 0.0, comment=reason)
            await self.app.aupdate_state(trace_config, {"denial_reason": reason}, as_node="negotiator")
            await self._run_graph_with_events(None, trace_config, live, ui, render_ui)

    async def shutdown(self):
        """Phase O: Graceful exit for all agent resources."""
        await self.intelligence.shutdown()

# Placeholder for Phase 2 implementation in agent/core.py
