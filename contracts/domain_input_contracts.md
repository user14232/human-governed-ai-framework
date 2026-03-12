# Domain input contracts (project-provided)

## Responsibility

Define the **minimal runnable set** of project inputs required to run the workflow.  
This repository (framework) does **not** provide domain logic; it only defines required artifacts and their contracts.

## Contract shape (applies to all domain inputs)

Each input artifact must:

- have a stable filename (see below)
- be written/owned by humans (or project tooling), not framework agents
- be explicit, deterministic, and unambiguous
- avoid hidden state and implicit rules

## Mandatory inputs (workflow must not start without these)

### `domain_scope.md`

- **Purpose**: define what is explicitly in-scope and out-of-scope.
- **Minimum sections**:
  - In scope
  - Out of scope
  - Definitions / references

### `domain_rules.md`

- **Purpose**: hard domain invariants that must never be violated.
- **Minimum sections**:
  - Invariants (numbered, testable where possible)
  - Forbidden actions/patterns
  - Definitions / references

### `source_policy.md`

- **Purpose**: define sources of truth, priorities, conflict rules.
- **Minimum sections**:
  - Sources (with identifiers)
  - Priority order
  - Conflict resolution rules
  - Allowed evidence / citations policy (project-defined)

### `glossary.md`

- **Purpose**: ensure semantic clarity and unambiguous terminology.
- **Minimum sections**:
  - Terms (one per entry)
  - Synonyms / forbidden synonyms
  - Notes / references

### `architecture_contract.md`

- **Purpose**: explicit architecture contract defining:
  - system boundaries
  - layers & dependency direction
  - allowed / forbidden patterns
  - stability guarantees
- **Minimum sections**:
  - Boundaries
  - Layering and dependency rules
  - Allowed patterns
  - Forbidden patterns
  - Stability guarantees

## Recommended inputs (quality enhancers; do not alter workflow)

### `data_model.md`

- **Purpose**: key entities, relationships, semantic expectations.

### `evaluation_criteria.md`

- **Purpose**: define what “good enough” means beyond automated tests.

### `goldstandard_knowledge.md`

- **Purpose**: reference outputs, known-correct results, truth sets.

## Assumptions / trade-offs

- Framework performs **presence checks** only; semantic validation is project-owned.
- No interpretation of domain text is performed by the framework itself.
