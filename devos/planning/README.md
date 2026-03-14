# `devos.planning`

Deterministic planning package for repository-owned work breakdown artifacts.

## Responsibility

`devos/planning/` provides the planning layer before delivery workflow execution:

- load and parse the canonical planning artifact
- validate structure and semantic quality deterministically
- expose typed planning models for downstream adapters
- optionally project validated data into external systems via provider adapters

This package is upstream of runtime `PLANNING` state transitions. Runtime workflows
consume `change_intent.yaml`; this package manages work breakdown authoring and gating.

## Input Contract

- Default artifact path: `.devOS/planning/project_plan.yaml`
- Legacy fallback path: `.devos/planning/project_plan.yaml`
- CLI lint mode: `enforce` or `warn`
- Explicit plan path override: positional `plan` argument in CLI commands

## Output Contract

- Typed model: `ProjectModel` with deterministic hierarchy
- Quality findings: structured `LintViolation` records
- Optional sync output:
  - mapping JSON (`--output`, default `linear_mapping.json`)
  - run report JSON (`<mapping_stem>_report.json`)

## Determinism Rules

- no implicit scope expansion
- no hidden mutable state between stages
- no heuristic interpretation in gate decisions
- identical inputs must produce identical parse/lint outcomes

## Module Boundaries

- `planning_engine.py`  
  path resolution, parse + lint gate orchestration
- `planning_parser.py`  
  YAML-to-model parsing and structural validation
- `planning_models.py`  
  frozen planning dataclasses (no side effects)
- `work_item_linter.py`  
  deterministic semantic quality rules
- `work_item_provider.py`  
  provider contract for external projection adapters
- `cli.py`  
  batch entry points (`validate`, `sync`)

## CLI Usage

Validation only:

```bash
python -m devos.planning.cli validate .devOS/planning/project_plan.yaml --lint-mode enforce
```

Optional projection to Linear:

```bash
python -m devos.planning.cli sync linear .devOS/planning/project_plan.yaml --dry-run --lint-mode enforce --output tmp/planning_mapping.json
```

## Assumptions and Trade-offs

- source of truth remains repository artifact, not external trackers
- external provider sync is optional and executed only after validation
- lint `warn` mode is allowed for controlled migration, but `enforce` is default gate mode
- compatibility fallback for lowercase `.devos` is retained to avoid breaking existing repos

