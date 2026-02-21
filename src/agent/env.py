import os
import platform
import asyncio
from typing import Dict, Any

async def run_probe(cmd: str) -> str:
    """Helper to run a probe command asynchronously and return stripped output."""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout.decode().strip()
        return f"Error: {stderr.decode().strip()}"
    except Exception as e:
        return f"Exception: {str(e)}"

async def get_system_info() -> Dict[str, Any]:
    """Detect OS, Release, Shell, and DevOps tool context in parallel."""
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "shell": "unknown",
        "cwd": os.getcwd(),
        "tools": {}
    }

    # Normalize CWD for Windows casing safety
    if info["os"] == "Windows":
        info["cwd"] = info["cwd"].lower()

    # Detect Shell
    if os.name == 'nt':
        if "PSModulePath" in os.environ:
            info["shell"] = "powershell"
        else:
            info["shell"] = "cmd"
    else:
        info["shell"] = os.environ.get("SHELL", "bash").split("/")[-1]

    # DevOps Probes in Parallel
    kubectl_context_task = run_probe("kubectl config current-context")
    kubectl_ns_task = run_probe("kubectl config view --minify --output \"jsonpath={..namespace}\"")
    docker_info_task = run_probe("docker info")
    git_branch_task = run_probe("git rev-parse --abbrev-ref HEAD")
    git_remote_task = run_probe("git remote get-url origin")

    results = await asyncio.gather(
        kubectl_context_task,
        kubectl_ns_task,
        docker_info_task,
        git_branch_task,
        git_remote_task
    )

    info["tools"]["kubectl"] = {
        "context": results[0],
        "namespace": results[1]
    }
    
    info["tools"]["docker"] = {
        "status": "ready" if "Containers:" in results[2] else "not_running"
    }

    info["tools"]["git"] = {
        "branch": results[3],
        "remote": results[4]
    }

    return info

def get_env_hash(info: Dict[str, Any]) -> str:
    """Generate a stable hash of the environment state to detect drift."""
    import hashlib
    import json
    
    # We only hash the volatile parts that affect execution
    volatile = {
        "kubectl": info.get("tools", {}).get("kubectl", {}),
        "git_branch": info.get("tools", {}).get("git", {}).get("branch"),
        "shell": info.get("shell"),
        "cwd": info.get("cwd")
    }
    
    encoded = json.dumps(volatile, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
