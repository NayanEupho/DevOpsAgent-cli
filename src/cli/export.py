import os
from pathlib import Path
from datetime import datetime
from loguru import logger
from src.intelligence.registry import IntelligenceRegistry

class ExportService:
    @staticmethod
    async def export_session(session_id: str, output_format: str = "markdown") -> str:
        """Exports a session's history and findings into a professional report."""
        reg = IntelligenceRegistry.get_instance()
        
        # 1. Resolve Session Data
        details_str = await reg.get_session_details(session_id)
        if "not found" in details_str.lower():
            return f"Error: Session {session_id} not found."
            
        # Parse details (simple split for test)
        lines = details_str.split("\n")
        path_line = [l for l in lines if "GCC Path:" in l]
        if not path_line: return "Error: Could not resolve session path."
        session_path = Path(path_line[0].split(": ", 1)[1])
        
        log_path = session_path / "log.md"
        commit_path = session_path / "commit.md"
        
        # 2. Build Report Content
        report = []
        report.append(f"# DEVOPS AGENT: SESSION REPORT")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Session ID:** {session_id}")
        report.append("\n---\n")
        
        # Metadata Section
        report.append("## 1. EXECUTIVE SUMMARY")
        report.append(details_str)
        report.append("\n")
        
        # Milestones Section
        if commit_path.exists():
            report.append("## 2. KEY FINDINGS & MILESTONES")
            with open(commit_path, 'r', encoding='utf-8') as f:
                report.append(f.read())
            report.append("\n")
            
        # Full Log Section
        if log_path.exists():
            report.append("## 3. CHRONOLOGICAL EXECUTION LOG")
            with open(log_path, 'r', encoding='utf-8') as f:
                report.append(f.read())
                
        # 3. Save to Exports Folder
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        export_filename = f"report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        export_path = export_dir / export_filename
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
            
        logger.info(f"ExportService: Generated report at {export_path}")
        return str(export_path)
