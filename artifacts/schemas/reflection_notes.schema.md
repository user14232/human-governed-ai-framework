# Schema: `reflection_notes.md` (v1)

## Schema metadata

- **schema_id**: `reflection_notes`
- **version**: `v1`
- **artifact_name**: `reflection_notes.md`

## Responsibility

Record structured, evidence-cited reflection notes for the improvement cycle.

## Owner roles

- `agent_reflector`

## Allowed readers

- `human`
- `agent_improvement_designer`
- `agent_orchestrator`

## Write policy

- **Mutability**: versioned
- **Overwrite allowed**: no

## Required sections

### Evidence referenced

- `run_metrics.json` (run_id/ref, if present)
- `test_report.json` (run_id/ref)
- `review_result.md` (version/ref)

### Observations (facts)

- Bullet list; each item must cite evidence.

### Hypotheses (explicitly labeled)

- Bullet list; each item must cite what it is based on and what would falsify it.

### Open questions

- Bullet list.

## Determinism requirements

- Keep observations separate from hypotheses.
- No new requirements or changes proposed here.
