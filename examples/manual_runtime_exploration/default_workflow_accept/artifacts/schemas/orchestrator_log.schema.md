# Schema: `orchestrator_log.md` (v1)

## Schema metadata

- **schema_id**: `orchestrator_log`
- **version**: `v1`
- **artifact_name**: `orchestrator_log.md`

## Responsibility

Record deterministic orchestration decisions, gate outcomes, and agent invocation records
as a human-readable audit trace. This artifact is the alternative normative location for
agent invocation records when `run_metrics.json` is not used
(see `contracts/runtime_contract.md` Section 5.2).

## Owner roles

- `agent_orchestrator`

## Allowed readers

- `human`
- `agent_reviewer`
- `agent_release_manager`
- `agent_reflector`

## Write policy

- **Mutability**: append-only preferred (or versioned if append-only is not supported)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `run_id`: stable run identifier (see `contracts/runtime_contract.md` Section 1.1)

## Required sections (MUST appear in this order)

### 1) Run identifier

- Stable `run_id` string.

### 2) Workflow reference

- `default_workflow.yaml` version/id.

### 3) Gate checks (append-only entries)

Each gate-check entry must include:

- timestamp (ISO-8601)
- from_state â†’ to_state
- required artifacts present: yes/no (list missing)
- required approvals present in `decision_log.yaml`: yes/no (list decision_id refs)
- outcome: proceed | stop

### 4) Agent invocation records (append-only entries)

Required per `contracts/runtime_contract.md` Section 5.2 when `run_metrics.json` is not used as the
primary machine-readable record. Each invocation entry must include:

- `invocation_id`: stable string
- `run_id`: same as run identifier above
- `agent_role`: role name
- `workflow_state`: current state at time of invocation
- `invoked_at`: ISO-8601 timestamp
- `input_artifacts`: list of `{name, artifact_id, artifact_hash}`
- `output_artifacts`: list of `{name, artifact_id, artifact_hash}`
- `outcome`: `completed | blocked | failed`
- `notes`: optional string

## Determinism requirements

- No hidden transitions.
- Gate outcomes must be reproducible from referenced artifacts and `decision_log` entries.
- Invocation records must cover every agent role executed in the run.
- If both `orchestrator_log.md` and `run_metrics.json` exist for a run, `run_metrics.json`
  is the normative machine-readable record for invocations; this log is the human-readable trace.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Agent invocation records section per runtime_contract.md Section 5.2. Updated Determinism requirements. |
