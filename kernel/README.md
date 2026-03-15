# DevOS Runtime — Kernel Implementation

The runtime is the **active implementation of the DevOS Kernel**. It is the only component that executes.

This directory contains the DevOS Kernel — the deterministic governance core. It enforces workflow execution, gate validation, artifact validation, and event logging. It does not perform AI reasoning. AI reasoning occurs in the Agent Runtime (external adapters). See `docs/vision/devos_kernel_architecture.md` for the four-system architecture overview.

## Intent

The Kernel implementation is intentionally minimal.

It provides the core execution engine for DevOS workflows and is designed to remain small and deterministic. Every design decision in this codebase prioritizes correctness and auditability over convenience and automation.

## What the Runtime Does

The runtime executes a single responsibility: **advance a run through a defined workflow, one deterministic transition at a time**.

That means:

- Initialize a run from a `change_intent.yaml` input.
- Load the workflow definition from `framework/workflows/`.
- Evaluate gate conditions before each transition.
- Record artifacts, decisions, and events to the run directory.
- Emit typed events for every system action.
- Detect terminal states and halt cleanly.

## Module Map

```
runtime/
├── cli.py                  Entry point — five commands: run, resume, status, check, advance
├── types/                  Shared value objects; no dependencies on other runtime modules
├── framework/              Read-only loaders for workflow, schema, and agent contracts
├── store/                  Filesystem abstraction — atomic writes, SHA-256 hashing, run layout
├── engine/
│   ├── run_engine.py       Run lifecycle: init, resume, terminal detection
│   ├── workflow_engine.py  State machine traversal; one transition per call
│   └── gate_evaluator.py   Four-step gate check before each transition
├── artifacts/
│   └── artifact_system.py  Storage, hashing, structural validation, immutability enforcement
├── decisions/
│   └── decision_system.py  Decision log reader; returns typed signals, never writes
├── events/
│   ├── event_system.py     Event construction, monotonic ID assignment
│   └── metrics_writer.py   Append-only writes to run_metrics.json
└── knowledge/
    └── extraction_hooks.py Trigger-event emitter at terminal states (no extraction performed)
```

## Design Constraints

- **One transition per `advance` invocation.** The CLI does not loop autonomously. Each call attempts exactly one state transition.
- **No hidden state.** No in-memory state survives between CLI invocations. State is always reconstructed from the filesystem.
- **No semantic interpretation.** The runtime validates artifact structure (field presence, headings, outcome values), not content meaning.
- **No implicit approvals.** Every gate requiring human approval must have a matching explicit entry in `decision_log.yaml`.

## What the Runtime Does Not Do

- It does not extract knowledge or write to `knowledge_index.json`.
- It does not invoke AI models directly. The `AgentAdapter` protocol is defined; concrete adapters are project-level concerns.
- It does not trigger improvement cycles automatically.
- It does not connect to any external service.

These are future extension points. See `docs/roadmap/future_features.md`.

## Documentation

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture reference.
- `docs/architecture/system_map.md` — Concrete module map of all four systems.
- `docs/vision/product_vision.md` — MVP scope, principles, and non-goals.
- `docs/runtime/runtime_execution_model.md` — execution model and future extension points.
- `docs/runtime/runtime_module_architecture.md` — full module interface specifications.
- `docs/roadmap/future_features.md` — capabilities parked outside the MVP.
