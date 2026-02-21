# DevOps Agent — Product Requirements Document
**Version:** 3.0 | **Status:** Ready for Development | **Prepared for:** Antigravity | **Date:** February 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Scope](#3-goals--scope)
4. [System Architecture](#4-system-architecture)
5. [The Permission Model — How It Works](#5-the-permission-model--how-it-works)
6. [SKILL.md Permission System](#6-skillmd-permission-system)
7. [GCC Memory System](#7-gcc-memory-system)
8. [Session Management](#8-session-management)
9. [CLI Interface](#9-cli-interface)
10. [Permission Flow & Negotiation](#10-permission-flow--negotiation)
11. [Transparency & Explanation Engine](#11-transparency--explanation-engine)
12. [Technology Stack](#12-technology-stack)
13. [Configuration & Environment](#13-configuration--environment)
14. [Technical Requirements](#14-technical-requirements)
15. [User Stories](#15-user-stories)
16. [Phased Roadmap](#16-phased-roadmap)
17. [Success Metrics](#17-success-metrics)
18. [Appendix](#18-appendix)

---

## 1. Executive Summary

DevOps Agent is a single-user, terminal-native AI agent that accepts natural language commands and translates them into precise CLI operations across Docker, Kubernetes, and Git. It is built in Python on a universal CLI MCP (Model Context Protocol) foundation, powered by a local Ollama inference engine, governed by a SKILL.md permission tier system, and backed by a GCC (Git-Context-Controller) memory layer that persists every action, reasoning step, and outcome across sessions.

The agent operates transparently — announcing every command before execution, logging all reasoning in structured OTA (Observation–Thought–Action) format, and maintaining a navigable session history that both the agent and the user can read, search, and continue from at any time.

> **Core Design Philosophy**
> The agent is not a black box. Every decision has a paper trail. Every command has a reason. The user is always in control — no destructive action executes without explicit approval. Memory persists across sessions — the agent never forgets what it investigated, found, or decided.

---

## 2. Problem Statement

### 2.1 The Core Problem

Modern DevOps workflows require engineers to context-switch across multiple CLIs — kubectl, docker, git, helm — each with hundreds of subcommands and context-specific flags. This creates compounding friction:

- High cognitive load memorising exact syntax across tools under operational pressure
- Slow diagnostic workflows requiring manual command chaining and raw output interpretation
- No native explanation layer — understanding why a command is needed requires external documentation
- Session amnesia — closing a terminal erases all diagnostic context, forcing re-investigation from scratch
- Destructive operation risk — no safety layer prevents accidental `kubectl delete` in production

### 2.2 Why Existing Tools Fall Short

| Tool | Limitation | What We Do Differently |
|---|---|---|
| Raw CLI | No NL interface, no safety layer, no memory | Natural language + permission tiers + persistent GCC memory |
| Dashboards (Lens, k9s) | Click-based, not conversational, no explanation | Full conversational context with OTA reasoning trail |
| Custom scripts | Brittle, limited coverage, no explanation layer | Universal coverage via CLI MCP foundation |
| LLM chat (no tools) | Cannot execute, no real-time cluster state | Directly executes with live output and session memory |
| Claude Code / Gemini CLI | Session-scoped memory only, no structured logging | GCC persistent memory across sessions with user visibility |

---

## 3. Goals & Scope

### 3.1 Goals

- Enable natural language control of Docker, Kubernetes, and Git from a single terminal interface
- Provide full execution transparency — every command announced before running
- Enforce SKILL.md-driven permission tiers — auto, approval-required, and destructive
- Persist all agent reasoning, actions, and outcomes in GCC across sessions
- Give the user equal visibility into the GCC log — not just the agent
- Support session management — create, continue, delete, and archive sessions
- Provide an Ollama-style CLI interface with keyboard-driven mode switching
- Allow intelligent permission negotiation — alternatives on denial, arguments when necessary

### 3.2 Non-Goals (v1)

- Multi-user or team sharing — this is a single-user tool
- Web or GUI interface — terminal only
- Cloud infrastructure provisioning (Terraform, Pulumi, cloud CLIs)
- Cluster creation or kubeconfig management
- Real-time monitoring dashboards or alerting

---

## 4. System Architecture

### 4.1 Architectural Approach

The agent is built on a single universal CLI MCP server rather than per-command tool wrappers. This provides full CLI coverage on day one, minimal maintenance burden, and a clean extension path to new tools (Helm, Terraform, AWS CLI) by simply adding a new SKILL.md file.

> **Why CLI MCP Over Per-Command Wrappers**
>
> **Approach A (Per-command wrappers):** Weeks of upfront work, hundreds of handlers, constant maintenance as CLIs evolve, perpetual coverage gaps.
>
> **Approach B (CLI MCP — chosen):** One `run_command` tool, full coverage immediately, safety handled by SKILL.md + permission classifier. New tools added via config not code.

### 4.2 Component Map

| Component | Language | Responsibility |
|---|---|---|
| CLI MCP Server | Python | **Internal execution engine.** Exposes `run_command` tool, captures stdout/stderr/exit code, handles timeouts and real-time streaming to the agent core. Built with `mcp` SDK. |
| SKILL.md Parser | Python | Reads all skill definition files at startup, builds permission map. Using `pydantic` for schema validation. |
| Permission Classifier | Python | Deterministic rule-based gate. Intercepts every planned command before execution. |
| GCC Memory Layer | Python | Persistent versioned memory. Manages sessions, log.md, commit.md, metadata.yaml. |
| Session Manager | Python | Handles create, continue, list, delete, archive of sessions. |
| Ollama Client | Python | Wraps `ollama` Python SDK (async). All model config driven from `.env` via `pydantic-settings`. |
| Context Injector | Python | Injects cluster context, namespace, git branch, docker context, and last session state into agent system prompt. |
| Output Formatter | Python | Truncates and structures raw CLI output for LLM consumption. |
| Explanation Engine | Python | Generates contextual explanations using session log. |
| Permission Negotiator | Python | Surfaces alternatives or argues the case using session log as evidence. |
| NL Intent Parser | Python | Classifies user permission responses. Keyword-based matching. |
| Mode Controller | Python | Manages CHAT/MANUAL mode switching. **Smart Shell Detection:** Automatically spawns `powershell.exe` on Windows and `/bin/bash` on Linux for manual drops. |
| UI Logger | Python | Handles streaming output and beautiful terminal rendering using `Rich`. |

### 4.3 Execution Pipeline

Every agent action follows this exact sequence — no exceptions:

1. User submits natural language request in CHAT mode
2. Agent (LLM) decides what action is needed and which command to run
3. **Permission Classifier intercepts — checks command against SKILL.md rules**
4. Agent announces: "To perform this I will execute: `<command>`"
5. Auto-tier commands execute immediately. Approval-tier pauses for user input.
6. Output captured, structured, appended to session `log.md` as OTA entry
7. Agent synthesises response from output and accumulated session context
8. On explain request: Explanation Engine generates full context chain from GCC log

### 4.4 Why Latency Is Not a Concern in Python

A common question when choosing between Python and TypeScript for agent tooling is latency. For this project it is a non-issue:

| Source | % of Total Latency | Python Impact |
|---|---|---|
| LLM inference (Ollama) | ~95% | Zero — Ollama doesn't care what calls it |
| CLI command execution | ~4% | Zero — subprocess is subprocess |
| Application code | ~1% | Negligible — < 5ms for all file and classification ops |

Python's subprocess management and async I/O are well-suited to this use case — cleaner streaming output handling and more ergonomic file operations than the Node.js equivalent.

---

## 5. The Permission Model — How It Works

This section describes the most critical architectural decision in the system.

### 5.1 The Core Principle

The LLM decides **what** needs to happen. The SKILL.md classifier decides **whether it is allowed to happen**. These are two completely separate systems.

```
User: "delete the crashed pod"
         │
         ▼
    LLM decides action
    "I need to run: kubectl delete pod api-7d4f9"
         │
         ▼
    SKILL.md Classifier intercepts  ← deterministic code, not LLM
    checks: does "kubectl delete *" match any rule?
         │
         ├── Matches auto_execute?      → run immediately
         ├── Matches requires_approval? → pause, ask user
         ├── Matches destructive?       → pause, warn, ask user
         └── No match found?            → default to requires_approval
```

### 5.2 Why the Gate Must Be Outside the LLM

If the LLM were responsible for both deciding what to do AND deciding whether it is safe to do it, the safety layer could be reasoned around, confused by a bad prompt, or overridden by a clever user instruction. By making SKILL.md a hard code-level gate, safety is completely outside the LLM's influence. Even if the LLM plans a destructive command, it still goes through the classifier. The model cannot argue, reason, or prompt-inject its way past it.

```
LLM    = the brain   (decides what needs to happen)
SKILL.md = the gate  (deterministic code — decides if it's allowed)
MCP Server = the hands (actually executes the approved command)
```

### 5.3 The Classifier is the Safety Guarantee

The classifier is not a suggestion. It is enforced at the MCP server level — not in the UI layer. This means even if something bypasses the conversational interface, no unapproved command reaches the shell.

---

## 6. SKILL.md Permission System

### 6.1 Overview

Each supported CLI tool has a corresponding SKILL.md file in the `/skills` directory. The SKILL.md Parser reads all files at startup and builds an in-memory permission map. Every planned command is classified before execution — no exceptions. Unrecognised commands default to `requires_approval` — never auto-execute.

### 6.2 Directory Structure

```
/skills
├── kubectl/SKILL.md
├── docker/SKILL.md
├── git/SKILL.md
└── core/SKILL.md
```

### 6.3 SKILL.md File Format

```markdown
# kubectl Skills

## timeout
default: 30s
streaming_commands: ["kubectl logs -f", "kubectl get -w"]

## auto_execute
# Read-only operations. Execute immediately, no user prompt.
- kubectl get *
- kubectl describe *
- kubectl logs *
- kubectl top *
- kubectl explain *
- kubectl diff *
- kubectl version
- kubectl cluster-info

## requires_approval
# Mutating operations. Pause, show plan, await yes/no.
- kubectl apply *
- kubectl scale *
- kubectl rollout *
- kubectl edit *
- kubectl patch *
- kubectl label *
- kubectl annotate *
- kubectl exec *

## destructive
# Irreversible operations. Show consequences. Require explicit approval.
- kubectl delete *
- kubectl drain *
- kubectl cordon *
- kubectl uncordon *
- kubectl replace --force *

## context
# Used by explanation engine when generating contextual explanations.
When explaining commands, always relate to:
- cluster health and current observed state
- what changed vs commands earlier in this session
- what the next logical diagnostic or remediation step would be
- risk level and reversibility of the action
```

### 6.4 Permission Tiers

| Tier | Behaviour | Example Commands |
|---|---|---|
| ✅ Auto Execute | Executes immediately with announcement. No user input required. | `kubectl get *`, `kubectl logs *`, `git log *`, `git status`, `docker ps` |
| ⚠️ Requires Approval | Pauses. Shows command and consequence. Awaits user decision. | `kubectl apply *`, `kubectl scale *`, `git push`, `docker build`, `docker run` |
| 🔴 Destructive | Pauses. Shows command, explicit consequence warning, irreversibility notice. Awaits decision. | `kubectl delete *`, `kubectl drain *`, `git push --force`, `git reset --hard`, `docker rm -f` |

---

## 7. GCC Memory System

### 7.1 Overview

GCC (Git-Context-Controller) is the agent's persistent memory layer, inspired by the paper "Git Context Controller: Manage the Context of LLM-Based Agents Like Git" (Wu, 2025). It treats agent memory as a structured file system — navigable, persistent, and readable by both the agent and the user at any time.

GCC is not an internal implementation detail. It is a first-class product feature. The user can open any GCC file and read exactly what the agent was thinking, why it made every decision, and what it found. The agent reads the same files to resume intelligently after any break.

### 7.2 Shared Source of Truth

Both the user and the agent read and write to the same GCC files. Neither party is ever operating blind:

- **Agent reads GCC** to orient itself at session start, recall prior findings, and ground its explanations in actual history
- **User reads GCC** to understand what the agent did, why, and what it found — at any time, including after the session ends
- **Agent writes GCC** in structured OTA format after every action
- **User writes GCC** implicitly via MANUAL mode — every command run in manual mode is logged as a HUMAN entry

### 7.3 File System Structure

```
.GCC/
├── main.md                                      # Global index: all sessions, current goal, overall status
└── sessions/
    ├── session_001_2026-02-19_investigate-api-crash/
    │   ├── log.md                               # Full OTA trace: every command, output, reasoning
    │   ├── commit.md                            # Confirmed milestones and findings
    │   └── metadata.yaml                       # Machine-readable state (context, shell type, session IDs)
    ├── session_002_2026-02-20_fix-memory-limits/
    │   ├── log.md
    │   ├── commit.md
    │   └── metadata.yaml
    └── archived/                                # Soft-deleted sessions (recoverable)
        └── session_003_2026-02-18_test-session/
```

### 7.4 File Roles

| File | Contents & Purpose |
|---|---|
| `main.md` | Global project state. Lists all sessions with status, key findings, and links. Updated on session open, commit, and close. The bird's-eye view of everything ever done. |
| `log.md` | Append-only OTA trace. Every HUMAN and AI action logged with timestamp, reasoning, command, output, and inference. Never edited — only appended to. |
| `commit.md` | Milestone checkpoints. Each COMMIT appends: branch purpose, cumulative progress summary, and this commit's specific contribution. |
| `metadata.yaml` | Snapshot of environment at session start: active kube context, namespace, cluster name, git repo, current branch, docker context, running containers. |

### 7.5 GCC Commands

| Command | When Used & Effect |
|---|---|
| `COMMIT <summary>` | Agent identifies a confirmed milestone. Appends structured entry to commit.md. Optionally updates main.md. |
| `CONTEXT` | Called at session start. Returns project state and session list to orient agent. |
| `CONTEXT --session <id>` | Returns that session's commit.md summary and last 10 log entries. Used for intelligent resume. |
| `CONTEXT --log` | Returns last 20 lines of current session log.md. Used for recent action recall. |
| `CONTEXT --metadata` | Fetches metadata.yaml. Used to detect context drift between sessions. |
| `BRANCH <name>` | Explores alternative approach without affecting main session. Scaffolded in v1, UI-exposed in v2. |
| `MERGE <branch>` | Integrates branch conclusion back into main session. v2 feature. |
| `GRAPH` | **[NEW]** Renders a visual ASCII/Rich tree of session commits and branches, similar to a Git Graph. |

### 7.7 Visual History Graph
To provide VS Code-style visibility into the reasoning history, the agent supports a `GRAPH` view. This uses `Rich.Tree` to display:
- **Main Branch:** The primary reasoning path.
- **Side Branches:** Isolated explorations triggered by `BRANCH`.
- **Commits:** Milestones with short summaries.
- **Merge Points:** Where side-explorations were integrated.

### 7.6 OTA Log Format

The log.md uses a strict OTA (Observation–Thought–Action) format for AI entries. Human entries use a simpler format. This structure is readable by both humans and the agent as a re-ingestion source.

```markdown
## [14:32] HUMAN
kubectl get pods -n production

OUTPUT:
NAME          READY   STATUS             RESTARTS
api-7d4f9     0/1     CrashLoopBackOff   14

---

## [14:35] AI
OBSERVATION: api-7d4f9 has restarted 14 times in CrashLoopBackOff state.
             High restart count points to OOM, bad config, or failing health check.

THOUGHT: Need logs from the previous crashed container — current state won't show
         the failure reason. --previous flag pulls from the terminated container buffer.

PERMISSION: auto-execute (read-only per kubectl/SKILL.md)

ACTION: kubectl logs api-7d4f9 --previous -n production

OUTPUT:
java.lang.OutOfMemoryError: Java heap space
Killed

INFERENCE: OOMKilled confirmed. Memory limit is the constraint.
           Next logical step: check resource limits vs actual usage with kubectl top.

---

## [14:38] AI — COMMIT
MILESTONE: Root cause confirmed.
FINDING: Container OOMKilled. Memory limit set to 256Mi, actual usage peaks at 410Mi.
SAVED TO: commit.md entry #1

---

## [14:41] APPROVAL REQUEST
COMMAND: kubectl delete pod api-7d4f9 -n production
TIER: destructive
USER RESPONSE: "yes but explain what comes after"
USER DECISION: approved with explanation requested
ACTION EXECUTED: yes
RESULT: pod deleted, rescheduled in 8s, now Running
```

---

## 8. Session Management

### 8.1 What a Session Is

A session is a named, timestamped, goal-scoped work block. Each session has its own isolated GCC directory. Sessions are named with a goal slug so the history is immediately readable at a glance: `session_003_2026-02-21_deploy-memory-hotfix` tells you everything without opening the file.

### 8.2 Session Lifecycle

#### Creating a New Session

```
$ devops-agent new "investigate database connection timeouts"

  Suggested name: session_004_2026-02-21_investigate-db-timeouts
  Confirm name or rename? (press Enter to confirm)
  >

  ✓ Session created
  ✓ metadata.yaml snapshot taken:
    kube-context: prod-cluster / namespace: production
    git: main branch, 0 uncommitted changes
    docker: desktop context, 3 running containers

  AI: Starting session — I'll investigate the database connection
  timeouts. What symptoms are you seeing?
  >>>
```

#### Continuing a Session

```
$ devops-agent continue

  Recent sessions:
  [1] session_004  2026-02-21  investigate-db-timeouts      (in progress)
  [2] session_003  2026-02-21  deploy-memory-hotfix         (closed)
  [3] session_001  2026-02-19  investigate-api-crash        (closed)

  Which session? (1)
  >

  AI: Resuming session_004 — investigate-db-timeouts

  Last commit: 'Confirmed timeouts occurring every ~30s, pattern suggests
  connection pool exhaustion not network latency'
  Last action: kubectl describe deployment/api (saw pool size = 5)
  Next logical step: check db connection pool settings vs actual load

  Ready to continue.
  >>>
```

#### Listing Sessions

```
$ devops-agent sessions

  SESSION HISTORY
  ──────────────────────────────────────────────────────────────────
  #    Date         Goal                          Status   Commits
  004  2026-02-21   investigate-db-timeouts       active   2
  003  2026-02-21   deploy-memory-hotfix          closed   3
  002  2026-02-20   fix-memory-limits             closed   2
  001  2026-02-19   investigate-api-crash         closed   4
  ──────────────────────────────────────────────────────────────────
  archived: 1 session  (devops-agent sessions --archived to view)
```

#### Closing a Session (Ctrl+X)

```
  [Ctrl+X pressed]

  AI: Closing session_004 — investigate-db-timeouts

      Session summary:
      ✅ Commit 1: Confirmed timeout pattern — every ~30s, connection pool
      ✅ Commit 2: Root cause — pool size 5 vs peak load requiring 18
      ⚙️  Commands executed: 14 (11 agent / 3 manual)
      ⏱  Duration: 52 minutes

      Save summary to main.md? (y/n)
      > y

      ✓ Session closed and saved.
```

#### Deleting a Session

```
$ devops-agent delete session_003

  ⚠️  About to delete:
  session_003_2026-02-21_deploy-memory-hotfix

  Contents: 47 log entries, 3 commits, 1 metadata snapshot
  Last commit: 'Fix confirmed stable in production'

  This will move the session to .GCC/archived/ (recoverable).
  To permanently delete: devops-agent delete session_003 --permanent

  Confirm? (yes / no)
  > yes

  ✓ Session archived.
```

---

## 9. CLI Interface

### 9.1 Design Principles

The CLI is modelled after Ollama — minimal, clean, terminal-native. No web interface. The agent lives in the terminal and feels like it belongs there. Commands are short, output is structured, and keyboard shortcuts are intuitive.

### 9.2 CLI Commands

| Command | Description |
|---|---|
| `devops-agent` | Start agent in CHAT mode. Offers to resume last active session if one exists. |
| `devops-agent new "<goal>"` | Create and start a new session with the given goal description. |
| `devops-agent continue` | List recent sessions and resume selected one. |
| `devops-agent continue <session_id>` | Directly resume a specific session by ID. |
| `devops-agent sessions` | List all sessions with status, date, goal, and commit count. |
| `devops-agent sessions --archived` | List soft-deleted sessions. |
| `devops-agent delete <session_id>` | Soft-delete a session to archived folder. |
| `devops-agent delete <session_id> --permanent` | Permanently delete. Requires confirmation. |
| `devops-agent log` | Print current session's log.md to terminal. |
| `devops-agent log <session_id>` | Print a specific session's log.md to terminal. |
| `devops-agent context` | Show current session's GCC context summary. |
| `devops-agent --help` | Show all commands and keyboard shortcuts. |

### 9.3 Keyboard Shortcuts & Modes

| Shortcut | From | To | Effect |
|---|---|---|---|
| `Ctrl+D` | CHAT | MANUAL | Drop to raw shell. All commands logged as HUMAN entries in GCC. |
| `Ctrl+S` | MANUAL | CHAT | Return to agent. Agent reviews manual commands and offers analysis. |
| `Ctrl+X` | Any | EXIT | Close session with summary. Prompts to save to main.md. |
| `Ctrl+C` | Any | — | Cancel current running command. Does not exit session. |

#### CHAT Mode Prompt

```
  [session_004 · production · main] >>>
```

The prompt shows: session ID, active kube namespace, and git branch. Always contextually aware.

#### MANUAL Mode Banner

```
  ─────────────────────────────────────────────────────
    MANUAL MODE  ·  session_004  ·  commands are logged
    Press Ctrl+S to return to agent
  ─────────────────────────────────────────────────────
  $
```

#### Return to CHAT — Agent Reviews Manual Actions

```
  $ kubectl get pods -n production
  $ kubectl describe pod api-7d4f9
  $ [Ctrl+S]

  ─────────────────────────────────────────────────────
    CHAT MODE  ·  agent reviewing your manual commands
  ─────────────────────────────────────────────────────

  AI: I see you ran kubectl get pods and kubectl describe
  while in manual mode. I've logged both to the session.

  The describe output shows the pod's last restart was due
  to OOMKilled — aligns with our commit from earlier.
  Want me to proceed with patching the memory limit?

  [session_004 · production · main] >>>
```

---

## 10. Permission Flow & Negotiation

### 10.1 Approval Prompt Design

```
  ┌──────────────────────────────────────────────────────────────┐
  │  🔴  APPROVAL REQUIRED — DESTRUCTIVE OPERATION              │
  │                                                              │
  │  Command:    kubectl delete pod api-7d4f9 -n production     │
  │  Tier:       Destructive                                    │
  │  Effect:     Permanently removes the pod. Kubernetes will   │
  │              reschedule a new one from the deployment.      │
  │  Reversible: No — pod is deleted immediately               │
  │                                                              │
  │  y / yes / approve     — execute                           │
  │  n / no / skip         — decline                           │
  │  why                   — explain the reasoning             │
  │  plan                  — show what comes after this        │
  │  history               — what we've done so far            │
  └──────────────────────────────────────────────────────────────┘
  >>>
```

### 10.2 User Response Types

| Intent | Example Inputs | Agent Behaviour |
|---|---|---|
| Approve | `y`, `yes`, `ok`, `sure`, `go ahead`, `do it`, `approved`, `looks good`, `yep` | Executes immediately. Logs decision to GCC. |
| Deny | `n`, `no`, `skip`, `stop`, `don't`, `hold`, `wait`, `cancel`, `abort` | Does not execute. Triggers negotiation flow. |
| Approve + Explain | `yes but why`, `approve explain it`, `ok walk me through this`, `sure what's the plan` | Delivers full explanation first, then executes. |
| Explain Only | `why`, `what does this do`, `explain`, `what's the reasoning` | Answers fully. Re-presents approval prompt. Does not execute. |
| History | `what have we done`, `history`, `show session so far` | Summarises GCC log for current session. Re-presents prompt. |
| Plan | `what comes after`, `what's the plan`, `next steps` | Shows intended command sequence after this one. Re-presents prompt. |
| Ambiguous | Anything that does not match above patterns | Treats as a question. Answers. Re-presents prompt. |

### 10.3 When User Says No — Negotiation Flow

#### Scenario A: Alternatives Exist

```
  >>> no

  AI: Understood. Let me find other ways to achieve this...

  Goal: Clear the stuck pod and get a fresh one running.

  Alternative 1 — Safer (Rolling restart):
  kubectl rollout restart deployment/api -n production
  → Less aggressive. Triggers rolling pod replacement.
  → Slower but preserves current pod logs until new one is ready.

  Alternative 2 — Safest (Scale down/up):
  kubectl scale deployment/api --replicas=0 -n production
  kubectl scale deployment/api --replicas=3 -n production
  → Full control over timing. ~60s longer.

  Which would you prefer?
  (original / alt1 / alt2 / skip)
  >>>
```

#### Scenario B: No Viable Alternatives — Agent Makes Its Case

```
  >>> no

  AI: I understand the hesitation. Let me be transparent about
  why this is the only viable path here.

  Why alternatives won't work in this specific case:

  ✗ kubectl rollout restart — already tried at 14:32 (session log).
    Pod is stuck in Terminating state, not responding to rollout signals.

  ✗ Scale down/up — deployment controller is also stuck. The Terminating
    pod is blocking the replica count. No new pods will schedule.

  ✗ Waiting — pod has been in Terminating for 18 minutes. Default grace
    period is 30s. This pod will not self-resolve.

  The hard delete forces the kubelet to release the pod, unblocking
  the deployment controller. A fresh pod will schedule in ~8 seconds.

  Your call — still your decision to make.

  (y to execute / n to skip and move on)
  >>>
```

> **Design Rule:** The agent makes its case exactly once. It does not loop, repeat arguments, or increase pressure. After one argument, the user's decision is final and respected without further comment.

---

## 11. Transparency & Explanation Engine

### 11.1 Command Announcement

Before executing any command — regardless of permission tier — the agent announces its intention. Non-negotiable, cannot be disabled.

```
  AI: To investigate the crash I will execute:
  →  kubectl logs api-7d4f9 --previous -n production

      Reason: --previous flag retrieves logs from the last terminated
      container instance, which is where the crash error will appear.

      [auto-executing — read-only per kubectl/SKILL.md]
```

### 11.2 Contextual Explanation — Four Dimensions

When a user asks for an explanation, the Explanation Engine generates a structured response covering:

| Dimension | What the Agent Covers |
|---|---|
| What it does | Plain English description of the command's mechanism and immediate effect. |
| Why now | How this relates to findings from earlier in this session. References specific GCC log entries and commits. |
| What it won't solve | Honest limitations. Is this diagnostic or a fix? What could still be wrong? |
| What comes next | The intended sequence of follow-up commands and what each is trying to confirm. |

```
  User: yes but explain what this does and what comes after

  AI: Here's the full picture before I execute:

  WHAT THIS DOES:
  kubectl delete pod sends a SIGTERM to the pod and removes it from
  the API server. Kubernetes will immediately reschedule a fresh pod
  from the deployment spec.

  WHY WE'RE HERE (session context):
  → 14:32 — Confirmed 14 restarts, CrashLoopBackOff
  → 14:35 — OOMKilled confirmed via --previous logs (Commit #1)
  → 14:41 — You confirmed 401Mi usage vs 256Mi limit (manual mode)
  → 14:47 — Memory limit patched to 512Mi (you approved)
  → 14:52 — rollout restart issued but pod stuck in Terminating

  WHY THIS IS THE ONLY PATH:
  The Terminating pod is blocking the deployment controller.
  The hard delete forces the kubelet to release it.

  WHAT COMES NEXT:
  1. kubectl get pods -w     — watch new pod come up
  2. kubectl top pods        — confirm memory stable under 512Mi
  3. COMMIT if stable for 5+ mins

  Executing now...
  →  kubectl delete pod api-7d4f9 -n production --grace-period=0 --force
```

---

## 12. Technology Stack

### 12.1 Core Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.12+ | Modern async support, type hinting, and performance improvements. |
| Package Manager | `uv` | Extreme speed, unified tool management, and deterministic builds. |
| CLI Framework | `Typer` | Type-safe, modern CLI generation with excellent help text and validation. |
| LLM Integration | `ollama-python` | Official async client for local Ollama inference. |
| Terminal UI | `Rich` | High-fidelity terminal formatting, tables, progress bars, and streaming token support. |
| MCP SDK | `mcp` | Official MCP Python SDK for tool and resource management. |
| Configuration | `pydantic-settings` | Type-safe environment variable management and validation. |
| Async Loop | `asyncio` | Native Python concurrency for non-blocking I/O and streaming. |
| Testing | `pytest` | Industry standard testing framework. |
| Formatting/Linting | `Ruff` | Fast, all-in-one Python linter and formatter. |

### 12.2 Recommended Model

The agent runs on a local Ollama instance. The model is fully configurable via `.env`.

| Model | VRAM | Best For |
|---|---|---|
| `devstral:24b` | ~26GB | **Recommended** — Purpose-built for agentic CLI use and precise tool calling |
| `qwen3:32b` (Q8) | ~36GB | Balanced alternative — excellent reasoning + speed |
| `qwen3:72b` (Q4_K_M) | ~48GB | Maximum quality, slower inference |
| `qwen3:14b` (Q8) | ~16GB | Constrained hardware |
| `qwen3:8b` | ~8GB | Minimum viable |

> Validated on A100 80GB. `qwen3:32b` at Q8 runs comfortably with headroom for large GCC context windows.

---

## 13. Configuration & Environment

### 13.1 `.env` File

```bash
# ─── Ollama Configuration ─────────────────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=devstral:24b

# ─── Model Parameters ─────────────────────────────────
OLLAMA_TEMPERATURE=0.3
OLLAMA_CONTEXT_SIZE=32768
OLLAMA_TIMEOUT=120

# ─── Agent Configuration ──────────────────────────────
AGENT_NAME=devops-agent
GCC_BASE_PATH=./.GCC
SKILLS_PATH=./skills
LOG_LEVEL=info
```

Temperature is set to 0.3 intentionally — deterministic, precise command generation is preferred over creative variation.

### 13.2 `config.py`

```python
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class OllamaConfig:
    host: str         = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model: str        = os.getenv("OLLAMA_MODEL", "qwen3:32b")
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
    context_size: int  = int(os.getenv("OLLAMA_CONTEXT_SIZE", "32768"))
    timeout: int       = int(os.getenv("OLLAMA_TIMEOUT", "120"))

@dataclass
class AgentConfig:
    name: str         = os.getenv("AGENT_NAME", "devops-agent")
    gcc_base_path: str = os.getenv("GCC_BASE_PATH", "./.GCC")
    skills_path: str   = os.getenv("SKILLS_PATH", "./skills")
    log_level: str     = os.getenv("LOG_LEVEL", "info")

@dataclass
class Config:
    ollama: OllamaConfig = OllamaConfig()
    agent: AgentConfig   = AgentConfig()

config = Config()
```

### 13.3 Swapping Models

To switch models — change one line in `.env`, restart the agent:

```bash
# Switch to devstral
OLLAMA_MODEL=devstral:24b

# Point to remote Ollama instance
OLLAMA_HOST=http://192.168.1.100:11434
OLLAMA_MODEL=qwen3:72b
```

No code changes. No recompile.

### 13.4 `.env.example` — Commit This to the Repo

```bash
# Copy to .env and configure
# cp .env.example .env

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=devstral:24b
OLLAMA_TEMPERATURE=0.3
OLLAMA_CONTEXT_SIZE=32768
OLLAMA_TIMEOUT=120

AGENT_NAME=devops-agent
GCC_BASE_PATH=./.GCC
SKILLS_PATH=./skills
LOG_LEVEL=info
```

Commit `.env.example`. Add `.env` to `.gitignore`.

### 13.5 Project Structure

```
devops-agent/
├── .env                          ← your config (gitignored)
├── .env.example                  ← committed template
├── pyproject.toml
├── src/
│   ├── config.py                 ← reads .env, single source of truth
│   ├── ollama_client.py          ← Ollama SDK wrapper + health check
│   ├── mcp/
│   │   └── server.py             ← CLI MCP run_command tool
│   ├── skills/
│   │   └── parser.py             ← SKILL.md parser + permission classifier
│   ├── gcc/
│   │   ├── session.py            ← session create/continue/close/delete
│   │   ├── log.py                ← OTA log writer
│   │   └── context.py            ← CONTEXT retrieval commands
│   ├── agent/
│   │   ├── core.py               ← main agent loop
│   │   ├── explanation.py        ← explanation engine
│   │   ├── negotiator.py         ← alternatives + argument logic
│   │   └── intent_parser.py      ← NL approval response classifier
│   └── cli/
│       ├── main.py               ← CLI entry point (click/typer)
│       └── mode_controller.py    ← CHAT/MANUAL mode switching
└── skills/
    ├── kubectl/SKILL.md
    ├── docker/SKILL.md
    ├── git/SKILL.md
    └── core/SKILL.md
```

---

## 14. Technical Requirements

### 14.1 CLI MCP Server

- Single tool exposed: `run_command(cmd: str, context: str = None)`
- Returns structured dict: `{ stdout, stderr, exit_code, duration, command }`
- Configurable timeout per command (default 30s, overridable per SKILL.md)
- Streaming support for long-running commands (`kubectl logs -f`, `docker build`, `git clone`)
- Command never executes without passing through Permission Classifier first — enforced at server level not UI level

### 14.2 SKILL.md Parser & Permission Classifier

- Reads all `/skills/**/SKILL.md` files at agent startup
- Builds prefix map for O(1) permission tier lookup with glob support (`kubectl delete *`)
- Hot-reloads on file change without agent restart
- Unrecognised commands default to `requires_approval` — never auto-execute
- Classifier is deterministic rule-based code — completely outside LLM influence
- Parser errors surface clearly — agent does not silently fall back to permissive behaviour

### 14.3 GCC File System

- All GCC files are plain UTF-8 text — readable in any text editor
- `log.md` is append-only — never edited, only appended to
- File writes are atomic — partial writes on crash must not corrupt existing log entries
- Session directory names: `session_NNN_YYYY-MM-DD_goal-slug`
- Archived sessions moved to `.GCC/archived/` — never silently deleted
- `main.md` updated on: session open, COMMIT, session close

### 14.4 Ollama Client

- Wraps official `ollama` Python SDK
- All model parameters driven from `config.py` — no hardcoded values anywhere
- Health check on startup: verifies host reachable and specified model is available
- Graceful error if model not found — lists available models and exits cleanly

### 14.5 NL Intent Parser

- Classifies permission responses: `APPROVE / DENY / EXPLAIN / APPROVE_EXPLAIN / AMBIGUOUS`
- Keyword-based matching — no external NLP dependency required for v1
- Ambiguous responses treated as questions — agent answers and re-presents prompt
- Keyword lists defined in config, not hardcoded

### 14.6 Output Handling

- Outputs exceeding 4,000 tokens truncated with clear notice and summary
- Structured parsing for common formats: `kubectl -o json`, `git log --format`, `docker inspect`
- Streaming output displayed in real-time; full output captured to GCC log
- AI responses MUST stream tokens to the terminal in real-time (Ollama-style)
- `stderr` and `stdout` clearly differentiated in both display and log

### 14.7 Safety Requirements

- No command executes without permission classifier evaluation — enforced in MCP server
- Destructive commands require explicit string approval
- All commands, approvals, denials, and negotiation written to immutable GCC log
- Agent cannot modify its own SKILL.md files at runtime
- Session delete always soft-deletes first — permanent delete requires `--permanent` flag and confirmation
- **Binary Path Resolution:** The MCP server MUST resolve the absolute path of every binary before execution to prevent execution of malicious local shell aliases.

---

## 14.8 Resilience & Edge Case Handling

| Edge Case | Requirement |
|---|---|
| **Output Flooding** | For outputs > 4,000 tokens, the agent MUST truncate and trigger a "Summary Loop" or use a dedicated utility to extract key log lines/errors before re-ingestion. |
| **Environment Drift** | Upon returning from MANUAL mode (Ctrl+S), the agent MUST run internal context probes (`git branch`, `kubectl config view --minify`) to sync its state with any user changes. |
| **Hanging Commands** | The MCP server MUST detect when a command is waiting for user input (`stdin`). If detected outside of intentional interactive mode, it MUST time out or alert the user to use MANUAL mode. |
| **Data Integrity** | All writes to `.GCC/` MUST be atomic (temporary file write + atomic rename) to prevent history corruption during crashes or system power loss. |
| **Zombied Processes** | Every command MUST be spawned in a unique process group; `Ctrl+C` MUST terminate the entire group to ensure no orphan background tasks persist. |

---

## 15. User Stories

| # | As a user I want to... | Acceptance Criteria |
|---|---|---|
| 1 | Say what I want in plain English and have the agent figure out the commands | Agent generates correct commands for kubectl, docker, and git requests without requiring CLI syntax from user |
| 2 | See the exact command before it runs every time | Every command announced with reason before execution. No silent execution ever. |
| 3 | Be protected from accidental destructive operations | All destructive commands pause for explicit approval. No destructive command auto-executes. |
| 4 | Understand what the agent is doing and why at every step | OTA log written to session log.md in plain English for every AI action. User can read it at any time. |
| 5 | Ask why before approving a command and get a full contextual explanation | Explain response covers: what it does, why now (session context), limitations, and what comes next. |
| 6 | Drop to manual shell without losing session context | Ctrl+D enters MANUAL mode. All manual commands logged as HUMAN entries in GCC with full output. |
| 7 | Return to agent after manual work and have it aware of what I did | Ctrl+S returns to CHAT. Agent reads manual entries and offers analysis before resuming. |
| 8 | Resume a session days later and have the agent know exactly where we left off | `devops-agent continue` loads last commit and recent log entries. Agent provides clear resumption summary. |
| 9 | Create named sessions with clear goals | Sessions created with goal-slug names. Name proposed by agent, user can rename before confirming. |
| 10 | Delete sessions I no longer need | Delete soft-archives to `.GCC/archived/`. Permanent delete requires `--permanent` flag and confirmation. |
| 11 | Have the agent try alternatives when I say no | On denial: agent checks for alternatives and presents them. If none, makes one clear argument. Never pressures twice. |
| 12 | View the full history of what was done in a session | `devops-agent log` prints full log.md. In-session 'history' command shows session summary. |
| 13 | Close a session cleanly with a summary | Ctrl+X triggers session close flow with summary of commits, commands, and duration. |
| 14 | Use natural language for approval — not just y/n | All natural language approval variants recognised. Ambiguous input treated as question not rejection. |
| 15 | Have the agent save confirmed findings as milestones | Agent calls COMMIT when a significant finding is confirmed. Commit saved to commit.md and shown to user. |
| 16 | Change the AI model or Ollama host without touching code | Model and host configurable via .env only. One line change, restart agent. |

---

## 16. Phased Roadmap

| Phase | Timeline | Deliverables |
|---|---|---|
| Phase 1 | Week 1–2 | Foundation: Python project setup, .env config module, Ollama client with health check, CLI MCP server (`run_command`), SKILL.md parser and permission classifier, kubectl and docker support, command announcement on every execution |
| Phase 2 | Week 2–3 | GCC Core: Session create/continue/close, log.md OTA logging (AI entries), commit.md milestone checkpoints, metadata.yaml snapshots, main.md global index, CONTEXT retrieval at session startup |
| Phase 3 | Week 3–4 | User Experience: Git support, MANUAL mode (Ctrl+D/S), HUMAN log entries from manual commands, NL intent parser for approvals, explanation engine (4-dimension responses), Ollama-style CLI interface |
| Phase 4 | Week 4–5 | Session Management: Session list/delete/archive, continue with resume summary, close with Ctrl+X summary, soft-delete with `--permanent` flag, session naming flow |
| Phase 5 | Week 5–6 | Negotiation & Polish: Alternatives on denial, agent argument when no alternatives, streaming output support, output truncation with summaries, hot-reload SKILL.md, full audit log integrity |
| Phase 6 | Week 6–7 | Intelligence Layer: SQLite session tracking, LanceDB semantic vector search, "Platinum Envelope" structured ingestion, Shadow Indexing background tasks |
| Phase 7 | Week 7–8 | Advanced Extensions: Helm support, Session Branch & Merge (lineage tracking), Parent-Child Session forks, Professional Markdown Reporting engine |
| Phase 8 | Week 8–9 | Observability: LangSmith integration, PII/Secret Redaction layer, Session-correlated tracing, Performance monitoring |
| Phase 9 | Week 9–10 | Visualization: D3.js Session Tree, FastAPI bridge, React/Bun Dashboard, Light/Dark mode themes |
| Phase 10 | Week 10–11 | Collaboration: AI Summoner (Ctrl+R), Handover Reconciliation, Context Recap on resume, Manual Action Awareness |
| Phase 11 | Week 11–12 | Documentation: Complete technical spec overhaul, ARCHITECTURE.md, user_guide.md, and advanced usage guides |
| Phase 12 | Week 12–13 | CLI UX: Ollama-style streaming (astream_events), Live Status HUD, Natural Language redirection support |
| Phase 13 | Week 13–14 | **Audit & Hardening**: Professional PII masking (B64/Private Keys), Context Truncation utility, Async thread-safety, Binary decoding resilience |
| Phase 14 | Week 14–15 | **Advanced Input**: Multi-line query support (Shift+Enter), Professional prompt session, line continuation UI |

---

## 17. Success Metrics

| Metric | Target (v1) | How Measured | Why It Matters |
|---|---|---|---|
| Command intent accuracy | >90% | Manual test suite of 50 NL commands per tool | Core value proposition of NL interface |
| Destructive ops without approval | 0 | Automated safety test suite | Non-negotiable safety requirement |
| Explanation usefulness | >4/5 rating | Self-review of 20 explanation responses | Key differentiator vs raw CLI |
| Session resume accuracy | >85% | Resume 10 sessions, verify context recall | Validates GCC memory approach |
| Time to first working command | < 2 minutes from install | Fresh install timing test | Developer onboarding friction |
| Manual mode log completeness | 100% of commands logged | Automated verification of HUMAN entries | Audit trail integrity |
| NL approval recognition rate | >95% | Test suite of 40 approval phrase variants | Validates intent parser |
| Model swap time | < 30 seconds | Change .env, restart, verify working | Validates modular config |

---

## 18. Appendix

### 18.1 Complete SKILL.md Files

#### docker/SKILL.md

```markdown
# docker Skills

## auto_execute
- docker ps *
- docker images *
- docker inspect *
- docker logs *
- docker stats *
- docker version
- docker info
- docker network ls
- docker volume ls

## requires_approval
- docker build *
- docker run *
- docker start *
- docker stop *
- docker restart *
- docker pull *
- docker push *
- docker tag *
- docker network create *
- docker volume create *

## destructive
- docker rm *
- docker rmi *
- docker system prune *
- docker volume rm *
- docker network rm *
- docker kill *
```

#### git/SKILL.md

```markdown
# git Skills

## auto_execute
- git log *
- git status *
- git diff *
- git show *
- git branch *
- git remote *
- git fetch --dry-run *
- git stash list

## requires_approval
- git add *
- git commit *
- git checkout *
- git switch *
- git merge *
- git rebase *
- git push *
- git pull *
- git stash *
- git tag *

## destructive
- git push --force *
- git push --force-with-lease *
- git reset --hard *
- git clean -f *
- git branch -D *
- git rebase --onto *
```

### 18.2 main.md Format

```markdown
# DevOps Agent — Project Memory

## Active Session
→ session_004_2026-02-21_investigate-db-timeouts (in progress)
   Started: 2026-02-21 09:14
   Last commit: 'Connection pool exhaustion confirmed, pool size 5 vs peak 18'

## Session History

| Session | Date       | Goal                      | Status | Commits | Key Finding              |
|---------|------------|---------------------------|--------|---------|--------------------------|
| 003     | 2026-02-21 | deploy-memory-hotfix      | closed | 3       | Fix stable in prod       |
| 002     | 2026-02-20 | fix-memory-limits         | closed | 2       | 512Mi confirmed staging  |
| 001     | 2026-02-19 | investigate-api-crash     | closed | 4       | OOMKilled root cause     |
```

### 18.3 Keyboard Shortcut Reference

| Shortcut | Action |
|---|---|
| `Ctrl+D` | Enter MANUAL mode — drop to raw shell, commands logged as HUMAN entries |
| `Ctrl+S` | Return to CHAT mode — agent reviews manual commands and resumes |
| `Ctrl+X` | Close session — shows summary, prompts to save to main.md, exits |
| `Ctrl+C` | Cancel current running command — does not exit session or change mode |

### 18.4 NL Intent Parser — Keyword Reference

| Intent | Keywords |
|---|---|
| APPROVE | `y`, `yes`, `ok`, `sure`, `go`, `do it`, `approved`, `looks good`, `go ahead`, `execute`, `run it`, `confirm`, `agreed`, `yep`, `yup` |
| DENY | `n`, `no`, `skip`, `stop`, `don't`, `hold`, `wait`, `cancel`, `abort`, `not yet` |
| EXPLAIN | `why`, `explain`, `what does`, `how does`, `reason`, `tell me`, `walk me through`, `what's the plan`, `what did we do` |
| APPROVE + EXPLAIN | Any APPROVE keyword + any EXPLAIN keyword in the same message |
| AMBIGUOUS | Anything that does not clearly match the above — treated as a question |

---

*DevOps Agent PRD v3.0 · Prepared for Antigravity · Confidential · February 2026*
