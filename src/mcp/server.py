import asyncio
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from loguru import logger
from src.skills.parser import PermissionClassifier
from src.config import config
from typing import Dict, Any, Optional

# Initialize FastMCP server
mcp = FastMCP("devops-agent-mcp")

# Initialize safety classifier
classifier = PermissionClassifier(config.agent.skills_path)

# Phase 4: Configurable timeout (CC BASH_DEFAULT_TIMEOUT_MS pattern)
DEFAULT_TIMEOUT = int(os.environ.get("DEVOPS_CMD_TIMEOUT", "120"))

@mcp.tool()
async def run_command(cmd: str, cwd: Optional[str] = None, timeout: Optional[int] = None) -> str:
    """
    Execute a CLI command (kubectl, docker, git).
    
    Args:
        cmd: The full shell command to execute.
        cwd: Optional working directory for the command.
        timeout: Optional timeout in seconds (default: 120s).
        
    Returns:
        The command output as a string.
    """
    tier, pattern = classifier.classify(cmd)
    logger.info(f"FastMCP: Classified command '{cmd}' as {tier} (Pattern: {pattern}, CWD: {cwd})")
    
    # Safety Gate Logic (Architectural requirement: destructive and requires_approval 
    # should be interrupted at the LangGraph level, but we keep this check here as a second layer)
    if tier == "destructive":
        logger.warning(f"Blocking destructive command in MCP layer: {cmd}")
        return f"REFUSED: Command '{cmd}' is DESTRUCTIVE. Use the agent to request approval."

    # Phase 27: Command Optimizer (Claude Interception Pattern)
    import shutil
    optimized_cmd = cmd
    if "grep " in cmd and shutil.which("rg"):
        # Simple substitution: grep -> rg --smart-case --hidden
        # Note: This is a basic mapping; we avoid complex regex flags for safety.
        optimized_cmd = cmd.replace("grep ", "rg --smart-case --hidden ")
        if optimized_cmd != cmd:
            logger.info(f"FastMCP: Optimized '{cmd}' -> '{optimized_cmd}'")

    # Phase 4: CWD validation with fallback (CC CHANGELOG L118)
    effective_cwd = cwd
    if effective_cwd:
        cwd_path = Path(effective_cwd)
        if not cwd_path.exists():
            # Fall back to parent directory if CWD was deleted
            fallback = cwd_path.parent
            while fallback != fallback.parent and not fallback.exists():
                fallback = fallback.parent
            logger.warning(f"FastMCP: CWD '{effective_cwd}' not found, falling back to '{fallback}'")
            effective_cwd = str(fallback)

    cmd_timeout = timeout or DEFAULT_TIMEOUT
    process = None
    
    try:
        process = await asyncio.create_subprocess_shell(
            optimized_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=effective_cwd  # Expert Hardening Phase K
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=cmd_timeout
            )
        except asyncio.TimeoutError:
            # Phase 4: Timeout — kill subprocess cleanly
            if process.returncode is None:
                process.kill()
                await process.wait()
            logger.warning(f"FastMCP: Command timed out after {cmd_timeout}s: {cmd}")
            return f"TIMEOUT: Command '{cmd}' exceeded {cmd_timeout}s and was killed. Consider breaking it into smaller steps."
        
        out_str = stdout.decode('utf-8', errors='replace').strip()
        err_str = stderr.decode('utf-8', errors='replace').strip()
        
        output = ""
        if out_str:
            output += f"{out_str}\n"
        if err_str:
            output += f"STDERR:\n{err_str}\n"
        if process.returncode != 0:
            output += f"[Exit Code: {process.returncode}]"
            
        if not output:
            output = "(Command executed with no output)"
            
        return output

    except asyncio.CancelledError:
        # Phase 4: Esc interrupt — explicitly kill subprocess to prevent zombies
        # CC Pattern: ChildProcess/AbortController cleanup (CHANGELOG L29)
        if process and process.returncode is None:
            try:
                process.kill()
                await process.wait()
                logger.info(f"FastMCP: Killed subprocess for cancelled command: {cmd}")
            except ProcessLookupError:
                pass  # Process already exited
        raise  # Re-raise for upstream handling
    except Exception as e:
        logger.error(f"FastMCP execution error: {e}")
        return f"Execution Error: {str(e)}"
    finally:
        # Phase 4: Final safety net — ensure no orphaned processes
        if process and process.returncode is None:
            try:
                process.kill()
                await process.wait()
            except (ProcessLookupError, OSError):
                pass

if __name__ == "__main__":
    mcp.run()
