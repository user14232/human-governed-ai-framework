# DevOS Phase 3 – Runtime Realization Plan

**Document type**: Normative engineering specification  
**Version**: v1  
**Date**: 2026-03-12  
**Status**: Active  
**Supersedes**: None  

---

## 0. Document scope and authority

This document defines the **Phase 3 Runtime Realization Plan** for the DevOS framework.

It is the **authoritative reference** for:

- What the DevOS runtime must implement.
- How to measure implementation completeness.
- What constitutes Phase 3 completion.

This document does not add governance rules. Every behavioral requirement stated here derives
from the normative framework contracts listed in Section 2.2. Any apparent addition is
either a clarification of an existing contract or an explicit implementation constraint.

**Reading contract**: Implementers must read this document alongside the normative source
contracts. Where this document and a source contract conflict, the source contract governs.

---

## 1. Phase 3 purpose

### 1.1 Why this phase exists

The DevOS framework layer (Phase 1 and 2) defines:

- Workflow state machines (`workflow/default_workflow.yaml`, `workflow/improvement_cycle.yaml`,
  `workflow/release_workflow.yaml`)
- Artifact contracts (`artifacts/schemas/`)
- Agent role contracts (`agents/*.md`)
- Governance rules (`contracts/system_invariants.md`, `contracts/runtime_contract.md`)
- Decision logging (`artifacts/schemas/decision_log.schema.yaml`)
- Event emission (`docs/event_model.md`)
- Knowledge extraction rules (`docs/knowledge_query_contract.md`)

The framework layer is **complete and assessed as v1.1 ready** (see `docs/v1_readiness_assessment.md`).
No governance-significant design decisions remain implicit.

The framework layer describes **what** must happen. It does not execute.

Phase 3 exists to build the **minimal executable runtime engine** that enacts the framework
contracts in practice. Without Phase 3, the framework remains a specification without an
executing system. The runtime is the mechanism that converts the framework's normative rules
into observable, auditable behavior.

### 1.2 What Phase 3 is not

Phase 3 is not:

- A redesign or reinterpretation of the framework contracts.
- An opportunity to introduce new governance rules.
- An autonomous agent platform.
- A distributed system infrastructure project.
- An enterprise integration effort.

The runtime is an **implementation of the contracts**, bounded strictly by them.

---

## 2. Input contracts

### 2.1 Preconditions for Phase 3

Phase 3 may begin when all of the following are true:

| Precondition | Evidence |
| --- | --- |
| Framework v1.1 readiness assessment is complete | `docs/v1_readiness_assessment.md` verdict: PASS |
| All workflow YAML definitions are stable | `workflow/default_workflow.yaml`, `workflow/improvement_cycle.yaml`, `workflow/release_workflow.yaml` |
| All artifact schemas are complete | `artifacts/schemas/` — all required fields defined |
| Runtime contract is normative | `contracts/runtime_contract.md` v1 |
| Event model is normative | `docs/event_model.md` v1 |

### 2.2 Normative source contracts

The runtime must be implemented against these documents in their current versions:

| Document | Governs |
| --- | --- |
| `contracts/runtime_contract.md` | Run identity, artifact namespace, versioning, approval binding, agent invocation, gate validation, resume/recovery, rework model |
| `workflow/default_workflow.yaml` | Delivery workflow states, transitions, gate conditions |
| `workflow/improvement_cycle.yaml` | Improvement cycle states and transitions |
| `workflow/release_workflow.yaml` | Release lifecycle states and transitions |
| `agents/*.md` | Single-shot agent role contracts and I/O |
| `artifacts/schemas/` | Artifact structure, required fields, owner/reader contracts |
| `docs/event_model.md` | Canonical event types, payloads, persistence rules |
| `docs/knowledge_query_contract.md` | Knowledge extraction trigger points and index contract |
| `contracts/system_invariants.md` | Non-negotiable framework invariants |
| `contracts/capability_integration_contract.md` | Capability invocation and gate-blocking semantics |

---

## 3. Runtime architecture

### 3.1 Architectural statement

The DevOS runtime is a **batch-oriented, deterministic workflow execution engine**.

It operates on a single run at a time. It does not schedule or parallelize runs.
It does not maintain persistent in-memory state between invocations. All durable state
is stored in the run directory and the decision log, from which the runtime can
deterministically reconstruct run state at any time.

### 3.2 High-level component model

```
┌──────────────────────────────────────────────────────────┐
│                    DevOS Runtime                         │
│                                                          │
│  ┌─────────────┐    ┌──────────────────┐                 │
│  │  Run Engine │───▶│ Workflow Engine  │                 │
│  └─────────────┘    └────────┬─────────┘                 │
│         │                    │                           │
│         │           ┌────────▼─────────┐                 │
│         │           │   Gate Evaluator │                 │
│         │           └────────┬─────────┘                 │
│         │                    │                           │
│         │           ┌────────▼─────────┐                 │
│         │           │ Agent Invocation │                 │
│         │           │     Layer        │                 │
│         │           └────────┬─────────┘                 │
│         │                    │                           │
│  ┌──────▼──────┐    ┌────────▼─────────┐                 │
│  │  Artifact   │    │  Decision System │                 │
│  │   System    │    └──────────────────┘                 │
│  └──────┬──────┘                                         │
│         │                                                │
│  ┌──────▼──────┐    ┌──────────────────┐                 │
│  │   Event     │    │  Knowledge       │                 │
│  │   System    │    │  Extraction Hooks│                 │
│  └─────────────┘    └──────────────────┘                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
        │                        │
        ▼                        ▼
   runs/<run_id>/          Framework contracts
   (filesystem)            (YAML/MD/JSON - read-only)
```

### 3.3 Data flow invariant

All data flow between runtime components passes through the run directory on the filesystem.
No component passes data to another component via in-memory channels or implicit shared state.
Every intermediate result is a file in `runs/<run_id>/`.

This constraint is derived from `contracts/system_invariants.md`:
> All handoffs occur exclusively through artifacts.

### 3.4 Framework contracts as read-only inputs

The framework contracts (workflow YAML, artifact schemas, agent role files) are **read-only
inputs** to the runtime. The runtime reads and interprets them; it never modifies them.
The runtime does not cache parsed framework contracts across runs unless the implementation
provides explicit cache invalidation tied to file modification timestamps.

---

## 4. Core runtime components

### 4.1 Run Engine

**Responsibility**: Manage the lifecycle of a single run from creation to terminal state.

**Input contract**:
- `change_intent.yaml` — identifies the work to be executed
- Framework contracts (workflow definition, project inputs)

**Output contract**:
- Run directory created at `runs/<run_id>/`
- `run.started` event emitted
- `run.completed` event emitted at terminal state

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Assign `run_id` at INIT before any artifact is written | `runtime_contract.md` §1.1 |
| Format: `RUN-<YYYYMMDD>-<suffix>` | `runtime_contract.md` §1.1 |
| `run_id` is globally unique within the project | `runtime_contract.md` §1.1 |
| Create run directory `runs/<run_id>/artifacts/` | `runtime_contract.md` §2.1 |
| Detect terminal states: ACCEPTED, ACCEPTED_WITH_DEBT, FAILED, HUMAN_DECISION | `workflow/default_workflow.yaml` |
| Emit `run.started` event on initialization | `docs/event_model.md` §2.1 |
| Emit `run.completed` event on terminal state | `docs/event_model.md` §2.1 |
| Support resume from last confirmed state | `runtime_contract.md` §7 |

**Prohibited behaviors**:
- Automatically restarting a FAILED run.
- Assigning a new `run_id` to a resumed run.
- Modifying project input artifacts.

---

### 4.2 Workflow Engine

**Responsibility**: Interpret workflow YAML definitions and execute state transitions in
the sequence defined by the active workflow.

**Input contract**:
- Active workflow YAML (`workflow/default_workflow.yaml` or `workflow/improvement_cycle.yaml`
  or `workflow/release_workflow.yaml`)
- Current run state (from `run_metrics.json` or artifact presence)
- Gate evaluation results (from Gate Evaluator, Section 4.2.1)

**Output contract**:
- `workflow.transition_checked` event on each gate evaluation
- `workflow.transition_completed` event on each successful transition
- `run.blocked` event when a gate fails

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Load and parse workflow YAML at run start | `workflow/default_workflow.yaml` |
| Traverse transitions in the order defined | `workflow/default_workflow.yaml` |
| Evaluate all `requires` conditions before executing a transition | `runtime_contract.md` §6.1 |
| Block and emit `run.blocked` when any condition fails | `runtime_contract.md` §6.4 |
| Record the blocking reason in the event payload | `docs/event_model.md` §3 (`run.blocked`) |
| Support all three workflow definitions as distinct run types | `runtime_contract.md` §1.2 |
| Treat the improvement cycle as a separate run with its own `run_id` | `runtime_contract.md` §1.2 |

**Gate evaluation sequence** (per `runtime_contract.md` §6.1):

1. `inputs_present` — verify all mandatory project inputs exist.
2. `artifact_presence` — verify each listed artifact file exists in the run directory.
3. `approval_check` — for each artifact listed under `human_approval`, execute the
   approval lookup algorithm (`runtime_contract.md` §4.3).
4. `condition_check` — evaluate explicit `conditions` by reading the specified field from
   the artifact header or YAML fields (exact string match, case-sensitive).

A transition executes only when all four checks pass. The workflow engine must not
skip, reorder, or short-circuit these checks.

**Prohibited behaviors**:
- Inferring transition eligibility from anything other than artifact presence, decision log
  entries, and field values.
- Executing multiple transitions in a single engine step without evaluating gates at each step.
- Applying implicit defaults when `conditions` fields are absent.

---

#### 4.2.1 Gate Evaluator (sub-component)

**Responsibility**: Execute the four-step gate check procedure for a given transition's
`requires` block and return a structured pass/fail result with per-check detail.

**Input contract**:
- Transition `requires` block (parsed from workflow YAML)
- Run directory path (for artifact presence checks)
- `decision_log.yaml` path (for approval lookup)
- Artifact schemas (for field validation)

**Output contract**:
- Structured gate check result: list of `{check_type, subject, result, detail}` tuples
- Aggregate result: `pass` or `fail`

**Approval lookup algorithm** (per `runtime_contract.md` §4.3):

A gate requiring `human_approval` on artifact `X` passes if and only if `decision_log.yaml`
contains at least one entry satisfying all three:

1. `decision == "approve"`
2. `references` contains an entry matching by `artifact_id` AND `artifact_hash`
   (or `artifact_id` alone when hash was explicitly omitted with documented rationale)
3. Entry `timestamp` post-dates the artifact's `created_at`

**Markdown artifact structural validation** (per `runtime_contract.md` §6.2):

1. File exists and is non-empty.
2. Each required section heading (from schema "Required sections" list) is present.
   Match rule: case-insensitive prefix match against `##` or `###` heading text.
3. All required artifact fields are present in the file header (before the first `#` heading)
   as bare `key: value` lines. Fields `id`, `supersedes_id`, and `outcome` (where applicable)
   must be non-empty and match allowed values.

**YAML/JSON artifact structural validation** (per `runtime_contract.md` §6.3):

1. File parses without error.
2. All `required_fields` from the artifact schema are present and non-null/non-empty.

---

### 4.3 Agent Invocation Layer

**Responsibility**: Invoke agent roles, pass read-only input artifacts, collect output
artifacts, and record invocation results.

**Input contract**:
- Current workflow state
- Agent role contract (`agents/<role>.md`) — identifies input artifacts, output artifacts,
  and write permissions
- Input artifact paths from the run directory

**Output contract**:
- Output artifacts written to `runs/<run_id>/artifacts/`
- `agent.invocation_started` event
- `agent.invocation_completed` event
- Invocation record appended to `run_metrics.json` (per `runtime_contract.md` §5.2)

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Invoke each agent role as a single-shot execution | `contracts/system_invariants.md` |
| Pass input artifacts as read-only | `runtime_contract.md` §5.4 |
| Restrict write access to artifact-schema-defined owner fields only | `runtime_contract.md` §5.4 |
| Record invocation envelope (agent_role, state, inputs, outputs, outcome) | `runtime_contract.md` §5.2 |
| Emit `agent.invocation_started` before invocation | `docs/event_model.md` §2.1 |
| Emit `agent.invocation_completed` after invocation | `docs/event_model.md` §2.1 |
| Compute SHA-256 hash of each output artifact after it is written | `runtime_contract.md` §4.2 |
| Enforce single-shot constraint: no re-invocation of same role in same state without rework transition | `runtime_contract.md` §5.3 |

**Invocation record schema** (per `runtime_contract.md` §5.2):

```yaml
invocation:
  run_id: "<run_id>"
  agent_role: "<agent_role_name>"
  workflow_state: "<state>"
  invoked_at: "<iso-8601>"
  input_artifacts:
    - name: "<artifact_name>"
      artifact_id: "<id_or_null>"
      artifact_hash: "<sha256_or_null>"
  output_artifacts:
    - name: "<artifact_name>"
      artifact_id: "<id>"
      artifact_hash: "<sha256>"
  outcome: "<completed|blocked|failed>"
  notes: "<string_or_null>"
```

**Prohibited behaviors**:
- Granting an agent write access to artifacts it does not own per the artifact schema.
- Looping agent invocation within a single workflow state.
- Inferring agent output acceptability from content; structural validation only.

---

### 4.4 Artifact System

**Responsibility**: Manage artifact storage, identification, hashing, structural validation,
and supersession.

**Input contract**:
- Artifact files produced by agent invocations
- Artifact schemas (`artifacts/schemas/`)
- Run directory path

**Output contract**:
- Artifacts stored in `runs/<run_id>/artifacts/`
- `artifact.created` event on each new artifact
- `artifact.superseded` event when a prior version is renamed (recommended)
- `artifact.validated` / `artifact.validation_failed` events (recommended)

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Store all run artifacts under `runs/<run_id>/artifacts/` | `runtime_contract.md` §2.1 |
| Assign stable `artifact_id` at creation; format: `<prefix>-<run-id-short>-<monotonic>` | `runtime_contract.md` §3.2 |
| Compute SHA-256 hash (UTF-8, LF line endings, no BOM) immediately after write | `runtime_contract.md` §4.2 |
| On artifact revision: rename prior to `<name>.v<N>.<ext>`, write new as canonical name | `runtime_contract.md` §3.1 |
| Require new version to contain `supersedes_id` referencing prior artifact's id | `runtime_contract.md` §3.1 |
| Enforce immutability: reject writes to any artifact already referenced in an approved `decision_log.yaml` entry | `runtime_contract.md` §3.3 |
| Validate structural compliance against schema before gate evaluation | `runtime_contract.md` §6.2, §6.3 |
| Maintain project input artifacts as read-only; reject any write attempt | `runtime_contract.md` §2.2 |

**Supersession procedure**:

1. Locate the current canonical artifact file.
2. Determine the next version number `N` by counting existing `.v<N>.<ext>` suffixes.
3. Rename the current file to `<name>.v<N>.<ext>`.
4. Write the new version as `<name>.<ext>`.
5. Verify the new version contains `supersedes_id` referencing the prior artifact's `id`.
6. Emit `artifact.superseded` event referencing both old and new artifact IDs.

**Prohibited behaviors**:
- Modifying artifact content after an approval is recorded against it.
- Assigning new artifact IDs to renamed (archived) versions.
- Computing hashes from in-memory content; hashes must be computed from the file on disk.

---

### 4.5 Decision System

**Responsibility**: Read the `decision_log.yaml`, detect new entries appended by humans,
validate their structure, and emit `decision.recorded` events. The runtime never writes
decisions; it reads and reacts to them.

**Input contract**:
- `runs/<run_id>/decision_log.yaml` (append-only, human-written)
- `artifacts/schemas/decision_log.schema.yaml`

**Output contract**:
- `decision.recorded` event for each new `decision_log.yaml` entry detected
- Gate re-evaluation triggered when a new approval entry is detected

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Treat `decision_log.yaml` as append-only; never write or modify entries | `runtime_contract.md` §2.3 |
| Detect new entries by comparing known last-processed entry count or timestamp | `runtime_contract.md` §2.3 |
| Emit `decision.recorded` event for each detected new entry | `docs/event_model.md` §2.1 |
| Trigger gate re-evaluation after any `decision: approve` entry | `runtime_contract.md` §8.2 |
| Validate that new entries conform to the `decision_log.schema.yaml` required fields | `artifacts/schemas/decision_log.schema.yaml` |
| Accept `decision: reject` and trigger rework model (Section 4.3 re-invocation) | `runtime_contract.md` §8.2 |
| Accept `decision: defer` and hold the workflow blocked without retry | `runtime_contract.md` §8.3 |

**Prohibited behaviors**:
- Inferring approvals from artifact content, metadata, or field values.
- Writing any entry to `decision_log.yaml`.
- Auto-escalating deferred decisions.
- Treating per-artifact embedded approval fields as substitutes for `decision_log.yaml` entries.

---

### 4.6 Event System

**Responsibility**: Generate, structure, and persist runtime events to `run_metrics.json`
as an append-only chronological event stream.

**Input contract**:
- Trigger signals from all other runtime components (Run Engine, Workflow Engine, Agent
  Invocation Layer, Artifact System, Decision System)
- Current run context (run_id, workflow_state, producer identity)

**Output contract**:
- Events appended to `runs/<run_id>/artifacts/run_metrics.json` under the `events` array
- Agent invocation records appended under `invocation_records`

**Required event types** (per `docs/event_model.md` §2.1):

| Event type | Trigger |
| --- | --- |
| `run.started` | Run created and `run_id` assigned |
| `run.completed` | Run reaches a terminal state |
| `run.blocked` | Gate check fails; run cannot advance |
| `workflow.transition_checked` | Gate check evaluated (pass or fail) |
| `workflow.transition_completed` | Transition executed successfully |
| `agent.invocation_started` | Agent role invoked |
| `agent.invocation_completed` | Agent role invocation finishes |
| `artifact.created` | New artifact version written to run directory |
| `decision.recorded` | New entry appended to `decision_log.yaml` |

**Recommended event types** (per `docs/event_model.md` §2.2):

| Event type | Trigger |
| --- | --- |
| `artifact.superseded` | Artifact renamed to versioned suffix |
| `artifact.validated` | Artifact passes structural validation |
| `artifact.validation_failed` | Artifact fails structural validation |
| `run.rework_started` | Rejected artifact triggers re-invocation |
| `run.resumed` | Run resumes from interrupted state |

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Assign monotonically increasing `event_id` per run: `EVT-<run_id_short>-<counter>` | `docs/event_model.md` §5 |
| Write all envelope fields: `event_id`, `event_type`, `run_id`, `timestamp`, `producer`, `workflow_state`, `causation_event_id`, `correlation_id`, `payload` | `docs/event_model.md` §1 |
| Append events in chronological order; no reordering | `docs/event_model.md` §4 |
| Never delete or modify an event after it is written | `docs/event_model.md` non-negotiables |
| Never emit events retroactively or infer from artifact presence | `docs/event_model.md` non-negotiables |
| Persist agent invocation events under `invocation_records`; all other events under `events` | `docs/event_model.md` §4 |

**Prohibited behaviors**:
- Deleting, modifying, or reordering events.
- Emitting events for actions that did not actually occur.
- Substituting events for decisions in `decision_log.yaml`.

---

### 4.7 Knowledge Extraction Hooks

**Responsibility**: Detect normative extraction trigger points and signal the responsible
roles to initiate extraction. The runtime does not perform extraction itself.

**Input contract**:
- Current run terminal state
- Workflow trigger definitions (`workflow/default_workflow.yaml` `post_workflow_activities.knowledge_extraction`)
- Knowledge query contract (`docs/knowledge_query_contract.md` §7)

**Output contract**:
- Notification or log entry indicating an extraction trigger point has been reached
- No automatic extraction; extraction is performed by `agent_reflector`, `agent_improvement_designer`,
  or a human per `docs/knowledge_query_contract.md` §7

**Trigger points** (per `docs/knowledge_query_contract.md` §7):

| Trigger | Workflow location | Responsible role |
| --- | --- | --- |
| Run reaches ACCEPTED or ACCEPTED_WITH_DEBT | `default_workflow.yaml` terminal state | `agent_reflector`, `human` |
| Run reaches FAILED | `default_workflow.yaml` terminal state | `agent_reflector`, `human` |
| Improvement cycle enters OBSERVE | `improvement_cycle.yaml` OBSERVE | `agent_reflector` |
| `architecture_change_proposal.md` approved | Any run | `agent_architecture_guardian`, `human` |

**Required behaviors**:

| Behavior | Source contract |
| --- | --- |
| Detect terminal state transitions and log extraction trigger points | `docs/knowledge_query_contract.md` §7 |
| Record extraction trigger as an event in `run_metrics.json` (recommended) | `docs/event_model.md` |
| Not perform automated extraction | `docs/knowledge_query_contract.md` non-negotiables |

**Prohibited behaviors**:
- Automatically populating `knowledge_record` artifacts.
- Modifying `knowledge_index.json` without explicit agent or human action.
- Inferring knowledge content from artifact data.

---

## 5. Execution model

### 5.1 Nominal run progression

The following describes the deterministic execution sequence for a delivery run.
Each step maps to a specific contract obligation.

```
1. Run Engine: receive change_intent.yaml
2. Run Engine: assign run_id (RUN-<YYYYMMDD>-<suffix>)
3. Run Engine: create runs/<run_id>/artifacts/ directory
4. Event System: emit run.started
5. Workflow Engine: load default_workflow.yaml
6. Workflow Engine: set current state = INIT

Loop until terminal state:
  7. Workflow Engine: identify eligible transitions from current state
  8. Gate Evaluator: evaluate gate conditions for each eligible transition
  9. Event System: emit workflow.transition_checked (pass or fail per check)
  10a. Gate PASS:
       Workflow Engine: execute transition
       Event System: emit workflow.transition_completed
       Workflow Engine: set current state = next state
       Agent Invocation Layer: determine agent for new state
       Event System: emit agent.invocation_started
       Agent executes (single-shot)
       Artifact System: receive output artifacts, compute hashes
       Event System: emit artifact.created for each output
       Event System: emit agent.invocation_completed
  10b. Gate FAIL:
       Event System: emit run.blocked with blocking reason
       Runtime: halt and wait for human action (approval or rework)

When terminal state reached:
  11. Event System: emit run.completed
  12. Knowledge Extraction Hooks: log extraction trigger point
```

### 5.2 Rework execution path

When `decision_log.yaml` receives a `decision: reject` entry:

```
1. Decision System: detect new decision_log.yaml entry
2. Event System: emit decision.recorded
3. Decision System: identify rejected artifact and owning agent
4. Event System: emit run.rework_started (recommended)
5. Artifact System: rename current artifact to versioned suffix (v<N>)
6. Event System: emit artifact.superseded (recommended)
7. Agent Invocation Layer: re-invoke owning agent
8. Artifact System: receive new version, compute hash
9. Event System: emit artifact.created
10. Decision System: wait for new human_approval entry
11. Gate Evaluator: re-evaluate gate on new approval
```

No state regression occurs. The workflow remains at the blocked state until the new
version receives an `approve` decision with matching `artifact_id` and `artifact_hash`.

### 5.3 State reconstruction on resume

On resume after interruption (`runtime_contract.md` §7.1):

1. Attempt to read last `stage` event from `run_metrics.json`.
2. If `run_metrics.json` is present: set current state to the state recorded in the last
   `workflow.transition_completed` event.
3. If `run_metrics.json` is absent: traverse workflow transitions in order; for each
   transition, evaluate gate conditions against artifact presence and `decision_log.yaml`.
   Set current state to the highest transition that passes.
4. Emit `run.resumed` event.
5. Continue execution from the reconstructed state.

Reconstruction is based solely on artifact presence and `decision_log.yaml` entries.
Partial artifact content and metadata fields are not used for reconstruction.

### 5.4 Architecture change path (ARCH_CHECK blocking)

Per `runtime_contract.md` §8.4:

```
1. agent_architecture_guardian produces arch_review_record.md with outcome: CHANGE_REQUIRED
2. Gate Evaluator: ARCH_CHECK → TEST_DESIGN fails (outcome ≠ PASS)
3. Event System: emit run.blocked
4. agent_architecture_guardian: produce architecture_change_proposal.md
5. Event System: emit artifact.created
6. Human: record approve decision in decision_log.yaml referencing architecture_change_proposal.md
7. Decision System: detect approval, emit decision.recorded
8. agent_architecture_guardian: produce new arch_review_record.md with outcome: PASS
9. Gate Evaluator: re-evaluate ARCH_CHECK → TEST_DESIGN (now passes)
10. Workflow Engine: execute transition
```

---

## 6. Artifact lifecycle

### 6.1 Artifact states

```
[written by agent]
  → structural validation (Artifact System)
  → VALID (proceeds to gate evaluation) | INVALID (invocation outcome: failed)
  → [gate evaluation includes approval check if required]
  → APPROVED (referenced in decision_log.yaml approve entry)
  → FROZEN (immutable)
  → [if rejected and rework required]
  → SUPERSEDED (renamed to versioned suffix)
     └─ new version starts lifecycle at [written by agent]
```

### 6.2 Artifact identity rules

| Rule | Source |
| --- | --- |
| Every versioned artifact has a stable `id` assigned at creation | `runtime_contract.md` §3.2 |
| ID format recommendation: `<type-prefix>-<run-id-short>-<monotonic-suffix>` | `runtime_contract.md` §3.2 |
| IDs must be unique within a project | `runtime_contract.md` §3.2 |
| IDs must not change when an artifact is superseded | `runtime_contract.md` §3.2 |
| SHA-256 hash computed from disk after write (UTF-8, LF line endings, no BOM) | `runtime_contract.md` §4.2 |

### 6.3 Artifact immutability enforcement

The Artifact System must enforce immutability for any artifact whose `artifact_id` appears in
an approved `decision_log.yaml` entry. The enforcement procedure:

1. Before any write to an existing artifact, query `decision_log.yaml` for approval entries
   referencing that artifact's `id`.
2. If an approved entry exists: reject the write. A superseded version must be created instead.
3. If no approved entry exists: allow the write and recompute the hash.

---

## 7. Agent invocation model

### 7.1 Agent contract obligations

Each agent role is defined by a contract in `agents/<role>.md` that specifies:

- **Inputs** (read-only): which artifacts and project documents the agent reads.
- **Outputs**: which artifacts the agent produces and which schemas they must conform to.
- **Write policy**: which artifacts the agent may write.
- **Prohibitions**: what the agent must not do.

The runtime enforces these constraints at invocation time. An agent must not receive
a file path with write access to artifacts it does not own.

### 7.2 Single-shot constraint

Per `contracts/system_invariants.md`:

> Agents are single-shot, never looping.

The runtime enforces this by:

1. Recording each invocation in `run_metrics.json` with state, agent role, and outcome.
2. Before any invocation, checking that the same agent role has not already been invoked in
   the same workflow state in this run (unless a rework transition has occurred).
3. Rejecting duplicate invocations with a `run.blocked` event and an explanatory note.

### 7.3 Agent invocation modes

The runtime must support two invocation modes. The mode is selected by the implementation
and project convention; the runtime contract is mode-agnostic:

| Mode | Description |
| --- | --- |
| **Human-as-agent** | A human performs the agent role, produces the output artifact, and places it in the run directory. The runtime detects artifact presence and proceeds. |
| **Automated agent** | An automated process is invoked by the runtime with input artifact paths. The process produces output artifacts. The runtime detects completion by artifact presence. |

In both modes the invocation record, event emission, and gate evaluation requirements are
identical.

### 7.4 Agent role inventory

The following agent roles are defined by the framework and must be supported by the runtime's
agent invocation layer:

| Agent role | Workflow state | Produces |
| --- | --- | --- |
| `agent_planner` | PLANNING | `change_intent.yaml`, `implementation_plan.yaml`, `design_tradeoffs.md` |
| `agent_architecture_guardian` | ARCH_CHECK | `arch_review_record.md`, optionally `architecture_change_proposal.md` |
| `agent_test_designer` | TEST_DESIGN | `test_design.yaml` |
| `agent_branch_manager` | BRANCH_READY | `branch_status.md` |
| `agent_implementer` | IMPLEMENTING | implementation artifacts (codebase); optional `implementation_summary.md` |
| `agent_test_author` | IMPLEMENTING | optional `test_change_summary.md` |
| `agent_test_runner` | TESTING | `test_report.json` |
| `agent_reviewer` | REVIEWING | `review_result.md` |
| `agent_reflector` | REFLECT (improvement cycle) | `reflection_notes.md` |
| `agent_improvement_designer` | PROPOSE (improvement cycle) | `improvement_proposal.md` |
| `agent_release_manager` | RELEASE_PREPARING | `release_notes.md`, `release_metadata.json` |
| `agent_orchestrator` | all states | `run_metrics.json`, `orchestrator_log.md` |
| `human_decision_authority` | all approval gates | `decision_log.yaml` entries |

---

## 8. Event emission model

### 8.1 Event emission is mandatory

Per `contracts/runtime_contract.md` non-negotiables:

> A runtime that omits any required event emission (see `docs/event_model.md` Section 2.1)
> is not compliant.

All nine required event types (Section 4.6) must be emitted. Omitting any one of them
constitutes a compliance failure, regardless of other system behavior.

### 8.2 Event envelope completeness

Every event must include all eight envelope fields. An event with a missing required
envelope field is malformed and must not be persisted. If an event cannot be constructed
with all fields, the runtime must log the failure in `orchestrator_log.md` and halt.

### 8.3 Append-only enforcement

The `run_metrics.json` file is append-only. The runtime must:

1. Never truncate or overwrite `run_metrics.json`.
2. Append new events by reading the current file, appending the new event, and rewriting.
   Implementations may use file-append operations where atomic append is available.
3. Verify that event IDs are monotonically increasing before writing.

### 8.4 Causation chain

The `causation_event_id` field must be populated for all events where a causal prior event
exists in the same run. For `run.started` it is `null`. For all subsequent events, it must
reference the event that directly caused the current event. This enables deterministic
event chain reconstruction during post-run analysis.

---

## 9. Progress metrics

The following metrics define measurable indicators of Phase 3 implementation progress.
Each metric must be evaluable by inspection of the implementation at any point in time.

### 9.1 Component implementation coverage

| Metric | Target | Measurement method |
| --- | --- | --- |
| Runtime components implemented | 7 of 7 (Sections 4.1–4.7) | Component present, passes its unit tests |
| Run Engine behaviors implemented | All rows in Section 4.1 required behaviors table | Checklist verification against contract |
| Workflow Engine behaviors implemented | All rows in Section 4.2 required behaviors table | Checklist |
| Gate Evaluator behaviors implemented | All four check types (§4.2.1) operational | Checklist |
| Agent Invocation Layer behaviors implemented | All rows in Section 4.3 required behaviors table | Checklist |
| Artifact System behaviors implemented | All rows in Section 4.4 required behaviors table | Checklist |
| Decision System behaviors implemented | All rows in Section 4.5 required behaviors table | Checklist |
| Event System behaviors implemented | All rows in Section 4.6 required behaviors table | Checklist |
| Knowledge Extraction Hooks implemented | All rows in Section 4.7 required behaviors table | Checklist |

### 9.2 Workflow transition coverage

| Metric | Target | Measurement method |
| --- | --- | --- |
| Delivery workflow transitions executable | 11 of 11 (from `default_workflow.yaml`) | End-to-end test per transition |
| Improvement cycle transitions executable | 4 of 4 (from `improvement_cycle.yaml`) | End-to-end test per transition |
| Release workflow transitions executable | 5 of 5 (from `release_workflow.yaml`) | End-to-end test per transition |
| Gate conditions evaluated correctly | All gate types: input_presence, artifact_presence, approval, condition | Gate test matrix (see below) |

**Gate test matrix** (minimum required test cases):

| Gate | Test case | Expected outcome |
| --- | --- | --- |
| INIT → PLANNING | inputs missing | FAIL |
| INIT → PLANNING | inputs present | PASS |
| PLANNING → ARCH_CHECK | plan not approved | FAIL |
| PLANNING → ARCH_CHECK | plan approved with matching artifact_id + hash | PASS |
| ARCH_CHECK → TEST_DESIGN | arch_review_record outcome = CHANGE_REQUIRED | FAIL |
| ARCH_CHECK → TEST_DESIGN | arch_review_record outcome = PASS | PASS |
| REVIEWING → ACCEPTED | review_result outcome = FAILED | FAIL |
| REVIEWING → ACCEPTED | review_result outcome = ACCEPTED | PASS |
| REVIEWING → ACCEPTED_WITH_DEBT | no human approval | FAIL |
| REVIEWING → ACCEPTED_WITH_DEBT | outcome = ACCEPTED_WITH_DEBT + approval | PASS |

### 9.3 Artifact system coverage

| Metric | Target | Measurement method |
| --- | --- | --- |
| Artifact schemas with structural validation implemented | All schemas in `artifacts/schemas/` used by delivery workflow | Schema list cross-reference |
| Supersession rule implemented and tested | PASS | Supersession test: rename prior, write new, verify `supersedes_id` |
| Hash computation implemented and tested | PASS | Compute hash of known fixture, compare to expected SHA-256 |
| Immutability enforcement tested | PASS | Attempt write to approved artifact; verify rejection |

### 9.4 Event emission coverage

| Metric | Target | Measurement method |
| --- | --- | --- |
| Required event types emitted | 9 of 9 (Section 4.6) | Inspect `run_metrics.json` after test run |
| Event envelope fields complete | All 8 fields present in every event | Schema validation of `run_metrics.json` |
| Events append-only (no deletion or modification) | PASS | Hash `run_metrics.json` before and after each operation; detect any non-append modification |
| Event causation chain navigable | PASS | For each event with a non-null `causation_event_id`, verify the referenced event exists in the same run |

### 9.5 Compliance prohibitions coverage

| Prohibition | Test case | Expected outcome |
| --- | --- | --- |
| No implicit approvals | Run gate check with artifact present but no decision_log entry | FAIL |
| No looping in single state | Attempt re-invocation of same agent without rework transition | REJECT |
| No modification of approved artifact | Write to artifact after approval recorded | REJECT |
| No modification of project inputs | Write to project input artifact | REJECT |
| No inferred state reconstruction | Remove run_metrics.json; reconstruct from artifacts | Deterministic state derived from artifact presence + decision_log only |

---

## 10. Phase 3 success criteria

Phase 3 is complete when **all** of the following criteria are met. Each criterion must be
verifiable by inspection or test execution.

### SC-01: Run lifecycle is fully operational

A run can be initialized, assigned a `run_id`, progress through all delivery workflow
states, and reach a terminal state (ACCEPTED, ACCEPTED_WITH_DEBT, or FAILED).
All required events are emitted and persisted in `run_metrics.json`.

**Verification**: End-to-end delivery run test covering INIT → PLANNING → ARCH_CHECK →
TEST_DESIGN → BRANCH_READY → IMPLEMENTING → TESTING → REVIEWING → ACCEPTED.

### SC-02: Gate evaluation is contract-compliant

All four gate check types (input_presence, artifact_presence, approval, condition) are
implemented and tested against the gate test matrix in Section 9.2.
The approval lookup algorithm (`runtime_contract.md` §4.3) is implemented including
artifact_id + hash matching.

**Verification**: Gate test matrix (Section 9.2) — all 10 test cases pass.

### SC-03: Agent invocation is single-shot and permission-enforced

The runtime correctly invokes each agent role with read-only inputs and write access
restricted to owned artifacts. Duplicate invocations in the same state without rework
transitions are rejected.

**Verification**: Single-shot enforcement test (Section 9.5, prohibition row 2).

### SC-04: Artifact versioning and immutability are enforced

The supersession rule, immutability-after-approval, and SHA-256 hash computation are
implemented. Attempts to modify approved artifacts are rejected.

**Verification**: Artifact system tests in Section 9.3.

### SC-05: Decision system reads decision_log.yaml deterministically

The runtime correctly reads new entries from `decision_log.yaml`, emits `decision.recorded`
events, triggers gate re-evaluation on `approve`, initiates rework on `reject`, and blocks
indefinitely on `defer`.

**Verification**: Decision system test for each of approve, reject, and defer.

### SC-06: Event system is append-only and complete

All 9 required event types are emitted. The `run_metrics.json` file is append-only.
Event envelopes are complete. The causation chain is navigable.

**Verification**: Event emission coverage metrics (Section 9.4) — all targets met.

### SC-07: Resume and recovery are deterministic

A run interrupted at any state can be resumed. The reconstructed state matches the state
that would have been reached by uninterrupted execution.

**Verification**: Interruption test — start a run, terminate at each workflow state,
resume, verify the reconstructed state is correct.

### SC-08: Improvement cycle and release workflow are executable

The improvement cycle and release workflow can each be executed as separate runs with their
own `run_id`, following the same event, artifact, and gate contracts.

**Verification**: End-to-end test for each of the two secondary workflows.

### SC-09: Knowledge extraction trigger points are signaled

When a delivery run reaches a terminal state, the runtime logs an extraction trigger
point in `run_metrics.json`. No automated extraction occurs.

**Verification**: Terminal state test — verify trigger log entry present, verify
`knowledge_index.json` is not automatically modified.

### SC-10: Rework path is operational

When a human records `decision: reject`, the rework path executes correctly:
artifact is renamed to versioned suffix, the owning agent is re-invoked, the new
version receives a new approval, and the gate re-evaluates.

**Verification**: Rework path test, including ARCH_CHECK `CHANGE_REQUIRED` path.

---

## 11. Runtime maturity levels

The following levels define the maturity progression of the DevOS runtime implementation.
Each level includes objective criteria. Levels are cumulative: a runtime at level N must
satisfy all criteria for levels 1 through N.

### Level 1 — Prototype Runtime

**Definition**: The runtime can execute a subset of the delivery workflow with manual
facilitation at every step. No automated gate evaluation. Event emission is partially
implemented. Used for early validation of the component architecture.

**Objective criteria**:

| Criterion | Required |
| --- | --- |
| Run Engine: `run_id` assignment and run directory creation | Yes |
| Workflow Engine: can parse `default_workflow.yaml` and list states | Yes |
| Artifact System: can write artifacts to `runs/<run_id>/artifacts/` | Yes |
| Event System: emits at least `run.started` and `run.completed` | Yes |
| Gate Evaluator: at least artifact_presence check implemented | Yes |
| Agent Invocation Layer: human-as-agent mode only | Yes |
| End-to-end path: INIT → PLANNING → ARCH_CHECK (manual gate bypass permitted) | Yes |

**Does not require**:
- Approval lookup (hash matching)
- Automated agent invocation
- Rework path
- Resume/recovery
- All 9 required event types

---

### Level 2 — Functional Runtime

**Definition**: The runtime can execute the complete delivery workflow end-to-end with
correct gate evaluation (including approval lookup) and full required event emission.
Rework path is operational. Both human-as-agent and automated agent modes supported.

**Objective criteria**:

| Criterion | Required |
| --- | --- |
| All Level 1 criteria | Yes |
| Gate Evaluator: all four check types implemented | Yes |
| Approval lookup: `artifact_id` + `artifact_hash` matching implemented | Yes |
| All 9 required event types emitted | Yes |
| Event envelopes complete (all 8 fields) | Yes |
| Rework path: artifact supersession, re-invocation, re-approval | Yes |
| Decision System: reads `decision_log.yaml`, triggers gate re-evaluation | Yes |
| Artifact immutability enforcement after approval | Yes |
| SHA-256 hash computation from disk | Yes |
| End-to-end delivery run: INIT → ACCEPTED (no manual gate bypass) | Yes |
| End-to-end delivery run: REVIEWING → FAILED path | Yes |

**Does not require**:
- Resume/recovery
- Improvement cycle
- Release workflow
- Knowledge extraction hooks
- Compliance prohibition tests passing

---

### Level 3 — Framework-Compliant Runtime

**Definition**: The runtime satisfies all Phase 3 success criteria (Section 10). All three
workflow definitions are executable. Resume and recovery are operational. All compliance
prohibitions are enforced and tested. The runtime passes the full gate test matrix.

**Objective criteria**:

| Criterion | Required |
| --- | --- |
| All Level 2 criteria | Yes |
| All Phase 3 success criteria SC-01 through SC-10 met | Yes |
| Improvement cycle executable as a separate run | Yes |
| Release workflow executable as a separate run | Yes |
| Resume/recovery: deterministic state reconstruction from artifacts | Yes |
| All compliance prohibition tests passing (Section 9.5) | Yes |
| Full gate test matrix passing (Section 9.2) | Yes |
| Event append-only enforcement tested | Yes |
| Knowledge extraction trigger points signaled at terminal states | Yes |
| Single-shot enforcement tested | Yes |

**Does not require**:
- Capability integration (`capability_integration_contract.md`)
- Knowledge record writing or `knowledge_index.json` management
- Multi-project support
- CI/CD integration
- Persistence beyond the local filesystem

---

### Level 4 — Production-Ready Runtime

**Definition**: The runtime is deployable in a production engineering environment with
verified capability integration, knowledge layer integration, operational tooling,
and documented project onboarding. The runtime has been exercised on a real project run.

**Objective criteria**:

| Criterion | Required |
| --- | --- |
| All Level 3 criteria | Yes |
| Capability integration: at least one gate-blocking capability registered and exercised | `contracts/capability_integration_contract.md` |
| Knowledge layer integration: `knowledge_index.json` updated by `agent_reflector` at extraction trigger points | `docs/knowledge_query_contract.md` |
| Operational tooling: CLI or equivalent interface for run initialization, status inspection, and decision log entry | Yes |
| Project onboarding documentation: step-by-step guide for initializing a new project with the runtime | Yes |
| Real project run: at least one delivery run completed end-to-end on an actual project | Yes |
| Framework versioning compliance: runtime handles `contracts/framework_versioning_policy.md` version checks | Yes |
| Migration support: `contracts/migration_contract.md` — runtime detects version mismatches and blocks with explicit error | Yes |
| `run_metrics.json` schema compliance: validated against `artifacts/schemas/run_metrics.schema.json` | Yes |

---

## 12. Phase 3 definition of done

Phase 3 is **done** when the runtime has reached **Maturity Level 3 — Framework-Compliant
Runtime** and all of the following are true:

### DoD-01: All success criteria met

All ten Phase 3 success criteria (SC-01 through SC-10, Section 10) are verified and passing.
Each criterion must be backed by a test case or inspection checklist with a recorded outcome.

### DoD-02: No open compliance violations

No known compliance violations against `contracts/runtime_contract.md` non-negotiables:

- Gate skipping: not possible.
- Implicit approvals: not possible.
- Project input modification: not possible.
- Intra-state looping: not possible.
- Automatic improvement proposal application: not possible.
- Required event omission: not possible.

### DoD-03: Event log integrity

A completed test run's `run_metrics.json` passes the following checks:

1. All 9 required event types are present.
2. All event envelopes contain all 8 required fields.
3. Events are in chronological order with no gaps in the monotonic counter.
4. Causation chain is navigable from `run.completed` back to `run.started`.

### DoD-04: Artifact audit trail is intact

For a completed test run:

1. All required artifacts for the executed path are present in `runs/<run_id>/artifacts/`.
2. All approved artifacts are referenced in `decision_log.yaml` with `artifact_id` and
   `artifact_hash`.
3. No approved artifact has been modified (verified by recomputing SHA-256 and comparing
   to the hash in `decision_log.yaml`).

### DoD-05: Three workflow definitions are executable

All three workflows (`default_workflow.yaml`, `improvement_cycle.yaml`, `release_workflow.yaml`)
have been executed end-to-end in the runtime as separate runs with separate `run_id` values.

### DoD-06: Resume/recovery is verified

At least one test documents: (a) a run interrupted at mid-workflow state, (b) runtime
restarted cold (no in-memory state), (c) state correctly reconstructed, (d) run completed
to terminal state.

### DoD-07: Implementation document is produced

An implementation document (`docs/phase3_implementation_record.md` or equivalent) records:

- The maturity level attained.
- Evidence for each success criterion.
- Known limitations with rationale.
- The date Phase 3 was declared complete.

---

## 13. Out-of-scope items

The following items are explicitly outside Phase 3. Their exclusion is by design.

| Item | Rationale |
| --- | --- |
| Autonomous agent loop execution | Violates `contracts/system_invariants.md` — agents are single-shot |
| Automated knowledge extraction | `docs/knowledge_query_contract.md` — extraction is manual by design |
| Self-optimizing workflow modification | `contracts/system_invariants.md` — improvements are proposals only |
| Distributed multi-node execution | Not required for minimal compliant runtime |
| Enterprise IAM integration | Framework uses string identity by design (`docs/v1_readiness_assessment.md` §Remaining limitations) |
| Advanced UI or dashboard | No framework contract governs UI |
| Multi-project coordination | Single-project scope for Phase 3 |
| Semantic artifact content validation | `runtime_contract.md` §6.2 — semantic validation is project-owned via `domain_validation` capability |
| Automated CI/CD integration | Capability-layer concern, not runtime core |

---

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines Phase 3 scope, runtime architecture, all seven runtime components, execution model, artifact lifecycle, agent invocation model, event emission model, progress metrics, success criteria, four maturity levels, and definition of done. |
