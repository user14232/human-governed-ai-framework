# DevOS – Anti-Patterns, Failure Modes, and Non-Goals

**Document type**: Governance reference
**Status**: Normative — applies to all DevOS implementations and extensions
**Date**: 2026-03-15

---

## 1. Purpose

This document defines explicitly what DevOS must not do, what it must not become, and which behaviors are forbidden regardless of technical feasibility.

A governance kernel is only trustworthy if it can state clearly what it will never do — even when it could.

---

## 2. What DevOS Must Never Become

These are permanent boundaries. They are not missing features or future candidates. They are deliberate, non-negotiable limits.

### DevOS must never become an AI platform

DevOS is a governance kernel. It does not build, host, or manage AI infrastructure. It does not manage model deployments, inference endpoints, or AI provider accounts. All AI execution happens in external systems behind the `AgentAdapter` protocol.

**Violation signal**: Any code path inside the runtime that invokes an LLM directly, manages model state, or routes AI traffic.

### DevOS must never become a planning system

DevOS does not define what should be built. It does not prioritize work items, create epics, or manage backlogs. Planning is the responsibility of external planning tools. DevOS consumes the output of planning tools as `change_intent.yaml`. It has no knowledge of the planning system that produced it.

**Violation signal**: Any DevOS component that queries a planning system, modifies work items, or makes scheduling decisions.

### DevOS must never become an autonomous agent framework

DevOS does not drive autonomous AI loops. It defines contracts for agents but does not implement agent reasoning. The CLI advances exactly one workflow transition per invocation. There is no run-until-done command.

**Violation signal**: Any command or code path that drives a workflow to completion without human intervention at each gate.

### DevOS must never become a distributed AI infrastructure

DevOS is a single-process local CLI tool. It has no server component, no distributed runtime, and no external service dependency. It must operate fully from the local filesystem.

**Violation signal**: Any requirement for a running service, database, or cloud API to execute a run.

### DevOS must never infer approvals

All approvals require explicit `decision_log.yaml` entries. The kernel never infers an approval from artifact content, timing, or prior decisions. No artifact advances past a gate without a matching, explicit decision log entry.

**Violation signal**: Any gate check logic that approves a transition without reading a matching decision log entry.

---

## 3. Anti-Patterns (Forbidden Behaviors)

These behaviors are forbidden in DevOS implementations, even when technically possible.

### AP-01: Implicit progress without artifacts

A workflow transition proceeds without a required artifact being present and validated.

**Why forbidden**: Violates the artifact-first principle. Produces phantom decisions. Breaks the audit trail.

**Correct behavior**: Gate failure is hard. No fallback, no inference, no automatic retry.

---

### AP-02: Agents interpreting incomplete requirements

An agent proceeds with ambiguous or incomplete input by making assumptions without recording them as explicit artifact content.

**Why forbidden**: Destroys determinism. Shifts responsibility from the human to the system. Makes decisions non-auditable.

**Correct behavior**: Ambiguity must be resolved before an agent is invoked. If an agent cannot produce a valid artifact from the given inputs, it must stop and the gate must block.

---

### AP-03: Architecture changes as implementation details

Architecture rules are modified implicitly through code, configuration, or tests without an explicit `architecture_change_proposal.md` and approval.

**Why forbidden**: Architecture drifts invisibly. Review loses its reference point. Decisions are not traceable.

**Correct behavior**: The only legal path for an architecture change is: produce `architecture_change_proposal.md` → get explicit approval in `decision_log.yaml` → produce `arch_review_record.md` with `outcome: PASS`.

---

### AP-04: Automated decisions without human record

Scripts, tools, or agents make decisions that are designated as human gates, without writing an entry to `decision_log.yaml`.

**Why forbidden**: Governance is simulated, not enforced. Accountability is not assignable.

**Correct behavior**: All decisions must be recorded in `decision_log.yaml`. No approval or rejection is valid unless it appears there with the required fields.

---

### AP-05: External tool state as workflow state

External tools (GitHub Issues, Linear, CI systems) are treated as the source of truth for DevOS run state.

**Why forbidden**: Violates the filesystem-first principle. Creates hidden dependencies. Makes runs non-reproducible.

**Correct behavior**: The run directory at `runs/<run_id>/` is always the authoritative state. External tools are mirrors, not sources.

---

### AP-06: Semantic validation inside the kernel

The runtime kernel validates artifact content meaning, not just structure.

**Why forbidden**: The kernel must remain tool-agnostic and domain-agnostic. Semantic validation is project-level concern.

**Correct behavior**: The artifact system validates structure only — required fields, heading presence, outcome value format. Content semantics are the responsibility of the project capability layer.

---

## 4. Expected Failure Modes

These are valid operational states. They are not bugs. The system is working correctly when these occur.

### FM-01: INIT → FAILED (missing inputs)

The run cannot start because required inputs are absent.

**Expected behavior**: Hard stop. No fallback. No best-guess execution. Clear error output indicating which inputs are missing.

---

### FM-02: Gate blocked — missing approval

A workflow state cannot advance because the required `decision_log.yaml` entry is absent.

**Expected behavior**: The run is in a valid blocked state. It waits indefinitely. No automated escalation, no time pressure from the system.

---

### FM-03: REVIEWING → FAILED

The review artifact carries `outcome: REJECT`.

**Expected behavior**: The run terminates. The run directory is preserved as an audit record. No automatic rework. A new run with a new `run_id` is required for any retry.

---

### FM-04: ARCH_CHECK blocked — CHANGE_REQUIRED

The `arch_review_record.md` carries `outcome: CHANGE_REQUIRED`.

**Expected behavior**: The run is blocked at `ARCH_CHECK`. An `architecture_change_proposal.md` must be produced and approved. A new `arch_review_record.md` with `outcome: PASS` is required before the run can proceed.

---

### FM-05: Gate blocked — artifact reject

A human decision entry in `decision_log.yaml` carries `decision: reject`.

**Expected behavior**: The workflow is blocked. A new version of the artifact must be produced. The new version must be validated and re-approved. No automatic escalation.

---

## 5. Permanent Non-Goals

These are design decisions, not capability gaps.

| Non-goal | Rationale |
| --- | --- |
| Autonomous goal definition | DevOS never defines goals. All intent comes from external planning systems and human-authored `change_intent.yaml`. |
| Implicit optimization | DevOS never improves plans, simplifies architecture, or "helps" without explicit instruction. Improvement is a separate, explicit workflow. |
| Self-healing | DevOS surfaces failures visibly. It does not repair artifacts, retry failures, or correct errors. |
| Domain intelligence | DevOS does not understand the project's domain. It validates structure, not meaning. |
| Implicit scaling | Additional projects do not change the framework. No shared state across runs. No shortcuts for experienced users. |
| Heuristic confidence scoring | All gate checks are binary pass/fail. No probability scores, no soft gates, no fuzzy approvals. |

---

## Further Reading

- `docs/vision/product_vision.md` — DevOS scope and positioning
- `docs/vision/system_architecture.md` — Four-layer architecture model
- `docs/architecture/integration_model.md` — Artifact-first integration rules
- `docs/runtime/runtime_execution_model.md` — MVP runtime scope and explicit exclusions
