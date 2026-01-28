# Workflow state machine (visualization, non-normative)

This document provides a **visualization** of the workflow state machines defined by:

- `workflow/default_workflow.yaml` (primary delivery cycle)
- `improvement/improvement_cycle.yaml` (secondary improvement cycle)

It is **derivative** and **non-normative**. The YAML files remain the source of truth.

## Primary delivery cycle (`workflow/default_workflow.yaml`)

```mermaid
stateDiagram-v2
  [*] --> INIT

  INIT --> PLANNING: inputs_present=true
  INIT --> FAILED: inputs_present=false

  PLANNING --> ARCH_CHECK: artifacts + human_approval (implementation_plan, design_tradeoffs)
  ARCH_CHECK --> TEST_DESIGN
  TEST_DESIGN --> BRANCH_READY: artifacts + human_approval (test_design)
  BRANCH_READY --> IMPLEMENTING
  IMPLEMENTING --> TESTING
  TESTING --> REVIEWING: artifacts (test_report)

  REVIEWING --> ACCEPTED: review_outcome=ACCEPTED
  REVIEWING --> ACCEPTED_WITH_DEBT: review_outcome=ACCEPTED_WITH_DEBT + human_approval (review_result)
  REVIEWING --> FAILED: review_outcome=FAILED

  ACCEPTED --> [*]
  ACCEPTED_WITH_DEBT --> [*]
  FAILED --> [*]
```

Notes (derived from YAML, not additional logic):

- Transitions that list `human_approval` require explicit entries in `decision_log.yaml` (no implicit approvals).
- `ARCH_CHECK` is a governance gate; if an architecture change is required, it must be captured explicitly via `architecture_change_proposal.md`.

## Secondary improvement cycle (`improvement/improvement_cycle.yaml`)

```mermaid
stateDiagram-v2
  [*] --> OBSERVE

  OBSERVE --> REFLECT: artifacts (run_metrics, test_report, review_result)
  REFLECT --> PROPOSE: artifacts (reflection_notes)
  PROPOSE --> HUMAN_DECISION: artifacts + human_approval (improvement_proposal) + decision_log

  HUMAN_DECISION --> [*]
```

Notes (derived from YAML, not additional logic):

- The improvement cycle produces proposals only; it never applies changes automatically.
- Outcomes may include an optional new `change_intent.yaml`, but only via explicit human decision recorded in `decision_log.yaml`.
