# 📜 GCC (Git Context Controller) Spec

GCC is the persistent memory system that gives the DevOps Agent its "Project Awareness." It is inspired by the Git DAG but optimized for AI-Human interaction tracks.

---

## 1. The Core Philosophy
Normal AI agents lose context when the process restarts. GCC solves this by treating the entire project history as a **Versioned Filesystem**. 

*   **Atomic**: Every action is logged immediately to disk.
*   **Human-Readable**: All history is stored in Markdown (`log.md`, `commit.md`).
*   **Branchable**: You can fork a session to explore a fix without breaking your main progress.

---

## 2. File Specifications

### `log.md` (The Linear Timeframe)
Stores the raw conversation and execution trace.
```markdown
## [HH:MM] AI
Reasoning: I need to check the pods.
Command: `kubectl get pods`

## [HH:MM] HUMAN [MANUAL]
ls -la
# This was run during a manual takeover
```

### `commit.md` (The Milestone Log)
Stores "Findings" and high-level results. 
```markdown
## 2026-02-20 10:00
- Finding: The ingress controller was misconfigured.
- Result: Updated helm chart values.
```

---

## 3. Key Functions

### `create_session(goal)`
Initializes a new folder with metadata and blank logs. Links the new node to a parent if it's a branch.

### `history sync`
A process that scans the user's manual shell history and appends it to `log.md` with a `[MANUAL]` tag. This ensures the AI is aware of what you did while "Chat" was closed.

### `activate_session(id)`
Updates the project's global `main.md` pointer. Future AI turns will now target this session's context.

---

## 4. Implementation Detail: Atomic Writes
To prevent data corruption during terminal crashes, GCC uses a **Shadow Copy** write strategy:
1. Write to a temporary `.tmp` file in the same directory.
2. Flush to disk.
3. Atomically rename to the target `file.md`.

This ensures that even a hard-kill of the process never leaves a partially-written log file.

### Worker Thread Safety (Phase 13)
Directory-intensive operations (like branching massive sessions) are performance-offloaded to dedicated worker threads using `asyncio.to_thread` to prevent terminal lag.

### Context Management
The GCC logic now includes an **Automatic Truncator** that keeps only the most relevant messages for the AI, ensuring even year-long sessions remain context-safe.

---

## 5. Branching & Lineage
GCC maintains a DAG (Directed Acyclic Graph) in the `sessions` table of the Intelligence DB. 
*   **Parent-Child**: When you fork, the new session stores its `parent_id`.
*   **Visualizing**: The D3 dashboard uses this lineage to render the tree.
