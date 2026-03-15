# DevOS – Architectural Vision

> **Note**: The canonical MVP product vision is at `docs/vision/product_vision.md`. The system architecture overview is at `docs/vision/system_architecture.md`. This document provides the broader conceptual vision and design rationale.

## 1. Vision

DevOS is a **workflow governance kernel for AI-assisted engineering**.

It introduces structure, governance, and traceability around AI-driven development processes. DevOS sits between planning systems and AI execution systems. It orchestrates work but does not perform reasoning itself.

Instead of relying on autonomous agents that operate without constraints, DevOS integrates AI reasoning into **explicit workflows governed by artifacts, decisions, and system rules**.

The goal is to make AI-assisted engineering:

* reproducible
* inspectable
* architecturally consistent
* governed by explicit rules
* traceable across planning, execution, and decisions

DevOS treats software development as a **structured system of workflows rather than a sequence of informal AI interactions**.

---

# 2. The Problem DevOS Addresses

Modern AI coding tools dramatically accelerate code generation but introduce new risks in structured engineering environments.

Common problems include:

* architecture drift caused by unconstrained code generation
* reasoning that is lost because it is not captured in structured artifacts
* lack of traceability between decisions and implementation
* inconsistent development processes when AI-generated changes bypass normal review structures
* difficulty reconstructing why a system evolved in a particular way

AI improves **local productivity**, but it often weakens **global engineering structure**.

DevOS addresses this gap.

---

# 3. Core Idea

DevOS introduces a structured execution model for AI-assisted development.

Development work is modeled as **runs executing workflows**.

Each run progresses through defined states where specialized agents produce artifacts that capture reasoning and implementation steps.

Transitions are governed by explicit decisions.

The core model is:

```text
Runs execute workflows
Workflows invoke agents
Agents produce artifacts
Artifacts carry knowledge
Decisions authorize transitions
```

This model preserves the benefits of AI reasoning while maintaining the discipline of engineering processes.

---

# 4. System Philosophy

DevOS is built on several key principles.

### Determinism over autonomy

DevOS prioritizes deterministic workflows rather than autonomous agent behavior.

AI agents perform reasoning tasks but do not control system execution.

The workflow engine governs the process.

---

### Artifacts as system memory

Artifacts are the primary carriers of knowledge in DevOS.

Examples include:

* plans
* design analyses
* implementation summaries
* review outcomes

Artifacts form a durable knowledge layer that allows development history to be reconstructed.

---

### Explicit governance

All structural changes require explicit decisions.

Decisions are recorded in append-only logs and are linked to specific artifacts.

This ensures that system evolution is **transparent and auditable**.

---

### Separation of reasoning and control

DevOS separates:

* **AI reasoning** (performed by agents)
* **system control** (performed by the workflow engine)

This separation prevents AI from unintentionally altering system behavior or bypassing governance rules.

---

# 5. System Structure

DevOS operates across four layers. The governance kernel is the second.

```text
Planning Layer   (external: epics / stories / tasks → change_intent.yaml)
    ↓
DevOS Governance Kernel  (run lifecycle / workflow / gates / artifacts / decisions)
    ↓
Agent Execution Layer    (external: AI reasoning / code generation)
    ↓
Tooling Layer            (external: Git / testing / linting / scanning)
```

Within the governance kernel, the internal layer structure is:

```text
Framework Layer  (DevOS kernel rules)
    ↓
Workflows        (orchestration)
    ↓
Runs             (execution)
```

### Framework Layer

The framework layer defines the normative structure of the system.
It acts as the DevOS kernel — the set of rules that all workflows and runs must comply with.

It includes:

* artifact contracts
* agent roles
* workflow definitions
* system invariants
* governance rules

The framework layer describes **how DevOS operates**.

---

### Workflows

Workflows define structured engineering processes.

Examples include:

* feature delivery
* system improvement
* architectural review
* incident resolution

Each workflow defines:

* states
* responsible agents
* required artifacts
* decision gates

Workflows define **how development work progresses**.

---

### Runs

Runs represent concrete executions of workflows.

Each run contains:

* produced artifacts
* recorded decisions
* execution events
* workflow state

Runs are the fundamental units of work within DevOS.

---

# 6. Role of AI in DevOS

AI systems in DevOS act as **reasoning agents inside structured processes**.

Agents may perform tasks such as:

* analyzing requirements
* proposing architecture changes
* generating implementation plans
* writing code
* evaluating code quality
* designing tests

However, AI does not determine workflow progression.

The system retains control through deterministic rules and decision gates.

---

# 7. DevOS in the AI Tool Ecosystem

DevOS does not attempt to replace AI coding tools, IDEs, or planning systems.

Instead, it provides a **governance and workflow layer between them**.

```text
Planning systems (Linear / gstack / GitHub Issues)
        ↓
  change_intent.yaml
        ↓
DevOS governance kernel
  (workflow / gates / artifacts / decisions)
        ↓
Agent execution layer (Cursor / gstack / local LLMs)
        ↓
Tooling layer (Git / Pytest / Ruff / Semgrep)
```

AI editors accelerate coding. Planning tools organize work. DevOS ensures that AI-assisted development remains **structured, governed, and traceable** across all layers.

---

# 8. Minimum Viable DevOS

The first functional version of DevOS focuses on a minimal but complete system.

Core primitives include:

* Runs
* Workflows
* Agents
* Artifacts
* Decisions

A minimal workflow may include:

```text
INIT
→ PLAN
→ IMPLEMENT
→ REVIEW
→ DONE
```

This provides a working foundation while preserving the architectural principles of the system.

---

# 9. Long-Term Vision (Roadmap)

> **Roadmap** — The capabilities in this section are not part of the MVP runtime. For a full inventory of parked features, see `docs/roadmap/future_features.md`.

In the long term, DevOS aims to become a **workflow governance kernel and personal AI development toolkit** at the center of a structured AI-assisted engineering practice.

Potential future capabilities include:

* concrete `AgentAdapter` implementations for gstack, Cursor, and local LLM backends
* LLM provider abstraction layer with local and cloud model support (see `docs/architecture/llm_strategy.md`)
* persistent knowledge extraction from artifacts and decisions
* queryable engineering history across runs
* architecture evolution tracking
* external tool adapters for planning systems and code hosting platforms
* capability plugin system for extended gate validation
* automated improvement cycle triggering

These are extensions built on top of the DevOS governance kernel. The kernel itself remains minimal and stable.

DevOS envisions a development environment where AI reasoning operates inside **structured, governed workflows rather than informal prompts**.

---

# 10. Guiding Principle

The central idea behind DevOS is simple:

AI should not remove structure from software engineering.

AI should operate **within structured systems that preserve engineering discipline while amplifying human reasoning**.
