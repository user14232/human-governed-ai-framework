> **Future Feature — Not part of the MVP runtime.**
> This document describes a post-MVP hybrid AI execution architecture. None of the capabilities described here are implemented in the current runtime. The MVP runtime contains no LLM invocation code. See `docs/roadmap/future_features.md` for the full roadmap inventory.

# Hybrid AI Runtime (Future Feature)

**Document type**: Roadmap reference
**Status**: Post-MVP design; informative only
**Date**: 2026-03-15

---

## 1. Motivation

DevOS must remain provider-independent. All AI execution happens in external adapters behind the `AgentAdapter` protocol. The hybrid AI runtime defines how those adapters should route invocations between local and cloud models.

The hybrid approach enables:

- Near-zero operating costs for routine development tasks
- Data privacy for sensitive codebases
- Reduced latency for high-frequency agent invocations
- Elimination of hard dependency on any specific AI provider

This aligns with the DevOS architecture: DevOS is the governance Kernel. The hybrid AI runtime is one possible implementation of the Agent Runtime beneath it.

---

## 2. Architecture Position

The hybrid AI runtime lives in the **Agent Runtime**, not in the DevOS Kernel.

```
Planning Layer
    (external planning tools)
         ↓
DevOS Kernel
    (run lifecycle / workflow / gate evaluation / artifact validation)
         ↓
Agent Runtime
    ┌────────────────────────────────────────────┐
    │           AgentAdapter                     │
    │                ↓                           │
    │          LLM Provider Client               │
    │        (abstract interface)                │
    │         ↙              ↘                   │
    │  Local Models     Cloud Models             │
    │  (Ollama/vLLM)    (API fallback)           │
    └────────────────────────────────────────────┘
         ↓
Artifact output → DevOS gate evaluation
```

The kernel sees only the artifact produced by the adapter. It has no knowledge of which model was used.

---

## 3. Hybrid Execution Model

The guiding principle:

```
Most tasks → local models
    (routine code generation, implementation, testing, documentation)

Strategic reasoning → cloud models (explicit, not automatic)
    (complex multi-step architecture decisions, high-stakes planning)
```

Expected workload distribution: **~95% local, ~5% cloud**.

### Task routing table

| Task type | Preferred model location |
| --- | --- |
| Code generation | Local |
| Refactoring | Local |
| Unit test generation | Local |
| Documentation generation | Local |
| Implementation planning (small changes) | Local |
| Architecture review (major changes) | Cloud (optional) |
| Complex multi-step reasoning | Cloud (optional) |
| Security analysis | Local |

Routing must be explicit and deterministic. No heuristic routing. No confidence-score-based decisions. Task-type-based routing is explicit configuration, not runtime inference.

---

## 4. Local Model Infrastructure

Local model execution is the default target.

### Target runtime components

| Component | Role |
| --- | --- |
| **Ollama** | Model serving daemon; exposes a local HTTP API for model inference |
| **vLLM** | High-throughput inference server for GPU-accelerated local models |

### Target model categories

| Category | Example models |
| --- | --- |
| Code generation and refactoring | Qwen2.5-Coder, DeepSeek Coder, CodeLlama |
| Code review and analysis | Models with strong code reasoning capabilities |
| Architecture analysis | Models with long context for document analysis |

### Hardware context

Local model execution is viable on consumer hardware (e.g., modern GPU with ≥16 GB VRAM). Model sizes in the 14B–34B range offer a practical balance of quality, speed, and memory requirements.

---

## 5. Cloud Model Role

Cloud models are not excluded. They serve as an explicit fallback for:

- Complex architectural reasoning where local model quality is insufficient
- High-stakes planning decisions that warrant additional validation
- Tasks where context requirements exceed local model window size

Cloud models must never be the default. They are an explicit opt-in for specific task types.

---

## 6. Model Routing Component

The model router is a future component that sits inside the adapter layer.

```
AgentAdapter
         ↓
ModelRouter
    ↓             ↓
LocalProvider   CloudProvider
(Ollama/vLLM)   (API call)
```

The router:
1. receives the agent role and task context
2. looks up the configured routing rule for that task type
3. dispatches to the appropriate provider
4. parses the structured output into a schema-conformant artifact

The router must not use heuristics or confidence scores. Routing rules are explicit configuration.

---

## 7. Context Management

Local models have smaller context windows than cloud models. This creates a context retrieval problem for large codebases.

A future retrieval layer addresses this:

```
Run artifacts + project inputs
         ↓
Relevant context retrieval
  (select relevant files and sections)
         ↓
Local model prompt (within context budget)
```

The retrieval layer ensures local models receive only the relevant portion of the codebase for each task. This is a separate future component, not part of the DevOS kernel.

---

## 8. Relationship to DevOS Kernel

The hybrid AI runtime is external to the DevOS governance kernel. The kernel's `AgentAdapter` protocol is the integration boundary.

| Concern | Owner |
| --- | --- |
| Workflow governance | DevOS kernel |
| Agent contract definition | DevOS framework |
| Model selection and invocation | Adapter layer (hybrid AI runtime) |
| Artifact production | Adapter layer (hybrid AI runtime) |
| Artifact validation | DevOS kernel (artifact system) |

The kernel does not change when the hybrid AI runtime is introduced. Only new adapter implementations are added.

---

## 9. Prerequisites

This feature should be developed after:

- The DevOS MVP runtime is stable and in production use
- Concrete `AgentAdapter` implementations exist for at least one execution mode
- Artifact schemas are proven through multiple real runs
- The task routing configuration format is designed

Building the hybrid runtime before the MVP is stable creates complexity without validated foundations.

---

## Further Reading

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture; Agent Runtime responsibilities
- `docs/architecture/llm_strategy.md` — LLM independence principle and provider abstraction
- `docs/architecture/agent_contracts.md` — Agent contract model and adapter concept
- `docs/architecture/integration_model.md` — Adapter architecture and integration rules
- `docs/roadmap/future_features.md` — Full roadmap inventory
