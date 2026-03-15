# Event model (v1)

## Responsibility

Define the **canonical, typed event model** for the DevOS framework.

Events are the first-class observability primitive of the runtime. Every significant action
performed by the runtime, orchestrator, or agent must produce a corresponding event. Events
are append-only, immutable after creation, and form the definitive timeline of a run.

This document defines: event types, required fields, producer contracts, and persistence rules.

## Input contract

- **Inputs**: None (framework contract document).
- **Readers**: Runtime implementers, `agent_orchestrator`, `agent_reflector`, humans.

## Output contract

- **Outputs**: Normative rules that bind all compliant runtime implementations.
- Events are persisted to `run_metrics.json` (machine-readable) and/or `orchestrator_log.md`
  (human-readable). See `contracts/runtime_contract.md` Section 5.2 and `artifacts/schemas/run_metrics.schema.json`.

## Non-negotiables

- Every listed required event type **must** be emitted by a compliant runtime.
- Events must never be deleted or modified after creation.
- Events must not be emitted retroactively or inferred from artifact presence.
- No event may substitute for a decision in `decision_log.yaml`.
- Event emission does not replace artifact production; artifacts remain the governance source.

---

## 1. Event envelope

All events share a common envelope. The `payload` field is typed per event type (Section 3).

```json
{
  "event_id":        "<stable-string-id>",
  "event_type":      "<event_type_name>",
  "run_id":          "<run_id>",
  "timestamp":       "<iso-8601>",
  "producer":        "<agent_role | human | runtime>",
  "workflow_state":  "<current_state_at_emission>",
  "causation_event_id":  "<prior_event_id_or_null>",
  "correlation_id":  "<run_id_or_custom_scope_id>",
  "payload":         {}
}
```

### Field rules

| Field | Required | Allowed values |
| --- | --- | --- |
| `event_id` | yes | stable unique string within run |
| `event_type` | yes | one of the defined event types (Section 2) |
| `run_id` | yes | stable run identifier per `contracts/runtime_contract.md` Section 1.1 |
| `timestamp` | yes | ISO-8601 |
| `producer` | yes | `agent_role` name, `human`, or `runtime` |
| `workflow_state` | yes | current state name at emission time |
| `causation_event_id` | yes | id of the event that directly caused this one, or `null` |
| `correlation_id` | yes | `run_id` for delivery runs; improvement cycle may use sub-scope id |
| `payload` | yes | typed object as defined per event type (may be empty `{}`) |

---

## 2. Required and optional event types

### 2.1 Required event types (every compliant runtime must emit these)

| Event type | Producer | Trigger |
| --- | --- | --- |
| `run.started` | `runtime` | A new run is created and assigned a `run_id` |
| `run.completed` | `runtime` | A run reaches a terminal state |
| `run.blocked` | `runtime` | A gate check fails and the run cannot advance |
| `workflow.transition_checked` | `runtime` | A gate check is evaluated (pass or fail) |
| `workflow.transition_completed` | `runtime` | A transition executes successfully |
| `agent.invocation_started` | `runtime` | An agent role is invoked |
| `agent.invocation_completed` | `runtime` | An agent role invocation finishes |
| `artifact.created` | agent role / `runtime` | A new artifact version is written to the run directory |
| `decision.recorded` | `runtime` | A new entry is appended to `decision_log.yaml` |

### 2.2 Optional event types (recommended for richer observability)

| Event type | Producer | Trigger |
| --- | --- | --- |
| `artifact.superseded` | `runtime` | An artifact is superseded by a new version |
| `artifact.validated` | `runtime` | An artifact passes schema/structural validation |
| `artifact.validation_failed` | `runtime` | An artifact fails schema/structural validation |
| `run.rework_started` | `runtime` | A rejected artifact triggers re-invocation |
| `run.resumed` | `runtime` | A run resumes from an interrupted state |

---

## 3. Event payload schemas

### `run.started`

```json
{
  "workflow_id": "<default_workflow | improvement_cycle | ...>",
  "change_intent_id": "<id from change_intent.yaml>",
  "project_inputs": ["domain_scope.md", "..."]
}
```

### `run.completed`

```json
{
  "terminal_state": "<ACCEPTED | ACCEPTED_WITH_DEBT | FAILED | HUMAN_DECISION>",
  "duration_seconds": "<number>"
}
```

### `run.blocked`

```json
{
  "blocked_at_state": "<state>",
  "blocking_reason": "<gate_check | missing_artifact | missing_approval | failed_condition>",
  "missing_artifacts": ["<artifact_name>", "..."],
  "missing_approvals": ["<artifact_name>", "..."],
  "failed_conditions": [
    {
      "field": "<condition_field>",
      "expected": "<expected_value>",
      "actual": "<actual_value_or_missing>"
    }
  ]
}
```

### `workflow.transition_checked`

```json
{
  "from_state": "<state>",
  "to_state": "<state>",
  "result": "<pass | fail>",
  "checks": [
    {
      "check_type": "<input_presence | artifact_presence | approval | condition>",
      "subject": "<artifact_name_or_field>",
      "result": "<pass | fail>",
      "detail": "<string_or_null>"
    }
  ]
}
```

### `workflow.transition_completed`

```json
{
  "from_state": "<state>",
  "to_state": "<state>"
}
```

### `agent.invocation_started`

```json
{
  "agent_role": "<role_name>",
  "input_artifacts": [
    {
      "name": "<artifact_name>",
      "artifact_id": "<id_or_null>",
      "artifact_hash": "<sha256_or_null>"
    }
  ]
}
```

### `agent.invocation_completed`

```json
{
  "agent_role": "<role_name>",
  "outcome": "<completed | blocked | failed>",
  "output_artifacts": [
    {
      "name": "<artifact_name>",
      "artifact_id": "<id>",
      "artifact_hash": "<sha256>"
    }
  ],
  "duration_seconds": "<number>"
}
```

### `artifact.created`

```json
{
  "artifact_name": "<filename>",
  "artifact_id": "<id>",
  "artifact_hash": "<sha256>",
  "owner_role": "<role_name>"
}
```

### `decision.recorded`

```json
{
  "decision_id": "<decision_id>",
  "decision": "<approve | reject | defer>",
  "scope": "<string>",
  "artifact_refs": [
    {
      "artifact": "<filename>",
      "artifact_id": "<id_or_null>",
      "artifact_hash": "<sha256_or_null>"
    }
  ]
}
```

---

## 4. Persistence rules

- Events must be persisted as entries in `run_metrics.json` under `invocation_records`
  (for agent invocation events) and `events` (for all other event types).
- Each event entry maps to the envelope defined in Section 1.
- Events must be appended in chronological order; no reordering.
- If `run_metrics.json` is not used, events may be persisted in `orchestrator_log.md`
  in the Section 4 "Agent invocation records" block; however `run_metrics.json` is
  **strongly recommended** as the machine-readable primary record.

---

## 5. Event ID format

Recommended format: `EVT-<run_id_short>-<monotonic_counter>`.
Example: `EVT-RUN20260310-042`.

The counter must be monotonically increasing within a run. Gaps are allowed (e.g., if
an event was skipped due to an error), but reversals are not.

---

## Assumptions and trade-offs

- Events are batch-oriented and append-only; no streaming infrastructure is required.
- The event model is designed for per-run audit and replay, not for real-time telemetry.
- Optional event types are not required for compliance but significantly improve
  observability and improvement-cycle analysis.
- Event payloads are typed per event type to support deterministic tooling; free-form
  `notes` fields are disallowed in required payload structures.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines canonical typed event model, required/optional event types, payload schemas, and persistence rules. |
