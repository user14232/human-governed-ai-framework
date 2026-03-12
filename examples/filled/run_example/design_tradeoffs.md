id: DT-RUN20260310-001
supersedes_id: null

# Design tradeoffs: CSV export (RUN-20260310-001)

## 1) Context

- Change intent reference: `CI-RUN20260310-001`
- Plan reference: `IP-RUN20260310-001`

## 2) Options considered

### Option A — stdlib csv module (selected)

- **id**: opt-A
- **description**: Use Python's stdlib `csv` module to produce RFC 4180-compliant output.
- **pros**:
  - No new external dependency
  - Complies with architecture_contract.md (Forbidden patterns: no external libs without proposal)
  - RFC 4180 quoting handled correctly by stdlib
- **cons**:
  - Limited configurability (delimiter, quoting style fixed to RFC 4180 defaults)
- **constraints**: architecture_contract.md — Forbidden patterns (no new external dependencies without architecture_change_proposal)

### Option B — third-party csv library (e.g., pandas)

- **id**: opt-B
- **description**: Use pandas DataFrame.to_csv() for richer formatting options.
- **pros**:
  - More formatting options
  - Familiar to data engineers
- **cons**:
  - Introduces new external dependency (pandas) — requires architecture_change_proposal
  - Adds significant weight to the service dependency tree
  - Over-engineered for a simple RFC 4180 use case
- **constraints**: architecture_contract.md — Forbidden patterns (new external dependency would require proposal)

## 3) Decision

- **Selected option**: opt-A
- **Rationale**: Stdlib is sufficient for RFC 4180 compliance and avoids any architecture review overhead.
  Option B would require an `architecture_change_proposal.md`, adding governance steps not justified
  by the incremental benefit.

## 4) Assumptions

- **id**: A-001
  - **statement**: The Report domain object exposes a stable `.to_dict()` or equivalent iterable
    interface that CsvFormatter can consume without modifying the domain model.
  - **risk if false**: CsvFormatter would need to access domain internals directly, violating
    layer boundaries. Would require a new plan item.
  - **how to validate**: Review domain model interface before implementation (IP-001).

- **id**: A-002
  - **statement**: Existing fixture reports are representative of production report shapes
    and do not contain untested edge cases in field values.
  - **risk if false**: RFC 4180 edge cases (embedded commas, double-quotes, newlines) may be
    present in production but absent from tests.
  - **how to validate**: Manual inspection of fixture reports during test authoring (IP-003).

## 5) Risks and mitigations

- **id**: R-001
  - **risk**: Existing export endpoint has JSON-specific logic that is not cleanly separated;
    adding a CSV branch may introduce test failures across both paths.
  - **mitigation**: Write regression tests for the JSON path explicitly in IP-004 before
    modifying the endpoint handler.

- **id**: R-002
  - **risk**: RFC 4180 requires specific handling of CRLF line endings; stdlib default is
    system-dependent unless explicitly set.
  - **mitigation**: CsvFormatter must explicitly set `lineterminator='\r\n'` per RFC 4180.
    This is a required constraint in IP-001.

## 6) Decision reference

- `decision_id`: `DEC-0002` (see `decision_log.yaml`)

## Determinism requirements

- All assumptions are explicit; no implicit behavior assumed.
- Any change to this decision creates a new version (supersedes_id reference required).
