# Artifact status model (framework guidance, v1.1)

## Responsibility

Define a **canonical, reusable status vocabulary** for **versioned artifacts** to improve lifecycle
clarity, tooling interoperability, and governance — **without introducing implicit transitions** or
automatic progression.

## Input contract

- **Inputs**: None (framework guidance document).
- **Readers**: All roles and humans.

## Output contract

- **Outputs**: A canonical status vocabulary that projects and framework artifacts **may** adopt **explicitly**.
- **Non-output**: This document does **not** change any existing artifact schema requirements and
  introduces **no enforcement** by itself.

## Scope (where this model applies)

### Applies to (intended users)

This status model is intended for artifacts that are **versioned** or **immutable-preferred**
contracts/results where a lifecycle is meaningful, e.g.:

- planning and governance artifacts (e.g. `implementation_plan.yaml`, `design_tradeoffs.md`,
  `architecture_change_proposal.md`, `improvement_proposal.md`)
- review and release artifacts (e.g. `review_result.md`, `release_notes.md`, `release_metadata.json`)

### Does not apply to (explicit exclusions)

This status model is **not** intended for artifacts that are primarily **append-only records** or
**factual run outputs** where “status” would be ambiguous or duplicative, e.g.:

- append-only audit logs and decision records (e.g. `decision_log.yaml`, `orchestrator_log.md`)
- run outputs/measurements (e.g. `run_metrics.json`, `test_report.json`)

Rationale: for append-only records, lifecycle is expressed by **new entries** (and, if needed,
explicit superseding references), not by mutating a status field.

## Canonical statuses

### Mandatory statuses (canonical set)

The framework’s canonical set consists of the following statuses:

- **`DRAFT`**: Work-in-progress; not ready for human approval or gating.
- **`PROPOSED`**: Presented for human decision/approval; content is complete enough to decide.
- **`APPROVED`**: Explicitly approved by a human decision authority (approval must be recorded when
  the workflow requires it).
- **`SUPERSEDED`**: Replaced by a newer, explicitly referenced version (the superseding reference must be explicit).
- **`DEPRECATED`**: Still exists for traceability, but should not be used for new work; replacement guidance should be explicit.

### Optional statuses (allowed extensions)

Optional statuses may be used **only if explicitly defined by the adopting project**, and must not be
used for implicit gating. Recommended optional statuses:

- **`REJECTED`**: A proposal was explicitly rejected; it remains for auditability.
- **`WITHDRAWN`**: The owner withdrew a proposal before decision.

## Status change policy (no implicit transitions)

### Non-negotiables

- **No implicit status changes**: a status may change only through an explicit, authored update
  (typically a new version of the artifact).
- **No automatic progression**: tools and agents must not “advance” status by inference.
- **No hidden governance**: any status used as an approval signal must be backed by an explicit
  `decision_log.yaml` entry when the workflow requires human approval.

### How to represent status (non-enforcing guidance)

Because existing schemas do not require a `status` field, adopters should treat status as **optional
metadata** and represent it in a way that is:

- explicit
- stable across versions
- easy to validate deterministically

Recommended representations:

- **Markdown artifacts**: include a single line near the top, e.g. `Status: APPROVED`
- **YAML/JSON artifacts**: include a top-level `status: <STATUS>` only if the project’s validator
  permits additional fields

Important: absence of a status must never be interpreted as an implicit status.

## Suggested lifecycle (explicit, not automatic)

Allowed transitions (by intent) for the canonical statuses:

- `DRAFT` → `PROPOSED`
- `PROPOSED` → `APPROVED` | `REJECTED` (optional) | `WITHDRAWN` (optional)
- `APPROVED` → `SUPERSEDED` | `DEPRECATED`
- `SUPERSEDED` → (terminal)
- `DEPRECATED` → (terminal)

Notes:

- Transitioning to `SUPERSEDED` requires an explicit reference to the newer artifact version (or
  identifier) in the superseding artifact and/or in the decision log entry.
- `DEPRECATED` should include explicit replacement guidance (which artifact/version should be used instead).

## Adoption guidance by artifact type (framework-wide)

### Artifacts that SHOULD adopt this model (if a project wants explicit lifecycle)

- `implementation_plan.yaml` (versioned)
- `design_tradeoffs.md` (versioned)
- `test_design.yaml` (versioned)
- `review_result.md` (versioned)
- `architecture_change_proposal.md` (versioned)
- `improvement_proposal.md` (versioned)
- `reflection_notes.md` (versioned)
- `release_notes.md` / `release_metadata.json` (versioned)

### Artifacts that SHOULD NOT adopt this model

- `decision_log.yaml` (append-only audit record; superseding is represented by new entries referencing prior `decision_id`)
- `orchestrator_log.md` (append-only preferred run trace)
- `test_report.json` and `run_metrics.json` (run outputs; lifecycle is per-run, not via status)

## Explicitly not solved here

- No schema updates are introduced in v1.1. Making `status` required (or machine-validated) would
  require an explicit schema evolution proposal and coordinated tooling changes.
