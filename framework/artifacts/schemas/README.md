# Artifact schemas (templates) — v1

## Responsibility

Provide **deterministic, minimal templates** for framework artifacts.
Artifacts are the only legal communication channel between roles.

## Naming convention (v1)

- For YAML artifacts: `<artifact>.schema.yaml`
- For JSON artifacts: `<artifact>.schema.json`
- For Markdown artifacts: `<artifact>.schema.md` (required sections + rules)

## Decision / approval records

- `decision_log.yaml` is the default framework approval record (append-only).
- Schema: `decision_log.schema.yaml`

## Contract shape (applies to all schemas)

Each schema template must define:

- **schema_id** and **version**
- **artifact_name** (the produced artifact filename)
- **owner roles** (who may write)
- **readers** (who may read)
- **write policy** (append-only / overwrite allowed)
- **required content** (fields or sections)
- **determinism requirements** (stable IDs, traceability)

## Note

These are templates; projects may evolve them, but changes must be explicit and versioned.
