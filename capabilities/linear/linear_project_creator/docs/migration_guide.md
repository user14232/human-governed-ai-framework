# Linear Project Creator — Migration Guide

This document covers migration from the pre-optimization schema to the current schema
introduced in the DevOS Integration Optimization. It provides rule-by-rule migration
steps and quality metrics for pilot monitoring.

---

## What Changed

### New required field: `design_freedom` on Stories

`design_freedom` was previously optional. It is now required and enforced by
`STORY_DESIGN_FREEDOM_REQUIRED`.

**Migration action:**
Add `design_freedom: "high"` or `design_freedom: "restricted"` to every story.

```yaml
# Before
- name: "Implement shared types"
  effort: 2
  complexity: 2
  description: "..."

# After
- name: "Implement shared types"
  design_freedom: "restricted"    # add this
  effort: 2
  complexity: 2
  description: "..."
```

### New optional field: `task_type` on Tasks

Tasks may now declare `task_type: implementation` or `task_type: verification`.

`task_type: verification` is the preferred way to satisfy `STORY_MISSING_TEST_TASK`
instead of relying on keyword matching in the task name.

**Migration action (recommended but not required):**
Add `task_type` to tasks that already satisfy `STORY_MISSING_TEST_TASK` by keyword.
No existing tasks are broken — keyword matching still works.

```yaml
# Before (still valid)
- name: "Write unit tests for X"
  done_criteria: "All tests pass."

# After (preferred)
- name: "Write unit tests for X"
  task_type: verification          # add this
  done_criteria: "All tests pass."
```

### New linter rules (breaking in enforce mode)

| Rule | Trigger |
|---|---|
| `STORY_DESIGN_FREEDOM_REQUIRED` | Story missing `design_freedom` |
| `EPIC_AC_CHECKBOX_FORMAT` | Epic AC missing `- [ ]` items |
| `EPIC_BLOCKS_CYCLE` | Cycle detected in epic `blocks` graph |
| `STORY_BLOCKS_CYCLE` | Cycle detected in story `blocks` graph |
| `TASK_TYPE_VALID` | `task_type` has an invalid value |

`EPIC_BLOCKS_CYCLE` and `STORY_BLOCKS_CYCLE` are only triggered when cycles actually
exist; well-formed YAMLs are unaffected.

`EPIC_AC_CHECKBOX_FORMAT` fires if any epic AC lacks `- [ ]` items. If existing epics
use plain text AC (no checkboxes), add `- [ ]` prefix to each criterion.

---

## Migration Checklist

Run `--lint-mode warn` to identify all violations without blocking:

```powershell
python main.py my_project.yaml --dry-run --lint-mode warn
```

Then address each violation category:

1. **`STORY_DESIGN_FREEDOM_REQUIRED`** — Add `design_freedom` to all stories.
2. **`EPIC_AC_CHECKBOX_FORMAT`** — Add `- [ ]` to all epic AC items.
3. **`EPIC_BLOCKS_CYCLE` / `STORY_BLOCKS_CYCLE`** — Remove the cycle; revise `blocks`.
4. **`TASK_TYPE_VALID`** — Fix invalid `task_type` values (must be `implementation` or `verification`).

Re-run with `--lint-mode enforce` to confirm zero violations before submitting to the
DevOS planning pipeline.

---

## Pilot Quality Metrics

Track the following metrics during and after rollout to verify improvement:

### Pre-build metrics (from lint output / run report `lint` section)

| Metric | Target | Source |
|---|---|---|
| `violation_count` per run | 0 | `lint.violation_count` in `_report.json` |
| `STORY_DESIGN_FREEDOM_REQUIRED` violations | 0 | `lint.violations[].rule_id` |
| `EPIC_AC_CHECKBOX_FORMAT` violations | 0 | `lint.violations[].rule_id` |
| Cycle violations (`*_CYCLE`) | 0 | `lint.violations[].rule_id` |

### Post-build metrics (from run report `build` section)

| Metric | Target | Source |
|---|---|---|
| `unresolved_blocks_count` | 0 | `build.unresolved_blocks_count` in `_report.json` |
| `relations_created` / expected | 100% | `build.relations_created` |

### Structural quality metrics (tracked across runs)

| Metric | Notes |
|---|---|
| % of tasks with `task_type` set | Track adoption of explicit type annotation |
| % of tasks with `task_type: verification` vs keyword-only | Prefer explicit over keyword |
| Stories per epic (distribution) | Should vary; symmetric counts signal template-following |

---

## Enforcement Rollout Sequence

1. **Validation (now):** Run all existing YAMLs with `--lint-mode warn`. Zero violations expected
   for YAMLs that already had `design_freedom` set (e.g. `runtime_phase3`).
2. **Hardening (next new YAML):** Use `--lint-mode enforce` for all new project YAMLs.
   No exceptions. Zero violations required before any Linear API call.
3. **Retroactive migration (existing YAMLs):** Address violations using the migration
   checklist above. Re-run with `--lint-mode enforce` after each fix.
4. **`task_type` adoption:** Add `task_type` fields to new tasks incrementally.
   Existing keyword-based test tasks continue to satisfy `STORY_MISSING_TEST_TASK`.

---

## Compatibility Note

The existing `runtime_phase3_runtime_implementation_project.yaml` passes all new rules
with zero violations (verified by dry-run on 2026-03-14). No migration is needed for
this YAML.
