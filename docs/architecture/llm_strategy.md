# DevOS – LLM Independence and Provider Strategy

**Document type**: Architecture reference
**Status**: Normative for independence principle; informative for future provider abstractions
**Date**: 2026-03-15

> **Note on MVP scope**: The DevOS MVP runtime contains no LLM invocation code. The `AgentAdapter` protocol is defined but no concrete adapters are built. This document describes the architectural principle of LLM independence and the intended future provider abstraction strategy.

---

## 1. Core Principle: LLM Independence

DevOS must remain independent from LLM vendors and LLM runtimes.

This independence is not a preference — it is an architectural constraint with the same status as the no-external-service-dependency rule.

**What independence means in practice:**

1. The DevOS Kernel (`runtime/`) contains no LLM SDK imports.
2. The DevOS framework (`framework/`) contains no model-specific prompts or configurations.
3. Agent contracts specify behavior in terms of inputs and outputs, not in terms of how a model should be prompted.
4. Any model — local or cloud — that can produce schema-conformant artifacts is a valid implementation.

The DevOS Kernel governs workflow execution. LLM interaction belongs in the **Agent Runtime**, behind the `AgentAdapter` protocol. LLM adapters are Agent Runtime implementations — they are not part of the Kernel.

DevOS interacts with LLMs exclusively through adapters. The Kernel has no knowledge of which model was used, what provider was called, or how many tokens were consumed.

### Possible LLM runtimes

DevOS is designed to work with any of these:

| Runtime | Type | Notes |
| --- | --- | --- |
| Ollama | Local | Model serving daemon; local HTTP API |
| vLLM | Local | High-throughput GPU-accelerated inference |
| Any cloud LLM | Cloud | For complex reasoning tasks where local quality is insufficient |

No runtime is mandatory. The adapter isolates the kernel from all of them.

---

## 2. Where LLM Interaction Belongs

LLM interaction must occur in the **Agent Runtime**, not in the Kernel.

```
DevOS Kernel (runtime/)
         ↓
AgentAdapter.invoke(agent_role, run_context)
         ↓
[Agent Runtime — adapter + LLM client]
         ↓
LLM provider (local or cloud)
         ↓
structured artifact produced
         ↓
artifact returned to Kernel
```

The Kernel sees only the resulting artifact. It does not know what model was used, what prompts were sent, or how many tokens were consumed.

This separation is the foundation of provider independence. LLM adapters are Agent Runtime components. They live outside the Kernel boundary.

---

## 3. Provider Abstraction Model

A provider abstraction layer should sit inside the Agent Runtime, between agent adapters and LLM backends.

Conceptual structure (Agent Runtime internal):

```
AgentAdapter
         ↓
LLMProviderClient (abstract interface)
         ↓
┌────────────────────┬──────────────────────┐
│  LocalProvider     │  CloudProvider       │
│  (Ollama / vLLM)   │  (any cloud model)   │
└────────────────────┴──────────────────────┘
```

The `LLMProviderClient` interface abstracts:

- model selection
- prompt submission
- response parsing
- error handling

**This layer is a future feature.** It is not part of the MVP. The design must be implemented as a project-level Agent Runtime adapter, not inside the DevOS Kernel.

---

## 4. Hybrid Execution Model

The intended default execution model for DevOS agent invocations:

```
Most tasks → local models (Ollama / vLLM)
    (routine code generation, implementation planning, testing, review)
         ↓
Strategic reasoning → cloud models (optional fallback)
    (complex multi-step architecture decisions, high-stakes planning)
```

Local models are the default. Cloud models are an explicit fallback, not the default. This keeps costs near zero, data private, and latency low for the majority of agent invocations.

This hybrid model is a post-MVP capability. See `docs/roadmap/hybrid_ai_runtime.md` for the full design.

---

## 5. Local AI Runtime Strategy

DevOS is designed to support local AI infrastructure as the primary execution mode.

### Rationale

- Local models eliminate dependency on cloud providers.
- Local execution reduces latency for routine development tasks.
- Local models improve data privacy for sensitive codebases.
- Cost approaches zero for high-frequency agent invocations.

### Target local runtime components

| Component | Role |
| --- | --- |
| Ollama | Model serving daemon; exposes a local HTTP API for model inference |
| vLLM | High-throughput inference server for GPU-accelerated local models |

### Target local model categories

| Category | Examples |
| --- | --- |
| Code generation and implementation | DeepSeek Coder, Qwen Coder, CodeLlama |
| Code review and analysis | Models with strong code reasoning capabilities |
| Architecture analysis | Models with long context for document analysis |

Local models are the default target for routine agent roles such as `agent_planner`, `agent_implementer`, and `agent_reviewer`.

### Cloud model role

Cloud models are not excluded. They remain an option for:

- complex multi-step architectural reasoning
- high-stakes planning decisions
- tasks where local model quality is insufficient

Cloud models should be treated as a fallback, not as the default.

---

## 6. Hybrid Routing (Future Feature)

> **Future feature** — not part of the MVP runtime. See `docs/roadmap/hybrid_ai_runtime.md`.

In a future routing layer, DevOS may direct invocations to local or cloud models based on task type.

Conceptual routing logic:

| Task type | Preferred model location |
| --- | --- |
| Routine code generation | Local |
| Implementation planning for small changes | Local |
| Architecture review for major changes | Cloud (optional) |
| Security analysis | Local |
| High-level system design | Cloud (optional) |

Routing decisions must be explicit and deterministic. No heuristic or confidence-based routing.

---

## 7. Provider Selection Rules

When implementing a provider adapter, the following rules apply:

1. **The adapter must not embed provider-specific logic in the kernel.** All provider-specific code lives in the adapter.
2. **Model selection must be explicit.** No dynamic model selection based on inferred task complexity.
3. **Prompt templates are adapter-level, not kernel-level.** The kernel passes the agent contract and run context; the adapter constructs the prompt.
4. **Responses must be parsed into schema-conformant artifacts before returning to the kernel.** The kernel never sees raw model output.
5. **Failures must produce explicit error artifacts or raise a typed exception.** No silent fallback to a different model.

---

## 8. Current State

The MVP runtime contains no LLM invocation. This is intentional.

| Component | Current state |
| --- | --- |
| AgentAdapter protocol | Interface defined in `runtime/agents/invocation_layer.py` |
| Concrete LLM adapters | Not built; project-level concern |
| Provider abstraction layer | Not built; future feature |
| Local model integration | Not built; future feature |
| Model routing | Not built; future feature |

In the MVP, no concrete automated adapters are built. Agent roles are fulfilled manually in a development context: an operator reads the agent contract, consumes the input artifacts, and writes the output artifact. This is a bootstrap mode only. In production operation, all agent roles are fulfilled by automated implementations (AI agents, scripted tools). The governance role (`human_decision_authority`) remains separate and operates only through `decision_log.yaml`.

---

## Further Reading

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture; Agent Runtime responsibilities
- `runtime/agents/invocation_layer.py` — AgentAdapter protocol (Kernel ↔ Agent Runtime boundary)
- `docs/architecture/agent_contracts.md` — Agent contract model and invocation model
- `docs/architecture/integration_model.md` — Adapter architecture and integration rules
- `docs/roadmap/hybrid_ai_runtime.md` — Hybrid local/cloud AI runtime design (post-MVP)
- `docs/roadmap/future_features.md` — Automated agent invocation (post-MVP)
