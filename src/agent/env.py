import os
import platform
import asyncio
from typing import Dict, Any

async def run_probe(cmd: str) -> str:
    """Helper to run a probe command asynchronously with a hard timeout."""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            return "Error: probe timed out"
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
    docker_count_task = run_probe("docker ps -q | wc -l") if os.name != 'nt' else run_probe("docker ps -q")
    git_branch_task = run_probe("git rev-parse --abbrev-ref HEAD")
    git_remote_task = run_probe("git remote get-url origin")
    git_status_task = run_probe("git status --short")
    ls_task = run_probe("ls -F" if os.name != 'nt' else "dir /b")

    results = await asyncio.gather(
        kubectl_context_task,
        kubectl_ns_task,
        docker_info_task,
        docker_count_task,
        git_branch_task,
        git_remote_task,
        git_status_task,
        ls_task
    )

    info["tools"]["kubectl"] = {
        "context": results[0],
        "namespace": results[1]
    }
    
    # Process docker count for Windows/Linux
    d_count = results[3]
    if os.name == 'nt' and "Error" not in d_count:
        d_count = len(d_count.splitlines())

    info["tools"]["docker"] = {
        "status": "ready" if "Containers:" in results[2] else "not_running",
        "container_count": d_count if "Error" not in str(d_count) else 0
    }

    info["tools"]["git"] = {
        "branch": results[4],
        "remote": results[5],
        "status_summary": results[6]
    }

    # Proactive Workspace Context (Claude Eager Pattern)
    info["workspace"] = {
        "ls": results[7][:1000] if "Error" not in results[7] else "N/A" # Truncate for safety
    }

    return info

def get_env_hash(info: Dict[str, Any]) -> str:
    """Generate a stable hash of the environment state to detect drift."""
    import hashlib
    import json
    
    # We only hash stable fields that signal meaningful environment drift.
    # Avoid raw error strings (e.g. kubectl not found) which vary per call and cause false drift.
    volatile = {
        "kubectl_active": "Error" not in str(info.get("tools", {}).get("kubectl", {}).get("context", "Error")),
        "git_branch": info.get("tools", {}).get("git", {}).get("branch", "Error"),
        "shell": info.get("shell"),
        "cwd": info.get("cwd")
    }
    
    encoded = json.dumps(volatile, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
