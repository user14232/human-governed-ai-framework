# TASK QUALITY CHECKLIST

Tasks represent concrete implementation actions.

## Task Requirements

□ Task represents a single implementation step
□ Task affects a limited number of files or components
□ Task produces a concrete result

## Task Clarity

□ Task description is unambiguous
□ Task does not combine multiple unrelated actions

## Examples

Bad:

Implement parser and refactor event system.

Good:

Implement YAML workflow parsing logic.

Good:

Add unit tests for workflow parsing module.

## Definition of Done

□ `done_criteria` field is present and non-empty (required by TASK_MISSING_DOD)
□ `done_criteria` references a concrete output artifact, passing test result,
  or observable system state — not a vague description of effort
□ `done_criteria` is sufficient for another engineer or agent to verify
  task completion without subjective judgement

## Examples: done_criteria

Bad:

```
done_criteria: "Implementation is complete."
```

Good:

```
done_criteria: |
  runtime/framework/workflow_loader.py is implemented.
  Loader parses workflow YAML into WorkflowDefinition structures.
  All unit tests in tests/test_workflow_loader.py pass.
```

Good:

```
done_criteria: |
  Gate check functions for inputs_present, artifact_present, approved,
  and condition_met are implemented in runtime/gate/evaluator.py.
  Deterministic test fixtures cover all pass and fail cases.
  All existing tests continue to pass.
```
