# DevOS Future Feature — Context System

**Status:** Future Feature
**Priority:** High
**Depends on:** Knowledge System

---

# Purpose

The DevOS Context System enables agents to retrieve the **correct contextual information for a task** without embedding large amounts of information directly into prompts.

The system ensures that agents operate with:

* relevant architectural constraints
* domain rules
* repository context
* run artifacts
* accumulated engineering knowledge

The Context System acts as a **structured retrieval layer** between agents and the information sources available in a DevOS workspace.

---

# Motivation

LLM-based agents perform poorly when:

* prompts contain excessive information
* context is incomplete
* context is unrelated to the task

Providing the entire repository or documentation as context often results in:

* hallucinations
* architecture violations
* scope expansion
* unstable outputs

The Context System solves this by allowing agents to load **bounded, role-specific context**.

---

# Design Principle

Context retrieval must be:

* role-specific
* deterministic
* artifact-driven
* capability-based

Agents should never receive the entire system context.

Instead they request context through dedicated **context capabilities**.

---

# Context Sources

The Context System retrieves information from multiple sources inside the DevOS environment.

## Repository Context

```text
source code
repository structure
module boundaries
dependency relationships
```

---

## Domain Context

```text
workspace/inputs/domain_scope.md
workspace/inputs/domain_rules.md
workspace/inputs/glossary.md
```

---

## Architecture Context

```text
workspace/inputs/architecture_contract.md
architecture documentation
architecture decision records
```

---

## Run Context

Artifacts produced during previous workflow runs.

Examples:

```text
implementation_summary.md
test_report.json
design_tradeoffs.md
review_result.md
```

---

## Knowledge Context

The Context System integrates with the DevOS Knowledge System.

The Knowledge System stores structured engineering knowledge extracted from completed runs.

Examples:

```text
implementation patterns
failure patterns
testing strategies
architecture constraints
```

The Context System retrieves relevant knowledge records and exposes them to agents when appropriate.

---

# Context Surfaces

A **Context Surface** is a defined category of retrievable context.

Typical surfaces include:

```text
repository context
domain context
architecture context
run artifact context
knowledge context
planning context
```

Agents retrieve context selectively from these surfaces.

---

# Role-Specific Context Sets

Each agent role has a predefined context profile.

## Planner Context

Typical inputs:

```text
change_intent.yaml
domain_scope.md
architecture_contract.md
planning rules
knowledge records related to the change
```

The planner may also retrieve:

```text
previous implementation patterns
testing strategies for similar features
```

---

## Implementer Context

Typical inputs:

```text
implementation_plan.yaml
design_tradeoffs.md
relevant code modules
architecture constraints
knowledge about similar implementations
```

---

## Tester Context

Typical inputs:

```text
test_design.yaml
implementation_summary.md
codebase
knowledge about testing strategies
```

---

## Reviewer Context

Typical inputs:

```text
implementation_summary.md
test_report.json
architecture_contract.md
design_tradeoffs.md
knowledge about failure patterns
```

---

# Capability-Based Context Retrieval

Agents retrieve context via capabilities.

Example capability interface:

```text
context.load_architecture_context
context.load_domain_context
context.load_repository_context
context.load_related_knowledge
context.load_component_context
```

Agents request context as needed.

Example:

```text
planner
  → context.load_domain_context
  → context.load_architecture_context
  → context.load_related_knowledge
```

---

# Determinism Requirements

Context retrieval must remain deterministic.

Given identical:

* repository state
* workspace inputs
* run artifacts
* knowledge index

the retrieved context must be identical.

Randomized retrieval or uncontrolled semantic search must not influence DevOS workflow gates.

---

# Relationship to the Knowledge System

The Knowledge System acts as a persistent store of engineering knowledge.

The Context System queries the knowledge index and retrieves relevant records.

Example pipeline:

```text
DevOS run
  ↓
artifacts generated
  ↓
knowledge extraction
  ↓
knowledge records stored
  ↓
context retrieval
  ↓
agent reasoning
```

The Context System does not modify knowledge records.

It only retrieves them.

---

# Relationship to DevOS Architecture

The Context System operates outside the DevOS Kernel.

```text
DevOS Kernel
    workflow execution
    artifact validation
    governance rules

Agent Runtime
    reasoning agents

Context System
    structured context retrieval

Knowledge System
    persistent engineering memory
```

The kernel is unaware of context retrieval.

Agents interact with the Context System through capabilities.

---

# Non-Goals

The Context System does not:

* control workflow execution
* influence governance gates
* modify artifacts
* store persistent knowledge

Those responsibilities belong to the DevOS Kernel and Knowledge System.

---

# Future Extensions

Possible future improvements include:

* semantic repository indexing
* architecture-aware context loading
* dependency graph context retrieval
* component-level context surfaces
* run-similarity detection
* knowledge-assisted planning

---

# Summary

The DevOS Context System provides structured, role-specific context retrieval for agents.

It integrates repository information, workspace inputs, run artifacts, and knowledge records to ensure that agents operate with the **correct information for their task**.

By separating context retrieval from prompt construction, the system enables more stable and scalable agent behavior.
