# Runtime contract (v1)

## Responsibility

Define the **normative contract** that a compliant runtime system must satisfy to execute the framework
deterministically. This document closes the specification gap between the framework's normative
description and a concrete implementation.

This document is **not** a runtime implementation.
It defines what a runtime **must** do, must not do, and must not decide on its own.

## Input contract

- **Inputs**: All framework layer documents (normative).
- **Readers**: Runtime implementers, `agent_orchestrator`, human operators.

## Output contract

- **Outputs**: Normative rules that bind all compliant runtime implementations.

## Non-negotiables (runtime-specific)

- A runtime that skips any gate check is not compliant.
- A runtime that infers approvals from artifact content is not compliant.
- A runtime that modifies project input artifacts is not compliant.
- A runtime that allows looping within a single workflow state without a transition is not compliant.
- A runtime that applies improvement proposals automatically is not compliant.
- A runtime that omits any required event emission (see `docs/framework/event_model.md` Section 2.1) is not compliant.

## References to related normative documents

| Document | Governs |
| --- | --- |
| `framework/workflows/default_workflow.yaml` | Delivery workflow states, transitions, gate conditions |
| `framework/workflows/improvement_cycle.yaml` | Improvement cycle states and transitions |
| `framework/agents/*.md` | Single-shot agent role contracts and I/O |
| `framework/artifacts/schemas/` | Artifact structure, field requirements, owner/reader contracts |
| `docs/framework/event_model.md` | Canonical event types, payloads, and persistence rules |
| `system_invariants.md` | Non-negotiable framework invariants |

---

## 1. Run identity model

### 1.1 Run ID

Every execution of the delivery workflow constitutes a **run**.

- Each run **must** be assigned a `run_id` at `INIT`.
- `run_id` format: `RUN-<YYYYMMDD>-<suffix>`, where suffix is either a monotonic counter or a
  short random string (project-defined scheme).
- The `run_id` **must** be:
  - globally unique within a project
  - stable once assigned
  - assigned before any artifact is written for the run

### 1.2 Run scope

- A run corresponds to exactly one `change_intent.yaml`.
- A run covers exactly one execution of `framework/workflows/default_workflow.yaml`.
- The improvement cycle (`framework/workflows/improvement_cycle.yaml`) is a **separate run** with its own
  `run_id` and artifact namespace.
- Release activities (post-ACCEPTED) are outside the delivery workflow state machine.

---

## 2. Artifact namespace per run

### 2.1 Run directory layout

All run-produced artifacts **must** reside under a per-run directory.
The following layout is the **canonical recommendation**; projects may adapt it with explicit
project-level convention override:

```
runs/
  <run_id>/
    artifacts/
      change_intent.yaml
      implementation_plan.yaml          (versioned if revised: .v1.yaml, .v2.yaml, â€¦)
      design_tradeoffs.md
      arch_review_record.md             (required at ARCH_CHECK)
      architecture_change_proposal.md   (only if CHANGE_REQUIRED)
      test_design.yaml
      branch_status.md                  (required at BRANCH_READY)
      implementation_summary.md         (optional trace)
      test_change_summary.md            (optional trace)
      test_report.json
      review_result.md
      run_metrics.json                  (optional, append-only)
      orchestrator_log.md               (optional, append-only)
    decision_log.yaml                   (append-only, single governance record)
```

### 2.2 Project inputs

Project inputs (`domain_scope.md`, `domain_rules.md`, `source_policy.md`, `glossary.md`,
`architecture_contract.md`) live **outside** the run directory.
They are read-only inputs shared across runs and must not be modified by the runtime.

#### Canonical location

The **canonical location** for mandatory project inputs is:

```
<project_root>/.devOS/project_inputs/
```

The runtime resolves `project_inputs_root` using the following deterministic fallback chain:

1. **Explicit argument**: `--project-inputs-root` CLI flag, or `project_inputs_root` parameter
   passed directly to `RunEngine.initialize_run()` / `resume_run()`.
2. **Canonical namespace**: `<project_root>/.devOS/project_inputs/` — used if the directory exists.
3. **Legacy fallback**: `<project_root>` — used only if neither 1 nor 2 applies.

The resolved root is stored in `RunContext.project_inputs_root` and used exclusively for all
`input_presence` gate checks. It is set once at run initialization and never changes within a run.

The legacy fallback (project root) is a migration aid. Once all project inputs are relocated to
`.devOS/project_inputs/`, the fallback should not be relied upon.

Templates for mandatory inputs are provided under `examples/templates/mandatory/`.
Copy them to `.devOS/project_inputs/` and fill in project-specific content before starting a run.

### 2.3 Decision log scope

- `decision_log.yaml` for a given run lives at `runs/<run_id>/decision_log.yaml`.
- This is the **only** append-only governance record for the run.
- All human approvals and decisions for this run are recorded exclusively here.
- Per-artifact embedded approval fields are informational summaries only; they never substitute
  for a `decision_log.yaml` entry.

---

## 3. Artifact versioning conventions

### 3.1 Supersession rule

When an artifact must be revised after rejection or rework:

1. Rename the current version with a version suffix: `implementation_plan.v1.yaml`.
2. Write the new version as the canonical name: `implementation_plan.yaml`.
3. The new version **must** reference the prior version:
   - YAML/JSON artifacts: top-level field `supersedes_id: "<prior-artifact-id>"`
   - Markdown artifacts: line near the top `Supersedes: <prior-artifact-id>`

### 3.2 Artifact ID requirement

Every versioned artifact **must** include a stable instance `id` field assigned at creation.
The ID **must not** change when the artifact is superseded or renamed.
IDs must be unique within a project.

Format recommendation: `<artifact-type-prefix>-<run-id-short>-<monotonic-suffix>`
Example: `IP-RUN20260310-001`

### 3.3 Immutability after approval

Once an artifact is referenced in an approved `decision_log.yaml` entry, its content is **frozen**.
Any modification requires a superseding version and a new approval.

---

## 4. Hash and reference binding for approvals

### 4.1 Approval binding

Every `decision_log.yaml` entry approving an artifact **must** include in its `references` block:

```yaml
references:
  - artifact: "<canonical-filename>"
    artifact_id: "<artifact-id>"          # mandatory if artifact has an id field
    artifact_hash: "<sha256-hex>"         # strongly recommended; omit only with explicit rationale
```

### 4.2 Hash computation

- **Text artifacts** (Markdown, YAML, JSON): SHA-256 of the file content (UTF-8, LF line endings,
  no trailing BOM).
- Hashes must be computed **after** the artifact is finalized and before it is presented for approval.

### 4.3 Approval lookup

A gate check requiring `human_approval` on artifact `X` passes if and only if
`decision_log.yaml` contains at least one entry where:

- `decision == "approve"`
- `references` contains an entry matching the artifact by **both** `artifact_id` and `artifact_hash`
  (or by `artifact_id` alone if hash was explicitly omitted with rationale)
- The entry `timestamp` post-dates the artifact's `created_at`

---

## 5. Agent invocation envelope

### 5.1 Definition

An **agent invocation** is an atomic, single-shot execution of a defined agent role.
The runtime enforces the single-shot constraint by providing exactly the specified read-only
inputs and accepting exactly the specified outputs.

### 5.2 Invocation record

For each agent invocation, the runtime **must** record the following entry
(appended to `run_metrics.json` events or `orchestrator_log.md`):

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

### 5.3 Single-shot enforcement

- The runtime **must not** invoke the same agent role twice within the same workflow state without
  an explicit transition into a new state.
- Re-invocation after rework requires a rework transition (Section 8).

### 5.4 Permission model

An agent role **must not** receive write access to any artifact it is not listed as an owner of
in the artifact schema. The runtime is responsible for enforcing this constraint at invocation time.
Input artifacts are passed as read-only; the agent produces outputs as new files.

---

## 6. Gate validation

### 6.1 Gate check procedure

Before executing any workflow transition, the runtime **must** evaluate the transition's
`requires` block in sequence:

1. **Input presence**: verify all `inputs_present` conditions.
2. **Artifact presence**: verify each listed artifact file exists in the run directory.
3. **Approval check**: for each artifact listed under `human_approval`, execute the approval
   lookup (Section 4.3).
4. **Condition check**: evaluate any explicit `conditions` (e.g., `review_outcome: ACCEPTED`).
   Conditions are evaluated by reading the specified field in the artifact.
   For Markdown artifacts, condition fields are read from the **top-level artifact header**:
   the leading lines of the file before any Markdown heading, expressed as bare `key: value`
   pairs. The runtime reads the value of the matching key and compares it to the expected value
   (exact string match, case-sensitive). See artifact schema "Required artifact fields" sections
   for the authoritative list of condition-bearing fields and their allowed values.

A transition **must not** execute unless all checks pass.

### 6.2 Markdown artifact validation

For Markdown artifacts, the runtime **must** check:

- The file exists and is non-empty.
- Each required section heading (as defined in the artifact schema's "Required sections" list)
  is present. Match rule: case-insensitive prefix match against `##` or `###` heading text.
- All **required artifact fields** (defined in the schema's "Required artifact fields" section)
  are present in the file header as bare `key: value` lines. Match rule: exact key name, before
  the first `#` heading. Fields must be non-empty.
  - Field `id` must be present and non-empty.
  - Field `supersedes_id` must be present (value may be `null`).
  - Field `outcome` must be present and match one of the allowed values defined in the schema
    (for artifacts that carry a gate-controlling outcome).

Semantic content is **not** validated by the runtime. This is project-owned via the
`domain_validation` capability.

### 6.3 YAML/JSON artifact validation

For YAML/JSON artifacts, the runtime **must** check:

- The file parses without error.
- All `required_fields` defined in the artifact schema are present and non-null/non-empty.

Full semantic validation is project-owned.

### 6.4 Blocking behavior

If a gate check fails, the runtime **must**:

- Stop at the current state.
- Record the blocking reason as an event in `run_metrics.json` (if used).
- Not proceed, not retry automatically, not infer or fill missing artifacts.
- Not escalate; humans are notified through standard project channels.

---

## 7. Resume and recovery

### 7.1 State reconstruction

If a run is interrupted, the orchestrator **must** reconstruct the current state by reading
the last recorded `stage` event in `run_metrics.json`. If `run_metrics.json` is absent,
the orchestrator evaluates artifact presence and approval status to determine the highest
satisfied state in the workflow, traversing transitions in order.

Reconstruction **must** be based solely on artifact presence and `decision_log.yaml` entries.
It must not be inferred from partial artifact content or metadata fields.

### 7.2 Resume behavior

On resume, the orchestrator:

- Starts from the last confirmed completed state.
- Does not re-execute already completed agent roles (verified by artifact presence and invocation records).
- Re-checks gate conditions before advancing.

---

## 8. Rework model

### 8.1 FAILED state

When a workflow reaches the `FAILED` terminal state:

- The run is terminal. No automatic restart.
- A new run **must** be started with a new `run_id`.
- The new run may reference prior artifacts as inputs, but must produce new artifact versions
  for all stages that failed.
- The new `change_intent.yaml` may include a `supersedes_run_id: "<prior_run_id>"` field.

### 8.2 Rejected artifact (decision: reject)

When a human records `decision: "reject"` in `decision_log.yaml` for a required artifact:

- The workflow is blocked at the current gate.
- The owning agent is re-invoked to produce a new version of the artifact.
- The prior version is retained with a version suffix (Section 3.1).
- The new version requires a new approval entry in `decision_log.yaml`.
- The orchestrator re-checks the gate after the new approval is recorded.
- No state regression occurs; the workflow does not move backward.

### 8.3 Deferred decision (decision: defer)

When a human records `decision: "defer"` for a required artifact:

- The workflow is blocked at the current gate until an explicit `approve` or `reject` decision
  is recorded.
- No timeout or automatic escalation is defined at the framework level.

### 8.4 Architecture change required

When `agent_architecture_guardian` produces an `arch_review_record.md` with
`outcome: CHANGE_REQUIRED`:

- The workflow is blocked at `ARCH_CHECK`.
- `agent_architecture_guardian` must also produce `architecture_change_proposal.md`.
- The proposal requires human approval recorded in `decision_log.yaml`.
- After approval, a new `arch_review_record.md` version with `outcome: PASS` must be produced.
- Only then may the workflow advance to `TEST_DESIGN`.

---

## 9. Improvement cycle run model

- The improvement cycle is a separate, optional run with its own `run_id`.
- Its input artifacts (`run_metrics.json`, `test_report.json`, `review_result.md`) are referenced
  by path from prior delivery runs.
- If `run_metrics.json` is not available from a prior run, the improvement cycle cannot start.
  Runs intended to feed into the improvement cycle must treat `run_metrics.json` as required.
- Its output (`improvement_proposal.md`) follows the same artifact versioning rules.
- A new `change_intent.yaml` resulting from an approved improvement is treated as the input to
  a new delivery run; it follows the `change_intent` schema with an added
  `improvement_proposal_ref: "<proposal-id>"` field.

---

## Assumptions / trade-offs

- Runtime remains tool-agnostic. The directory layout in Section 2 is a recommendation;
  projects may define alternative layouts with an explicit written project convention.
- Markdown validation by heading presence is an approximate structural check only;
  section content is not validated by the runtime.
- Hash-based approval binding requires the runtime to compute and record hashes at write time.
  Retrofitting hashes to existing approvals that lacked them is not supported.
- State reconstruction from artifact presence (Section 7.1 fallback) is deterministic but
  requires artifact IDs and timestamps to be well-formed.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added event emission as a non-negotiable rule. Clarified Markdown field reading procedure in Section 6.1 and 6.2. Added references to related normative documents table. |
| v1.1 | 2026-03-15 | Section 2.2: defined canonical `project_inputs_root` resolution chain (explicit arg → `.devOS/project_inputs/` → legacy root fallback). Added `RunContext.project_inputs_root` as explicit runtime contract field. |
