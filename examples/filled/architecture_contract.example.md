# Example: `architecture_contract.md` (guidance, non-normative)

This document is a **non-normative example** of a project-provided `architecture_contract.md`.
It is **guidance only**: projects may adopt, adapt, or ignore it.

## Responsibility (example)

Define an explicit architecture contract that:

- establishes **system boundaries**
- defines **layers** and **dependency direction**
- lists **allowed** and **forbidden** patterns
- states **stability guarantees**
- defines the **governed change process** (no implicit drift)

## Boundaries

### In scope

- The systemâ€™s source code and build configuration.
- Data schemas and interfaces owned by the system.
- Runtime configuration that affects behavior (must be explicit and versioned).

### Out of scope

- External systems and services not owned by this system (they are treated as dependencies).
- Human processes outside the workflow (they may be referenced but are not enforced here).

### External dependencies (explicit)

- All dependencies must be listed with:
  - **name**
  - **purpose**
  - **ownership** (internal/external)
  - **stability expectation** (stable/volatile)
  - **upgrade policy** (who decides, how recorded)

## Layering and dependency rules

### Conceptual layers (example)

The system is organized into the following layers (names are illustrative):

1) **Ingress / Interface**
   - API handlers, CLI entrypoints, adapters
   - Translates external requests into application commands/queries

1) **Application**
   - Use-cases, orchestration of domain logic
   - Defines ports (interfaces) that infrastructure must implement

1) **Domain**
   - Domain model, domain services, deterministic business rules
   - Must be side-effect free where possible

1) **Infrastructure**
   - Persistence, messaging, network, filesystem, external integrations
   - Implements ports defined by Application (or Domain, if explicitly allowed)

1) **Observability**
   - Logging/metrics/tracing adapters
   - Must not introduce hidden control flow

### Dependency direction (hard rules)

- **Ingress** may depend on **Application** and **Domain**.
- **Application** may depend on **Domain**.
- **Domain** must not depend on **Infrastructure**.
- **Infrastructure** may depend on **Application**/**Domain** only via **interfaces/ports** defined upstream.
- **No cyclic dependencies** between layers.

### Allowed cross-cutting mechanisms

- Dependency inversion via explicit interfaces/ports
- Explicit configuration objects passed through constructors (no implicit globals)
- Pure functions for deterministic transformations

## Allowed patterns

- **Ports & adapters** (hexagonal) or equivalent explicit boundary pattern
- **Explicit data contracts** at boundaries (versioned and reviewed)
- **Deterministic identifiers** for artifacts and interface versions where applicable
- **Batch-oriented processing** for data workflows (no hidden streaming loops)
- **Explicit error handling** with traceable failure modes (no silent retries)

## Forbidden patterns

- **Hidden state** that changes behavior without being declared (implicit environment coupling)
- **Runtime reflection / dynamic imports** that obscure dependency direction
- **Cross-layer shortcuts** (e.g., Ingress calling Infrastructure directly)
- **Implicit schema drift** (changing interfaces without versioning and recorded decision)
- **â€œMagicâ€ auto-wiring** that makes data/control flow non-auditable

## Stability guarantees

### Guaranteed stable (example)

- Layer boundaries and dependency direction rules in this contract
- Public interfaces exposed to other internal modules (as defined by the project)
- Artifact handoff policy: artifacts are the only legal inter-role communication channel

### Expected to evolve (explicitly, via governed change)

- Infrastructure implementations (as long as ports remain stable)
- Internal performance optimizations that do not change interfaces/contracts

## Change policy (governed; no implicit drift)

- Changes to `architecture_contract.md` are **not automatic** and must be explicit and versioned.
- If a change is needed, create an `architecture_change_proposal.md` artifact following the framework schema:
  - `artifacts/schemas/architecture_change_proposal.schema.md`
- Human approval must be recorded as an append-only entry in:
  - `runs/<run_id>/decision_log.yaml` (schema: `artifacts/schemas/decision_log.schema.yaml`)

## Consistency notes (framework alignment)

- This contract must not introduce domain logic into the framework layer.
- This contract is a **project input** (see `contracts/domain_input_contracts.md`) and should be explicit, deterministic, and unambiguous.
