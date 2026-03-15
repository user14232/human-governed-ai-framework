# DevOS – Future Features (Roadmap)

**Document type**: Roadmap inventory  
**Status**: Informative, non-normative  
**Scope**: Post-MVP / Future Development

---

## Purpose

This document lists capabilities that are **intentionally excluded from the DevOS MVP runtime**.

These features are not excluded due to design flaws or abandonment. They are parked here so the MVP runtime remains small, deterministic, and shippable. Each item is documented as a potential future extension with a clear relationship to the MVP core.

**None of the features in this document are implemented in the current runtime.**

---

## Parked Features

### 0. Planning System Integrations

Automated conversion of planning tool output into DevOS `change_intent.yaml` files, enabling seamless pipeline entry without manual authoring.

**What it involves:**
- Linear task → `change_intent.yaml` converter
- GitHub Issues → `change_intent.yaml` converter
- gstack task export adapter
- Bidirectional state mirroring: DevOS run state projected back into the planning tool

**Why parked:**
The MVP uses manual `change_intent.yaml` authoring. The integration boundary is already defined — `change_intent.yaml` is the entry contract. Automated converters are project-level adapters that can be built on top of the stable MVP runtime without any runtime changes.

**Reference:** `docs/architecture/integration_model.md §4`, `docs/roadmap/integration_ecosystem_vision.md`

---

### 1. Knowledge Record System

A structured system for capturing reusable engineering insights derived from run artifacts.

**What it involves:**
- `knowledge_record` artifact format (schema already defined at `framework/artifacts/schemas/knowledge_record.schema.json`)
- Extraction from review results, decision logs, and design tradeoff artifacts
- Append-only `knowledge_index.json` for cross-run querying

**Why parked:**
The MVP runtime emits extraction trigger events at terminal states (`extraction_hooks.py`) but performs no extraction itself. Extraction and indexing require a stable, validated runtime to build upon. The trigger hooks are the integration point once this feature becomes active.

**Reference:** `docs/framework/knowledge_query_contract.md`

---

### 2. Knowledge Index

A queryable index of engineering knowledge derived from multiple completed runs.

**What it involves:**
- Aggregation of knowledge records across runs
- Query interface (by topic, run, artifact type, or decision outcome)
- Supersession tracking for outdated knowledge records

**Why parked:**
Requires the knowledge record system to be operational and a stable artifact corpus from multiple completed runs.

---

### 3. Capability Registry Execution

A project-defined registry of capability validators that extend runtime gate checks.

**What it involves:**
- `capability_registry.schema.yaml` (schema already defined at `framework/artifacts/schemas/capability_registry.schema.yaml`)
- Runtime integration point at gate evaluation for project-defined semantic validators
- Example: `domain_validation` capability for semantic content checking

**Why parked:**
The MVP Artifact System validates structure only (field presence, heading presence, outcome values). Semantic validation is deliberately project-owned and not runtime-enforced in the MVP. The `AgentAdapter` protocol is the existing integration point for project-specific execution.

**Reference:** `framework/contracts/capability_integration_contract.md`

---

### 4. Improvement Cycle Automation

Automated triggering of the improvement cycle workflow after delivery run completion.

**What it involves:**
- Automatic `improvement_cycle.yaml` run initialization post-ACCEPTED state
- Analysis agent invocation without explicit human trigger
- Automated improvement proposal generation

**Why parked:**
The improvement cycle workflow (`framework/workflows/improvement_cycle.yaml`) is already defined and executable via the CLI. Automation of its triggering — without explicit human initiation — violates the MVP non-autonomous constraint. The workflow can be run manually at any time.

---

### 5. Automated Agent Invocation (Adapter Integration)

Pre-built `AgentAdapter` implementations that invoke AI models automatically during workflow execution.

**What it involves:**
- Subprocess or HTTP adapters for specific agent roles
- LLM-backed agent execution triggered by the `invocation_layer`
- Automated output artifact writing

**Why parked:**
The `AgentAdapter` protocol is already defined in `runtime/agents/invocation_layer.py`. The runtime supports `InvocationMode.AUTOMATED` as a code path. Building concrete adapter implementations is a project-level concern and out of scope for the MVP runtime.

---

### 6. Model Routing

Dynamic routing of AI invocations to local or cloud models based on task type and context.

**What it involves:**
- Task-type classifier at the invocation layer
- Local model execution (via Ollama or equivalent)
- Cloud model fallback for high-complexity tasks
- Cost-aware routing logic

**Why parked:**
Requires stable adapter implementations and a defined task classification scheme. Documented in detail at `docs/roadmap/hybrid_ai_runtime.md`.

---

### 7. AI-Driven Analysis Workflows

Automated analysis runs that produce structured engineering insights without direct change intent.

**What it involves:**
- Architecture analysis workflows
- Codebase health analysis
- Technical debt quantification runs

**Why parked:**
These require well-tested workflow definitions, stable artifact schemas, and proven adapter implementations — all of which require MVP stability first.

---

### 8. Integration Layer (External Tool Adapters)

Adapters that mirror DevOS run state into external project management and code hosting tools.

**What it involves:**
- Project management system integration (issue tracking, sprint boards)
- Code repository integration (branch/PR mirroring)
- Dashboard and notification adapters
- Event-driven adapter architecture

**Why parked:**
Integration adapters depend on a stable, validated runtime and event model. The runtime event model is defined and usable as the integration surface. Documented in detail at `docs/roadmap/integration_ecosystem_vision.md`.

---

## Integration Points Already Present in MVP

The following items are **already present in the MVP runtime** as forward-compatible stubs or protocols, ready for future activation without runtime redesign:

| Item | Location | Status |
| --- | --- | --- |
| Knowledge extraction trigger events | `runtime/knowledge/extraction_hooks.py` | Active in MVP (events emitted, no extraction performed) |
| Automated agent invocation path | `runtime/agents/invocation_layer.py` — `InvocationMode.AUTOMATED` | Code path exists; no adapters built |
| `AgentAdapter` protocol | `runtime/agents/invocation_layer.py` | Interface defined; implementations are project-level |
| Artifact schema validation | `runtime/artifacts/artifact_system.py` | Structural validation active; semantic validation is future |

---

## Excluded by Design (Non-Goals)

These are **permanent non-goals**, not just parked features:

- **Autonomous execution loops**: DevOS will never drive unbounded autonomous runs. One transition per `advance` invocation is a hard design constraint.
- **Implicit approvals**: DevOS will never infer approvals from artifact content. All approvals require explicit `decision_log.yaml` entries.
- **External system dependency**: DevOS will never require an external service (database, API, cloud provider) to function. It must remain fully operable from the local filesystem.
