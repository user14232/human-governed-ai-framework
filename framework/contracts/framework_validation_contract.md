# Framework validation contract (v1)

## Responsibility

Define the **normative self-consistency criteria** that the framework must satisfy at any version.

This contract allows the framework to be validated against itself. It replaces ad-hoc prose
readiness assessments with a deterministic, enumerable checklist that can be evaluated
systematically — either manually or by tooling.

The criteria defined here are the basis for the `docs/v1_readiness_assessment.md` and
any future automated compliance checks.

## Input contract

- **Inputs**: All framework layer documents (normative).
- **Readers**: Framework maintainers, runtime implementers, `agent_orchestrator`, humans.

## Output contract

- **Outputs**: Normative validation criteria. A compliant framework version must pass all
  criteria in each category.

## Non-negotiables

- No criterion may be waived without an explicit `architecture_change_proposal.md`.
- A "PASS with known limitation" is permitted only when the limitation is explicitly listed
  in the readiness assessment under "Remaining known limitations" with a target version.
- Criteria must not be added or removed without incrementing the framework version.

---

## Category 1: Workflow completeness

Each criterion must be satisfied by the workflow definitions.

| ID | Criterion | How to verify |
| --- | --- | --- |
| WF-01 | Every delivery workflow state has at least one outgoing transition defined. | Check `workflow/default_workflow.yaml` transitions. |
| WF-02 | Every terminal state is explicit (`ACCEPTED`, `ACCEPTED_WITH_DEBT`, `FAILED`). | Check `workflow/default_workflow.yaml` states list. |
| WF-03 | Every transition that requires a human approval explicitly lists `human_approval`. | Check all `transitions` blocks in workflow YAML. |
| WF-04 | Every artifact referenced in a transition gate has a corresponding schema file in `artifacts/schemas/`. | Cross-check `artifacts_used` list against schema filenames. |
| WF-05 | Every artifact required as a gate condition has a machine-readable outcome field defined in its schema. | Check schema "Required artifact fields" for `outcome` field. |
| WF-06 | The improvement cycle has a distinct `run_id` scope from the delivery workflow. | Verify `improvement_cycle.yaml` states and `runtime_contract.md` Section 9. |
| WF-07 | The release workflow is either fully normative or explicitly deferred with a target version. | Check `workflow/release_workflow.yaml` or `post_workflow_activities` note. |

---

## Category 2: Artifact contract completeness

Each criterion must be satisfied by the artifact schemas.

| ID | Criterion | How to verify |
| --- | --- | --- |
| AC-01 | Every schema has a `schema_id`, `version`, `artifact_name`, `owner_roles`, and `write_policy`. | Check each file in `artifacts/schemas/`. |
| AC-02 | Every versioned artifact schema defines required `id` and `supersedes_id` fields. | Check "Required artifact fields" section of each versioned schema. |
| AC-03 | Every artifact that carries a gate-controlling outcome field defines that field in "Required artifact fields" with allowed values. | Check `arch_review_record.schema.md` and `review_result.schema.md`. |
| AC-04 | Every schema referenced in a workflow YAML `artifacts_used` list exists in `artifacts/schemas/`. | Cross-check. |
| AC-05 | No two schemas define the same `artifact_name`. | Check uniqueness of `artifact_name` across all schemas. |
| AC-06 | Every approval-bearing schema defines the `decision_id` reference field or refers to `decision_log.yaml` as the authority. | Check schema "Decision reference" or "Decision record" sections. |

---

## Category 3: Agent contract completeness

Each criterion must be satisfied by the agent role contracts.

| ID | Criterion | How to verify |
| --- | --- | --- |
| AR-01 | Every agent role referenced in a workflow state is defined in `agents/`. | Cross-check `v1_readiness_assessment.md` roles table. |
| AR-02 | Every agent role contract defines: Responsibility, Inputs, Outputs, Write policy, Prohibitions, Determinism requirements. | Check each `agents/*.md`. |
| AR-03 | Every artifact listed as an agent output has a schema in `artifacts/schemas/`. | Cross-check agent output lists against schema filenames. |
| AR-04 | No agent role lists an artifact as output that it is not defined as `owner_role` in the schema. | Cross-check agent output vs schema `owner_roles`. |
| AR-05 | No agent role is defined as autonomous-looping. Each role is explicitly single-shot. | Check "Prohibitions" sections for looping prohibition. |

---

## Category 4: Approval and governance

Each criterion must be satisfied by the governance model.

| ID | Criterion | How to verify |
| --- | --- | --- |
| GV-01 | `decision_log.yaml` is the sole normative approval record; no other artifact may substitute for it. | Check `runtime_contract.md` Section 4 and schema ownership. |
| GV-02 | Every gate requiring human approval references `decision_log.yaml` as the evidence source. | Check all `human_approval` blocks in workflow YAMLs. |
| GV-03 | The approval lookup algorithm is deterministic and fully specified. | Check `runtime_contract.md` Section 4.3. |
| GV-04 | Artifact hash-based binding is defined for all approved artifacts. | Check `runtime_contract.md` Section 4.1–4.2. |
| GV-05 | No implicit approvals are permitted; this is stated as a non-negotiable. | Check `system_invariants.md` and `runtime_contract.md`. |

---

## Category 5: Runtime contract completeness

Each criterion must be satisfied by `runtime_contract.md`.

| ID | Criterion | How to verify |
| --- | --- | --- |
| RC-01 | Run identity model (run_id format, scope, uniqueness) is fully defined. | Check `runtime_contract.md` Section 1. |
| RC-02 | Per-run artifact namespace and directory layout is defined. | Check `runtime_contract.md` Section 2. |
| RC-03 | Artifact versioning (supersession, immutability) is fully defined. | Check `runtime_contract.md` Section 3. |
| RC-04 | Gate check procedure is fully defined and covers all check types. | Check `runtime_contract.md` Section 6. |
| RC-05 | Resume and recovery procedure is fully defined. | Check `runtime_contract.md` Section 7. |
| RC-06 | Rework model (FAILED, reject, defer, CHANGE_REQUIRED) is fully defined. | Check `runtime_contract.md` Section 8. |
| RC-07 | Every required event type is listed in `docs/event_model.md`. | Check event model Section 2.1. |
| RC-08 | Agent invocation record schema is defined in `artifacts/schemas/run_metrics.schema.json`. | Check `invocation_records` field in schema. |

---

## Category 6: Observability and knowledge layer

Each criterion must be satisfied by the event model and knowledge layer contracts.

| ID | Criterion | How to verify |
| --- | --- | --- |
| OK-01 | A first-class event model with typed events and payloads is defined. | Check `docs/event_model.md`. |
| OK-02 | Required event types cover all governance-significant runtime actions. | Check `docs/event_model.md` Section 2.1. |
| OK-03 | Event envelope schema is defined. | Check `artifacts/schemas/event_envelope.schema.json`. |
| OK-04 | Knowledge record and index schemas are defined. | Check `artifacts/schemas/knowledge_record.schema.json` and `knowledge_index.schema.json`. |
| OK-05 | Knowledge query contract defines deterministic query operations only. | Check `docs/knowledge_query_contract.md` Section 4. |

---

## Category 7: Extensibility and evolution

Each criterion must be satisfied by extensibility and versioning contracts.

| ID | Criterion | How to verify |
| --- | --- | --- |
| EX-01 | Capability integration contract is defined (when/how capabilities integrate). | Check `capability_integration_contract.md`. |
| EX-02 | Capability registry schema is defined. | Check `artifacts/schemas/capability_registry.schema.yaml`. |
| EX-03 | Framework versioning policy is defined (Major/Minor, breaking change taxonomy). | Check `framework_versioning_policy.md`. |
| EX-04 | Migration contract and migration record schema are defined. | Check `migration_contract.md` and `artifacts/schemas/migration_record.schema.yaml`. |
| EX-05 | Release workflow is either normative or explicitly deferred. | Check `workflow/release_workflow.yaml` or delivery workflow deferred note. |

---

## Evaluation process

To evaluate framework compliance against this contract:

1. For each criterion in each category, verify the "How to verify" check.
2. Record the result as `PASS`, `PASS_WITH_LIMITATION`, or `FAIL`.
3. For `PASS_WITH_LIMITATION`: add an entry to `docs/v1_readiness_assessment.md`
   under "Remaining known limitations" with a target version.
4. For `FAIL`: the framework is not compliant at the claimed version.
   A `FAIL` must be resolved before a version is declared stable.

The `docs/v1_readiness_assessment.md` derives its verdict from this contract.
It must reference criterion IDs from this document for each PASS/FAIL/limitation.

---

## Assumptions and trade-offs

- This contract is evaluated manually in v1. Automated tooling is a future addition.
- Categories 6 and 7 (Observability and Extensibility) are evaluated as v1.1-scope
  additions; prior versions were compliant for categories 1–5 only.
- The contract is itself versioned. Changes to criteria follow the framework versioning policy.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines 35 normative self-consistency criteria across 7 categories (Workflow, Artifact, Agent, Governance, Runtime, Observability, Extensibility). |
