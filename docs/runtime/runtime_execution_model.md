# Runtime Execution Model

## Runtime Responsibilities

The DevOS runtime is responsible for deterministic workflow execution over a workspace state.  
Core responsibilities include:

- Loading workflow definitions
- Evaluating gate conditions
- Invoking agents for workflow steps
- Recording artifacts for each run
- Emitting runtime events
- Transitioning workflow states until completion

## Run Lifecycle

A typical run follows this ordered lifecycle:

`run start` -> `workflow load` -> `gate evaluation` -> `agent invocation` -> `artifact creation` -> `event emission` -> `state transition` -> `terminal state`

This lifecycle repeats state-by-state until the run reaches a terminal state (for example success, blocked, or failure according to workflow rules).

## Role of the Workflow Engine

Key runtime engine modules:

- `runtime/engine/workflow_engine.py`: Interprets workflow definitions and manages valid workflow progression semantics.
- `runtime/engine/run_engine.py`: Coordinates run-level execution, including progression through states, gate checks, and invocation flow.

Together, these modules provide the execution backbone that maps workflow definitions to concrete run behavior.

## Event Emission

Runtime events are emitted during execution to provide traceability of run behavior and state changes.

Event writing is handled through:

- `runtime/events/event_system.py`

These events form the execution audit trail for lifecycle transitions, gate outcomes, invocations, and artifact-related milestones.

## Artifact Persistence

Run outputs are persisted through runtime store components:

- `runtime/store/file_store.py`
- `runtime/store/run_store.py`

These modules provide file-based and run-level persistence primitives so each run's artifacts and metadata are durably recorded and retrievable.
