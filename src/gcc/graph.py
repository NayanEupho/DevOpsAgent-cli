from rich.tree import Tree
from rich.console import Console
from pathlib import Path
import yaml
from src.config import config

class GCCGraph:
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.console = Console()

    def render(self):
        # Load metadata
        meta_path = self.session_path / "metadata.yaml"
        goal = "Unknown Goal"
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                meta = yaml.safe_load(f)
                goal = meta.get("goal", goal)

        tree = Tree(f"[bold blue]GCC Graph[/bold blue] — [cyan]{goal}[/cyan]")
        
        # Load commits
        commit_path = self.session_path / "commit.md"
        if commit_path.exists():
            with open(commit_path, 'r') as f:
                content = f.read()
                # Simple parsing for Phase 1
                commits = []
                import re
                matches = re.findall(r'### \[(.*?)\] COMMIT\n\*\*Summary:\*\* (.*?)\n', content)
                
                main_branch = tree.add("[bold green]main[/bold green]")
                for ts, summary in matches:
                    main_branch.add(f"[yellow]{ts}[/yellow] — {summary}")
        else:
            tree.add("[italic gray]No commits yet[/italic gray]")

        return tree

    def show(self):
        tree = self.render()
        self.console.print(tree)
