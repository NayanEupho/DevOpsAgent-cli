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
1.  **Chat Mode**: Type your requests. Responses stream in **token-by-token**.
2.  **Live Status**: Watch the status bar at the bottom (`🧠 Thinking`, `🛠️ Executing`) to see what the agent is doing.
3.  **Safety Gate**: If the agent proposes a sensitive command:
    *   **Approve**: Type `y` or say *"Sure, go for it"* / *"Approve"*.
    *   **Redirect**: Say *"Instead, try finding the pod first"* to pivot the AI's strategy.
    *   **Deny**: Type `n` or say *"Stop"* to cancel the plan.
4.  **Manual Mode**: Type `manual` in chat. You are dropped into a real shell.
5.  **AI Summoner**: While in Manual Mode, press **Ctrl+R** to instantly return to the AI.

### Advanced Multi-line Input (V0.2)
You can now write multi-paragraph queries:
- **Shift+Enter** / **Alt+Enter**: Add a new line.
- **Enter**: Submit your query to the agent.

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
*   **Branching Tree**: Click on any node to see what was happening in that session segment.
*   **Live Logs**: Watch the "Execution Log" update in real-time as you or the AI work.
*   **Theme Switch**: Toggle between Light and Dark modes in the top right.
*   **Session Switching**: Select an old session and click **"Set Active"** to resume work from that point in time.

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
To completely wipe the agent's memory and start from zero (DANGER: Cannot be undone):
```bash
# We recommend a manual purge for safety:
rm -rf ./.GCC
rm -rf ./.lancedb
rm agent_intelligence.db
```
*(Coming soon: `uv run devops-agent reset --nuclear`)*

---

## 5. Troubleshooting

*   **Ollama Timeout**: If the AI takes too long, check `uv run devops-agent check_health`.
*   **K8s/Docker Errors**: Ensure your terminal has the correct contexts active (`kubectl config current-context`).
*   **Ctrl+R Not Working**: Ensure you are running in a Windows Terminal or PowerShell environment.
