# DevOS Runtime – Module Architecture

**Document type**: Implementation architecture specification  
**Version**: v1  
**Date**: 2026-03-12  
**Status**: Active  
**Derived from**: `docs/archive/phase3_runtime_realization_plan.md` v1

> **MVP scope**: This document defines the full module architecture. The active MVP runtime covers sections 4–8 (run_engine, workflow_engine, gate_evaluator, artifact_system, decision_system, event_system, CLI). Section 7.8 (knowledge extraction hooks) is active in the MVP as an event-emitting stub only — no extraction is performed. Capabilities, autonomous loops, and semantic validation are future extension points documented in `docs/roadmap/future_features.md`.  

---

## 0. Document purpose and scope

This document defines the **concrete module architecture** for implementing the DevOS runtime.

It translates the seven runtime components defined in `phase3_runtime_realization_plan.md`
(Sections 4.1–4.7) into a specific module decomposition with:

- Directory layout and module boundaries
- Responsibility of each module (one sentence)
- Public interface (inputs and return types)
- Inbound and outbound dependencies
- Shared type definitions
- Key design decisions with rationale

This document is **implementation-agnostic with respect to language** where possible.
Signatures are written in a Python-style pseudocode for concreteness. A compliant
implementation may use any language provided it satisfies the contracts.

---

## 1. Module inventory

| Module ID | Path | Maps to plan section |
| --- | --- | --- |
| `types` | `runtime/types/` | Shared across all |
| `framework` | `runtime/framework/` | §3.4 — contract loading |
| `store` | `runtime/store/` | §2.1 — filesystem layout |
| `run_engine` | `runtime/engine/run_engine` | §4.1 |
| `workflow_engine` | `runtime/engine/workflow_engine` | §4.2 |
| `gate_evaluator` | `runtime/engine/gate_evaluator` | §4.2.1 |
| `artifact_system` | `runtime/artifacts/artifact_system` | §4.4 |
| `invocation_layer` | `runtime/agents/invocation_layer` | §4.3 |
| `decision_system` | `runtime/decisions/decision_system` | §4.5 |
| `event_system` | `runtime/events/event_system` | §4.6 |
| `extraction_hooks` | `runtime/knowledge/extraction_hooks` | §4.7 |
| `cli` | `runtime/cli` | Entry point |

---

## 2. Directory layout

```
devos-runtime/
│
├── runtime/
│   │
│   ├── types/
│   │   ├── run.py              # RunId, RunContext, RunState, TerminalState
│   │   ├── workflow.py         # WorkflowDefinition, State, Transition, RequiresBlock
│   │   ├── artifact.py         # ArtifactRef, ArtifactId, ArtifactHash, ArtifactStatus
│   │   ├── event.py            # EventEnvelope, EventType, all payload dataclasses
│   │   ├── decision.py         # DecisionEntry, DecisionType
│   │   └── gate.py             # GateResult, GateCheckDetail, CheckType
│   │
│   ├── framework/
│   │   ├── workflow_loader.py  # Parse workflow/*.yaml → WorkflowDefinition
│   │   ├── schema_loader.py    # Parse artifacts/schemas/* → ArtifactSchema
│   │   └── agent_loader.py     # Parse agents/*.md → AgentContract
│   │
│   ├── store/
│   │   ├── run_store.py        # Run directory creation, enumeration, path resolution
│   │   └── file_store.py       # Atomic write, rename, hash-from-disk, read operations
│   │
│   ├── engine/
│   │   ├── run_engine.py       # Run lifecycle: init, resume, terminal detection
│   │   ├── workflow_engine.py  # State machine traversal and transition execution
│   │   └── gate_evaluator.py   # Four-step gate check procedure
│   │
│   ├── artifacts/
│   │   └── artifact_system.py  # Storage, hashing, versioning, immutability enforcement
│   │
│   ├── agents/
│   │   └── invocation_layer.py # Single-shot agent dispatch, permission enforcement
│   │
│   ├── decisions/
│   │   └── decision_system.py  # decision_log.yaml reader, rework trigger, gate signal
│   │
│   ├── events/
│   │   ├── event_system.py     # Event construction, ID assignment, routing
│   │   └── metrics_writer.py   # Append-only run_metrics.json writer
│   │
│   └── knowledge/
│       └── extraction_hooks.py # Trigger point detection and log entry
│
├── tests/
│   ├── unit/                   # Per-module unit tests
│   ├── integration/            # Cross-module tests (gate matrix, rework path)
│   └── e2e/                    # End-to-end workflow tests
│
└── cli.py                      # Entry point: devos run | resume | status | check
```

---

## 3. Module dependency graph

Arrows denote "depends on / calls". The filesystem (`runs/<run_id>/`) is not shown
as a module dependency because it is the shared data substrate for all modules, not
a runtime call dependency.

```
cli
 └─► run_engine
       ├─► workflow_engine
       │     └─► gate_evaluator
       │           ├─► artifact_system  (reads artifacts for validation/hash)
       │           └─► decision_system  (reads decision_log for approval lookup)
       ├─► invocation_layer
       │     └─► artifact_system        (registers outputs, enforces write perms)
       ├─► artifact_system
       ├─► decision_system
       ├─► event_system                 (called by all components above)
       └─► extraction_hooks             (called on terminal state)

framework/   ──► (loaded once at run start, passed into components as config)
store/       ──► (used by artifact_system, run_engine, event_system, decision_system)
types/       ──► (imported by all modules; no dependencies of its own)
```

**Dependency rules**:

1. `types/` has no inbound dependencies from runtime modules. It is the stable foundation.
2. `framework/` has no runtime module dependencies. It reads files and returns parsed types.
3. `store/` has no runtime module dependencies. It abstracts filesystem operations only.
4. `event_system` is called by every other component but depends on nothing except `types/`
   and `store/`. This prevents circular dependencies.
5. No module other than `run_engine` calls `workflow_engine` directly.
6. `gate_evaluator` is the only module that jointly reads artifacts and decision log.

---

## 4. Shared types (`runtime/types/`)

All types are value objects: immutable, no methods beyond construction and equality.
No shared mutable state anywhere.

### 4.1 `types/run.py`

```python
RunId = str                  # format: RUN-<YYYYMMDD>-<suffix>

@dataclass(frozen=True)
class RunContext:
    run_id:         RunId
    project_root:   Path     # absolute path to project root
    run_dir:        Path     # absolute path to runs/<run_id>/
    artifacts_dir:  Path     # absolute path to runs/<run_id>/artifacts/
    workflow_def:   WorkflowDefinition
    current_state:  str      # name of current workflow state

@dataclass(frozen=True)
class RunState:
    run_id:         RunId
    current_state:  str
    is_terminal:    bool
    last_event_id:  str | None

TERMINAL_STATES: frozenset[str] = frozenset({
    "ACCEPTED", "ACCEPTED_WITH_DEBT", "FAILED", "HUMAN_DECISION",
    "RELEASED", "RELEASE_FAILED",
})
```

### 4.2 `types/workflow.py`

```python
@dataclass(frozen=True)
class RequiresBlock:
    inputs_present:  bool | None          # None = not specified
    artifacts:       tuple[str, ...]      # artifact filenames
    human_approval:  tuple[str, ...]      # artifact filenames requiring approval
    conditions:      dict[str, str]       # field_name → expected_value

@dataclass(frozen=True)
class Transition:
    from_state:  str
    to_state:    str
    requires:    RequiresBlock
    notes:       str | None

@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id:  str
    version:      str
    states:       tuple[str, ...]
    transitions:  tuple[Transition, ...]
    artifacts_used: tuple[str, ...]
```

### 4.3 `types/artifact.py`

```python
ArtifactId   = str   # format: <prefix>-<run-id-short>-<monotonic>
ArtifactHash = str   # SHA-256 hex digest

@dataclass(frozen=True)
class ArtifactRef:
    name:          str
    artifact_id:   ArtifactId | None
    artifact_hash: ArtifactHash | None

class ArtifactStatus(str, Enum):
    VALID      = "valid"
    INVALID    = "invalid"
    APPROVED   = "approved"
    SUPERSEDED = "superseded"

@dataclass(frozen=True)
class ArtifactSchema:
    artifact_type:      str          # e.g. "implementation_plan"
    file_format:        str          # "yaml" | "json" | "markdown"
    required_fields:    tuple[str, ...]
    required_sections:  tuple[str, ...]   # markdown only
    allowed_outcomes:   tuple[str, ...] | None
    owner_roles:        tuple[str, ...]
```

### 4.4 `types/event.py`

```python
class EventType(str, Enum):
    RUN_STARTED                  = "run.started"
    RUN_COMPLETED                = "run.completed"
    RUN_BLOCKED                  = "run.blocked"
    RUN_RESUMED                  = "run.resumed"
    RUN_REWORK_STARTED           = "run.rework_started"
    WORKFLOW_TRANSITION_CHECKED  = "workflow.transition_checked"
    WORKFLOW_TRANSITION_COMPLETED = "workflow.transition_completed"
    AGENT_INVOCATION_STARTED     = "agent.invocation_started"
    AGENT_INVOCATION_COMPLETED   = "agent.invocation_completed"
    ARTIFACT_CREATED             = "artifact.created"
    ARTIFACT_SUPERSEDED          = "artifact.superseded"
    ARTIFACT_VALIDATED           = "artifact.validated"
    ARTIFACT_VALIDATION_FAILED   = "artifact.validation_failed"
    DECISION_RECORDED            = "decision.recorded"

@dataclass(frozen=True)
class EventEnvelope:
    event_id:           str          # EVT-<run_id_short>-<monotonic>
    event_type:         EventType
    run_id:             RunId
    timestamp:          str          # ISO-8601
    producer:           str          # agent_role name | "human" | "runtime"
    workflow_state:     str
    causation_event_id: str | None
    correlation_id:     str          # run_id for delivery runs
    payload:            dict         # typed per EventType (see docs/event_model.md §3)
```

### 4.5 `types/decision.py`

```python
class DecisionType(str, Enum):
    APPROVE = "approve"
    REJECT  = "reject"
    DEFER   = "defer"

@dataclass(frozen=True)
class DecisionReference:
    artifact:      str
    artifact_id:   ArtifactId | None
    artifact_hash: ArtifactHash | None

@dataclass(frozen=True)
class DecisionEntry:
    decision_id:  str
    decision:     DecisionType
    scope:        str
    timestamp:    str                        # ISO-8601
    actor:        str                        # human identity string
    references:   tuple[DecisionReference, ...]
```

### 4.6 `types/gate.py`

```python
class CheckType(str, Enum):
    INPUT_PRESENCE    = "input_presence"
    ARTIFACT_PRESENCE = "artifact_presence"
    APPROVAL          = "approval"
    CONDITION         = "condition"

class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"

@dataclass(frozen=True)
class GateCheckDetail:
    check_type: CheckType
    subject:    str           # artifact name or field name
    result:     CheckResult
    detail:     str | None

@dataclass(frozen=True)
class GateResult:
    transition:    Transition
    result:        CheckResult    # aggregate: pass only if all checks pass
    checks:        tuple[GateCheckDetail, ...]
```

---

## 5. Framework loaders (`runtime/framework/`)

Read-only. Parse framework contracts into typed structures.
Called once at run initialization; results are passed into components via `RunContext` or
direct arguments. No framework loader is called during the main execution loop.

### 5.1 `framework/workflow_loader.py`

```python
def load_workflow(workflow_path: Path) -> WorkflowDefinition:
    """
    Parse a workflow YAML file and return a WorkflowDefinition.
    Raises ParseError if the file is malformed or missing required fields.
    """
```

### 5.2 `framework/schema_loader.py`

```python
def load_schema(schema_path: Path) -> ArtifactSchema:
    """
    Parse an artifact schema file (YAML or Markdown) and return an ArtifactSchema.
    """

def load_all_schemas(schemas_dir: Path) -> dict[str, ArtifactSchema]:
    """
    Load all schemas from artifacts/schemas/ and return a mapping of
    artifact_type → ArtifactSchema.
    """
```

### 5.3 `framework/agent_loader.py`

```python
@dataclass(frozen=True)
class AgentContract:
    role_id:          str
    input_artifacts:  tuple[str, ...]   # read-only inputs
    output_artifacts: tuple[str, ...]   # artifacts the agent may produce
    owned_artifacts:  tuple[str, ...]   # artifacts the agent has write permission for
    workflow_states:  tuple[str, ...]   # states where this agent is invoked

def load_agent_contract(agent_path: Path) -> AgentContract:
    """
    Parse an agent role Markdown file and return its contract.
    Extracts: Inputs, Outputs, Write policy sections.
    """

def load_all_agent_contracts(agents_dir: Path) -> dict[str, AgentContract]:
    """
    Load all agent contracts and return a mapping of role_id → AgentContract.
    """
```

---

## 6. Store layer (`runtime/store/`)

Pure filesystem abstraction. No framework semantics.

### 6.1 `store/run_store.py`

```python
def create_run_directory(project_root: Path, run_id: RunId) -> Path:
    """
    Create runs/<run_id>/artifacts/ directory tree.
    Returns the path to the run directory.
    Raises DirectoryExistsError if the run directory already exists.
    """

def run_directory(project_root: Path, run_id: RunId) -> Path:
    """
    Return the path to runs/<run_id>/ without creating it.
    Raises RunNotFoundError if the directory does not exist.
    """

def list_run_ids(project_root: Path) -> list[RunId]:
    """
    Return all run_ids found under runs/ in lexicographic order.
    """

def decision_log_path(run_dir: Path) -> Path:
    """
    Return the path to runs/<run_id>/decision_log.yaml.
    Does not check for existence.
    """

def run_metrics_path(run_dir: Path) -> Path:
    """
    Return the path to runs/<run_id>/artifacts/run_metrics.json.
    Does not check for existence.
    """
```

### 6.2 `store/file_store.py`

```python
def atomic_write(path: Path, content: str) -> None:
    """
    Write content to path atomically (write to temp file, rename).
    Content is encoded UTF-8 with LF line endings, no BOM.
    """

def atomic_rename(src: Path, dst: Path) -> None:
    """
    Rename src to dst atomically. Both must be on the same filesystem.
    Raises FileExistsError if dst already exists.
    """

def sha256_from_disk(path: Path) -> ArtifactHash:
    """
    Compute SHA-256 of file at path.
    Read as bytes, normalize to UTF-8 + LF line endings before hashing.
    Returns hex digest string (lowercase).
    """

def read_yaml(path: Path) -> dict:
    """
    Parse YAML file at path. Raises ParseError on malformed YAML.
    """

def read_json(path: Path) -> dict:
    """
    Parse JSON file at path. Raises ParseError on malformed JSON.
    """

def read_text(path: Path) -> str:
    """
    Read text file at path as UTF-8 string.
    """

def append_json_array_element(path: Path, element: dict) -> None:
    """
    Append one element to the JSON array in the file at path.
    If file does not exist, create it with a single-element array.
    Operation is NOT atomic across concurrent writers; callers must
    ensure single-writer access per run.
    """
```

---

## 7. Module specifications

### 7.1 Run Engine (`runtime/engine/run_engine.py`)

**Responsibility**: Manage the lifecycle of a single run from initialization to terminal
state detection. Owns run_id assignment and run directory creation.

**Dependencies**: `types/run`, `types/event`, `framework/workflow_loader`,
`store/run_store`, `event_system`, `workflow_engine`

**Public interface**:

```python
class RunEngine:

    def initialize_run(
        self,
        project_root: Path,
        change_intent_path: Path,
        workflow_name: str = "default_workflow",
    ) -> RunContext:
        """
        Create a new run.

        Steps (per plan §5.1 steps 1–6):
          1. Validate change_intent_path exists and parses.
          2. Generate run_id: RUN-<YYYYMMDD>-<4-char-suffix>.
             Suffix: monotonic counter from existing run count + 1, zero-padded.
          3. Load workflow definition from workflow/<workflow_name>.yaml.
          4. Create run directory via run_store.create_run_directory().
          5. Copy change_intent.yaml into runs/<run_id>/artifacts/.
          6. Emit run.started event via event_system.
          7. Return RunContext with current_state = "INIT".

        Raises:
          RunIdCollisionError  if generated run_id already exists (retry with incremented suffix).
          MissingInputError    if change_intent_path does not exist.
        """

    def resume_run(
        self,
        project_root: Path,
        run_id: RunId,
    ) -> RunContext:
        """
        Resume an existing run after interruption.

        Steps (per plan §5.3):
          1. Verify run directory exists.
          2. Load workflow definition.
          3. Reconstruct current state via workflow_engine.reconstruct_state().
          4. Emit run.resumed event.
          5. Return RunContext with reconstructed current_state.

        Raises:
          RunNotFoundError     if run_id directory does not exist.
          StateReconstructionError if state cannot be determined deterministically.
        """

    def declare_terminal(
        self,
        ctx: RunContext,
        terminal_state: str,
    ) -> None:
        """
        Mark a run as having reached a terminal state.

        Steps:
          1. Verify terminal_state is in TERMINAL_STATES.
          2. Emit run.completed event with terminal_state and duration_seconds.
          3. Trigger extraction_hooks.check_triggers() and log any trigger points.

        Raises:
          InvalidTerminalStateError if terminal_state is not a known terminal.
        """
```

---

### 7.2 Workflow Engine (`runtime/engine/workflow_engine.py`)

**Responsibility**: Load workflow definitions, advance the state machine by one
transition per call, and delegate gate evaluation to `gate_evaluator`.

**Dependencies**: `types/workflow`, `types/gate`, `types/event`, `types/run`,
`framework/workflow_loader`, `gate_evaluator`, `event_system`

**Public interface**:

```python
class WorkflowEngine:

    def __init__(self, workflow_def: WorkflowDefinition):
        """Store the workflow definition. Does not load files."""

    def get_eligible_transitions(self, current_state: str) -> list[Transition]:
        """
        Return all transitions whose from_state matches current_state.
        Order is preserved from the workflow YAML definition.
        """

    def advance(
        self,
        ctx: RunContext,
        evaluator: GateEvaluator,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> AdvanceResult:
        """
        Attempt to advance the workflow by one transition from ctx.current_state.

        For each eligible transition in order (per plan §5.1 steps 7–10):
          1. Call evaluator.evaluate(transition, ctx.artifacts_dir, decision_log_path, schemas).
          2. Emit workflow.transition_checked event.
          3. If gate passes: emit workflow.transition_completed, return AdvanceResult(
               transitioned=True, new_state=transition.to_state).
          4. If gate fails: emit run.blocked, return AdvanceResult(
               transitioned=False, blocked_at=ctx.current_state, gate_result=gate_result).

        Only the first passing transition is executed.
        The loop does NOT continue after the first passing transition.

        Raises:
          NoEligibleTransitionsError if current_state has no outbound transitions.
        """

    def reconstruct_state(
        self,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
        run_metrics_path: Path | None,
    ) -> str:
        """
        Deterministically reconstruct the current workflow state (per plan §5.3).

        Primary path: read last workflow.transition_completed event from run_metrics_path.
        Fallback (run_metrics absent): traverse transitions in order; return the state
        of the last transition whose gate conditions pass.

        Returns the state name string.
        Raises StateReconstructionError if no state can be determined.
        """

@dataclass(frozen=True)
class AdvanceResult:
    transitioned:  bool
    new_state:     str | None      # populated when transitioned=True
    blocked_at:    str | None      # populated when transitioned=False
    gate_result:   GateResult | None
```

---

### 7.3 Gate Evaluator (`runtime/engine/gate_evaluator.py`)

**Responsibility**: Execute the four-step gate check procedure for a single transition
and return a structured, auditable result.

**Dependencies**: `types/gate`, `types/workflow`, `types/artifact`, `types/decision`,
`artifact_system` (read-only: validate and read artifact fields),
`decision_system` (read-only: approval lookup)

**Public interface**:

```python
class GateEvaluator:

    def evaluate(
        self,
        transition: Transition,
        project_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        """
        Execute all four checks in sequence (per plan §4.2.1 / runtime_contract §6.1).

        Checks run in this fixed order:
          1. check_inputs_present    (only if transition.requires.inputs_present is set)
          2. check_artifact_presence (for each name in transition.requires.artifacts)
          3. check_approval          (for each name in transition.requires.human_approval)
          4. check_conditions        (for each field/value in transition.requires.conditions)

        A check that is not applicable for this transition produces no GateCheckDetail entry.
        GateResult.result = PASS iff all executed checks pass.
        """

    def check_inputs_present(
        self,
        project_root: Path,
        required_inputs: list[str],
    ) -> list[GateCheckDetail]:
        """
        Verify each required project input file exists at project_root/<name>.
        Returns one GateCheckDetail per input file.
        """

    def check_artifact_presence(
        self,
        artifacts_dir: Path,
        artifact_names: list[str],
    ) -> list[GateCheckDetail]:
        """
        Verify each artifact file exists in artifacts_dir.
        Returns one GateCheckDetail per artifact name.
        """

    def check_approval(
        self,
        artifacts_dir: Path,
        decision_log_path: Path,
        artifact_names: list[str],
        schemas: dict[str, ArtifactSchema],
    ) -> list[GateCheckDetail]:
        """
        For each artifact name, execute the approval lookup algorithm
        (runtime_contract §4.3):
          1. Read artifact_id from artifact header/fields.
          2. Compute SHA-256 hash of artifact file.
          3. Scan decision_log.yaml for an entry where:
               decision == "approve"
               AND references contains (artifact_id, artifact_hash) match
               AND entry timestamp > artifact created_at
          4. PASS if such an entry exists; FAIL otherwise.

        Returns one GateCheckDetail per artifact name.
        """

    def check_conditions(
        self,
        artifacts_dir: Path,
        conditions: dict[str, str],
        schemas: dict[str, ArtifactSchema],
    ) -> list[GateCheckDetail]:
        """
        For each (field_name, expected_value) pair:
          - Identify the artifact that owns that field (from schema registry).
          - Read the field value from the artifact header (Markdown) or YAML root field.
          - Compare to expected_value: exact string match, case-sensitive.
          - PASS if match; FAIL otherwise (including field absent).

        Returns one GateCheckDetail per condition.
        """
```

---

### 7.4 Artifact System (`runtime/artifacts/artifact_system.py`)

**Responsibility**: Manage artifact storage, identity, SHA-256 hashing, structural
validation against schemas, versioning, and immutability enforcement.

**Dependencies**: `types/artifact`, `types/event`, `store/file_store`,
`store/run_store`, `framework/schema_loader`, `event_system`

**Public interface**:

```python
class ArtifactSystem:

    def register(
        self,
        ctx: RunContext,
        artifact_name: str,
        owner_role: str,
        schemas: dict[str, ArtifactSchema],
    ) -> ArtifactRef:
        """
        Register a newly written artifact.

        Steps:
          1. Verify the artifact file exists in ctx.artifacts_dir.
          2. Compute SHA-256 hash from disk.
          3. Read artifact_id from the artifact file (YAML field or Markdown header).
             If absent and schema requires it: raise MissingArtifactIdError.
          4. Run structural validation (validate_structure).
             If invalid: raise ArtifactStructureError.
          5. Emit artifact.created event.
          6. Return ArtifactRef(name, artifact_id, artifact_hash).
        """

    def validate_structure(
        self,
        artifact_path: Path,
        schema: ArtifactSchema,
    ) -> ValidationResult:
        """
        Validate structural compliance of artifact at artifact_path against schema.

        For Markdown (per runtime_contract §6.2):
          1. File exists and non-empty.
          2. Each schema.required_sections heading is present (case-insensitive prefix match
             against ## or ### headings).
          3. Each schema.required_fields key is present in the header block
             (lines before the first # heading, bare key: value format).
          4. 'id' and 'supersedes_id' fields are non-empty.
          5. 'outcome' field (if in schema.required_fields) matches one of
             schema.allowed_outcomes.

        For YAML/JSON (per runtime_contract §6.3):
          1. File parses without error.
          2. All schema.required_fields are present and non-null/non-empty.

        Returns ValidationResult(valid: bool, errors: list[str]).
        Never raises; errors are returned in the result.
        """

    def supersede(
        self,
        ctx: RunContext,
        artifact_name: str,
        decision_log_path: Path,
    ) -> SupersessionResult:
        """
        Execute the supersession procedure (per plan §4.4 / runtime_contract §3.1).

        Steps:
          1. Verify the artifact is not approved+frozen (check_immutability).
             If frozen: raise ImmutableArtifactError.
          2. Count existing .v<N>.<ext> suffixes to determine next version number N.
          3. Rename <name>.<ext> → <name>.v<N>.<ext> via file_store.atomic_rename.
          4. Emit artifact.superseded event with prior artifact_id and prior hash.
          5. Return SupersessionResult(versioned_path, prior_artifact_id, version_number).

        The caller is responsible for writing the new version. After writing,
        the caller calls register() on the new version.
        """

    def check_immutability(
        self,
        artifact_id: ArtifactId,
        decision_log_path: Path,
    ) -> bool:
        """
        Return True if artifact_id appears in any approved decision_log.yaml entry.
        Return False otherwise.
        An approved artifact must not be written or modified.
        """

    def compute_hash(self, artifact_path: Path) -> ArtifactHash:
        """
        Compute and return SHA-256 hex digest from disk (UTF-8, LF, no BOM).
        Delegates to file_store.sha256_from_disk.
        """

    def read_artifact_field(
        self,
        artifact_path: Path,
        field_name: str,
        file_format: str,
    ) -> str | None:
        """
        Read a specific field value from an artifact file.
        For Markdown: scan header lines (before first # heading) for 'field_name: value'.
        For YAML/JSON: access the top-level key.
        Returns the value string or None if absent.
        """

    def is_project_input(
        self,
        artifact_path: Path,
        project_root: Path,
    ) -> bool:
        """
        Return True if artifact_path is located outside all run directories
        (i.e., it is a project-level input, not a run artifact).
        Project inputs must not be written by the runtime.
        """

@dataclass(frozen=True)
class ValidationResult:
    valid:  bool
    errors: tuple[str, ...]

@dataclass(frozen=True)
class SupersessionResult:
    versioned_path:    Path
    prior_artifact_id: ArtifactId
    version_number:    int
```

---

### 7.5 Agent Invocation Layer (`runtime/agents/invocation_layer.py`)

**Responsibility**: Dispatch agent role invocations with read-only input enforcement,
single-shot constraint checking, invocation record production, and output collection.

**Dependencies**: `types/run`, `types/artifact`, `types/event`, `framework/agent_loader`,
`artifact_system`, `event_system`

**Public interface**:

```python
class AgentInvocationLayer:

    def invoke(
        self,
        ctx: RunContext,
        agent_role: str,
        agent_contracts: dict[str, AgentContract],
        schemas: dict[str, ArtifactSchema],
        mode: InvocationMode,
        adapter: AgentAdapter | None = None,
    ) -> InvocationResult:
        """
        Invoke a single agent role (per plan §4.3 / runtime_contract §5).

        Steps:
          1. Load contract for agent_role from agent_contracts.
          2. check_single_shot(ctx, agent_role, ctx.current_state): raise if duplicate.
          3. Resolve input artifact paths from ctx.artifacts_dir (read-only).
          4. Emit agent.invocation_started event with input artifact refs.
          5. Dispatch based on mode:
               HUMAN_AS_AGENT: block and poll artifacts_dir for expected output files.
               AUTOMATED: call adapter.invoke(input_paths, output_dir).
          6. On completion: for each expected output artifact, call
             artifact_system.register() to compute hash and validate structure.
          7. Emit agent.invocation_completed event with output refs and duration.
          8. Write invocation record to run_metrics.json invocation_records array.
          9. Return InvocationResult.
        """

    def check_single_shot(
        self,
        ctx: RunContext,
        agent_role: str,
        workflow_state: str,
        run_metrics_path: Path,
    ) -> None:
        """
        Verify that agent_role has not already been invoked in workflow_state for this run,
        unless a rework transition has occurred since the prior invocation.

        Reads invocation_records from run_metrics_path.
        Raises SingleShotViolationError if a prior invocation exists without an
        intervening run.rework_started event.
        """

    def build_invocation_record(
        self,
        ctx: RunContext,
        agent_role: str,
        input_refs: list[ArtifactRef],
        output_refs: list[ArtifactRef],
        outcome: InvocationOutcome,
        invoked_at: str,
        notes: str | None,
    ) -> dict:
        """
        Construct the invocation record dict per runtime_contract §5.2.
        """

class InvocationMode(str, Enum):
    HUMAN_AS_AGENT = "human_as_agent"
    AUTOMATED      = "automated"

class InvocationOutcome(str, Enum):
    COMPLETED = "completed"
    BLOCKED   = "blocked"
    FAILED    = "failed"

@dataclass(frozen=True)
class InvocationResult:
    agent_role:      str
    outcome:         InvocationOutcome
    output_refs:     tuple[ArtifactRef, ...]
    duration_seconds: float
    invocation_record: dict

class AgentAdapter(Protocol):
    """
    Interface for automated agent adapters.
    An adapter wraps a specific agent implementation (subprocess, LLM call, etc.).
    """
    def invoke(
        self,
        input_paths: dict[str, Path],
        output_dir: Path,
    ) -> dict[str, Path]:
        """
        Execute the agent. Returns mapping of output artifact name → written path.
        Must not modify input_paths files.
        """
```

---

### 7.6 Decision System (`runtime/decisions/decision_system.py`)

**Responsibility**: Read `decision_log.yaml`, detect and validate new entries,
emit events, and return structured signals for gate re-evaluation or rework initiation.

**Dependencies**: `types/decision`, `types/artifact`, `types/event`,
`store/file_store`, `event_system`

**Public interface**:

```python
class DecisionSystem:

    def load_all(self, decision_log_path: Path) -> list[DecisionEntry]:
        """
        Parse decision_log.yaml and return all entries.
        Returns empty list if file does not exist.
        Raises DecisionLogParseError if the file exists but is malformed.
        """

    def get_new_entries(
        self,
        decision_log_path: Path,
        last_known_count: int,
    ) -> list[DecisionEntry]:
        """
        Load all entries and return those at index >= last_known_count.
        Used to detect entries appended since last check.
        """

    def process_new_entries(
        self,
        ctx: RunContext,
        decision_log_path: Path,
        last_known_count: int,
        schemas: dict[str, ArtifactSchema],
    ) -> list[DecisionSignal]:
        """
        For each new entry (since last_known_count):
          1. Validate entry structure against decision_log.schema.yaml.
          2. Emit decision.recorded event.
          3. Build and return a DecisionSignal based on entry.decision type.

        Returns one DecisionSignal per new entry.
        Never writes to decision_log.yaml.
        """

    def find_approval(
        self,
        entries: list[DecisionEntry],
        artifact_id: ArtifactId,
        artifact_hash: ArtifactHash | None,
        artifact_created_at: str,
    ) -> DecisionEntry | None:
        """
        Implementation of the approval lookup algorithm (runtime_contract §4.3).

        Scans entries for the first entry satisfying:
          1. decision == APPROVE
          2. references contains artifact_id match AND artifact_hash match
             (or artifact_id-only if hash is None with documented rationale)
          3. entry.timestamp > artifact_created_at (ISO-8601 comparison)

        Returns the matching entry, or None if not found.
        """

class SignalType(str, Enum):
    GATE_RECHECK  = "gate_recheck"    # decision: approve → re-evaluate gate
    REWORK        = "rework"          # decision: reject  → re-invoke owning agent
    DEFERRED      = "deferred"        # decision: defer   → hold, no action

@dataclass(frozen=True)
class DecisionSignal:
    signal_type:      SignalType
    entry:            DecisionEntry
    artifact_ref:     ArtifactRef | None   # populated for REWORK signals
```

---

### 7.7 Event System (`runtime/events/event_system.py` + `metrics_writer.py`)

**Responsibility**: Construct well-formed event envelopes, assign monotonic IDs, and
append events to `run_metrics.json` in the correct section.

**Dependencies**: `types/event`, `types/run`, `store/file_store`, `store/run_store`

**Design note**: The event system is the only module all other components call.
To avoid circular imports, it depends on nothing from the other runtime modules.
Components pass all required context values as explicit arguments.

**Public interface**:

```python
class EventSystem:

    def emit(
        self,
        run_metrics_path: Path,
        run_id: RunId,
        event_type: EventType,
        producer: str,
        workflow_state: str,
        causation_event_id: str | None,
        payload: dict,
    ) -> EventEnvelope:
        """
        Construct and persist one event (per docs/event_model.md §1).

        Steps:
          1. Read current event counter from run_metrics.json (or 0 if absent).
          2. Assign event_id: EVT-<run_id_short>-<counter+1>, zero-padded to 4 digits.
          3. Set timestamp = UTC now as ISO-8601.
          4. Set correlation_id = run_id.
          5. Construct EventEnvelope.
          6. Validate all 8 fields are present and non-empty (except causation which may be null).
             If any field missing: log to orchestrator_log.md and raise MalformedEventError.
          7. Route to correct section:
               agent.invocation_* → append to invocation_records array
               all others          → append to events array
          8. Call metrics_writer.append_event(run_metrics_path, envelope_as_dict, section).
          9. Return the EventEnvelope.

        Thread safety: this module assumes single-writer access per run.
        """

    def last_event_id(self, run_metrics_path: Path) -> str | None:
        """
        Return the event_id of the last event in run_metrics.json, or None if empty.
        """

    def read_events(
        self,
        run_metrics_path: Path,
        event_type: EventType | None = None,
    ) -> list[EventEnvelope]:
        """
        Read and return all events from run_metrics.json.
        If event_type is specified, filter to that type only.
        Returns empty list if file does not exist.
        """
```

```python
# metrics_writer.py

def append_event(
    run_metrics_path: Path,
    event_dict: dict,
    section: str,           # "events" | "invocation_records"
) -> None:
    """
    Append event_dict to the named section array in run_metrics.json.

    Procedure:
      1. If run_metrics.json does not exist: create it with empty events and
         invocation_records arrays plus run metadata stub.
      2. Read current file content.
      3. Parse JSON.
      4. Append event_dict to parsed[section].
      5. Verify monotonic counter: new event_id counter > all existing counters.
         If counter violation detected: raise EventCounterViolationError.
      6. Serialize back to JSON with consistent formatting.
      7. Write atomically via file_store.atomic_write.

    This function must not truncate or overwrite existing entries.
    """

def verify_append_only(run_metrics_path: Path, prior_hash: ArtifactHash) -> None:
    """
    Verify that run_metrics.json has only been appended to since prior_hash was recorded.
    Raise AppendOnlyViolationError if the file content that produced prior_hash
    is no longer a prefix of the current file content.
    Used by compliance tests (plan §9.4).
    """
```

---

### 7.8 Knowledge Extraction Hooks (`runtime/knowledge/extraction_hooks.py`)

> **MVP status**: Active as trigger-event emitter only. No knowledge records are created and no extraction is performed. Full knowledge extraction is a future feature — see `docs/roadmap/future_features.md §1`.

**Responsibility**: Detect normative extraction trigger points at terminal states and
log them as entries in `run_metrics.json`. No extraction is performed.

**Dependencies**: `types/run`, `types/event`, `event_system`

**Public interface**:

```python
@dataclass(frozen=True)
class ExtractionTrigger:
    trigger_point:     str             # e.g. "delivery_run_accepted"
    workflow_location: str             # e.g. "default_workflow.yaml ACCEPTED"
    responsible_roles: tuple[str, ...]
    source_artifacts:  tuple[str, ...]

# Static trigger registry derived from knowledge_query_contract.md §7
EXTRACTION_TRIGGERS: dict[str, ExtractionTrigger] = {
    "ACCEPTED": ExtractionTrigger(
        trigger_point="delivery_run_accepted",
        workflow_location="default_workflow.yaml ACCEPTED",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "decision_log.yaml", "design_tradeoffs.md"),
    ),
    "ACCEPTED_WITH_DEBT": ExtractionTrigger(
        trigger_point="delivery_run_accepted_with_debt",
        workflow_location="default_workflow.yaml ACCEPTED_WITH_DEBT",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "decision_log.yaml", "design_tradeoffs.md"),
    ),
    "FAILED": ExtractionTrigger(
        trigger_point="delivery_run_failed",
        workflow_location="default_workflow.yaml FAILED",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "arch_review_record.md"),
    ),
    "OBSERVE": ExtractionTrigger(
        trigger_point="improvement_cycle_observe",
        workflow_location="improvement_cycle.yaml OBSERVE",
        responsible_roles=("agent_reflector",),
        source_artifacts=("run_metrics.json", "test_report.json", "review_result.md"),
    ),
}

def check_triggers(terminal_state: str) -> ExtractionTrigger | None:
    """
    Return the ExtractionTrigger for the given terminal_state, or None if
    no trigger is defined for that state.
    Pure function; no I/O.
    """

def log_trigger(
    ctx: RunContext,
    trigger: ExtractionTrigger,
    event_system: EventSystem,
    run_metrics_path: Path,
    causation_event_id: str | None,
) -> None:
    """
    Record the extraction trigger point in run_metrics.json.

    Emits an event of a project-defined type (e.g., "knowledge.extraction_triggered")
    or appends a structured note to the run_metrics events array.

    Does NOT write to knowledge_index.json.
    Does NOT create knowledge_record artifacts.
    """
```

---

## 8. CLI entry point (`runtime/cli.py`)

**Responsibility**: Provide a command-line interface that maps user commands to Run Engine
operations. The CLI is the only external entry point.

**Design**: The CLI passes all context explicitly to each called function.
No global state is held between commands.

```
devos run     --project <dir> --change-intent <path> [--workflow <name>]
devos resume  --project <dir> --run-id <run_id>
devos status  --project <dir> --run-id <run_id>
devos check   --project <dir> --run-id <run_id>
devos advance --project <dir> --run-id <run_id>
```

| Command | Description |
| --- | --- |
| `run` | Initialize a new run and begin execution. |
| `resume` | Resume an interrupted run from reconstructed state. |
| `status` | Print current run state, last event, and blocking reason if blocked. |
| `check` | Evaluate gate conditions for the current state without advancing. |
| `advance` | Attempt one transition from the current state. Blocks if gate fails. |

The CLI does not drive the full execution loop autonomously. Each `advance` call
performs one transition attempt. A human operator or wrapper script calls `advance` iteratively.
This prevents unbounded autonomous execution without preventing fully automated runs — when no gate requires a human decision, a wrapper script can iterate without human presence.

---

## 9. Key design decisions

### D-01: Event system as the only cross-cutting dependency

All components call `event_system.emit()` as their output channel for observability.
The event system depends only on `types/` and `store/`. This eliminates circular
dependencies between components and keeps the event system as a pure side-effect sink.

**Trade-off**: Components must pass `run_metrics_path` and run context fields explicitly
rather than having the event system read them from a shared registry. This is the
correct choice given the "no hidden state" constraint.

### D-02: Framework loaders are called once at run initialization

Workflow definitions, schemas, and agent contracts are loaded at the start of each
run and passed as explicit arguments to each component. They are not re-read during
the execution loop.

**Trade-off**: Framework changes during a run are not picked up. This is acceptable
and correct: a run must execute against the framework version that was current at
`run.started`.

**Exception**: Resume calls reload the framework at the time of resume. If the
framework version has changed, the runtime must check `contracts/framework_versioning_policy.md`
and block with a version mismatch error if the change is Major.

### D-03: Decision System never writes

`decision_log.yaml` is owned exclusively by humans. The Decision System reads
and signals; it never appends or modifies. This is a hard constraint from
`runtime_contract.md` §2.3.

**Consequence**: The runtime has no mechanism to create approval entries.
Gate re-evaluation is triggered only by external writes to `decision_log.yaml`
detected by `decision_system.get_new_entries()`.

### D-04: Artifact System validates structure, not semantics

The Artifact System runs structural validation (field presence, heading presence,
outcome value matching) per `runtime_contract.md` §6.2–§6.3. Semantic content
validation (does the plan make sense?) is project-owned via the `domain_validation`
capability and is out of scope for the runtime.

This keeps the runtime independent of project domain knowledge.

> **Future extension point**: The `domain_validation` capability and capability registry execution are parked as post-MVP features. See `docs/roadmap/future_features.md §3`.

### D-05: CLI advances one transition per invocation

The CLI does not drive an autonomous loop. Each `advance` command attempts one
transition. If the gate passes, the agent is invoked, outputs are collected, and
the command returns. If the gate fails, the command reports the blocking reason
and exits.

This design makes every transition an observable, interruptible unit of work.
It prevents the runtime from becoming an autonomous loop, which would violate
`contracts/system_invariants.md`.

### D-06: AgentAdapter protocol isolates invocation mechanism

The `AgentAdapter` protocol decouples the invocation mechanism (subprocess, HTTP call,
LLM prompt) from the invocation layer's contract enforcement logic. A project
registers an adapter per agent role. The runtime core has no knowledge of how
agents are implemented.

**Consequence**: The framework and runtime remain tool-agnostic, as required by
`contracts/system_invariants.md` (tool-agnostic invariant).

> **Future extension point**: Concrete `AgentAdapter` implementations (LLM adapters, subprocess agents, HTTP agents) are project-level concerns and not part of the MVP runtime. See `docs/roadmap/future_features.md §5`.

### D-07: No in-memory state survives between CLI invocations

Each CLI command starts from scratch: loads all framework contracts, reconstructs
run state from disk, and proceeds. This ensures that the system can be resumed
from any point and that there is no hidden state that could cause divergence from
the artifact-based ground truth.

**Trade-off**: Slightly higher startup cost per command. Acceptable for a
batch-oriented system where correctness and auditability outweigh performance.

---

## 10. Module-to-contract traceability

| Module | Primary contract sections |
| --- | --- |
| `types/run.py` | `runtime_contract.md` §1.1, §1.2 |
| `types/workflow.py` | `workflow/default_workflow.yaml` structure |
| `types/artifact.py` | `runtime_contract.md` §3.2, §4.2 |
| `types/event.py` | `docs/event_model.md` §1, §2, §3 |
| `types/decision.py` | `artifacts/schemas/decision_log.schema.yaml` |
| `types/gate.py` | `runtime_contract.md` §6.1 |
| `framework/workflow_loader.py` | `workflow/*.yaml` |
| `framework/schema_loader.py` | `artifacts/schemas/` |
| `framework/agent_loader.py` | `agents/*.md` |
| `store/run_store.py` | `runtime_contract.md` §2.1 |
| `store/file_store.py` | `runtime_contract.md` §4.2 (hash), §3.1 (rename) |
| `engine/run_engine.py` | `runtime_contract.md` §1, §7; `docs/event_model.md` §2.1 (`run.*`) |
| `engine/workflow_engine.py` | `runtime_contract.md` §6, §7; `workflow/*.yaml` transitions |
| `engine/gate_evaluator.py` | `runtime_contract.md` §4.3, §6.1, §6.2, §6.3 |
| `artifacts/artifact_system.py` | `runtime_contract.md` §3, §4.2, §6.2, §6.3 |
| `agents/invocation_layer.py` | `runtime_contract.md` §5; `contracts/system_invariants.md` |
| `decisions/decision_system.py` | `runtime_contract.md` §2.3, §4.3, §8.2, §8.3 |
| `events/event_system.py` | `docs/event_model.md` §1, §4, §5 |
| `events/metrics_writer.py` | `docs/event_model.md` §4; `runtime_contract.md` §5.2 |
| `knowledge/extraction_hooks.py` | `docs/knowledge_query_contract.md` §7 |

---

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Full module decomposition derived from phase3_runtime_realization_plan.md §4. Defines directory layout, shared types, 8 module interfaces, CLI design, 7 design decisions, and contract traceability table. |
