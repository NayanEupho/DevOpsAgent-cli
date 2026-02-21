import asyncio
from mcp.server.fastmcp import FastMCP
from loguru import logger
from src.skills.parser import PermissionClassifier
from src.config import config
from typing import Dict, Any, Optional

# Initialize FastMCP server
mcp = FastMCP("devops-agent-mcp")

# Initialize safety classifier
classifier = PermissionClassifier(config.agent.skills_path)

@mcp.tool()
async def run_command(cmd: str, cwd: Optional[str] = None) -> str:
    """
    Execute a CLI command (kubectl, docker, git).
    
    Args:
        cmd: The full shell command to execute.
        cwd: Optional working directory for the command.
        
    Returns:
        The command output as a string.
    """
    tier = classifier.classify(cmd)
    logger.info(f"FastMCP: Classified command '{cmd}' as {tier} (CWD: {cwd})")
    
    # Safety Gate Logic (Architectural requirement: destructive and requires_approval 
    # should be interrupted at the LangGraph level, but we keep this check here as a second layer)
    if tier == "destructive":
        logger.warning(f"Blocking destructive command in MCP layer: {cmd}")
        return f"REFUSED: Command '{cmd}' is DESTRUCTIVE. Use the agent to request approval."

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd # Expert Hardening Phase K
        )
        stdout, stderr = await process.communicate()
        
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

    except Exception as e:
        logger.error(f"FastMCP execution error: {e}")
        return f"Execution Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
