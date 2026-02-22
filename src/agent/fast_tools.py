import os
import re
from pathlib import Path
from typing import List, Optional, Dict
from langchain_core.tools import tool
from loguru import logger

# Performance Optimization: Replicating Claude's dedicated Read/Grep/Glob tools.
# These avoid the ~100-200ms overhead of spawning a shell subprocess.

def _is_safe_path(path: str) -> bool:
    """Basic path safety to prevent reading system secrets via fast tools."""
    blocked = [".env", "config.json", "secrets", ".ssh", ".kube/config"]
    p = str(path).lower()
    for b in blocked:
        if b in p:
            return False
    return True

@tool
def fast_ls(path: str = ".") -> str:
    """
    List directory contents using native Python (bypasses shell).
    Provides file sizes and modification times.
    """
    try:
        if not _is_safe_path(path):
            return f"Error: Path '{path}' is restricted for safety."
            
        target = Path(path).resolve()
        if not target.exists():
            return f"Error: Path '{path}' does not exist."
        
        output = []
        # Sort directories first, then files
        items = sorted(list(target.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for item in items:
            prefix = "[DIR] " if item.is_dir() else "      "
            size = ""
            if item.is_file():
                s = item.stat().st_size
                if s > 1024 * 1024:
                    size = f" ({s / (1024*1024):.1f} MB)"
                elif s > 1024:
                    size = f" ({s / 1024:.1f} KB)"
                else:
                    size = f" ({s} B)"
            
            output.append(f"{prefix}{item.name}{size}")
            
        return "\n".join(output) if output else "(empty directory)"
    except Exception as e:
        logger.error(f"fast_ls error: {e}")
        return f"Error: {str(e)}"

@tool
def fast_read(path: str, max_lines: int = 500) -> str:
    """
    Read file content using native Python (bypasses cat/shell).
    Replicates Claude's Read tool with automatic truncation.
    """
    try:
        if not _is_safe_path(path):
            return f"Error: Path '{path}' is restricted for safety."
            
        target = Path(path).resolve()
        if not target.is_file():
            return f"Error: '{path}' is not a file or does not exist."
            
        # Basic binary check
        if target.suffix in ['.exe', '.bin', '.pyc', '.so', '.dll', '.zip', '.tar', '.gz']:
             return f"Error: Refusing to read binary file '{path}'."

        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... [TRUNCATED: Only first {max_lines} lines shown] ...")
                    break
                lines.append(line.rstrip())
            
            return "\n".join(lines)
    except Exception as e:
        logger.error(f"fast_read error: {e}")
        return f"Error: {str(e)}"

@tool
def fast_find(pattern: str, path: str = ".") -> str:
    """
    Find files matching a glob pattern (bypasses find/shell).
    Example: fast_find("*.py", "./src")
    """
    try:
        if not _is_safe_path(path):
             return f"Error: Path '{path}' is restricted for safety."
             
        target = Path(path)
        matches = list(target.rglob(pattern))
        
        if not matches:
            return f"No matches found for '{pattern}' in '{path}'"
            
        return "\n".join([str(m) for m in matches[:100]]) # Limit to 100 results
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def fast_grep(pattern: str, path: str = ".", recursive: bool = True) -> str:
    """
    Search for a regex pattern in files (bypasses grep/shell).
    Highly efficient for small-to-medium codebases.
    """
    try:
        if not _is_safe_path(path):
             return f"Error: Path '{path}' is restricted for safety."
             
        target = Path(path)
        regex = re.compile(pattern, re.IGNORECASE)
        results = []
        
        files = target.rglob("*") if recursive else target.iterdir()
        
        for f in files:
            if not f.is_file() or f.suffix in ['.git', '.pyc', '.so', '.dll']:
                continue
                
            try:
                with open(f, 'r', encoding='utf-8', errors='replace') as file:
                    for i, line in enumerate(file, 1):
                        if regex.search(line):
                            results.append(f"{f}:{i}: {line.strip()}")
                            if len(results) >= 50:
                                results.append("... [TRUNCATED: Max 50 matches shown] ...")
                                return "\n".join(results)
            except:
                continue # Skip unreadable files
                
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error: {str(e)}"
