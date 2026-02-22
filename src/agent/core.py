import asyncio
import re
from typing import Optional
from loguru import logger
from src.gcc.session import Session
from src.agent.graph_core import LangGraphAgent
from src.agent.render import RenderController
from src.ollama_client import ollama_client
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

console = Console()

# Phase 4: Pre-compiled regex for !cmd detection (CC hookify @lru_cache pattern)
BANG_REGEX = re.compile(r'^!\s*(.*)')

class AgentCore:
    def __init__(self, session: Session, debug_mode: bool = False):
        self.session = session
        self.agent = LangGraphAgent(session, debug_mode=debug_mode)
        self.active_task: Optional[asyncio.Task] = None  # Phase 4: Track for Esc cancellation
        
        # Session-isolated history
        history_path = self.session.path / ".history"
        
        # DevOps Completer
        devops_completer = WordCompleter([
            "docker", "kubectl", "git", "apply", "delete", "get", "logs", 
            "describe", "commit", "push", "pull", "status", "branch",
            "list all containers", "check system status", "audit docker"
        ], ignore_case=True)

        self.mode = "AUTO" # Options: AUTO, EXEC, CHAT
        self.modes = ["AUTO", "EXEC", "CHAT"]
        
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_path)),
            completer=devops_completer,
            complete_while_typing=True
        )

    async def _chat_direct(self, user_input: str):
        """
        Instant CHAT mode: bypasses LangGraph entirely.
        No prober, no ingestion, no GCC log, no DB writes.
        Streams directly from the LLM for zero-latency conversational responses.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful DevOps assistant. Answer questions clearly and concisely. "
                    "If asked for a command, provide it with a brief explanation. "
                    "Do not run any commands — this is a conversational-only mode."
                )
            },
            {"role": "user", "content": user_input}
        ]
        try:
            response = await ollama_client.chat(messages, stream=True)
            full_text = ""
            with Live("", refresh_per_second=15, console=console) as live:
                async for chunk in response:
                    delta = chunk.get("message", {}).get("content", "") if isinstance(chunk, dict) else getattr(getattr(chunk, "message", None), "content", "")
                    full_text += delta
                    live.update(Markdown(full_text))
        except Exception as e:
            logger.error(f"Direct chat error: {e}")
            console.print(f"[bold red]Chat Error:[/bold red] {e}")

    async def chat(self, user_input: str):
        """Standard chat entry point for the CLI."""
        try:
            await self.agent.run(user_input, user_mode=self.mode)
        except asyncio.CancelledError:
            # Phase 4: Esc interrupt — handled gracefully
            raise
        except Exception as e:
            logger.error(f"AgentCore Chat Error: {e}")
            console.print(f"[bold red]Error:[/bold red] {e}")

    async def _execute_direct_command(self, cmd: str):
        """
        Phase 4: Execute a human !cmd directly, log it, and inject context.
        CC Pattern: Human-in-the-loop with [HUMAN EXECUTED] prefix.
        """
        console.print(f"[dim]⚠️ Direct execution — no safety checks.[/dim]")
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.session.path)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=60  # 60s timeout for human commands
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                console.print("[yellow]Command timed out after 60s and was killed.[/yellow]")
                return "(Command timed out after 60 seconds)"
            
            out_str = stdout.decode('utf-8', errors='replace').strip()
            err_str = stderr.decode('utf-8', errors='replace').strip()
            
            output = ""
            if out_str:
                output += out_str
            if err_str:
                output += f"\nSTDERR:\n{err_str}"
            if process.returncode != 0:
                output += f"\n[Exit Code: {process.returncode}]"
            if not output:
                output = "(Command executed with no output)"
                
            return output
            
        except asyncio.CancelledError:
            # Esc during direct command — kill subprocess
            if process and process.returncode is None:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            logger.error(f"Direct command error: {e}")
            return f"Execution Error: {str(e)}"

    async def shutdown(self):
        """Phase O: Ensure agent resources are released."""
        await self.agent.shutdown()

    async def run_loop(self):
        console.print(f"\n[bold green]DevOps Agent Active[/bold green] | Session: [cyan]{self.session.id}[/cyan]")
        console.print(f"Goal: {self.session.goal}")
        console.print(f"[dim]Tip: Use !<command> for direct shell execution | Tab to cycle modes | Esc to interrupt[/dim]\n")
        
        # Key bindings for multi-line support, mode toggling, and Esc interrupt
        kb = KeyBindings()
        
        @kb.add('escape', 'enter') # Alt+Enter
        @kb.add('c-j')             # Ctrl+J (Standard terminal newline)
        def _(event):
            event.current_buffer.insert_text('\n')

        @kb.add('tab')
        def _(event):
            # If buffer is empty, cycle modes
            if not event.current_buffer.text.strip():
                idx = self.modes.index(self.mode)
                self.mode = self.modes[(idx + 1) % len(self.modes)]
                event.app.invalidate() # Force redraw of prompt
            else:
                # Fallback to completion (manual trigger)
                event.current_buffer.start_completion()

        def get_prompt():
            color = "ansiblue"
            if self.mode == "CHAT": color = "ansimagenta"
            elif self.mode == "EXEC": color = "ansired"
            
            return HTML(f'<{color}><b>({self.mode}) &gt;&gt;&gt; </b></{color}>')

        try:
            while True:
                try:
                    # Use prompt_toolkit for advanced CLI features
                    user_input = await self.prompt_session.prompt_async(
                        get_prompt,
                        key_bindings=kb
                    )
                    
                    if not user_input.strip():
                        continue
                        
                    user_input = user_input.strip()
                    if user_input.lower() in ["exit", "quit", "/exit"]:
                        console.print("\n[yellow]Exiting session...[/yellow]")
                        break
                    
                    # Phase 4: Direct Command Execution (!cmd)
                    bang_match = BANG_REGEX.match(user_input)
                    if bang_match:
                        cmd = bang_match.group(1).strip()
                        if not cmd:
                            console.print("[yellow]Usage: !<command>  (e.g. !kubectl get pods)[/yellow]")
                            continue
                        
                        # Execute the command directly
                        output = await self._execute_direct_command(cmd)
                        
                        # Display via RenderController
                        RenderController.render_direct_command(cmd, output)
                        
                        # Log to GCC (Human: tag)
                        self.agent.logger.log_human_action(cmd, output)
                        
                        # Inject into LangGraph state for AI context
                        # Truncate large outputs before injection (CC disk-spill pattern)
                        inject_output = output[:5000] if len(output) > 5000 else output
                        context_msg = f"[HUMAN EXECUTED] !{cmd}\nOutput:\n{inject_output}"
                        
                        # Store as pending human context for next AI turn
                        if not hasattr(self.agent, '_pending_human_context'):
                            self.agent._pending_human_context = []
                        self.agent._pending_human_context.append(context_msg)
                        
                        logger.info(f"Direct command executed and logged: !{cmd}")
                        continue
                        
                    # Normal AI chat flow with Esc interrupt support
                    self.active_task = asyncio.current_task()

                    # CHAT mode: bypass graph entirely — direct LLM stream
                    if self.mode == "CHAT":
                        await self._chat_direct(user_input)
                    else:
                        await self.chat(user_input)

                    self.active_task = None
                    
                except asyncio.CancelledError:
                    # Phase 4: Esc interrupt — grey feedback (CC "less alarming" style)
                    console.print("\n[grey70]Interrupted.[/grey70]")
                    self.active_task = None
                    continue  # Don't exit, just cancel current operation
                except KeyboardInterrupt:
                    # Ctrl+C handler: Expert Hardening Phase L (Exit on Ctrl+C)
                    console.print("\n[yellow]KeyboardInterrupt (Ctrl+C). Exiting session...[/yellow]")
                    break
                except EOFError:
                    # Ctrl+D handler
                    console.print("\n[yellow]EOF (Ctrl+D). Exiting...[/yellow]")
                    break
                except Exception as e:
                    logger.error(f"Loop error: {e}")
                    console.print(f"[bold red]System Error:[/bold red] {e}")
        finally:
            # Phase O: Decisive exit path
            await self.shutdown()
