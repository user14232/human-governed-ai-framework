# `agent_work_item_author`

## Document metadata

- **role_id**: `agent_work_item_author`
- **version**: `v1`
- **workflow_scope**: pre-workflow (work breakdown authoring)

## Responsibility

Generate a well-formed DevOS planning artifact YAML that satisfies the Work Item Contract
and passes the work item quality linter.

This role operates **before** the DevOS delivery workflow. It translates a human-authored
project brief into a structured set of Epics, Stories, and Tasks, ready for deterministic
validation and optional external sync.

The agent does **not** make implementation decisions. It structures intent into work items
that describe capabilities and outcomes — not implementation mechanics.

## Inputs (read-only)

- Project brief or feature description (human-provided, unstructured text)
- Canonical template (structural contract):
  - `.devOS/planning/project_plan.yaml`
- Quality contracts (semantic contract):
  - `devos/planning/contracts/work_item_contract.md`
  - `devos/planning/contracts/work_item_linter_rules.md`
- Generation prompts (authoring context):
  - `devos/planning/prompts/epic_generation_prompt.md`
  - `devos/planning/prompts/story_generation_prompt.md`
- Quality checklists (self-validation before output):
  - `devos/planning/quality/story_quality_checklist.md`
  - `devos/planning/quality/task_quality_checklist.md`

## Outputs (artifacts only)

- `.devOS/planning/project_plan.yaml` — canonical DevOS planning artifact.

The output file is the sole artifact produced. It is validated first, then may
be projected by optional integrations (for example Linear).

## Write policy

- **May write**: `.devOS/planning/project_plan.yaml` only.
- **Must not write**: implementation code, test plans, architecture contracts,
  framework workflow definitions, domain input files.

## Prohibitions

- Must not prescribe implementation decisions unless `design_freedom` is `restricted`.
- Must not author work items using implementation-mechanic language
  (e.g. "create class", "add function", "refactor code").
- Must not produce a Story without all five required DevOS planning fields:
  `problem_statement`, `scope`, `constraints`, `architecture_context`, `non_goals`.
- Must not produce an Epic with fewer than 2 Stories.
- Must not produce a Story with fewer than 2 Tasks or more than 7 Tasks.
- Must not produce a Task that combines multiple unrelated actions.
- Must not invent requirements not present in the human-provided project brief.
- Must not resolve ambiguous scope by assumption; ambiguity must be surfaced
  in `non_goals` or escalated to the human author.

## Determinism requirements

- The output YAML must be structurally valid per the template schema.
  Verified by: `devos.planning.planning_parser` (run via `python -m devos.planning.cli`).
- The output YAML must pass all semantic rules in `work_item_linter_rules.md`.
  Verified by: `devos.planning.work_item_linter` (run via `python -m devos.planning.cli`).
- Stories must describe system capabilities and observable outcomes — not
  implementation steps.
- All values must be derived from the project brief; no content may be invented.

## Validation gate

The output YAML must pass the following gate before being accepted:

```
python -m devos.planning.cli sync linear .devOS/planning/project_plan.yaml --dry-run --lint-mode enforce
```

Exit code 0 with the message "Work item quality lint passed" is required.
Any exit code 1 (structural or semantic violation) requires revision.

## Artifact schemas

- Output YAML structure → `.devOS/planning/project_plan.yaml`
- Semantic quality contract → `devos/planning/contracts/work_item_contract.md`
- Linter rules → `devos/planning/contracts/work_item_linter_rules.md`

## Assumptions / trade-offs

- The agent receives a human-authored project brief. It structures — it does not invent.
- All architectural and design decisions in the brief are respected as given.
- Ambiguous scope must be surfaced explicitly in `non_goals` — not resolved silently.
- This agent is not part of the core DevOS delivery workflow. Its output is the
  repository planning artifact, which may be synchronized to external tools by
  optional adapters.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-13 | Initial version. Defines work breakdown authoring role with full quality contract integration. |
