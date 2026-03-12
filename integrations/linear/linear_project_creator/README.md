# linear_project_creator

A Python CLI tool that creates a full project hierarchy in Linear (project → epics → stories → tasks) from a YAML definition file using the Linear GraphQL API.

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
python main.py <YAML_FILE> [--dry-run] [--verbose] [--output <path>]
```

### Arguments

| Argument      | Description                                              |
|---------------|----------------------------------------------------------|
| `YAML_FILE`   | Path to the project definition YAML file.                |
| `--dry-run`   | Log all actions without making any Linear API calls.     |
| `--verbose`   | Enable DEBUG-level logging.                              |
| `--output`    | Path for the output mapping JSON (default: `linear_mapping.json`). |

### Examples

**Dry-run against an included example:**

```powershell
python main.py examples/devos_runtime_v1.yaml --dry-run --verbose
```

**Create the project for real:**

```powershell
python main.py examples/devos_runtime_v1.yaml --output my_mapping.json
```

---

## YAML Input Contract

The tool enforces a strict quality contract before making any Linear API calls.
All validation errors are aggregated and reported in a single failure message.
See [`examples/template.yaml`](examples/template.yaml) for the full annotated reference.

### Required fields per object level

| Level     | Required fields                                                             |
|-----------|-----------------------------------------------------------------------------|
| `project` | `name`, `description`                                                       |
| `epic`    | `name`, `description`, `acceptance_criteria`                                |
| `story`   | `name`, `description`, `effort` (1–5), `complexity` (1–5)                  |
| `task`    | `name` (bare string or mapping)                                             |

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

Every epic must include a non-empty `acceptance_criteria` markdown block.
The tool appends it to the Linear issue body under a `## Acceptance Criteria` heading.

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
        effort: 2
        complexity: 3
        tasks:
          - name: "Implement X"
            description: "Implementation notes."
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

## Output: linear_mapping.json

After a successful run, a mapping file is written to `linear_mapping.json` (or the path specified with `--output`). It maps human-readable names to Linear IDs:

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

This file is flushed to disk incrementally after each epic completes. If the run fails mid-way, the partial mapping contains all IDs created before the failure.

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
├── main.py            # CLI entry point
├── linear_client.py   # GraphQL HTTP client with retry and rate-limit handling
├── project_builder.py # Orchestration: project → epics → stories → tasks
├── yaml_parser.py     # YAML loading and structural validation
├── models.py          # Frozen dataclasses (TaskModel, StoryModel, EpicModel, ProjectModel)
├── config.py          # Environment variable loading
├── requirements.txt
├── README.md
└── examples/
    ├── template.yaml                  # Annotated canonical input contract
    ├── shared_runtime_types_p-1.yaml  # Package 1: shared runtime types
    ├── framework_loaders_p-2.yaml     # Package 2: framework loader layer
    └── devos_runtime_v1.yaml          # Full DevOS runtime v1 project
```

---

## Error Handling

- **YAML validation errors** are reported upfront with every missing or invalid field listed before any API call is made.
- **Linear API errors** (GraphQL errors, HTTP 4xx/5xx) raise `LinearAPIError` with the response detail.
- **Transient failures** (HTTP 429, 5xx) are retried up to 3 times with exponential backoff (1s, 2s, 4s).
- **Rate limit budget** is monitored via the `X-RateLimit-Remaining` header; the client sleeps proactively when fewer than 5 requests remain.
- On any error mid-run, the partial mapping written so far is flushed to the output file.
