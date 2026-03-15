# Knowledge query contract (v1)

## Responsibility

Define the **normative contract** for how engineering knowledge accumulated by the framework
is structured, accessed, and maintained over time.

The knowledge layer distinguishes between:

- **Artifact archival**: keeping source artifacts (plans, reviews, decisions, tests) intact
  for auditability. This is already provided by the run directory model.
- **Knowledge extraction**: normalizing specific insights from archived artifacts into
  reusable, queryable `knowledge_record` objects.

This document governs the extraction, indexing, querying, and lifecycle of knowledge records.

## Input contract

- **Inputs**: None (framework contract document).
- **Readers**: Runtime implementers, `agent_reflector`, `agent_improvement_designer`, humans.

## Output contract

- **Outputs**: Normative rules for knowledge layer operations.

## Non-negotiables

- Knowledge records must not be inferred from data; they must be explicitly authored.
- Knowledge records must have traceable provenance to source artifacts and their run IDs.
- Query results must be deterministic given the same index state.
- Knowledge extraction must not modify source artifacts.
- No knowledge record may substitute for a governance artifact or decision.

---

## 1. Knowledge types and their extraction sources

| Knowledge type | Typical source artifact(s) | When to extract |
| --- | --- | --- |
| `decision` | `decision_log.yaml`, `design_tradeoffs.md` | After each human approval |
| `tradeoff` | `design_tradeoffs.md`, `architecture_change_proposal.md` | After plan approval |
| `architecture_rule` | `architecture_contract.md`, `architecture_change_proposal.md` | When contract changes |
| `definition` | `glossary.md`, `domain_rules.md` | When domain inputs are provided or updated |
| `finding` | `review_result.md`, `arch_review_record.md` | After each review pass |
| `goldstandard_example` | `goldstandard_knowledge.md`, `test_report.json` | When project provides examples or test baselines |
| `review_issue` | `review_result.md` | After each review pass |
| `domain_invariant` | `domain_rules.md` | When domain inputs are provided or updated |
| `improvement_hypothesis` | `reflection_notes.md` | After each reflection pass in improvement cycle |

---

## 2. Knowledge record lifecycle

```
extracted (DRAFT knowledge_record)
  → validated by human or agent_reflector
  → status: active
  → (if source artifact superseded) → status: superseded
  → (if no longer applicable) → status: deprecated
```

No implicit lifecycle transitions. All status changes must be authored explicitly.

See `artifacts/schemas/knowledge_record.schema.json` for the full field contract.

---

## 3. Index maintenance

The `knowledge_index.json` must be updated whenever:

1. A new knowledge record is created (append entry with `status: active`).
2. An existing knowledge record is superseded (update status field of old entry to `superseded`,
   append new entry for the new version).
3. A knowledge record is deprecated (update status field of old entry to `deprecated`).

The index is append-only for new entries. Status field updates to existing entries are
permitted only for supersession and deprecation.

---

## 4. Query interface

All knowledge queries operate on `knowledge_index.json` (see
`artifacts/schemas/knowledge_index.schema.json`). Direct file traversal is not required.

### Deterministic query operations

| Operation | Input | Output |
| --- | --- | --- |
| `filter_by_type` | `knowledge_type` | All active records of that type |
| `filter_by_status` | `status` | All records with that status |
| `filter_by_tag` | `tag` | All active records with that tag |
| `filter_by_run_id` | `run_id` | All records derived from that run |
| `lookup_by_knowledge_id` | `knowledge_id` | Single record (any status) |
| `get_history` | `knowledge_id` | All versions, ordered by creation date |

### Prohibited query operations

- Semantic / fuzzy search over knowledge content: prohibited.
  Rationale: non-deterministic results violate the framework's determinism requirements.
- Cross-field heuristic ranking: prohibited.
- Implicit inference of related records: prohibited; use `related_knowledge_ids` in the record.

---

## 5. Provenance requirements

Every knowledge record must include at minimum:

- `run_id` of the run from which the source artifact was produced.
- `artifact` filename and `artifact_id`.
- `artifact_hash` (strongly recommended; omit only with explicit rationale).
- `section_ref` where applicable (section heading or field path in the source artifact).

Knowledge records without provenance are not valid.

---

## 6. Relationship to artifact archival

Knowledge records **supplement** archived artifacts; they do not replace them.

- Archived artifacts: immutable, run-scoped, authoritative for governance.
- Knowledge records: normalized, project-scoped, designed for reuse and query.

An agent or human must always be able to navigate from a knowledge record back to its source
artifact via the provenance chain.

---

## 7. Extraction triggers (normative)

Knowledge extraction is not automatic. The following trigger points are defined as normative
anchor points where extraction **should** occur. Missing a trigger point is permitted but must
be noted as a gap in the run's improvement cycle.

| Trigger | Workflow location | Responsible role | Source artifacts |
| --- | --- | --- | --- |
| Delivery run reaches ACCEPTED or ACCEPTED_WITH_DEBT | `default_workflow.yaml` terminal state | `agent_reflector`, `human` | `review_result.md`, `decision_log.yaml`, `design_tradeoffs.md` |
| Delivery run reaches FAILED | `default_workflow.yaml` terminal state | `agent_reflector`, `human` | `review_result.md`, `arch_review_record.md` (if present) |
| Improvement cycle OBSERVE entry | `improvement_cycle.yaml` OBSERVE | `agent_reflector` | All evidence artifacts from prior run |
| Architecture contract changes | Any run where `architecture_change_proposal.md` is approved | `agent_architecture_guardian`, `human` | `architecture_change_proposal.md`, `design_tradeoffs.md` |
| Domain input updates | Project input update (outside workflow) | `human` | `domain_rules.md`, `glossary.md` |

The trigger points in `default_workflow.yaml` (`post_workflow_activities.knowledge_extraction`)
and `improvement_cycle.yaml` (`optional_activities_at_observe.knowledge_extraction`) are the
primary normative anchors. This section is the canonical definition; those references point here.

---

## Assumptions and trade-offs

- Knowledge extraction is explicitly manual (human or `agent_reflector` / `agent_improvement_designer`).
  Automated extraction requires a separate, explicitly scoped project tool.
- The query interface is intentionally narrow: exact-match only.
  More powerful search is out of scope for the framework layer.
- `knowledge_index.json` is project-scoped (covers all runs of a project), not run-scoped.
  This is intentional: the knowledge layer accumulates across runs.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Added Section 7 (Extraction triggers) to make knowledge extraction anchor points explicit in the workflow model. |
