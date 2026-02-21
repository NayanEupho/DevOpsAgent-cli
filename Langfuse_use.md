# 🔭 Langfuse & Observability (Local-First)

The DevOps Agent is "Production-Traceable" through deep integration with **Langfuse**. Unlike cloud-based solutions, this is a **self-hosted** observability stack.

---

## 1. Why Langfuse?
DevOps tasks are complex and involve sensitive data. Langfuse provides local-first monitoring:
*   **Call Graphs**: See the exact sequence from Planner to Safety to Executor on your local network.
*   **Latency Analysis**: Identify if Ollama or the local Shell is the bottleneck without internet jitter.
*   **Token Usage**: Track context bloat per session.
*   **Feedback Scores**: Automatically score agent turns (Approval = 1.0, Denial = 0.0) for future fine-tuning.

---

## 2. The Tracing Pipeline

Every agent turn emits a trace with the following structure:
1.  **Metadata**: (Session ID, OS, Shell, Goal).
2.  **Node: Prober**: Trace of environment discovery.
3.  **Node: Planner**: Detailed input (System Prompt + History) and AI response.
4.  **Node: Executor**: The raw command and its multi-line output.
5.  **Scores**: Automated "user-approval" scores attached to each trace.

---

## 3. Security: The Redaction Layer
Since DevOps work involves secrets, we've implemented a **Safety Interceptor**.

*   **Middleware**: Before a trace is sent to the local DB, it passes through `ObservabilityService`.
*   **Scrubbing**: Any string matching common API key patterns or `PASSWORD=` fields is masked with `[REDACTED]`.
*   **Expert Secret Masking**: The redactor handles multi-line **Private Keys**, large **Base64-encoded Kubeconfigs**, and environment variable patterns.
*   **Local First**: Traces are asynchronous. If the Langfuse Docker is down, the agent remains fully functional (No-Op Fallback).

---

## 4. Configuring Langfuse
1.  Start the local stack:
    ```bash
    docker-compose -f docker-compose.langfuse.yml up -d
    ```
2.  Set the following in `.env`:
    ```env
    LANGFUSE_PUBLIC_KEY="pk-lf-..."
    LANGFUSE_SECRET_KEY="sk-lf-..."
    LANGFUSE_HOST="http://localhost:3000"
    ```

---

## 6. Performance Impact: Enabled vs. Disabled

While Langfuse is extremely fast, there is a minor cost to maintaining a full audit trail.

| Metric | Observability: OFF | Observability: ON (Local) |
| :--- | :--- | :--- |
| **Startup Overhead** | 0ms | ~150ms (Module loading) |
| **Step Latency** | Base | +5ms to +20ms (PII Redaction) |
| **Memory Usage** | Minimal | +20MB to +50MB (Trace buffering) |
| **CPU Impact** | Idle | Peak spikes during log scrubbing |
| **Safety / Debug** | Blind Execution | **Full Reasoning Transparency** |

> [!TIP]
> **When to Disable?**
> If you are running thousands of automated batch operations where speed is the only priority and you don't need audit logs, set `LANGFUSE_PUBLIC_KEY=""` in `.env` to trigger the No-Op fallback.
