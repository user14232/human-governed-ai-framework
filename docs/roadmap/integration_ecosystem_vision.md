> **Future Feature — Not part of the MVP runtime.**
> This document describes a post-MVP integration ecosystem vision. None of the integrations described here are implemented in the current runtime. See `docs/roadmap/future_features.md` for the full roadmap inventory.

# DevOS Integration Ecosystem Vision (Future Feature)

**Document type**: Roadmap reference
**Status**: Post-MVP design; informative only
**Date**: 2026-03-15

---

## 1. Overview

The long-term DevOS ecosystem positions DevOS as the **governance orchestration layer** over a broad set of external development tools.

In this model, DevOS orchestrates workflows and artifacts across:

- Planning tools (issue trackers, project management systems)
- Agent frameworks (AI-backed agents, local LLM runtimes)
- Engineering tools (Git, CI systems, IDEs)
- Observability surfaces (dashboards, notification systems)

DevOS governs the engineering process through artifacts and workflow state. External tools serve as interfaces, execution engines, or output consumers. DevOS does not replace any of them.

---

## 2. Architectural Principle

The governing rule for all integrations:

> DevOS must never depend on external system state. The run directory is always the authoritative state. External tools are mirrors, not sources.

All integrations follow a one-directional model:

```
External Tools
  (Planning systems / SCM platforms / CI systems)
         ↓
Integration Layer
  (read-only adapters / event consumers / artifact converters)
         ↓
DevOS Governance Kernel
  (runs / artifacts / decisions / events)
```

External tools may provide input to DevOS (via `change_intent.yaml`). External tools may read DevOS output (via run directory and event log). External tools may never write to run state directly or trigger workflow transitions.

---

## 3. Planning System Integrations

Planning tools provide the work items that DevOS governs.

### Integration model

```
Planning System
  (gstack / Linear / GitHub Issues / any task system)
         ↓
Adapter
  (task → change_intent.yaml converter)
         ↓
change_intent.yaml
         ↓
DevOS run initialization
```

### Target planning systems

| System | Integration type |
| --- | --- |
| gstack | Native integration target; task export to `change_intent.yaml` |
| Linear | Task-to-intent converter via Linear API |
| GitHub Issues | Issue-to-intent converter via GitHub API |
| Local YAML files | Already supported in MVP (manual authoring) |

The `change_intent.yaml` schema is fixed and version-controlled. Planning adapters must conform to it. No planning system-specific logic enters the DevOS kernel.

### Bidirectional state mirroring (optional)

DevOS run state may be projected back into planning tools for visibility. Example:

| DevOS event | Planning tool action |
| --- | --- |
| `run.started` | Issue status → "In Progress" |
| `workflow.transition_completed` (REVIEWING) | Issue status → "In Review" |
| `run.completed` (ACCEPTED) | Issue status → "Done" |
| `run.completed` (FAILED) | Issue status → "Blocked" |

This mirroring is a projection only. Planning tools never become authoritative over run state.

---

## 4. Agent Framework Integrations

Agent frameworks implement DevOS agent contracts.

### Integration model

```
DevOS agent contract
  (framework/agents/<role>.md)
         ↓
AgentAdapter
  (project-level implementation)
         ↓
External agent framework
  (gstack agents / local LLM agents / Cursor agents)
         ↓
Artifact output
         ↓
DevOS gate evaluation
```

### Target agent frameworks

| Framework | Notes |
| --- | --- |
| gstack agents | Primary integration target; structured inputs/outputs align with DevOS artifact model |
| Local LLM agents | Adapter invokes Ollama or vLLM; adapter parses model output into schema-conformant artifact |
| Human agents | Supported in MVP via MANUAL invocation mode |
| Scripts | Deterministic transformation scripts; fully compatible with adapter model |

---

## 5. Local AI Runtime Integrations

Local AI runtimes provide the inference layer for automated agent implementations.

See `docs/roadmap/hybrid_ai_runtime.md` for the full hybrid local/cloud AI architecture.

Target components:

| Component | Role |
| --- | --- |
| Ollama | Local model serving; HTTP API |
| vLLM | High-throughput GPU-accelerated inference |

These are adapter-layer concerns. The DevOS kernel is not modified when a local AI runtime is added.

---

## 6. CI System Integrations

CI systems produce test and quality artifacts that DevOS gate checks consume.

### Integration model

```
Agent invocation (agent_test_runner)
         ↓
CI pipeline execution
  (pytest / Ruff / Semgrep / GitHub Actions / GitLab CI)
         ↓
Test report artifact
  (test_report.json)
         ↓
DevOS gate evaluation (TESTING → REVIEWING)
```

CI systems do not trigger workflow transitions. They produce artifacts. DevOS evaluates those artifacts. The agent adapter is responsible for invoking the CI system and writing the structured artifact.

---

## 7. Event-Driven Integration Architecture

The DevOS event log is the canonical integration surface for all event-driven adapters.

Every runtime action emits a typed event to `runs/<run_id>/events.jsonl`. External adapters read this log and react to events.

### Event-to-action examples

| DevOS event | External action |
| --- | --- |
| `artifact.created` | Post comment in issue tracker |
| `workflow.transition_completed` | Update project board status |
| `run.completed` | Close issue / send notification |
| `decision.recorded` | Log approval in external audit system |

### Adapter rules

Event-driven adapters must:

1. Read events only from `runs/<run_id>/events.jsonl`
2. Translate events into tool-specific actions
3. Never write back to the run directory
4. Never trigger workflow transitions
5. Maintain no local state about run progress

---

## 8. Target Integration Categories

| Category | Examples | Integration type |
| --- | --- | --- |
| Planning tools | gstack, Linear, GitHub Issues | Input adapter (→ `change_intent.yaml`) |
| Agent frameworks | gstack agents, local LLM agents | AgentAdapter implementation |
| Local AI runtimes | Ollama, vLLM | Provider backend for agent adapters |
| CI systems | pytest, GitHub Actions, GitLab CI | Tool adapter (produces artifacts) |
| Development tools | Git, Ruff, Semgrep | Tool adapter (produces artifacts) |
| Dashboards | Custom run viewers | Event log consumer |
| Notification systems | Slack, email, webhooks | Event log consumer |

---

## 9. Non-Goals of the Integration Ecosystem

The integration ecosystem explicitly does not pursue:

- Replacing established development tools
- Creating hard dependencies on specific platforms
- Shifting governance responsibility into external systems
- Enabling autonomous tool-driven workflow progression

DevOS remains the authoritative source for engineering governance. External tools serve as interfaces, execution engines, or output consumers.

---

## 10. Prerequisites

Integrations should be developed after:

- The MVP runtime is stable and in production use
- Artifact and event schemas are proven through multiple real runs
- At least one `AgentAdapter` implementation exists and is operational

Building integrations before the runtime is stable creates complexity without a reliable foundation.

---

## Further Reading

- `docs/architecture/integration_model.md` — Artifact-first integration philosophy and adapter architecture
- `docs/architecture/agent_contracts.md` — Agent contract model and external implementations
- `docs/roadmap/hybrid_ai_runtime.md` — Hybrid local/cloud AI runtime design
- `docs/roadmap/future_features.md` — Full roadmap inventory
