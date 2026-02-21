# 🤖 DevOps Agent — Terminal-Native OS-Aware Orchestrator

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react)](https://reactjs.org/)
[![Bun](https://img.shields.io/badge/Bun-000000?style=flat&logo=bun)](https://bun.sh/)
[![LangGraph](https://img.shields.io/badge/LangGraph-24b-orange)](https://github.com/langchain-ai/langgraph)

A premium, state-of-the-art AI assistant designed for high-stakes DevOps engineering. Built on **LangGraph**, **GCC (Git Context Controller)**, and **Ollama**, this agent doesn't just chat; it executes, reasons, and remembers every action inside your terminal.

---

## 🌟 Key Features

*   **⌨️ Hybrid Mode Switching (Tab)**: Cycle between `AUTO`, `EXEC`, and `CHAT` modes using the `Tab` key on an empty input.
*   **⚡ Speculative Fast-Path**: A localized reflexive model (Router) intercepts simple requests for sub-500ms command generation, bypassing the heavy planner.
*   **💬 Conversational Bypass**: Purely informational queries are short-circuited to a dedicated `Chat` node for instant, non-executing responses.
*   **🧠 LangGraph Intelligence**: Multi-node reasoning with circuit breakers and environment drift detection.
*   **📜 GCC (Git Context Controller)**: Git-inspired project memory with branching lineage, logs, and findings.
*   **🛡️ Safety Gate**: Built-in human-in-the-loop approval system for all terminal commands.
*   **🔭 High-Fidelity Visualizer**: Interactive 3-column dashboard with a deterministic D3 hierarchical tree, live log streaming, and resilient parser hardening.
*   **⚡ AI Summoner (Ctrl+R)**: Seamlessly switch between Manual Shell and AI Chat without losing context.
*   **🖥️ Live Status HUD**: A dynamic status bar tracking reasoning nodes (`🧠 Planning`, `🛠️ Executing`, `💬 Conversing`).
*   **🧠 Intelligence Layer**: Hybrid memory using SQLite and LanceDB with "Platinum Envelope" structured ingestion.
*   **👁️ Observability**: Full local tracing via **Langfuse** with automated PII/Secret redaction.
*   **🛡️ Production-Grade Hardening**: Built-in protection against PII leaks, context window overflow, and malformed command output.

---

## 🏗️ Technical Architecture

```mermaid
graph TD
    User([User CLI]) --> Mode{Mode Controller}
    Mode -- Tab --> Interaction[Interaction Mode: AUTO/EXEC/CHAT]
    Interaction --> Router{Fast-Path Router}
    
    Router -- Simple/Manual --> Fast[Speculative Execution]
    Router -- Informational --> ChatNode[Chat Node]
    Router -- Complex --> Planner[Heavy Planner]

    subgraph "Agent Core"
        Planner --> Safety[Safety Gate]
        Safety -- Approved --> Executor[Executor Node]
        Executor --> Analyzer[Analyzer Node]
    end
    
    subgraph "Project Memory (GCC)"
        Interaction <--> GCC[GCC Storage]
        GCC --> Log[log.md - History]
        GCC --> Commit[commit.md - Milestones]
    end
    
    subgraph "Intelligence Layer"
        Interaction <--> Registry[Intelligence Registry]
        Registry <--> SQLite[(SQLite - Metadata)]
        Registry <--> LanceDB[(LanceDB - Vector)]
    end
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (managed via `uv`)
- **Ollama** (running `devstral:24b` or equivalent)
- **Bun** (for the visualizer)

### 2. Installation
```bash
# Clone the repo
git clone https://github.com/your-repo/devops-agent-cli.git
cd DevOpsAgent-cli

# Setup environment
cp .env.example .env
# Edit .env with your OLLAMA_HOST and LANGFUSE keys

# Install dependencies
uv sync
```

### 3. Usage
```bash
# Start a new session
uv run devops-agent new "Fix the slow response time in my local Kubernetes cluster"

# Enter manual mode (shell)
# [While in Agent Chat] Type 'manual'
# [While in Manual] Press Ctrl+R to return to AI

# Optional: Launch Observability Dashboard
docker-compose -f docker-compose.langfuse.yml up -d

# Launch Visualizer
uv run python src/cli/api.py
cd src/cli/visualizer && bun run dev
```

---

## 📄 Documentation

- [**ARCHITECTURE.md**](ARCHITECTURE.md) - Deep technical dive into the core engine.
- [**user_guide.md**](user_guide.md) - Step-by-step setup and feature usage.
- [**GCC_git.md**](GCC_git.md) - Understanding the Git Context Controller logic.
- [**Langfuse_use.md**](Langfuse_use.md) - Local Observability and Monitoring guide.

---

## 🧹 Maintenance
*   **Nuclear Reset**: Wipe all local state (SQLite, LanceDB, GCC) and start fresh:
    ```bash
    uv run devops-agent reset --nuclear
    ```

---

## ⚖️ License
MIT © 2026 DevOps Agent Team
