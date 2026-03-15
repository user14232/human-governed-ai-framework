# DevOS – Agent Contracts

**Document type**: Architecture reference
**Status**: Normative for agent contract model; informative for external implementations
**Date**: 2026-03-15

---

## 1. What an Agent Contract Is

An agent contract is a specification that defines:

- the **role** of an agent within a workflow
- the **inputs** the agent must read (artifacts and read-only project references)
- the **outputs** the agent must produce (artifacts only)
- the **write policy** (what the agent may and must not write)
- the **prohibitions** (explicit must-not rules)
- the **determinism requirements** for the output artifacts

A contract does not specify how reasoning occurs. It does not prescribe an implementation. Any system — a human, a Cursor agent, a gstack agent, a local LLM, or a shell script — that consumes the correct inputs and produces the correct output artifacts is a valid implementation of that contract.

**Contract location**: `framework/agents/`

---

## 2. Contract Shape

Every agent contract in `framework/agents/` follows this structure:

```
role_id         — unique identifier for the role
version         — contract version
workflow_scope  — the workflow state this role operates in
responsibility  — single-purpose description
inputs          — list of artifacts and references to read
outputs         — list of artifacts to produce
write_policy    — what may and must not be written
prohibitions    — explicit must-not rules
determinism     — requirements for reproducible output
artifact_schemas — schema references for each input and output
```

---

## 3. Defined Agent Roles

### Delivery Workflow Roles

These roles are integrated into the primary delivery state machine (`INIT → ACCEPTED`).

| Role | Workflow state | Inputs | Outputs |
| --- | --- | --- | --- |
| `agent_orchestrator` | All | Run context | `orchestrator_log.md` |
| `agent_planner` | `PLANNING` | `change_intent.yaml`, project domain inputs | `implementation_plan.yaml`, `design_tradeoffs.md` |
| `agent_architecture_guardian` | `ARCH_CHECK` | `implementation_plan.yaml`, `architecture_contract.md` | `arch_review_record.md` (optionally `architecture_change_proposal.md`) |
| `agent_test_designer` | `TEST_DESIGN` | `implementation_plan.yaml`, `design_tradeoffs.md` | `test_design.yaml` |
| `agent_test_author` | `TEST_DESIGN` | `test_design.yaml` | Test code in project repository |
| `agent_test_runner` | `TESTING` | `implementation_summary.md`, test code | `test_report.json` |
| `agent_branch_manager` | `BRANCH_READY` | `implementation_plan.yaml` | `branch_status.md` |
| `agent_implementer` | `IMPLEMENTING` | `implementation_plan.yaml`, `design_tradeoffs.md`, `test_design.yaml` | `implementation_summary.md` |
| `agent_reviewer` | `REVIEWING` | `implementation_summary.md`, `test_report.json` | `review_result.md` |

### Improvement Cycle Roles

These roles operate in the asynchronous improvement loop.

| Role | Workflow state | Inputs | Outputs |
| --- | --- | --- | --- |
| `agent_reflector` | `REFLECT` | `run_metrics.json` from completed runs | Reflection artifact |
| `agent_improvement_designer` | `PROPOSE` | Reflection artifact | `improvement_proposal.md` |

### Pre-Workflow Authoring Roles

These roles run before a DevOS workflow is initialized.

| Role | Purpose | Outputs |
| --- | --- | --- |
| `agent_work_item_author` | Authors a `change_intent.yaml` from a human brief or planning system output | `change_intent.yaml` |

### Release Role

| Role | Workflow state | Inputs | Outputs |
| --- | --- | --- | --- |
| `agent_release_manager` | Release workflow | `review_result.md`, approval from decision log | Release artifacts |

### System Actor

`human_decision_authority` is not an automated agent. It is the explicit governance actor that writes entries to `decision_log.yaml`. All human approvals must flow through this channel.

---

## 4. Agent Invocation

Agents are invoked through the `AgentAdapter` protocol defined in `runtime/agents/invocation_layer.py`.

The protocol specifies:

```
AgentAdapter.invoke(
    agent_role: str,
    run_context: RunContext
) -> InvocationResult
```

The kernel calls this protocol. The adapter is responsible for translating the invocation into the actual execution method.

### Invocation modes

The protocol supports two invocation modes:

| Mode | Description | Current status |
| --- | --- | --- |
| `InvocationMode.MANUAL` | Human performs the agent role and produces artifacts manually | MVP mode; all agents operate this way |
| `InvocationMode.AUTOMATED` | Adapter invokes an external system automatically | Code path exists; no concrete adapters built |

In `MANUAL` mode, the CLI prompts for artifact production. The human performs the reasoning and writes the artifact to the correct path. The kernel then validates the artifact at the next gate.

---

## 5. Agent Contracts vs. Agent Implementations

**This distinction is fundamental to the DevOS architecture.**

| Concept | Owner | Location | Purpose |
| --- | --- | --- | --- |
| **Agent Contract** | DevOS | `framework/agents/` | Defines the interface: inputs, outputs, prohibitions, determinism requirements |
| **Agent Implementation** | External system | Project-level or external | Implements the contract: performs reasoning, writes the artifact |

The DevOS kernel knows only about contracts. It does not know about implementations. An implementation is isolated from the kernel by an **adapter**.

### Adapter concept

An adapter translates between a DevOS agent contract and a specific external execution mechanism. The adapter:

1. reads the agent contract from `framework/agents/`
2. loads the input artifacts from `runs/<run_id>/artifacts/`
3. invokes the external system (AI model, human workflow, script)
4. receives the result
5. writes a schema-conformant artifact to `runs/<run_id>/artifacts/`

The kernel never sees the external system. It only sees the resulting artifact.

### Example implementations

Any of these is a valid implementation of a DevOS agent contract:

- **gstack agents** — AI-backed agents that receive structured inputs and produce structured outputs
- **local LLM agents** — adapter calls Ollama or vLLM, prompts the model with the contract context, parses output into artifact
- **human agents** — human reads the contract, consumes input artifacts, writes the output artifact manually
- **scripts** — deterministic programs that transform input artifacts into output artifacts

DevOS contracts define the interface. External systems implement it.

Any system that can:

1. Read the specified input artifacts from `runs/<run_id>/artifacts/`
2. Produce the specified output artifacts in the correct format and schema
3. Write those artifacts to `runs/<run_id>/artifacts/`

...is a valid agent implementation.

### Example: gstack Integration

gstack agents implement DevOS agent contracts by consuming the adapter layer.

```
DevOS workflow state
         ↓
agent contract (framework/agents/<role>.md)
         ↓
gstack AgentAdapter implementation
         ↓
gstack agent invoked with run context
         ↓
gstack agent produces artifact
         ↓
artifact written to runs/<run_id>/artifacts/
         ↓
DevOS gate validates artifact
         ↓
workflow state transitions
```

DevOS remains independent from gstack. The adapter is the isolation boundary.

### Example: Cursor Agent Integration

Cursor agents may implement contracts by receiving the contract as context, reading the input artifacts, and producing the output artifacts.

The agent is invoked by a human or by a wrapper script that calls the Cursor API with the agent contract and run context as input.

### Example: Local LLM Integration

A local LLM backed adapter reads the agent contract, loads the input artifacts, prompts the model, and writes the structured output artifact to the correct path.

The kernel only sees the resulting artifact.

---

## 6. Contract Invariants

The following rules apply to all agent contracts and all agent implementations:

1. **Agents produce artifacts, not side effects.** The only permitted output is a valid, schema-conformant artifact written to `runs/<run_id>/artifacts/`.
2. **Agents do not advance workflow state.** State transitions are the exclusive responsibility of the DevOS kernel.
3. **Agents must not modify framework files.** The `framework/` directory is read-only during execution.
4. **Agents must not modify other agents' output artifacts.** Each artifact is immutable after production and approval.
5. **Agents must not broaden scope** beyond what is specified in `change_intent.yaml`.
6. **All assumptions must be explicit** and recorded inside the produced artifact.

---

## 7. Contract Versioning

Agent contracts are versioned using the framework versioning policy.

Each contract carries:

```
role_id:    agent_planner
version:    v1
```

Version changes follow the rules at `framework/contracts/framework_versioning_policy.md`.

---

## Further Reading

- `framework/agents/` — All agent contract definitions
- `runtime/agents/invocation_layer.py` — AgentAdapter protocol implementation
- `docs/architecture/integration_model.md` — Adapter architecture and integration rules
- `docs/architecture/llm_strategy.md` — LLM provider abstraction for agent implementations
- `docs/roadmap/future_features.md` — Automated adapter implementations (future feature)
