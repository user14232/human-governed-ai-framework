# DevOS – Development Pipeline

**Document type**: Architecture reference
**Status**: Normative for pipeline structure
**Date**: 2026-03-15

---

## 1. Overview

The DevOS development pipeline is the complete path from an idea to a completed, governed change in the codebase.

```
Idea
         ↓
Planning System                    ← EXTERNAL (gstack / Linear / GitHub Issues / any task system)
  (epics / stories / tasks)
         ↓
Task selection                     ← human or external automation
         ↓
change_intent.yaml                 ← entry point into DevOS
         ↓
DevOS Governance Kernel            ← DevOS boundary begins here
  Run initialization
         ↓
Workflow execution
  (INIT → PLANNING → ARCH_CHECK → TEST_DESIGN
   → BRANCH_READY → IMPLEMENTING → TESTING → REVIEWING)
         ↓
Planning Artifact                  ← produced by agent_planner
         ↓
Implementation                     ← produced by agent_implementer
         ↓
Review                             ← produced by agent_reviewer
         ↓
ACCEPTED                           ← terminal state, run complete
```

**Planning always comes from external tools.** DevOS does not define what should be built. It governs how approved, scoped work items progress through a disciplined execution workflow.

Every stage in this pipeline has explicit inputs, explicit outputs, and a defined responsibility. Nothing passes between stages except through artifacts.

**All artifacts are produced by agents or automated tools.** Humans interact with DevOS only through governance decisions recorded in `decision_log.yaml`. Humans never produce workflow artifacts.

---

## 2. Stage 1 — Idea and Planning

**Outside DevOS boundary.**

Development begins with an idea. The idea is captured in a planning system as a work item.

Planning systems may include:
- Linear
- GitHub Issues
- gstack
- A local project plan YAML

The planning system breaks work down into epics, stories, and tasks. This work is done by a human or a planning agent operating outside the DevOS kernel.

**Output of this stage**: A selected, scoped task ready to be executed.

---

## 3. Stage 2 — Change Intent Authoring

**Entry point into DevOS.**

The selected task is converted into a `change_intent.yaml` file. This conversion is the bridge between the planning layer and the DevOS governance kernel.

The `change_intent.yaml` specifies:
- the objective of the change
- the scope and constraints
- relevant domain references

It does not contain implementation decisions. Those are produced in the planning stage of the workflow.

**Artifact produced**: `change_intent.yaml`

**Schema**: `framework/artifacts/schemas/change_intent.schema.yaml`

The `agent_work_item_author` role may assist in producing this artifact from a human brief or planning system output. See `framework/agents/agent_work_item_author.md`.

---

## 4. Stage 3 — DevOS Run Initialization

**DevOS kernel takes control.**

```bash
devos run --intent change_intent.yaml
```

The CLI:
1. assigns a deterministic `run_id`
2. creates the run directory at `runs/<run_id>/`
3. copies `change_intent.yaml` into the artifact store
4. loads the workflow definition
5. records a `run.initialized` event
6. sets the initial workflow state to `INIT`

From this point, the run directory is the canonical state of the work. All subsequent actions are recorded there.

---

## 5. Stage 4 — Workflow Execution

The workflow advances through states. Each state is the responsibility of a defined agent role. Each transition requires gate validation to pass.

### PLANNING state

**Responsible agent**: `agent_planner`

The planner reads `change_intent.yaml` and all domain context files. It produces:

- `implementation_plan.yaml` — structured, scoped plan with explicit steps
- `design_tradeoffs.md` — explicit assumptions and trade-off decisions

**Gate requirements**: Both artifacts must be present, structurally valid, and approved via `decision_log.yaml`.

---

### ARCH_CHECK state

**Responsible agent**: `agent_architecture_guardian`

The architecture guardian reviews the implementation plan against the project's `architecture_contract.md`. It produces:

- `arch_review_record.md` with `outcome: PASS` or `outcome: CHANGE_REQUIRED`

If `CHANGE_REQUIRED`:
- an `architecture_change_proposal.md` must be produced
- the proposal must be approved
- a new `arch_review_record.md` with `outcome: PASS` must be produced

**Gate requirement**: `arch_review_record.md` must have `outcome: PASS`.

---

### TEST_DESIGN state

**Responsible agent**: `agent_test_designer`

The test designer defines the test strategy before implementation begins. It produces:

- `test_design.yaml` — test cases, coverage requirements, and test strategy

Tests are designed before code is written. This is intentional.

**Gate requirement**: `test_design.yaml` must be present and approved.

---

### BRANCH_READY state

**Responsible agent**: `agent_branch_manager`

The branch manager creates an isolated change surface (e.g., a Git branch or worktree). It produces:

- `branch_status.md` — records the base reference, branch identifier, and preparation steps

**Gate requirement**: `branch_status.md` must be present and approved.

---

### IMPLEMENTING state

**Responsible agent**: `agent_implementer`

The implementer writes the code changes according to the approved plan. It produces:

- `implementation_summary.md` — maps every change to a plan item, records deviations explicitly

The implementer must not broaden scope beyond `change_intent.yaml`. Architecture changes require a proposal and approval before code is written.

**Gate requirement**: `implementation_summary.md` must be present and approved.

---

### TESTING state

**Responsible agent**: `agent_test_runner`

The test runner executes tests against the implementation. It produces:

- `test_report.json` — structured results with pass/fail status per test case

**Gate requirement**: `test_report.json` must be present and approved.

---

### REVIEWING state

**Responsible agent**: `agent_reviewer`

The reviewer assesses the full change: implementation quality, test coverage, architectural compliance, and technical debt. It produces:

- `review_result.md` with `outcome: PASS`, `outcome: PASS_WITH_DEBT`, or `outcome: REJECT`

**Gate requirement**: `review_result.md` must be present and approved.

---

## 6. Stage 5 — Decision and Terminal State

The run reaches a terminal state based on the review outcome. If the final gate requires a governance decision, the `human_decision_authority` provides an approval or rejection entry in `decision_log.yaml`. If no approval is configured as a gate requirement, the terminal state is reached from the artifact outcome alone.

| Terminal state | Meaning |
| --- | --- |
| `ACCEPTED` | Change approved; no outstanding technical debt |
| `ACCEPTED_WITH_DEBT` | Change approved; technical debt explicitly recorded and accepted |
| `FAILED` | Change rejected; a new run is required for rework |

`FAILED` is terminal. The run directory is preserved as an audit record. No rework happens inside a failed run.

All terminal states record a final `run.completed` event and optionally emit knowledge extraction trigger events.

---

## 7. Artifact Data Flow

The full artifact chain produced across a run:

```
change_intent.yaml
    → implementation_plan.yaml
    → design_tradeoffs.md
    → arch_review_record.md
    → test_design.yaml
    → branch_status.md
    → implementation_summary.md
    → test_report.json
    → review_result.md
    → run_metrics.json
```

Supporting artifacts (produced conditionally):

- `architecture_change_proposal.md` — when `ARCH_CHECK` outcome is `CHANGE_REQUIRED`
- `orchestrator_log.md` — execution trace produced by `agent_orchestrator`
- `decision_log.yaml` — append-only; records all human approvals across all stages

---

## 8. Human Decision Points

### Human Decision Authority

`human_decision_authority` is the governance actor in a DevOS run.

**Responsibilities:**
- Provide an approval or rejection entry in `decision_log.yaml` when a gate is configured to require a decision
- Review run output when desired
- Intervene when governance input is required

**Non-responsibilities:**
- Producing workflow artifacts
- Executing agent roles
- Driving workflow execution

Humans are **governance participants**, not workflow workers. Their sole channel of interaction with DevOS is the `decision_log.yaml` file. They never write, modify, or produce workflow artifacts.

### Decision gate mechanism

Decision gates require a matching approval entry in `decision_log.yaml` before the workflow can advance. The entry must contain:

- `artifact_id` — the identifier of the artifact being approved
- `artifact_hash` — the SHA-256 hash of the artifact at time of approval
- `decision` — `approve` or `reject`
- `timestamp` — ISO 8601

The kernel never infers approvals. No artifact advances past a configured approval gate without a matching decision log entry.

**Human interaction is optional.** When no gate in a run is configured to require an approval decision, the run can complete without any human input. DevOS can operate fully autonomously when all gate conditions are satisfiable from artifact outcomes alone.

---

## 9. Improvement Cycle (Post-Run)

After a run reaches `ACCEPTED` or `ACCEPTED_WITH_DEBT`, an improvement cycle may be initiated as a separate run.

```
Completed run
  (run_metrics.json available)
         ↓
New improvement cycle run initialized
         ↓
OBSERVE → REFLECT → PROPOSE → HUMAN_DECISION
         ↓
(optional) new change_intent.yaml for next delivery run
```

The improvement cycle is a separate workflow with a separate `run_id`. It must be initiated explicitly — either by a human operator or by an automated trigger. It is not triggered automatically by the MVP runtime. See `docs/roadmap/future_features.md` for the future automation design.

---

## 10. Personal Toolkit Positioning

DevOS is designed to function as a **personal AI development toolkit**.

For a solo developer or small team, the pipeline coordinates:

| Category | Tools / systems |
| --- | --- |
| Planning | Linear, GitHub Issues, gstack, or a local YAML |
| Governance kernel | DevOS runtime |
| AI reasoning | Cursor agents, local LLMs, cloud models |
| Code tools | Git, editor, language toolchain |
| Verification | Pytest, Ruff, Semgrep, or equivalent |

DevOS provides discipline and traceability across these tools without requiring any of them to be integrated directly. The artifact-first model means any tool that writes a valid artifact is compatible.

---

## Further Reading

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture reference
- `docs/architecture/system_map.md` — Concrete module map of all four systems
- `docs/vision/system_architecture.md` — System interaction diagram
- `docs/architecture/agent_contracts.md` — Agent contract model and Agent Runtime integration
- `docs/architecture/integration_model.md` — Artifact-first integration philosophy
- `framework/workflows/` — Workflow state machine definitions
- `framework/agents/` — Agent contract specifications
- `docs/roadmap/future_features.md` — Future pipeline automation capabilities
