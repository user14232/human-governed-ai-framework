# Reference run example (non-normative)

This directory contains a complete, filled example of a delivery run.
It demonstrates the end-to-end artifact flow defined by the framework, including:

- a happy-path delivery (INIT â†’ ACCEPTED)
- a FAILED review and rework using artifact versioning
- a CHANGE_REQUIRED architecture check

## Run metadata

- **run_id**: `RUN-20260310-001`
- **scenario**: Add CSV export capability to the report generation module

## Workflow path demonstrated

```
INIT
  â†’ PLANNING            (human approval: implementation_plan, design_tradeoffs)
  â†’ ARCH_CHECK          (arch_review_record: CHANGE_REQUIRED first, then PASS after proposal approval)
  â†’ TEST_DESIGN         (human approval: test_design)
  â†’ BRANCH_READY        (branch_status evidence)
  â†’ IMPLEMENTING
  â†’ TESTING             (test_report: first run FAILED â†’ rework â†’ second run PASSED)
  â†’ REVIEWING
  â†’ ACCEPTED
```

## Files in this run

| File | Stage | Notes |
| --- | --- | --- |
| `change_intent.yaml` | INIT | Human-authored input |
| `implementation_plan.yaml` | PLANNING | Produced by agent_planner |
| `design_tradeoffs.md` | PLANNING | Produced by agent_planner |
| `arch_review_record.v1.md` | ARCH_CHECK | First record: CHANGE_REQUIRED |
| `architecture_change_proposal.md` | ARCH_CHECK | Produced after CHANGE_REQUIRED |
| `arch_review_record.md` | ARCH_CHECK | Second record: PASS (after proposal approved) |
| `test_design.yaml` | TEST_DESIGN | Produced by agent_test_designer |
| `branch_status.md` | BRANCH_READY | Produced by agent_branch_manager |
| `test_report.v1.json` | TESTING | First run: 2 failures |
| `test_report.json` | TESTING | Second run: all pass |
| `review_result.md` | REVIEWING | Produced by agent_reviewer |
| `decision_log.yaml` | all gates | Append-only approval record |

## Normative references

- Framework workflow: `workflow/default_workflow.yaml`
- Runtime contract: `contracts/runtime_contract.md`
- Schemas: `artifacts/schemas/`
