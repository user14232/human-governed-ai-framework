id: ACP-RUN20260310-001
supersedes_id: null

# Architecture change proposal: stdlib csv module dependency listing (RUN-20260310-001)

## 1) Summary

Add an explicit entry for Python's stdlib `csv` module to the "External dependencies" section
of `architecture_contract.md`. This formalizes an already-permitted implicit usage and provides
a stable, auditable record for the upgrade policy of this dependency.

## 2) Motivation (evidence)

- Plan item `IP-001` uses Python's stdlib `csv` module.
- `arch_review_record.md` (id: ARR-RUN20260310-001-v1) finding F-003 identified that the
  architecture contract does not explicitly list stdlib csv, creating an undocumented gap
  in the dependency registry.
- Without an explicit entry, future reviewers cannot determine the approved usage boundary
  or upgrade policy.

## 3) Proposed contract changes

Add the following entry to `architecture_contract.md` under "External dependencies":

```
- name: Python stdlib csv module
  purpose: RFC 4180-compliant CSV serialization
  ownership: internal (Python stdlib)
  stability_expectation: stable (governed by Python version policy)
  upgrade_policy: Follows project Python version upgrade; no independent action required.
                  Breaking changes require a new architecture_change_proposal.
```

No existing rules are modified or removed.

## 4) Impact analysis

- Affected layer: Application layer (CsvFormatter in src/application/export/)
- Risk: None. This is a documentation change; no runtime behavior changes.
- Mitigation: N/A

## 5) Alternatives considered

- **Do not list stdlib modules explicitly**: Rejected. Leaves an undocumented assumption and
  weakens the contract's completeness. Any future audit would raise the same gap.

## 6) Decision reference

- `decision_id`: `DEC-0003` (see `decision_log.yaml`)
