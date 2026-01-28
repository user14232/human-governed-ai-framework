# Schema: `orchestrator_log.md` (v1)

## Schema metadata

- **schema_id**: `orchestrator_log`
- **version**: `v1`
- **artifact_name**: `orchestrator_log.md`

## Responsibility

Record deterministic orchestration decisions and gate outcomes as a human-readable audit trace.

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

## Required sections (MUST appear in this order)

### 1) Run identifier

- Stable `run_id` string.

### 2) Workflow reference

- `default_workflow.yaml` version/id.

### 3) Gate checks (append-only entries)

Each entry must include:

- timestamp (ISO-8601)
- from_state → to_state
- required artifacts present: yes/no (list missing)
- required approvals present in `decision_log.yaml`: yes/no (list decision_id refs)
- outcome: proceed | stop

## Determinism requirements

- No hidden transitions.
- Gate outcomes must be reproducible from referenced artifacts and decision_log entries.
