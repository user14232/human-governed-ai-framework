# Framework versioning policy (v1)

## Responsibility

Define how the DevOS framework version evolves, what constitutes a breaking change,
and what compatibility promises are made to runtime implementers and projects.

## Input contract

- **Inputs**: None (framework governance document).
- **Readers**: Runtime implementers, project owners, `agent_orchestrator`, humans.

## Output contract

- **Outputs**: Normative versioning rules and compatibility guarantees.

## Non-negotiables

- No framework change may be applied silently. All changes follow the change classification
  and process defined in this document.
- Version numbers must be updated in the affected documents when a change is applied.
- An `architecture_change_proposal.md` is required for any Major change to the framework.

---

## 1. Version scheme

The framework uses a two-part version scheme: `vMAJOR.MINOR`.

| Version part | Meaning |
| --- | --- |
| MAJOR | Breaking change. Runtime must be updated to remain compliant. |
| MINOR | Backward-compatible addition or clarification. Runtime remains compliant without update. |

Patch-level fixes (typos, clarifications that do not change behavior) do not require a version bump
but must be noted in the relevant document's change log section.

---

## 2. Change classification

### Major changes (breaking)

A change is Major if a runtime or project that was compliant with the prior version would
become non-compliant under the new version without modification.

Examples:
- Adding a required field to an existing artifact schema.
- Adding a required event type to the event model.
- Adding a required gate to an existing workflow transition.
- Renaming an artifact type that existing contracts reference.
- Removing an allowed value from an enumerated field.

### Minor changes (backward-compatible)

A change is Minor if a compliant runtime or project remains fully compliant without modification.

Examples:
- Adding a new optional field to an artifact schema.
- Adding a new optional event type.
- Adding a new workflow (without affecting existing workflows).
- Adding new documentation or examples.
- Clarifying existing rules without changing behavior.
- Deprecating a feature (deprecation is not removal).

---

## 3. Change process

### Minor changes

1. Identify the affected documents.
2. Make the change.
3. Increment the MINOR version in each affected document's metadata.
4. Update `readme.md` v1 scope table to reflect the new version.
5. No `architecture_change_proposal.md` required.
6. No human approval required unless the change affects a normative contract
   (`system_invariants.md`, `runtime_contract.md`, or a workflow YAML).

### Major changes

1. Create an `architecture_change_proposal.md` (schema: `artifacts/schemas/architecture_change_proposal.schema.md`).
2. Record human approval in `decision_log.yaml`.
3. Apply the change to all affected documents.
4. Increment the MAJOR version in each affected document's metadata.
5. Create a migration record (see `migration_contract.md`).
6. Update the compatibility table in Section 4 of this document.
7. Update `readme.md` v1 scope table.

---

## 4. Compatibility table

This table records the compatibility history of the framework.

| Framework version | Compatible runtime versions | Compatible project versions | Notes |
| --- | --- | --- | --- |
| v1.0 | runtime v1.0+ | project v1.0+ | Initial release |
| v1.1 | runtime v1.1+ (v1.0 runtime compliant for delivery only, not release) | project v1.0+ | Adds normative release workflow |

---

## 5. Deprecation policy

A deprecated feature:
- Remains functional and fully specified until the next Major version.
- Must be marked with a `Deprecated since: vX.Y` note in the relevant document.
- Must include explicit replacement guidance.
- Must not be silently removed; removal requires a Major version change and a migration record.

---

## 6. Document versioning

Each framework document carries a version in its metadata (`version: v1`, `version: v1.1`, etc.).

When a document is updated:
- Its metadata version must be incremented to reflect the change classification.
- A brief change log entry must be added at the bottom of the document under `## Change log`.

---

## Assumptions and trade-offs

- The framework does not define a deprecation window (time-based). Deprecation is driven by
  explicit Major version changes, not by a timer.
- Runtime implementers are expected to track the compatibility table and update their
  implementations when a Major change is released.
- Projects that have not updated their domain inputs remain compatible with any Minor change.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines vMAJOR.MINOR scheme, breaking/compatible change taxonomy, change process, compatibility table, and deprecation policy. |
