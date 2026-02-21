import asyncio
from loguru import logger
from src.gcc.session import Session
from src.agent.graph_core import LangGraphAgent
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

console = Console()

class AgentCore:
    def __init__(self, session: Session, debug_mode: bool = False):
        self.session = session
        self.agent = LangGraphAgent(session, debug_mode=debug_mode)
        
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

    async def chat(self, user_input: str):
        """Standard chat entry point for the CLI."""
        try:
            await self.agent.run(user_input, user_mode=self.mode)
        except Exception as e:
            logger.error(f"AgentCore Chat Error: {e}")
            console.print(f"[bold red]Error:[/bold red] {e}")

    async def shutdown(self):
        """Phase O: Ensure agent resources are released."""
        await self.agent.shutdown()

    async def run_loop(self):
        console.print(f"\n[bold green]DevOps Agent Active[/bold green] | Session: [cyan]{self.session.id}[/cyan]")
        console.print(f"Goal: {self.session.goal}\n")
        
        # Key bindings for multi-line support and mode toggling
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
                        
                    await self.chat(user_input)
                    
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
