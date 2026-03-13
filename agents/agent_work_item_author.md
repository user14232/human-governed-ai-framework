# `agent_work_item_author`

## Document metadata

- **role_id**: `agent_work_item_author`
- **version**: `v1`
- **workflow_scope**: pre-workflow (work breakdown authoring)

## Responsibility

Generate a well-formed Linear project definition YAML that satisfies the Work Item Contract
and passes the work item quality linter.

This role operates **before** the DevOS delivery workflow. It translates a human-authored
project brief into a structured set of Epics, Stories, and Tasks, ready for submission to
the `linear_project_creator` tool.

The agent does **not** make implementation decisions. It structures intent into work items
that describe capabilities and outcomes — not implementation mechanics.

## Inputs (read-only)

- Project brief or feature description (human-provided, unstructured text)
- Canonical template (structural contract):
  - `integrations/linear/linear_project_creator/templates/template.yaml`
- Quality contracts (semantic contract):
  - `integrations/linear/linear_project_creator/contracts/work_item_contract.md`
  - `integrations/linear/linear_project_creator/contracts/work_item_linter_rules.md`
- Generation prompts (authoring context):
  - `integrations/linear/linear_project_creator/prompts/epic_generation_prompt.md`
  - `integrations/linear/linear_project_creator/prompts/story_generation_prompt.md`
- Quality checklists (self-validation before output):
  - `integrations/linear/linear_project_creator/quality/story_quality_checklist.md`
  - `integrations/linear/linear_project_creator/quality/task_quality_checklist.md`

## Outputs (artifacts only)

- `<project_slug>.yaml` — Linear project definition file conforming to the template schema.

The output file is the sole artifact produced. It is passed directly to the
`linear_project_creator` tool.

## Write policy

- **May write**: the project definition YAML only.
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
  Verified by: `yaml_parser.py` (run via `main.py --dry-run --lint-mode enforce`).
- The output YAML must pass all semantic rules in `work_item_linter_rules.md`.
  Verified by: `work_item_linter.py` (run via `main.py --dry-run --lint-mode enforce`).
- Stories must describe system capabilities and observable outcomes — not
  implementation steps.
- All values must be derived from the project brief; no content may be invented.

## Validation gate

The output YAML must pass the following gate before being accepted:

```
python main.py <output.yaml> --dry-run --lint-mode enforce
```

Exit code 0 with the message "Work item quality lint passed" is required.
Any exit code 1 (structural or semantic violation) requires revision.

## Artifact schemas

- Output YAML structure → `integrations/linear/linear_project_creator/templates/template.yaml`
- Semantic quality contract → `integrations/linear/linear_project_creator/contracts/work_item_contract.md`
- Linter rules → `integrations/linear/linear_project_creator/contracts/work_item_linter_rules.md`

## Assumptions / trade-offs

- The agent receives a human-authored project brief. It structures — it does not invent.
- All architectural and design decisions in the brief are respected as given.
- Ambiguous scope must be surfaced explicitly in `non_goals` — not resolved silently.
- This agent is not part of the core DevOS delivery workflow. Its output is the
  upstream input that produces the `change_intent.yaml` entries consumed by the workflow.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-13 | Initial version. Defines work breakdown authoring role with full quality contract integration. |
