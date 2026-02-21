import time
from enum import Enum
from typing import Optional, Dict, List, Any
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.box import ROUNDED, HEAVY
from rich.syntax import Syntax
from src.agent.sanitizer import Sanitizer

class RenderState(Enum):
    IDLE = "IDLE"
    INITIALIZING = "🚀 Initializing"
    PROBING = "🔍 Detecting Environment"
    INGESTING = "📚 Ingesting Context"
    CHAT = "💬 Conversing"
    PLANNING = "🧠 Planning"
    AWAITING_APPROVAL = "⚠️ Awaiting Approval"
    EXECUTING = "⚙️ Executing"
    ANALYZING = "🔬 Analyzing"
    COMPLETED = "✅ Completed"
    ERROR = "❌ Error"

class RenderController:
    def __init__(self, session_context: Dict[str, Any], debug_mode: bool = False):
        self.console = Console()
        self.state = RenderState.IDLE
        self.session_context = session_context
        self.debug_mode = debug_mode
        self.start_time = time.time()
        
        # State tracking
        self.seen_states = set()
        self.streaming_buffer = ""
        self.last_error: Optional[str] = None
        self.running_tool: Optional[str] = None
        self.tool_start_time: Optional[float] = None
        self.loop_count = 0
        
        # Performance/UI
        self.width = 100

    def transition(self, new_state: RenderState):
        """Update state and print header if it's the first time entering this state."""
        if self.state == new_state:
            return
        
        self.state = new_state
        if new_state not in self.seen_states and new_state not in [RenderState.IDLE, RenderState.CHAT]:
            self.seen_states.add(new_state)
            self._render_phase_header(new_state)

    def _render_phase_header(self, state: RenderState):
        """Prints a clean, deterministic phase header to the console (above the Live area)."""
        header_text = f"\n{state.value}"
        if state == RenderState.PLANNING:
            header_text += "..."
        
        self.console.print(Text("─" * 46, style="dim"))
        self.console.print(Text(header_text, style="bold cyan"))
        self.console.print(Text("─" * 46, style="dim"))

    def stream_token(self, token: str):
        """Accumulate tokens for delta-based printing."""
        self.streaming_buffer += token

    def clear_buffer(self):
        """Flush the streaming buffer for a new turn/phase."""
        self.streaming_buffer = ""

    def set_error(self, message: str):
        self.last_error = message
        self.state = RenderState.ERROR

    def set_loop_count(self, count: int):
        self.loop_count = count

    def render_hud(self) -> Panel:
        """Generates the mission-control HUD at the top of the Live display."""
        hud_lines = []
        
        # Info row
        info = Text.assemble(
            ("Cluster: ", "dim"), (self.session_context.get("cluster", "unknown") or "local", "bold white"),
            ("  Namespace: ", "dim"), (self.session_context.get("namespace", "default"), "bold white"),
            ("  Git: ", "dim"), (self.session_context.get("branch", "detached"), "bold green")
        )
        hud_lines.append(info)
        
        # Status row
        status = Text.assemble(
            ("Status: ", "dim"), (f"{self.state.value}", "bold cyan"),
            (f"  [Turn: {self.loop_count}/10]", "dim")
        )
        
        if self.tool_start_time and self.running_tool:
            elapsed = int(time.time() - self.tool_start_time)
            status.append(f"  🛠️ {self.running_tool} ({elapsed}s)", style="bold yellow")
            
        hud_lines.append(status)
        
        return Panel(
            Group(*hud_lines),
            title="[bold white]DevOps Agent Mission Control",
            title_align="left",
            style="cyan",
            box=ROUNDED,
            expand=True
        )

    def render_tool_result(self, cmd: str, output: str, status: str = "SUCCESS"):
        """Prints a structured tool result block below the headers."""
        self.console.print(f"\n[bold yellow]Result: {cmd.split()[0]}[/bold yellow]")
        self.console.print(Text("─" * 24, style="dim"))
        
        # Truncation logic
        lines = output.splitlines()
        if len(lines) > 100:
            output_display = "\n".join(lines[:50]) + f"\n\n[dim]... (Truncated {len(lines)-100} lines) ...[/dim]\n\n" + "\n".join(lines[-50:])
        else:
            output_display = output

        # Auto-syntax highlighting
        syntax_lang = "text"
        if output.strip().startswith("{") or output.strip().startswith("["): syntax_lang = "json"
        elif "apiVersion:" in output: syntax_lang = "yaml"
        
        sanitized = Sanitizer.sanitize(output_display)
        
        self.console.print(Syntax(sanitized, syntax_lang, theme="monokai", background_color="default"))
        
        style = "bold green" if status == "SUCCESS" else "bold red"
        self.console.print(Text(f"✓ {status}", style=style))

    def get_live_group(self) -> Group:
        """Builds the current Live display frame."""
        elements = [self.render_hud()]
        
        if self.last_error:
            elements.append(Panel(Text(f"⚠️ {self.last_error}", style="bold red"), title="System Alert", style="red", box=ROUNDED))

        if self.streaming_buffer.strip():
            elements.append(Text("")) # Spacer
            elements.append(Markdown(self.streaming_buffer))
            
        return Group(*elements)

    def render_session_header(self, session_id: str):
        """Renders the very first splash header of the session."""
        banner = Text.assemble(
            ("🚀 DevOps Agent — ", "bold cyan"),
            (session_id, "bold white"),
            (f" · {self.session_context.get('goal', '')[:50]}...", "dim")
        )
        self.console.print(Text("━" * self.width, style="bold cyan"))
        self.console.print(banner)
        self.console.print(Text("━" * self.width, style="bold cyan"))
