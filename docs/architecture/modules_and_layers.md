# DevOS – Runtime Module Layers

**Document type**: Architecture reference
**Status**: Non-normative reference; derived from `docs/runtime/runtime_module_architecture.md`
**Date**: 2026-03-15

> This document summarizes the DevOS runtime module decomposition. The authoritative Python-style interface signatures are in `docs/runtime/runtime_module_architecture.md`. The normative runtime rules are in `contracts/`.

---

## Overview

The DevOS runtime is decomposed into **12 modules across 6 layers**. This structure enforces strict dependency rules that prevent circular imports and maintain clear separation of concerns within the governance kernel.

```
Layer 1 — Types           (runtime/types/)          ← stable foundation, no runtime imports
Layer 2 — Framework       (runtime/framework/)       ← read-only parsers, called once at init
Layer 3 — Store           (runtime/store/)           ← pure filesystem abstraction
Layer 4 — Engine          (runtime/engine/)          ← core execution logic
Layer 5 — Domain          (runtime/artifacts/, agents/, decisions/, events/, knowledge/)
Layer 6 — CLI             (runtime/cli.py)           ← five commands
```

---

## Layer 1 — Shared Types (`runtime/types/`)

Frozen value objects. No external dependencies. No behavior beyond validation.

Every other module imports from here. Nothing here imports from any runtime module. This eliminates circular dependencies entirely.

| File | Key types |
| --- | --- |
| `run.py` | `RunId`, `RunContext`, `RunState`, `TERMINAL_STATES` |
| `workflow.py` | `WorkflowDefinition`, `Transition`, `RequiresBlock` |
| `artifact.py` | `ArtifactRef`, `ArtifactId`, `ArtifactHash`, `ArtifactStatus`, `ArtifactSchema` |
| `event.py` | `EventEnvelope`, `EventType` enum (14 types) |
| `decision.py` | `DecisionEntry`, `DecisionType`, `DecisionReference` |
| `gate.py` | `GateResult`, `GateCheckDetail`, `CheckType`, `CheckResult` |

---

## Layer 2 — Framework Loaders (`runtime/framework/`)

Read-only parsers that convert framework contract files into typed structures. Called once at run initialization and passed as arguments — never re-read during the execution loop.

**Key constraint**: A run executes against the framework version that was current at `run.started`. Framework files are never re-read mid-run.

| Module | Output type |
| --- | --- |
| `workflow_loader.py` | `WorkflowDefinition` |
| `schema_loader.py` | `dict[str, ArtifactSchema]` |
| `agent_loader.py` | `dict[str, AgentContract]` |

---

## Layer 3 — Store (`runtime/store/`)

Pure filesystem abstraction with no business logic and no framework semantics.

| Module | Responsibility |
| --- | --- |
| `run_store.py` | Run directory creation, path resolution, run enumeration |
| `file_store.py` | Atomic write, atomic rename, SHA-256 hashing (normalized UTF-8 + LF), JSON/YAML parse, append to JSON array |

The hash function lives in `file_store.py` because it is a pure I/O operation independent of artifact semantics.

---

## Layer 4 — Runtime Engine (`runtime/engine/`)

Core execution logic. Three modules.

| Module | Responsibility |
| --- | --- |
| `run_engine.py` | `initialize_run()`, `resume_run()`, `declare_terminal()`. Owns `run_id` assignment (format: `RUN-<YYYYMMDD>-<suffix>`). Calls `workflow_engine.reconstruct_state()` on resume. |
| `workflow_engine.py` | `advance()` executes one transition per call (deliberate — no autonomous loop). `reconstruct_state()` implements the two-path fallback from `contracts/runtime_contract.md §7.1`. |
| `gate_evaluator.py` | Four methods, one per check type: `check_inputs_present`, `check_artifact_presence`, `check_approval`, `check_conditions`. Returns a `GateResult` with per-check detail that feeds the `workflow.transition_checked` event payload. |

---

## Layer 5 — Domain Components

| Module | Responsibility |
| --- | --- |
| `runtime/artifacts/artifact_system.py` | `register()` (hash + structural validation + emit), `validate_structure()` (Markdown heading/header parsing and YAML field checking), `supersede()` (six-step supersession procedure), `check_immutability()` (queries decision log for frozen status). Structural validation never raises — errors returned in `ValidationResult`. |
| `runtime/agents/invocation_layer.py` | `invoke()` dispatches via `AgentAdapter` protocol. `check_single_shot()` reads `run_metrics.json` invocation records before any dispatch to enforce the single-shot invariant. Human-as-agent mode polls the output directory for artifact presence. |
| `runtime/decisions/decision_system.py` | `load_all()`, `get_new_entries()`, `process_new_entries()` — detects entries appended to `decision_log.yaml` since last check, emits `decision.recorded` events, returns typed `DecisionSignal` values (`GATE_RECHECK`, `REWORK`, `DEFERRED`). Never writes a single byte to `decision_log.yaml`. |
| `runtime/events/event_system.py` + `metrics_writer.py` | Event construction, monotonic ID assignment (`EVT-<run_id_short>-<counter>`), envelope validation (all 8 fields must be present before persisting), routing to correct section (`events` vs. `invocation_records`). `verify_append_only()` supports compliance checks. |
| `runtime/knowledge/extraction_hooks.py` | Static `EXTRACTION_TRIGGERS` registry keyed by terminal state. `check_triggers()` is a pure function. `log_trigger()` appends a trigger entry to `run_metrics.json`. Never touches `knowledge_index.json`. MVP: emits trigger events only; no extraction performed. |

---

## Layer 6 — CLI (`runtime/cli.py`)

Five commands: `run`, `resume`, `status`, `check`, `advance`.

The `advance` command performs exactly one workflow transition per invocation. There is no run-until-done loop command. A human or wrapper script calls `advance` iteratively. This is the structural enforcement of the human-in-the-loop model — the CLI cannot become an autonomous executor.

---

## Dependency Rules

Seven explicit rules govern the dependency graph:

1. `types/` has no runtime module imports — it is the stable foundation.
2. `framework/` has no runtime module imports — it only produces parsed types.
3. `store/` has no runtime module imports — it only abstracts the filesystem.
4. `event_system` is called by all components but depends on nothing except `types/` and `store/` — no circular dependencies.
5. Only `run_engine` calls `workflow_engine` directly.
6. `gate_evaluator` is the only module that jointly reads artifacts and the decision log.
7. Framework contracts are loaded once at run start; no mid-run re-reads.

---

## Further Reading

- `docs/runtime/runtime_module_architecture.md` — Full Python-style interface signatures for all modules
- `docs/runtime/runtime_execution_model.md` — MVP runtime scope and explicit exclusions
- `docs/architecture/devos_architecture.md` — Runtime architecture narrative and OS mental model
- `contracts/runtime_contract.md` — Normative runtime specification
