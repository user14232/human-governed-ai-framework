# workspace_examples/

This directory contains **example DevOS workspaces** — self-contained directories that simulate or demonstrate real DevOS workflow execution.

## Relation to DevOS Architecture

A DevOS workspace is a project root that contains the mandatory inputs and run artifacts produced by the kernel. These example workspaces provide reproducible references for understanding how runs are structured and how the kernel traverses workflow states.

## Contents

| Directory | Purpose |
| --- | --- |
| `manual_runtime_exploration/` | Workspace used for manual kernel invocation and exploratory testing of workflow transitions |
| `runtime_simulation/` | Workspace with pre-populated artifacts and run state to simulate a complete delivery workflow execution |

## What Belongs Here

- Self-contained workspace directories with project inputs and run artifacts
- Simulated or replayed run directories that demonstrate workflow state progression
- Reference workspaces for manual kernel testing

Do not place framework definitions, runtime implementation code, or test fixtures here.
