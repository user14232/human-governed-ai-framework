# tests/

This directory contains **automated verification** for the DevOS runtime.

## Relation to DevOS Architecture

Tests verify that the DevOS Kernel enforces workflow governance correctly — correct state transitions, artifact immutability, gate evaluation, decision log handling, and event emission. Tests do not test agent reasoning or LLM output.

## Contents

| Directory | Scope |
| --- | --- |
| `unit/` | Isolated tests for individual kernel modules: artifact system, gate evaluator, workflow engine, decision system, event system, store primitives |
| `integration/` | Multi-module tests covering full run lifecycle, autonomous workflow progression, event sequence requirements, and CLI smoke tests |
| `e2e/` | End-to-end manual and scripted tests exercising the full kernel invocation path |

## Running Tests

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

See `requirements-runtime-tests.txt` for test dependencies.

## What Belongs Here

- Kernel behavior tests (state machine, gate logic, artifact handling)
- Runtime CLI tests
- Integration tests that use the filesystem and real workflow definitions
- End-to-end invocation scripts

Do not place framework definitions, example workspaces, or runtime implementation here.
