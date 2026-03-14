id: IPROP-0004
supersedes_id: null

## 1) Problem statement (evidence-cited)
- `reflection_notes.md` identifies repeated early gate blocking when required artifacts are not present.
- `run_metrics.json` shows the blocked event occurred before required planning artifacts existed.

## 2) Proposed change
- Introduce a deterministic artifact starter template pack for workflow entry states.
- Keep generation explicit: a command writes files; no implicit auto-generation.

## 3) Expected impact
- Lower initial blocked transitions for first-time runs.
- Slight increase in up-front template maintenance.

## 4) Risks and mitigations
- Risk: template drift from current schema contracts.
- Mitigation: validate templates against schema files in CI and version templates with schema changes.

## 5) Required human decisions
- Approve or reject adoption of the starter template pack.
- Approve rollout scope (default workflow only vs all workflows).

## 6) Decision reference
- decision_id: DEC-0004-001
