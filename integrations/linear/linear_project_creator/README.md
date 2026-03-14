# linear_project_creator

DevOS planning CLI and optional Linear sync adapter.

The repository planning artifact (`.devOS/planning/project_plan.yaml`) is the
source of truth. This tool validates that artifact deterministically, then
optionally projects it to Linear (project → epics → stories → tasks).

---

## Requirements

- Python 3.10+
- A Linear account with API access
- A Linear team ID

---

## Installation

```bash
cd integrations/linear/linear_project_creator
pip install -r requirements.txt
```

---

## Obtaining a Linear API Key

1. Log in at [linear.app](https://linear.app).
2. Go to **Settings → API** (direct URL: `https://linear.app/settings/api`).
3. Under **Personal API keys**, click **Create key**.
4. Give it a descriptive label (e.g. `devos-project-creator`).
5. Copy the generated key — it is shown only once.

### Obtaining a Linear Team ID

1. Go to **Settings → General** for your workspace.
2. Click on the team you want to use.
3. The team ID is visible in the URL: `https://linear.app/<workspace>/settings/teams/<team-id>/general`
   or use the Linear API Explorer to run:

```graphql
{ teams { nodes { id name } } }
```

---

## Configuration

Set the following environment variables before running the tool:

| Variable          | Required | Description                              |
|-------------------|----------|------------------------------------------|
| `LINEAR_API_KEY`  | Yes      | Your Linear personal or application API key |
| `LINEAR_TEAM_ID`  | Yes      | The UUID of your Linear team            |

**Linux / macOS:**

```bash
export LINEAR_API_KEY="lin_api_xxxxxxxxxxxxxxxxxxxx"
export LINEAR_TEAM_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Windows (PowerShell):**

```powershell
$env:LINEAR_API_KEY = "lin_api_xxxxxxxxxxxxxxxxxxxx"
$env:LINEAR_TEAM_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

---

## Usage

```
python main.py [PROJECT_PLAN] [--dry-run] [--verbose] [--output <path>] [--lint-mode <enforce|warn>]
```

### Arguments

| Argument      | Description                                              |
|---------------|----------------------------------------------------------|
| `PROJECT_PLAN`| Path to DevOS planning artifact YAML (default: `.devOS/planning/project_plan.yaml`; legacy fallback: `.devos/planning/project_plan.yaml`). |
| `--dry-run`   | Log all actions without making any Linear API calls.     |
| `--verbose`   | Enable DEBUG-level logging.                              |
| `--output`    | Path for the output mapping JSON (default: `linear_mapping.json`). |
| `--lint-mode` | Lint gate behavior: `enforce` (default) or `warn`.       |

### Examples

**Dry-run against canonical DevOS planning artifact:**

```powershell
python main.py .devOS/planning/project_plan.yaml --dry-run --verbose --lint-mode enforce
```

**Validate then sync to Linear for real:**

```powershell
python main.py .devOS/planning/project_plan.yaml --output my_mapping.json --lint-mode enforce
```

---

## Work Item Quality System

The tool enforces two distinct validation layers before making any Linear API calls.

### Layer 1 — Structural validation (`yaml_parser.py`)

Checks required fields, types, and bounded values. Errors are reported as a single
aggregated message listing every violation.

### Layer 2 — Semantic quality lint (`work_item_linter.py`)

Applies the rules from [`contracts/work_item_linter_rules.md`](contracts/work_item_linter_rules.md)
to the parsed model. Checks that work items satisfy the
[Work Item Contract](contracts/work_item_contract.md) at the semantic level.

Rules enforced:

| Rule ID | Scope | Description |
|---|---|---|
| `PROJECT_NO_EPIC_DEPS` | Project | Multi-epic project must declare at least one epic `blocks` dependency |
| `EPIC_MIN_STORIES` | Epic | Must contain ≥ 2 stories |
| `EPIC_MAX_STORIES` | Epic | Must contain ≤ 10 stories |
| `EPIC_DESC_MIN_WORDS` | Epic | Description must contain ≥ 20 words covering capability, motivation, and system impact |
| `EPIC_MISSING_MILESTONE` | Epic | Must be assigned to a milestone when project defines milestones |
| `EPIC_AC_CHECKBOX_FORMAT` | Epic | `acceptance_criteria` must contain at least one `- [ ]` checkbox item |
| `EPIC_BLOCKS_VALID` | Epic | All `blocks` references must name epics defined in this project |
| `EPIC_BLOCKS_CYCLE` | Epic | `blocks` declarations must not form a directed cycle |
| `STORY_REQUIRED_FIELD` | Story | Must define all five DevOS planning fields |
| `STORY_DESIGN_FREEDOM_REQUIRED` | Story | `design_freedom` is required; must be `high` or `restricted` |
| `STORY_DESIGN_FREEDOM` | Story | `design_freedom`, when present, must be `high` or `restricted` |
| `STORY_AC_REQUIRED` | Story | Must include `acceptance_criteria` |
| `STORY_AC_CHECKBOX_FORMAT` | Story | `acceptance_criteria` must contain at least one `- [ ]` checkbox item |
| `STORY_TASK_MIN` | Story | Must contain ≥ 2 tasks |
| `STORY_TASK_MAX` | Story | Must contain ≤ 7 tasks |
| `STORY_MISSING_TEST_TASK` | Story | At least one task must declare `task_type: verification` or have a test-oriented name |
| `STORY_BLOCKS_VALID` | Story | All `blocks` references must name stories defined in this project |
| `STORY_BLOCKS_CYCLE` | Story | `blocks` declarations must not form a directed cycle |
| `TASK_MULTI_ACTION` | Task | Name must not combine multiple unrelated actions |
| `TASK_MISSING_DOD` | Task | Must include a non-empty `done_criteria` field |
| `TASK_TYPE_VALID` | Task | `task_type`, when present, must be `implementation` or `verification` |

Violations are reported with full context paths and rule IDs. Behavior is controlled by
`--lint-mode`:
- `enforce` (default): violations block execution with exit code `1`
- `warn`: violations are logged as warnings and execution continues

### Generation prompts

When authoring YAML input files, use the generation prompts as authoring guidance:

- [`prompts/epic_generation_prompt.md`](prompts/epic_generation_prompt.md) — Epic authoring rules
- [`prompts/story_generation_prompt.md`](prompts/story_generation_prompt.md) — Story authoring rules

### Quality checklists

Before submitting a YAML file, verify each Story and Task against:

- [`quality/story_quality_checklist.md`](quality/story_quality_checklist.md) — Story readiness checks
- [`quality/task_quality_checklist.md`](quality/task_quality_checklist.md) — Task readiness checks

A Story is considered DevOS-ready only when all checklist items pass. The linter enforces
the mechanically verifiable subset; the checklists cover the full semantic contract.

### Lint mode

```
python main.py <YAML_FILE> --lint-mode enforce
python main.py <YAML_FILE> --lint-mode warn
```

Use `enforce` for normal DevOS operation (deterministic gate).  
Use `warn` only when an explicitly approved temporary bypass is required (for example, legacy
YAML migration). Work items with unresolved violations must still be revised before entering
the DevOS planning pipeline.

### Task Definition of Done (`done_criteria`)

Every task should include a `done_criteria` field describing the verifiable outcome that
proves the task is complete. Linted by `TASK_MISSING_DOD`.

```yaml
tasks:
  - name: "Implement run lifecycle initialization logic"
    task_type: implementation
    description: "Add run_id assignment, run directory setup, and resume entry points."
    done_criteria: |
      runtime/run_engine.py initializes run directories with correct identifiers.
      Resume path reconstructs run state from persisted evidence.
      Unit tests cover both init and resume paths. All tests pass.
```

### Task Type (`task_type`)

Tasks may declare a `task_type` field to express their **semantic pipeline role**:

| Value | Meaning | Effect |
|---|---|---|
| `implementation` | Produces a code artifact or system change | Applied as a Linear label |
| `verification` | Produces test evidence | Applied as a Linear label; satisfies `STORY_MISSING_TEST_TASK` without keyword matching |

Using `task_type: verification` is the preferred way to declare a test task. It is
explicit, machine-readable, and works regardless of task name wording.

```yaml
tasks:
  - name: "Implement gate check sequence"
    task_type: implementation
    done_criteria: "gate_evaluator enforces checks in fixed order per contract."
  - name: "Write unit tests for gate check sequence"
    task_type: verification
    done_criteria: "All pass/fail cases covered. Test suite passes."
```

### Story Dependency Modeling (`blocks`)

Stories may declare explicit blocking dependencies using the `blocks` field.
After all issues are created, these are resolved to Linear `blocks` issue relations.

```yaml
stories:
  - name: "Implement shared types and framework loaders"
    blocks:
      - "Implement run engine and workflow engine state progression"
      - "Implement store and artifact system behavior"
```

This means `Implement shared types` must complete before the blocked stories can start.
The tool creates the corresponding Linear relations automatically in a post-build pass.
Cross-epic references are supported. Unresolvable names are logged as warnings and
captured in the run report.

Cycle detection runs at lint time (`STORY_BLOCKS_CYCLE`, `EPIC_BLOCKS_CYCLE`). Cycles
fail the build in `enforce` mode before any API call is made.

---

## YAML Input Contract

The tool enforces a strict quality contract before making any Linear API calls.
All validation errors are aggregated and reported in a single failure message.
See [`templates/template.yaml`](templates/template.yaml) for the full annotated reference.

### Required fields per object level

| Level     | Required fields                                                             |
|-----------|-----------------------------------------------------------------------------|
| `project` | `name`, `description`                                                       |
| `epic`    | `name`, `description` (≥ 20 words), `acceptance_criteria`                  |
| `story`   | `name`, `description`, `effort` (1–5), `complexity` (1–5), `design_freedom` |
| `task`    | `name` (bare string or mapping)                                             |

### Optional fields with lint enforcement

| Field | Level | Lint rule | Notes |
|---|---|---|---|
| `acceptance_criteria` | Epic | `EPIC_AC_CHECKBOX_FORMAT` | Must use `- [ ]` format |
| `acceptance_criteria` | Story | `STORY_AC_CHECKBOX_FORMAT` | When present, must use `- [ ]` format |
| `done_criteria` | Task | `TASK_MISSING_DOD` | Verifiable outcome for task completion |
| `task_type` | Task | `TASK_TYPE_VALID` | `implementation` or `verification`; enables agent filtering |
| `blocks` | Story | `STORY_BLOCKS_VALID`, `STORY_BLOCKS_CYCLE` | List of story names blocked by this story |
| `blocks` | Epic | `EPIC_BLOCKS_VALID`, `EPIC_BLOCKS_CYCLE` | List of epic names blocked by this epic |
| `assignee` | Story/Task | — | Strongly recommended; enables ownership tracking |

### Effort and complexity scales

Both `effort` and `complexity` are integers in the range **1–5**.

**Effort** — how much work is involved:

| Value | Meaning     | Guideline                                      |
|-------|-------------|------------------------------------------------|
| 1     | Trivial     | Straightforward change, < 1 day               |
| 2     | Small       | Clear scope, 1–2 days                         |
| 3     | Medium      | Moderate scope, a few days                    |
| 4     | Large       | Cross-module, ~1 week                         |
| 5     | Very Large  | High uncertainty or cross-system impact       |

**Complexity** — how difficult the design decisions are:

| Value | Meaning     | Guideline                                             |
|-------|-------------|-------------------------------------------------------|
| 1     | Simple      | Well-understood, deterministic solution               |
| 2     | Low         | Few decisions, low risk                               |
| 3     | Moderate    | Some unknowns or design decisions                     |
| 4     | High        | Significant unknowns or cross-cutting concerns        |
| 5     | Very High   | Exploratory, novel, or high coordination cost         |

### Story estimate derivation

```
estimate = effort + complexity   (range: 2–10)
```

The tool computes this value automatically. Do **not** set `estimate` manually in YAML.
If `estimate` is present and conflicts with the computed value, the parser returns a validation error.

### Epic acceptance criteria

Every epic must include a non-empty `acceptance_criteria` markdown block using `- [ ]`
checkbox format. The tool appends it to the Linear issue body under a `## Acceptance Criteria`
heading. Enforced by `EPIC_AC_CHECKBOX_FORMAT`.

```yaml
epics:
  - name: "My Epic"
    description: "Epic scope and goals."
    acceptance_criteria: |
      - [ ] Verifiable outcome A
      - [ ] Verifiable outcome B
    stories:
      - name: "My Story"
        description: "Story objective and scope."
        design_freedom: "high"
        effort: 2
        complexity: 3
        tasks:
          - name: "Implement X"
            task_type: implementation
            description: "Implementation notes."
            done_criteria: "Module X is implemented. All unit tests pass."
          - name: "Write unit tests for X"
            task_type: verification
            done_criteria: "All branches covered. Test suite passes."
```

### Label auto-creation

Labels referenced in `labels:` fields are resolved to Linear IDs automatically.
Labels not yet present in Linear are created on first use.

To provide metadata for new labels, define them in `label_definitions`:

```yaml
label_definitions:
  issue_labels:
    - name: "epic"
      description: "Top-level workstream issue."
      color: "#4F46E5"
  project_labels:
    - name: "platform"
      description: "Platform and infrastructure scope."
      color: "#14B8A6"
```

---

## Output Files

### `linear_mapping.json`

After a successful run, a mapping file is written to `linear_mapping.json` (or the path
specified with `--output`). It maps human-readable names to Linear IDs:

```json
{
  "project": "PRJ-xxxxxxxx",
  "milestones": {
    "Alpha": "MS-xxxxxxxx"
  },
  "epics": {
    "Runtime Foundation": "ISS-xxxxxxxx"
  },
  "stories": {
    "Shared runtime types": "ISS-yyyyyyyy"
  },
  "tasks": {
    "Implement RunId type": "ISS-zzzzzzzz"
  }
}
```

This file is flushed to disk incrementally after each epic completes. If the run fails
mid-way, the partial mapping contains all IDs created before the failure.

### `<mapping_stem>_report.json`

A machine-readable run report is written alongside the mapping file (e.g.
`linear_mapping_report.json`). It captures:

- Timestamp and input file path
- Lint mode and violation list
- Creation counts (milestones, epics, stories, tasks, relations)
- Unresolved blocks references (if any)

```json
{
  "schema_version": "1",
  "timestamp": "2026-03-14T10:00:00+00:00",
  "yaml_source": "/path/to/project.yaml",
  "dry_run": false,
  "lint": {
    "mode": "enforce",
    "violation_count": 0,
    "violations": []
  },
  "build": {
    "project_id": "PRJ-xxxxxxxx",
    "milestones_created": 3,
    "epics_created": 3,
    "stories_created": 13,
    "tasks_created": 39,
    "relations_created": 12,
    "unresolved_blocks_count": 0,
    "unresolved_blocks": []
  }
}
```

---

## Exit Codes

| Code | Meaning                                         |
|------|-------------------------------------------------|
| `0`  | Success (all objects created or dry-run passed) |
| `1`  | Configuration error, YAML validation error, or API error |

---

## Project Structure

```
linear_project_creator/
├── main.py                # Planning validation + optional Linear projection
├── planning_engine.py     # Tool-agnostic parsing + deterministic linting
├── linear_provider.py     # Linear WorkItemProvider adapter
├── work_item_provider.py  # External integration adapter interface
├── linear_client.py       # GraphQL HTTP client; includes create_issue_relation()
├── project_builder.py     # Orchestration: project → epics → stories → tasks → relations
│                          # Returns (mapping, BuildStats) with creation counters
├── yaml_parser.py         # YAML loading and structural validation (Layer 1)
├── work_item_linter.py    # Semantic quality linting against work item contract (Layer 2)
├── models.py              # Frozen dataclasses (TaskModel, StoryModel, EpicModel, ProjectModel)
├── config.py              # Environment variable loading
├── requirements.txt
├── README.md
├── contracts/
│   ├── work_item_contract.md       # Semantic quality requirements for all work items
│   └── work_item_linter_rules.md   # Automatable linting rules (enforced by work_item_linter.py)
├── prompts/
│   ├── epic_generation_prompt.md   # Authoring guidance for Epics (description requirements)
│   └── story_generation_prompt.md  # Authoring guidance for Stories (vertical slice + dependencies)
├── quality/
│   ├── story_quality_checklist.md  # Full Story readiness checklist (vertical slice + dependency)
│   └── task_quality_checklist.md   # Full Task readiness checklist (done_criteria + task_type)
└── templates/
    └── template.yaml               # Annotated canonical input contract
```

---

## Error Handling

- **YAML validation errors** are reported upfront with every missing or invalid field listed before any API call is made.
- **Linear API errors** (GraphQL errors, HTTP 4xx/5xx) raise `LinearAPIError` with the response detail.
- **Transient failures** (HTTP 429, 5xx) are retried up to 3 times with exponential backoff (1s, 2s, 4s).
- **Rate limit budget** is monitored via the `X-RateLimit-Remaining` header; the client sleeps proactively when fewer than 5 requests remain.
- On any error mid-run, the partial mapping written so far is flushed to the output file.
