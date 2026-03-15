# agent_runtime/

This directory implements the **Agent Runtime** — the layer that connects DevOS agent role contracts with external agent implementations.

## Relation to DevOS Architecture

The Agent Runtime sits between the DevOS Kernel and the underlying reasoning infrastructure. The Kernel invokes agents through the `AgentAdapter` protocol; this layer fulfills that protocol by selecting the appropriate agent, assembling context, invoking an LLM or other executor, and parsing the result back into a structured artifact.

The Agent Runtime performs **cognitive work only**. It does not govern workflow state, advance runs, or make decisions. All governance remains in the Kernel.

Agents may be implemented using LLMs, deterministic scripts, or other automation — the Agent Runtime is the adapter layer that abstracts these differences from the Kernel.

See `docs/architecture/agent_contracts.md` for the agent contract model and integration details.
See `docs/architecture/integration_model.md` for the artifact-first integration philosophy.

## Contents

| File | Purpose |
| --- | --- |
| `invocation_layer.py` | Dispatches agent invocations, manages the prompt/response cycle |
| `prompt_builder.py` | Assembles structured prompts from artifacts and agent role contracts |
| `llm_adapter.py` | Adapter for LLM backend calls |
| `llm_client.py` | Low-level LLM API client |
| `artifact_parser.py` | Parses LLM responses into structured artifacts |

## What Belongs Here

- Agent invocation adapters
- Prompt construction and context assembly
- LLM or automation backend clients
- Artifact parsing and structural extraction from agent outputs

Do not place workflow governance logic, state machine code, or domain rules here.
