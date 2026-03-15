# DevOS – Anti-Patterns, Failure Modes, and Non-Goals

**Document type**: Governance reference
**Status**: Normative — applies to all DevOS implementations and extensions
**Date**: 2026-03-15

---

# 1. Purpose

This document defines explicitly what DevOS must not do, what it must not become, and which behaviors are forbidden regardless of technical feasibility.

A governance kernel is only trustworthy if it can state clearly what it will never do — even when it could.

This document protects the DevOS architecture from scope drift, tool coupling, and unintended system evolution.

---

# 2. Permanent Boundaries (What DevOS Must Never Become)

These are permanent architectural limits.
They are not missing features or future roadmap candidates.

They are **non-negotiable system boundaries**.

---

## DevOS must never become an AI platform

DevOS is a governance kernel.
It does not build, host, or manage AI infrastructure.

It does not:

* host model deployments
* manage inference endpoints
* operate vector databases
* manage AI provider accounts

All AI execution happens in **external systems behind the `AgentAdapter` protocol**.

The DevOS Kernel contains **no LLM invocation logic**.

**Violation signal**

Any runtime code path that:

* invokes an LLM directly
* manages model state
* routes AI inference traffic
* embeds model-specific configuration

---

## DevOS must never become a planning system

DevOS does not function as a backlog management or project planning tool.

It does not:

- manage team backlogs
- perform prioritization
- schedule development work
- perform roadmap or sprint planning

Planning systems may be used as collaboration interfaces and may
store epics, stories, and tasks for human interaction.

DevOS may read from and write to planning systems through integration
adapters or agent capabilities.

However, DevOS must never depend on a planning system as the
authoritative source of workflow state.

The canonical input to a DevOS run remains a `change_intent.yaml`
artifact produced by an external system or agent.

DevOS workflows operate exclusively on artifacts inside the workspace.

**Violation signal**

Any DevOS component that:

- requires a planning system in order to execute a run
- treats planning tool state as the authoritative workflow state
- stores canonical workflow state only in an external planning system
- introduces planning tool APIs into the DevOS Kernel runtime

---

## DevOS Kernel must never implement autonomous execution

DevOS does not execute autonomous development loops.

The CLI advances **exactly one workflow transition per invocation**.

Agents may exist in external systems and may operate autonomously inside the **Agent Runtime**, but the **DevOS Kernel itself remains deterministic and gate-governed**.

**Violation signal**

Any command or code path that:

* drives a workflow to completion automatically
* bypasses explicit gate evaluation
* executes multi-step autonomous workflow progression

---

## DevOS Kernel must never become distributed infrastructure

The DevOS Kernel is a **single-process local CLI tool**.

It has:

* no server component
* no runtime service
* no external database dependency

All system state is reconstructible from the **workspace filesystem**.

External systems may be distributed (CI systems, agents, cloud models), but the **Kernel itself remains local and deterministic**.

**Violation signal**

Any requirement for:

* a running service
* a message queue
* an external database
* a persistent network dependency

in order to execute a run.

---

## DevOS must never infer approvals

All governance approvals must be explicitly recorded in `decision_log.yaml`.

The Kernel must never infer an approval from:

* artifact content
* timing
* historical decisions
* system state

**Violation signal**

Any gate check logic that allows workflow progression without reading a matching decision entry from `decision_log.yaml`.

---

# 3. Anti-Patterns (Forbidden Behaviors)

These behaviors are forbidden in DevOS implementations, even when technically possible.

---

## AP-01: Implicit progress without artifacts

A workflow transition proceeds without a required artifact being present and validated.

**Why forbidden**

Violates the artifact-first principle and destroys the audit trail.

**Correct behavior**

Gate failure is hard.
No fallback, no inference, no automatic retry.

---

## AP-02: Agents interpreting incomplete requirements

An agent proceeds with ambiguous or incomplete input by making assumptions without recording them explicitly.

**Why forbidden**

Breaks determinism and shifts responsibility away from the governance process.

**Correct behavior**

Ambiguity must be resolved before agent invocation.
All assumptions must be explicitly recorded in the produced artifact.

---

## AP-03: Architecture changes as implementation details

Architecture rules are modified implicitly through code changes or configuration without an explicit architecture proposal and approval.

**Why forbidden**

Architecture drift becomes invisible and untraceable.

**Correct behavior**

Architecture changes must follow the explicit path:

```
architecture_change_proposal.md
→ approval in decision_log.yaml
→ arch_review_record.md (outcome: PASS)
```

---

## AP-04: Automated decisions without human record

Scripts, tools, or agents make decisions that are designated as human governance gates.

**Why forbidden**

Governance becomes simulated rather than enforced.

**Correct behavior**

All governance decisions must appear in `decision_log.yaml`.

---

## AP-05: External tool state as workflow state

External systems are treated as the source of truth for workflow state.

Examples:

* GitHub Issues
* Linear
* CI systems
* dashboards

**Why forbidden**

Creates hidden dependencies and breaks reproducibility.

**Correct behavior**

The run directory at:

```
runs/<run_id>/
```

is always the authoritative system state.

External tools are **mirrors, never sources of truth**.

---

## AP-06: Semantic validation inside the Kernel

The runtime Kernel attempts to interpret the meaning of artifact content.

**Why forbidden**

The Kernel must remain domain-agnostic and tool-agnostic.

Semantic validation belongs in **project capabilities or agents**, not the Kernel.

**Correct behavior**

The Kernel validates **structure only**.

---

## AP-07: Agent side effects outside the artifact system

An agent performs an action that changes external system state without producing a corresponding artifact.

Examples:

* creating a Git branch
* triggering CI
* modifying repository files
* invoking external APIs

**Why forbidden**

State changes become invisible to the governance system.

**Correct behavior**

Every externally visible action must produce an artifact describing the action.

Artifacts are the audit trail.

---

## AP-08: Kernel capability implementation

Kernel modules directly implement tool integrations.

Examples:

* Git operations
* CI invocation
* LLM calls
* external service integrations

**Why forbidden**

The Kernel must remain tool-agnostic.

Tool integrations belong in the **Capability System or Agent Runtime adapters**.

**Correct behavior**

The Kernel invokes agents.
Agents use capabilities.
The Kernel never executes capabilities directly.

---

## AP-09: Agent-controlled workflow progression

An agent decides which workflow state should execute next.

**Why forbidden**

Workflow progression must remain deterministic and governed by the Kernel.

**Correct behavior**

Agents produce artifacts only.

The Kernel evaluates artifacts and advances the workflow.

---

# 4. Expected Failure Modes

These are valid operational states.
They are not bugs.

---

## FM-01: INIT → FAILED (missing inputs)

Required inputs are missing.

Expected behavior: hard stop with explicit error.

---

## FM-02: Gate blocked — missing approval

A required decision entry is absent.

Expected behavior: the run remains blocked indefinitely.

---

## FM-03: REVIEWING → FAILED

The review artifact contains `outcome: REJECT`.

Expected behavior: run terminates and must be restarted as a new run.

---

## FM-04: ARCH_CHECK blocked — CHANGE_REQUIRED

Architecture guardian requests changes.

Expected behavior: architecture proposal required before continuation.

---

## FM-05: Gate blocked — artifact rejection

Human decision entry carries `decision: reject`.

Expected behavior: workflow remains blocked until a new artifact version is produced.

---

## FM-06: Agent adapter failure

An adapter fails to invoke an agent implementation.

Expected behavior:

* the run blocks
* the failure is surfaced explicitly
* no automatic fallback to another implementation occurs

---

# 5. Permanent Non-Goals

These are architectural design decisions, not feature gaps.

| Non-Goal                   | Rationale                                                           |
| -------------------------- | ------------------------------------------------------------------- |
| Autonomous goal definition | DevOS never defines goals.                                          |
| Implicit optimization      | DevOS never improves artifacts without explicit workflow execution. |
| Self-healing workflows     | DevOS exposes failures instead of repairing them silently.          |
| Domain intelligence        | DevOS does not understand project semantics.                        |
| Cross-run shared state     | Runs are isolated execution units.                                  |
| Heuristic scoring          | Gate checks are binary pass/fail.                                   |

---

# 6. Architectural Principle

DevOS enforces a strict separation of responsibilities:

```
Agents perform reasoning
↓
Artifacts capture system knowledge
↓
Kernel enforces governance
↓
Decisions authorize transitions
```

Agents produce artifacts.

The Kernel governs workflows.

Humans provide explicit decisions.

No component may violate this separation.
