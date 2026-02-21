# 📖 DevOps Agent User Guide

This guide covers everything from initial setup to advanced session management and troubleshooting.

---

## 1. Installation & Setup

### Prerequisites
1.  **Download Ollama**: [ollama.com](https://ollama.com)
2.  **Pull the Model**:
    ```bash
    ollama pull devstral:24b
    ```
3.  **Install uv** (if not already present):
    ```bash
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### Configuration
1.  Navigate to the project directory.
2.  Edit `.env`:
    ```env
    OLLAMA_HOST="http://localhost:11434"
    OLLAMA_MODEL="devstral:24b"
    GCC_BASE_PATH="./.GCC"
    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY="your-key-here"
    ```

---

## 2. Using the CLI

### Start a New Task
```bash
uv run devops-agent new "Audit my local Docker containers for high resource usage"
```

### Resume an Existing Task
```bash
# List all sessions
uv run devops-agent list_sessions

# Continue the latest session
uv run devops-agent continue_session
```

### The Collaboration Loop
1.  **Interaction Modes (Tab)**: You can cycle through three modes by pressing **`Tab`** on an empty input line:
    *   **`(AUTO)`** (Blue): The default intelligent mode. Uses the Speculative Router to generated quick commands or routes to the Planner for complex tasks.
    *   **`(EXEC)`** (Red): Forced execution mode. Directly generates terminal commands without conversational pre-analysis.
    *   **`(CHAT)`** (Magenta): Information-only mode. Prevents accidental command execution; perfect for asking questions or explaining concepts.
2.  **Live Status**: Watch the status bar at the bottom (`🧠 Thinking`, `🛠️ Executing`, `💬 Conversing`) to see what the agent is doing.
3.  **Safety Gate**: If the agent proposes a sensitive command:
    *   **Approve**: Type `y` or say *"Sure, go for it"* / *"Approve"*.
    *   **Redirect**: Say *"Instead, try finding the pod first"* to pivot the AI's strategy.
    *   **Deny**: Type `n` or say *"Stop"* to cancel the plan.
4.  **Manual Mode**: Type `manual` in chat. You are dropped into a real shell.
5.  **AI Summoner**: While in Manual Mode, press **Ctrl+R** to instantly return to the AI.

### ⌨️ Multi-line Input Support
For complex, multi-paragraph instructions, use high-fidelity input:
*   **Shift+Enter** / **Alt+Enter** / **Ctrl+J**: Add a new line.
*   **Enter**: Submit your query to the agent.
*   *Note: Multi-line queries automatically route to the Planner node for deep reasoning.*

---

## 3. The Visualizer Dashboard

The Visualizer allows you to see the "Git Tree" of your work.

### Launching
1.  **Backend**: `uv run python src/cli/api.py`
2.  **Frontend**: 
    ```bash
    cd src/cli/visualizer
    bun run dev
    ```
3.  Open `http://localhost:5173` in your browser.

### Features
*   **Three-Column HUD**: Independently scrollable panels for Navigation, Logic Graph, and Details.
*   **Optimal Navigation**: Spacious Sidebar (`380px`) with multi-line text wrapping for long goal names.
*   **Intelligent Filtering**: Quickly find sessions using the "Today", "Active", or "Completed" pills.
*   **Deterministic Tree Graph**: View session lineage with clean Bezier connections and active-node "ripple" animations.
*   **Rich Telemetry**: Peek into the "Info" tab for session-specific metrics and environment info (OS/Shell) with improved label visibility.
*   **Secure Exports**: Download the full `log.md` or `commit.md` directly from the detail panel for offline auditing.

---

## 4. Maintenance & Resets

### Monitoring (LangSmith)
If `LANGSMITH_TRACING` is on, you can see deep traces of every reasoning step at [smith.langchain.com](https://smith.langchain.com).

### Deleting Sessions
Currently, sessions are stored in:
1.  **Filesystem**: `./.GCC/sessions/`
2.  **SQLite**: `agent_intelligence.db`
3.  **LanceDB**: `./.lancedb/`

### The "Nuclear Reset"
To completely wipe the agent's memory and start from zero (DANGER: Cannot be undone). This purges all session logs, SQLite metadata, and LanceDB vector memories.
```bash
uv run devops-agent reset --nuclear
```
You will be prompted with an interactive `y/n` confirmation before the wipe begins.

---

## 5. Troubleshooting

*   **Ollama Timeout**: If the AI takes too long, check `uv run devops-agent check_health`.
*   **K8s/Docker Errors**: Ensure your terminal has the correct contexts active (`kubectl config current-context`).
*   **Ctrl+R Not Working**: Ensure you are running in a Windows Terminal or PowerShell environment.
