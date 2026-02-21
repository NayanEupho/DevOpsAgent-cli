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
from src.agent.render import RenderController, RenderState
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
    Returns the new branch ID and switches context internally.
    """
    reg = IntelligenceRegistry.get_instance()
    # Note: In actual implementation, we'd need the agent instance to swap its session.
    # For now, we trigger the physical fork. The agent's next turn will detect the new branch if needed,
    # or the LLM can explicitly use the returned ID.
    try:
        # We'll use a globally tracked 'active_session_id' or similar for this tool's context
        # but for simplicity, the registry will fork the one it last knew about.
        rows = await reg.db.execute("SELECT id FROM sessions ORDER BY created_at DESC LIMIT 1")
        if not rows: return "No active session to branch."
        current_id = rows[0][0]
        
        branch_id = await reg.branch_session(current_id, branch_name)
        return f"SUCCESS: Branched '{current_id}' -> '{branch_id}'. Findings will be isolated until merged."
    except Exception as e:
        return f"Branching failed: {e}"

@tool
async def merge_current_session() -> str:
    """Merge findings from the current branch session back into its parent.
    Use this when a sub-task or experiment is complete.
    """
    reg = IntelligenceRegistry.get_instance()
    try:
        rows = await reg.db.execute("SELECT id FROM sessions ORDER BY created_at DESC LIMIT 1")
        if not rows: return "No active session found."
        current_id = rows[0][0]
        
        await reg.merge_session(current_id)
        return f"SUCCESS: Findings from '{current_id}' merged into parent. You can now switch back to the main goal."
    except Exception as e:
        return f"Merge failed: {e}"

@tool
async def switch_session(session_id: str) -> str:
    """Explicitly switch the current context to another session or branch.
    Use this to 'go back' to a parent or jump to a related exploration.
    """
    reg = IntelligenceRegistry.get_instance()
    try:
        details = await reg.get_session_details(session_id)
        if "Session not found" in details:
            return f"ERROR: Session '{session_id}' not found."
        
        # In this implementation, the switch happens at the start of the next turn
        # via _detect_and_handle_pivot, but we log the intent here.
        return f"SUCCESS: Intent to switch to '{session_id}' recorded. The agent will re-initialize in this context on the next turn."
    except Exception as e:
        return f"Switch failed: {e}"

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
    user_mode: str # AUTO, EXEC, CHAT

class LangGraphAgent:
    def __init__(self, session: Session, debug_mode: bool = False):
        self.session = session
        self.debug_mode = debug_mode
        self.handler = None
        self.logger = GCCLogger(session.path)
        self.config = config
        self.cached_sys_info = None  # Turn-level cache for environment detection
        
        # Phase 10: Late-binding commit summary
        self.context_recap = self._get_last_milestones()
        self.llm = ChatOllama(
            model=config.ollama.model,
            base_url=config.ollama.host,
            temperature=config.ollama.temperature,
            streaming=True  # Expert Hardening: Ensure token-level events are emitted
        )
        # Phase 25: Fast LLM for reflexive checks (Pivot Detection)
        self.fast_llm = None
        if config.ollama.fast_path_enabled:
            logger.info(f"FastPath: Initializing reflex model {config.ollama.fast_path_model} on {config.ollama.fast_path_host}")
            self.fast_llm = ChatOllama(
                model=config.ollama.fast_path_model,
                base_url=config.ollama.fast_path_host,
                temperature=0.0
            )
        else:
            logger.info("FastPath: Disabled per configuration.")
        # Bind LangChain tools to LLM
        self.tools = [
            langchain_run_command, 
            get_gcc_history, 
            list_past_sessions, 
            get_session_context,
            branch_session,
            merge_current_session,
            switch_session
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Initialize Intelligence Layer
        self.intelligence = IntelligenceRegistry.get_instance()
        from src.intelligence.cache import SemanticCache
        self.cache = SemanticCache()

        # Load Static Skills Documentation once at startup
        self.skills_documentation = self._load_all_skills()
        
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

    def _load_all_skills(self) -> str:
        """Discover and load all SKILL.md files into a single documentation block."""
        skills_path = Path(config.agent.skills_path)
        if not skills_path.exists():
            logger.warning(f"Skills path {skills_path} not found.")
            return "No skills documentation found."

        all_docs = []
        try:
            for sdir in skills_path.iterdir():
                if sdir.is_dir():
                    skill_file = sdir / "SKILL.md"
                    if skill_file.exists():
                        with open(skill_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            all_docs.append(f"### SKILL: {sdir.name.upper()}\n{content}")
            
            summary = f"Total loaded skills: {len(all_docs)}"
            logger.info(f"Agent: {summary}")
            return "\n\n".join(all_docs) if all_docs else "No skills documentation found."
        except Exception as e:
            logger.error(f"Error loading skills: {e}")
            return f"Error loading skills: {e}"

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
        
        # Expert Optimization: Use turn-level cache to save 300ms
        if self.cached_sys_info:
            sys_info = self.cached_sys_info
        else:
            sys_info = await get_system_info()
            self.cached_sys_info = sys_info
            
        env_hash = get_env_hash(sys_info)
        self.session.update_metadata({"env": sys_info, "env_hash": env_hash})
        
        # Log session to SQLite
        await self.intelligence.db.insert_session(self.session.id, self.session.goal, str(self.session.path))
        
        return {"env": sys_info, "env_hash": env_hash}

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
            # Use turn-level cache IF it was already populated this turn, else probe
            current_info = self.cached_sys_info or await get_system_info()
            self.cached_sys_info = current_info
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
        
        last_count = state.get("last_synced_count", 0)
        all_messages = GCCIngestor.parse_log(self.session.path / "log.md")
        message_count_on_disk = len(all_messages)
        
        if message_count_on_disk > last_count:
            new_entries = all_messages[last_count:]
            logger.info(f"Ingestion: Synced {len(new_entries)} new entries from GCC.")
            
            # Phase 10: Create a 'Handover Note' if there are manual entries
            manual_actions = [m.content for m in new_entries if isinstance(m, HumanMessage) and "[MANUAL]" in m.content]
            handover_note = ""
            if manual_actions:
                handover_note = f"\nHANDOVER NOTE: The human manually performed the following actions while you were away:\n" + "\n".join(manual_actions)
            
            # Shadow Indexing: Update semantic memory with new entries
            full_text = "\n\n".join([m.content for m in new_entries])
            await self.intelligence.index_session_log(self.session.id, full_text)

            # REORDERING LOGIC: 
            # We must ensure [HISTORY] comes BEFORE [CURRENT QUERY].
            # To fix this, we pop the current query, add history, then re-add the query.
            history = state.get("messages", [])
            current_query_msg = None
            if history and isinstance(history[-1], HumanMessage):
                # The last message is usually the new query we just added in run()
                current_query_msg = history[-1]
            
            from langgraph.graph.message import RemoveMessage
            updates = []
            
            # PIVOT DETECTION: If the new query is drastically different, 
            # we can prune the history to avoid confusion and improve TTFT.
            is_pivot = False
            last_goal = state.get("goal", "")
            if current_query_msg:
                # Simple logic: if query is short and unrelated to last actions
                q = str(current_query_msg.content).lower()
                # If it looks like a meta-question or a context switch
                if any(k in q for k in ["who are you", "what time", "what files", "stop", "reset"]):
                    is_pivot = True
                    logger.info("Ingestion: Pivot detected. Pruning context for faster response.")

            if is_pivot:
                # Clear all previous messages for this turn
                for m in history:
                    updates.append(RemoveMessage(id=m.id))
            elif current_query_msg:
                updates.append(RemoveMessage(id=current_query_msg.id))
            
            updates.extend(new_entries)
            if handover_note:
                updates.append(HumanMessage(content=handover_note))
            
            if current_query_msg:
                updates.append(current_query_msg)
            
            return {
                "messages": updates,
                "last_synced_count": message_count_on_disk
            }

        return {"last_synced_count": message_count_on_disk}

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
        # Static Skills are now loaded in __init__

        system_prompt = f"""Expert terminal AI. Env: {env.get('os')} ({env.get('release')}), {env.get('shell')}, CWD: {env.get('cwd')}.
Tools: K8s: {tools_info.get('kubectl', {}).get('context', 'N/A')}, Docker: {tools_info.get('docker', {}).get('status', 'N/A')}, Git: {tools_info.get('git', {}).get('branch', 'N/A')}.
{denial_context}

Rules:
1. Native commands for detected OS/Shell. Use absolute paths if ambiguity exists.
2. OBSERVATION FIRST: If the last message contains tool output, you MUST start by summarizing the findings (even if empty, e.g. "The command produced no output, confirming no containers are running") and explaining technical insights.
3. NEXT STEP: After summarizing, either propose the next tool command OR state that the goal is achieved and provide a final summary.
4. NEVER repeat the same command twice if the result was successful (even if empty). Move forward or refine your search.
5. Keep response concise but highly technical (max 5-7 sentences).

History/Rules:
{self.skills_documentation}

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
        
        if response.content and not response.tool_calls:
            # This is a final response or a direct answer without tool calls
            # Log it as a thought/closing statement
            self.logger.log_ai_action(
                thought=response.content,
                action="Final Response",
                inference="Goal reached or question answered."
            )
            
            # If it's a successful conclusion, log to commit.md too
            if not has_tool_results:
                self.logger.log_commit(
                    summary=f"Final response to: {user_query[:50]}...",
                    finding=response.content[:200]
                )

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
                            
                            # GCC LOGGING: Record the action and result in log.md
                            self.logger.log_ai_action(
                                thought=ai_msg.content,
                                action=cmd,
                                output=str(msg.content)
                            )
                            
                            # Expert Hardening Phase S: Success Detection & Recovery Reflex
                            output = str(msg.content).lower()
                            # STABILITY FIX: Ensure we are only looking at Tool outputs, not previous AI reflections
                            # AND check if the output is not just a summary of an error
                            fail_patterns = ["permission denied", "not found", "error:", "access denied", "no such file", "failed to"]
                            
                            # Refined: Only trigger if the output IS the failure, not if we're describing it
                            is_failure = any(fail in output for fail in fail_patterns)
                            is_system_thought = "[system reflection]" in output
                            
                            if is_failure and not is_system_thought:
                                logger.warning("Analyzer: Tool failure detected. Injecting recovery hint.")
                                # Update UI state if we are in an active run loop
                                # Note: This only works if analyzer_node has access to ui, 
                                # but usually it's passed via state or closure.
                                # Since this is a method, we can't easily reach 'ui' from 'run()'.
                                # We will rely on on_node_end to sync errors.
                                return {
                                    "messages": [HumanMessage(content=f"[SYSTEM REFLECTION] The previous command produced an error: '{output[:100]}...'. Do NOT repeat the same command. Try a different strategy.")],
                                    "next_step": "reprobe",
                                    "last_error": f"Tool Error: {output[:80]}..."
                                }
                        except Exception as e:
                            logger.error(f"Analyzer: Failed to log command: {e}")
        return {}

    async def router_node(self, state: AgentState):
        """Speculative Fast-Path: Bypasses the heavy planner for simple, one-shot DevOps commands."""
        user_mode = state.get("user_mode", "AUTO")
        
        # 1. Manual Force-Chat
        if user_mode == "CHAT":
            logger.info("Router: Manual CHAT mode detected.")
            return {"next_step": "chat"}

        # 2. Check if disabled
        if not self.config.ollama.fast_path_enabled or self.fast_llm is None:
            return {"next_step": "planner"}

        logger.info(f"Router: Evaluating speculative fast-path (Mode: {user_mode})...")
        
        user_query = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                user_query = str(m.content)
                break
        
        if not user_query or len(user_query) > 100 or "\n" in user_query.strip(): # Only speculate on short, single-line queries
            return {"next_step": "planner"}

        # Combined classification and generation prompt for 1-turn response
        import traceback
        system_os = state.get('env', {}).get('os', 'Linux')
        shell = state.get('env', {}).get('shell', 'bash')
        
        # Adjust prompt based on EXEC mode
        if user_mode == "EXEC":
            prompt = f"""System: {system_os} ({shell}).
Task: Return ONLY the terminal command required to: {user_query}
Format: Return exactly the command string."""
        else:
            prompt = f"""System: {system_os} ({shell}).
Task: If the user request is a single-turn DevOps command (ls, docker ps, git branch, etc.), return ONLY the command.
If it is complex (strategy, multi-step, analysis) OR a normal conversational question, respond ONLY with the word "COMPLEX".

Request: {user_query}
Format: Return exactly the command string or "COMPLEX"."""

        try:
            res = await self.fast_llm.ainvoke([HumanMessage(content=prompt)], stream=False)
            decision = str(res.content).strip().replace("`", "")
            logger.info(f"Router: Reflex model decision: '{decision}'")
            
            if decision:
                # If we detect a conversational query in AUTO mode, route to chat
                if user_mode == "AUTO" and decision.upper() == "COMPLEX":
                    # We'll do a second quick check or let planner handle it?
                    # Better: let's add a "CHAT" category to the router prompt for better accuracy
                    pass

                if "COMPLEX" not in decision.upper():
                    logger.info(f"Router: Fast-path confirmed: '{decision}'. Executing...")
                    
                    from uuid import uuid4
                    tool_call = {
                        "name": "run_command",
                        "args": {"cmd": decision},
                        "id": f"fast_{uuid4().hex[:8]}"
                    }
                    return {
                        "messages": [AIMessage(content=f"Routing to fast-path: {decision}", tool_calls=[tool_call])],
                        "next_step": "fast_path"
                    }
        except Exception as e:
            logger.warning(f"Router: Speculation error: {e}\nTraceback: {traceback.format_exc()}")
            
        return {"next_step": "planner"}

    async def chat_node(self, state: AgentState):
        """Conversational Node: Handles purely informational queries using the fast model."""
        logger.info("Chat: Generating informational response...")
        
        user_query = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                user_query = str(m.content)
                break
        
        prompt = f"""System: You are a helpful DevOps assistant. Answer the informational query briefly and accurately.
DO NOT suggest running dangerous commands. If asked for a command, provide the text but explain what it does.

Request: {user_query}"""
        
        # Use the fast model for instant responses
        res = await self.fast_llm.ainvoke([HumanMessage(content=prompt)])
        return {
            "messages": [AIMessage(content=res.content)],
            "next_node": "END" # Chat ends the turn
        }

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
                logger.warning("Audit Gate: Drift/Error detected. Re-probing environment.")
                return "prober"
            return "planner"

        def router_gate(state: AgentState) -> Literal["planner", "executor", "auto_executor", "chat", END]:
            # Support explicit short-circuits from router_node
            next_step = state.get("next_step")
            if next_step == "chat":
                return "chat"
            if next_step == "planner":
                return "planner"
            
            msgs = state.get("messages", [])
            if msgs and isinstance(msgs[-1], AIMessage) and msgs[-1].tool_calls:
                return safety_gate(state)
            return "planner"

        # 3. Nodes
        tool_node = ToolNode(self.tools)

        workflow.add_node("prober", self.prober_node)
        workflow.add_node("ingestion", self.ingestion_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", tool_node)
        workflow.add_node("auto_executor", tool_node)
        workflow.add_node("sanitizer", self.sanitizer_node)
        workflow.add_node("analyzer", self.analyzer_node)
        workflow.add_node("audit", self.audit_node)
        workflow.add_node("negotiator", self.negotiator_node)
        workflow.add_node("chat", self.chat_node)
        
        workflow.add_edge(START, "prober")
        workflow.add_edge("prober", "ingestion")
        workflow.add_edge("ingestion", "router")
        workflow.add_conditional_edges("router", router_gate, {
            "planner": "planner",
            "executor": "executor",
            "auto_executor": "auto_executor",
            "chat": "chat",
            END: END
        })
        workflow.add_edge("chat", END)
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

    async def run(self, user_input: str, user_mode: str = "AUTO"):
        """Execute one turn with Ollama-style streaming and a Live HUD."""
        # NEW: Automated Task Branching
        await self._detect_and_handle_pivot(user_input)

        # Expert Hardening Phase K: Update recap at the start of every user turn
        self.context_recap = self._get_last_milestones()
        
        # Phase 18: Check for existing state to avoid re-initializing
        trace_config = {
            "configurable": {"thread_id": self.session.id},
        }
        
        existing_state = await self.app.aget_state(trace_config)
        
        if existing_state and existing_state.values:
            logger.info(f"LangGraph: Resuming session {self.session.id}. History: {len(existing_state.values.get('messages', []))}")
            # We only send the NEW message. LangGraph handles the rest.
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "user_mode": user_mode
            }
        else:
            logger.info(f"LangGraph: Starting fresh session {self.session.id}")
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "session_id": self.session.id,
                "goal": self.session.goal,
                "last_synced_count": 0,
                "env": {},
                "env_hash": None,
                "next_step": None,
                "denial_reason": None,
                "loop_count": 0,
                "user_mode": user_mode
            }

        # BUG-18 FIX: Cache get_system_info() to avoid 6+ subprocess probes
        sys_info = await get_system_info()
        os_tag = f"os:{sys_info['os'].lower()}"

        trace_config.update({
            "callbacks": [self.handler] if self.handler else [],
            "tags": ["devops-agent", os_tag],
            "metadata": {
                "langfuse_session_id": self.session.id,
                "langfuse_tags": ["devops-agent", os_tag],
                "goal": self.session.goal
            }
        })

        # 1. Initialize RenderController
        # Gather environment context for the mission-control HUD
        env_context = {
            "cluster": sys_info.get("cluster_name", "local"),
            "namespace": sys_info.get("active_namespace", "default"),
            "branch": sys_info.get("git_branch", "detached"),
            "goal": self.session.goal
        }
        render = RenderController(env_context, debug_mode=self.debug_mode)
        render.render_session_header(self.session.id)
        
        # Phase 26: Reset turn-level cache at start of logical turn
        self.cached_sys_info = sys_info 

        # 2. Start Live Loop
        with Live(render.get_live_group(), refresh_per_second=10, console=console, vertical_overflow="visible") as live:
            await self._run_graph_with_events(initial_state, trace_config, live, render)

    async def _run_graph_with_events(self, input_data: Optional[Dict], trace_config: Dict, live: Live, render: RenderController):
        """Internal loop to process graph events and update HUD."""
        import time
        from langchain_core.messages import AIMessage, ToolMessage
        
        try:
            async for event in self.app.astream_events(input_data, config=trace_config, version="v2"):
                kind = event["event"]
                name = event["name"]

                # 1. Phase Transitions
                if kind in ["on_node_start", "on_chain_start"]:
                    node_name = event["metadata"].get("langgraph_node")
                    if not node_name and kind == "on_chain_start" and name == "LangGraph":
                        render.transition(RenderState.PLANNING)
                        continue
                    
                    if node_name:
                        if node_name == "prober":
                            render.transition(RenderState.PROBING)
                        elif node_name == "ingestion":
                            render.transition(RenderState.INGESTING)
                        elif node_name == "planner":
                            # Phase Logic: Clear token buffer on new planning turn to avoid clutter
                            if render.state == RenderState.ANALYZING:
                                # We are looping back from tool analysis
                                render.clear_buffer()
                            render.transition(RenderState.PLANNING)
                        elif node_name in ["executor", "auto_executor"]:
                            render.transition(RenderState.EXECUTING)
                        elif node_name == "analyzer":
                            render.transition(RenderState.ANALYZING)
                        elif node_name == "chat":
                            render.transition(RenderState.CHAT)
                        elif node_name == "audit":
                            # Audit is internal, don't necessarily need a new header every time
                            pass
                        
                        live.update(render.get_live_group())

                # 2. Streaming Responses
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        render.stream_token(chunk.content)
                        live.update(render.get_live_group())

                # 3. Handle Tool Results
                elif kind == "on_tool_start":
                    tool_input = event["data"].get("input", {})
                    cmd = tool_input.get("cmd", "") or tool_input.get("command", "")
                    if cmd:
                        render.running_tool = cmd
                        render.tool_start_time = time.time()
                        live.update(render.get_live_group())
                
                elif kind == "on_tool_end":
                    output_msg = event["data"].get("output")
                    cmd = render.running_tool or "command"
                    render.tool_start_time = None
                    render.running_tool = None
                    
                    if output_msg is not None:
                        content = output_msg.content if isinstance(output_msg, ToolMessage) else str(output_msg)
                        
                        # Use RenderController to print the structured result block (above Live area)
                        live.stop()
                        status = "SUCCESS"
                        if "[Exit Code:" in content and "Exit Code: 0]" not in content:
                            status = "FAILED"
                        render.render_tool_result(cmd, content, status)
                        live.start()
                    
                    live.update(render.get_live_group())

                # 4. Handle Interrupts / State Persistence
                if kind == "on_chain_end" and name == "LangGraph":
                    snapshot = await self.app.aget_state(trace_config)
                    # Sync loop count for HUD
                    render.set_loop_count(snapshot.values.get("loop_count", 0))
                    
                    if snapshot.next:
                        live.stop()
                        # We use a legacy adapter or update handle_safety_interrupt to use RenderController
                        await self._handle_safety_interrupt_v2(snapshot, trace_config, live, render)
                        live.start()
                    else:
                        # Final update for completion
                        render.transition(RenderState.COMPLETED)
                        live.update(render.get_live_group())
        except Exception as e:
            logger.critical(f"Fatal error in agent loop: {e}")
            await self.emergency_panic()
            raise e

    async def _detect_and_handle_pivot(self, user_input: str):
        """Detect if the user is switching tasks and automatically branch if so."""
        from datetime import datetime
        from pathlib import Path
        from src import config
        from src.gcc.session import Session
        from src.gcc.log import GCCLogger
        from src.gcc.checkpointer import GCCCheckpointer

        # 1. Very fast keyword check
        keywords = ["new task", "switch to", "different goal", "stop this", "reset session"]
        is_pivot_likley = any(k in user_input.lower() for k in keywords)
        
        # 2. If it's a long input or keywords matched, do a fast LLM check
        if is_pivot_likley or len(user_input) > 200:
            prompt = f"""Assess if this user input is a fundamental task switch from the current goal.
Current Goal: {self.session.goal}
User Input: {user_input}
Respond ONLY with 'SWITCH' or 'CONTINUE'."""
            
            try:
                # Use the fast_llm to avoid hanging on the primary model
                res = await self.fast_llm.ainvoke([HumanMessage(content=prompt)], stream=False)
                decision = str(res.content).strip().upper()
                logger.info(f"Pivot Detector Decision: {decision}")
                
                if "SWITCH" in decision:
                    logger.info(f"Pivot Detected: Switching context for '{user_input[:50]}'")
                    new_branch_id = await self.intelligence.branch_session(
                        parent_id=self.session.id,
                        branch_name=f"auto_{datetime.now().strftime('%H%M%S')}"
                    )
                    
                    # Swap context to the new branch
                    rows = await self.intelligence.get_session_details(new_branch_id)
                    # Simple parse of details string (re-fetching for safety)
                    self.session = Session(new_branch_id, user_input)
                    self.session.path = Path(config.agent.gcc_base_path) / "sessions" / new_branch_id
                    
                    # Update Agent Resources
                    self.logger = GCCLogger(self.session.path)
                    self.checkpointer = GCCCheckpointer(self.session.path)
                    self.app = self.graph.compile(checkpointer=self.checkpointer, interrupt_before=["executor"])
                    
                    # Log the transition
                    self.logger.log_commit(
                        summary="Automated Task Switch",
                        finding=f"Branched from {self.session.id} to handle: {user_input}"
                    )
            except Exception as e:
                logger.warning(f"Pivot detection failed: {e}")

    async def _handle_safety_interrupt_v2(self, snapshot, trace_config, live, render):
        """Adapter for the new RenderController to handle the safety gate."""
        render.transition(RenderState.AWAITING_APPROVAL)
        live.update(render.get_live_group())
        
        last_ai_msg = snapshot.values["messages"][-1]
        if not last_ai_msg.tool_calls:
            return

        # Stop Live to ask for input safely
        live.stop()
        console.print("\n[bold yellow]⚠️  SAFETY APPROVAL REQUIRED[/bold yellow]")
        for tc in last_ai_msg.tool_calls:
            cmd = tc["args"].get("cmd", "") or tc["args"].get("command", "")
            console.print(f"   Command: [white]{cmd}[/white]")
        
        user_response = console.input("\nApprove? (y/n/or type feedback): ").strip()
        live.start() # Resume Live
        
        lower_resp = user_response.lower()
        is_approval = any(x in lower_resp for x in ["y", "yes", "sure", "go", "approve", "ok"])
        is_denial = any(x in lower_resp for x in ["n", "no", "stop", "don't", "cancel", "deny"])

        if is_approval and not is_denial:
            console.print("[green]Approved. Executing...[/green]")
            ObservabilityService.score_trace(self.handler, "user-approval", 1.0)
            await self._run_graph_with_events(None, trace_config, live, render)
        else:
            reason = user_response if user_response and not is_denial else "User denied execution."
            ObservabilityService.score_trace(self.handler, "user-approval", 0.0, comment=reason)
            await self.app.aupdate_state(trace_config, {"denial_reason": reason}, as_node="negotiator")
            await self._run_graph_with_events(None, trace_config, live, render)

    async def shutdown(self):
        """Phase O: Graceful exit for all agent resources."""
        await self.intelligence.shutdown()

# Placeholder for Phase 2 implementation in agent/core.py
