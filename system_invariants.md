# System invariants (v1)

## Responsibility

Define **non-negotiable invariants** of the framework layer.  
These invariants apply globally and must not be bypassed by workflow, agents, or projects.

## Input contract

- **Inputs**: None (this is a framework contract document).
- **Readers**: All roles and humans.

## Output contract

- **Outputs**: Normative rules used by:
  - workflow definitions (`workflow/*.yaml`)
  - agent contracts (`agents/*.md`)
  - artifact schemas (`artifacts/schemas/*`)

## Invariants (Non-Negotiable)

- Agents are **single-shot**, never looping.
- Iteration happens **only via the Orchestrator**.
- All handoffs occur **exclusively through artifacts**.
- Artifacts are:
  - versioned
  - owner-bound
  - typically immutable
- Architecture may change, but **only explicitly and versioned**.
- Human decisions are **part of the system**.
- Improvements create **proposals**, never automatic changes.
- Artifact metadata (e.g. status) must not be used as implicit control flow.

## Enforcement

- **Primary enforcer**: `agent_architecture_guardian` (contract + review gates)
- **Coordinator**: `agent_orchestrator` (state machine compliance)
- **Human governance**: approvals for plans, trade-offs, debt, architecture changes
  - recorded explicitly as append-only decisions in `decision_log.yaml` (see `artifacts/schemas/decision_log.schema.yaml`)

## Change policy

This document is versioned by explicit proposal:

- create `architecture_change_proposal` artifact (see `artifacts/schemas/`)
- human approval required
- update corresponding workflow/agent contracts in the same change set

## Assumptions / trade-offs

- Framework remains **tool-agnostic** (no hard coupling to an IDE or VCS).
- Determinism and auditability are prioritized over convenience.
