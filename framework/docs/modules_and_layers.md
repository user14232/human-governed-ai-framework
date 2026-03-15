What was produced
The analysis of phase3_runtime_realization_plan.md yielded 12 modules organized into 6 layers. Here is the full picture.

Layer 1 — Shared types (runtime/types/)
Six files, all frozen value objects with no dependencies on any runtime module.

File	Key types
run.py	RunId, RunContext, RunState, TERMINAL_STATES
workflow.py	WorkflowDefinition, Transition, RequiresBlock
artifact.py	ArtifactRef, ArtifactId, ArtifactHash, ArtifactStatus, ArtifactSchema
event.py	EventEnvelope, EventType enum (14 types)
decision.py	DecisionEntry, DecisionType, DecisionReference
gate.py	GateResult, GateCheckDetail, CheckType, CheckResult
These are the lingua franca of the runtime. Every module imports from here; nothing here imports from a runtime module. This eliminates circular dependencies entirely.

Layer 2 — Framework loaders (runtime/framework/)
Read-only parsers that convert framework contract files into typed structures. Called once at run initialization and passed as arguments — never re-read during the execution loop. This means a run executes against the framework version that was current at run.started.

workflow_loader.py → WorkflowDefinition
schema_loader.py → dict[str, ArtifactSchema]
agent_loader.py → dict[str, AgentContract]
Layer 3 — Store (runtime/store/)
Pure filesystem abstraction with no framework semantics.

run_store.py — run directory creation, path resolution, run enumeration
file_store.py — atomic write, atomic rename, sha256_from_disk (normalized UTF-8 + LF), JSON/YAML parse, append to JSON array
The hash function lives here because it is a pure I/O operation independent of artifact semantics.

Layer 4 — Runtime engine (runtime/engine/)
Three modules implementing plan components 4.1 and 4.2:

run_engine.py — initialize_run(), resume_run(), declare_terminal(). Owns run_id assignment (format: RUN-<YYYYMMDD>-<suffix>) and directory creation. Calls workflow_engine.reconstruct_state() on resume.

workflow_engine.py — advance() executes one transition per call (a deliberate design choice — no autonomous loop). reconstruct_state() implements the two-path fallback from runtime_contract.md §7.1.

gate_evaluator.py — Four methods, one per check type: check_inputs_present, check_artifact_presence, check_approval, check_conditions. The approval lookup (runtime_contract.md §4.3) lives here: artifact_id + SHA-256 hash match + timestamp ordering. Returns a GateResult with per-check detail — this is exactly what feeds the workflow.transition_checked event payload.

Layer 5 — Domain components
Four modules implementing plan components 4.3–4.7:

artifact_system.py — register() (hash + structural validation + emit), validate_structure() (Markdown heading/header parsing and YAML field checking per §6.2/§6.3), supersede() (the six-step supersession procedure), check_immutability() (queries decision log for frozen status). Structural validation never raises — errors are returned in a ValidationResult.

invocation_layer.py — invoke() dispatches via an AgentAdapter protocol, keeping the runtime core tool-agnostic. check_single_shot() reads run_metrics.json invocation records before any dispatch to enforce the framework's single-shot invariant. Human-as-agent mode polls the output directory for artifact presence rather than driving an automated process.

decision_system.py — load_all(), get_new_entries(), process_new_entries() — the system detects entries appended to decision_log.yaml since last check, emits decision.recorded events, and returns typed DecisionSignal values (GATE_RECHECK, REWORK, DEFERRED). Never writes a single byte to decision_log.yaml.

event_system.py + metrics_writer.py — Event construction, monotonic ID assignment (EVT-<run_id_short>-<counter>), envelope validation (all 8 fields must be present before persisting), and routing to the correct section (events vs. invocation_records). verify_append_only() supports the compliance prohibition test in plan §9.4.

extraction_hooks.py — Static EXTRACTION_TRIGGERS registry keyed by terminal state, directly from knowledge_query_contract.md §7. check_triggers() is a pure function. log_trigger() appends a trigger entry to run_metrics.json. Never touches knowledge_index.json.

Layer 6 — CLI (runtime/cli.py)
Five commands: run, resume, status, check, advance. The key design decision: advance performs one transition per invocation. There is no run-until-done loop command. A human or wrapper script calls advance iteratively. This is the structural enforcement of the human-in-the-loop model — the CLI cannot become an autonomous executor.

Dependency rules
Seven explicit rules are stated in the dependency graph section to prevent future violations:

types/ has no runtime module imports — it is the stable foundation.
framework/ has no runtime module imports — it only produces parsed types.
store/ has no runtime module imports — it only abstracts the filesystem.
event_system is called by all components but depends on nothing except types/ and store/ — no circular dependencies.
Only run_engine calls workflow_engine directly.
gate_evaluator is the only module that jointly reads artifacts and decision log.
Framework contracts are loaded once at run start; no mid-run re-reads.