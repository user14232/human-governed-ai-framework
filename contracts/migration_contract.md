# Migration contract (v1)

## Responsibility

Define how projects and runtime implementations migrate from one framework version to another
when a Major change is released.

## Input contract

- **Inputs**: `framework_versioning_policy.md`, the `architecture_change_proposal.md` for
  the Major change, affected artifact schemas and workflow definitions.
- **Readers**: Runtime implementers, project owners, humans.

## Output contract

- **Outputs**: Normative migration process and `migration_record.yaml` artifact contract.

## Non-negotiables

- Migration must not be performed silently. Every migration must produce a `migration_record.yaml`.
- Migration records are append-only. One record per major version transition.
- No migration may silently discard governance history (artifacts, decisions, events).
- Projects that choose not to migrate must remain pinned to the prior framework version
  and must not mix framework versions within a single project.

---

## 1. Migration triggers

A migration is required when:

- The framework releases a Major version change (see `framework_versioning_policy.md` Section 2).
- A project or runtime implementer chooses to adopt the new Major version.

Migration is optional — projects may remain on a prior Major version. However, new framework
features and fixes are not back-ported to prior Major versions.

---

## 2. Migration process

### Step 1: Review the architecture change proposal

Read the `architecture_change_proposal.md` for the Major change. Understand what breaks and why.

### Step 2: Identify affected assets

Check which of the following are affected:
- Workflow definitions (`workflow/`, `improvement/`)
- Artifact schemas (`artifacts/schemas/`)
- Agent contracts (`agents/`)
- Runtime contract (`runtime_contract.md`)
- System invariants (`system_invariants.md`)

### Step 3: Update affected assets

Update each affected asset to the new version. Where artifact schemas change:
- Existing run artifacts produced under the prior version remain valid for their run.
- New runs must use the new schema version.

### Step 4: Produce a migration record

Create a `migration_record.yaml` at the project root (see Section 3 for the schema).

### Step 5: Record human approval

If the migration changes governance-relevant contracts, record human approval in
`decision_log.yaml` before the new framework version is used for production runs.

---

## 3. Migration record contract

Artifact: `migration_record.yaml`
Schema: `artifacts/schemas/migration_record.schema.yaml`

Required fields:

```yaml
id: "<stable-string-id>"
created_at: "<iso-8601>"
from_framework_version: "<vMAJOR.MINOR>"
to_framework_version: "<vMAJOR.MINOR>"
migration_date: "<iso-8601>"
performed_by: "<string>"
architecture_change_proposal_ref: "<proposal-id>"
decision_ref: "<decision_id from decision_log.yaml>"
affected_assets:
  - asset_path: "<path>"
    prior_version: "<version>"
    new_version: "<version>"
    migration_action: "<updated | replaced | removed | no_change>"
prior_run_compatibility:
  existing_runs_valid: "<true | false>"
  notes: "<explicit compatibility note>"
```

---

## 4. Existing run compatibility

When a Major migration occurs:

- Runs completed under the prior framework version remain valid and must be preserved.
- Their artifacts are not required to be updated; they are stamped with the prior
  framework version under which they were produced.
- New runs must be started under the new framework version.
- The improvement cycle may reference prior-version runs as evidence, but must note
  the version boundary explicitly in `reflection_notes.md`.

---

## Assumptions and trade-offs

- This contract defines migration process, not migration tooling. Tooling is project- or
  runtime-owned.
- Projects that mix framework versions within a project do so at their own risk;
  the framework does not define cross-version compatibility for in-flight runs.
- Migration records are project-level artifacts, not run-scoped artifacts.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines migration triggers, process steps, and requirements for migration records when applying Major framework version changes. |
