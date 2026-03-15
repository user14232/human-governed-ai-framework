from __future__ import annotations

from pathlib import Path

from agent_runtime.artifact_parser import ArtifactParseError, ParsedArtifact, parse_artifacts
from agent_runtime.llm_client import LLMClient
from agent_runtime.prompt_builder import (
    PromptContext,
    build_prompt,
    load_example_artifacts,
    load_input_contents,
)
from kernel.framework.agent_loader import AgentContract
from kernel.types.artifact import ArtifactSchema


class LLMAdapterError(RuntimeError):
    """Base class for LLM adapter errors."""


class MissingLLMOutputError(LLMAdapterError):
    """
    Raised when the LLM response does not contain one or more expected output artifacts.
    """


class LLMAgentAdapter:
    """
    Automated agent adapter that drives a single DevOS agent role using an LLM.

    Contract:
        - Implements the AgentAdapter protocol defined in runtime/agents/invocation_layer.py.
        - Stateless between invocations: no mutable state accumulates across calls.
        - Does NOT write to the decision log, workflow engine, or event system directly.
        - Does NOT modify framework files.
        - Only writes artifact files to output_dir (which is ctx.artifacts_dir).
        - Artifact validation is performed by the artifact system after writing.

    Constructor Args:
        agent_contract: Parsed agent contract for the role this adapter drives.
        schemas:        Map of artifact_type -> ArtifactSchema, used in prompt construction.
        llm_client:     Configured LLMClient instance for this adapter.
    """

    def __init__(
        self,
        agent_contract: AgentContract,
        schemas: dict[str, ArtifactSchema],
        llm_client: LLMClient,
    ) -> None:
        self._contract = agent_contract
        self._schemas = schemas
        self._llm_client = llm_client

    def invoke(
        self,
        input_paths: dict[str, Path],
        output_dir: Path,
    ) -> dict[str, Path]:
        """
        Execute one single-shot agent invocation.

        Steps:
        1. Read all input artifact files.
        2. Build a prompt from contract + inputs + schemas.
        3. Call the LLM client.
        4. Parse the LLM response into artifact blocks.
        5. Write each artifact to output_dir.
        6. Return mapping of artifact_name -> written path.

        Raises:
            FileNotFoundError:    If an input artifact path is missing.
            LLMAdapterError:      On LLM communication or parsing failures.
            MissingLLMOutputError: If an expected output artifact is absent from the response.
        """
        input_contents = load_input_contents(input_paths)
        output_schemas = self._extract_output_schemas()
        examples = load_example_artifacts(self._contract.output_artifacts)

        prompt_ctx = PromptContext(
            agent_role=self._contract.role_id,
            agent_contract=self._contract,
            input_contents=input_contents,
            output_schemas=output_schemas,
            example_artifacts=examples,
        )
        prompt = build_prompt(prompt_ctx)

        try:
            response = self._llm_client.generate(prompt)
        except Exception as exc:
            raise LLMAdapterError(
                f"LLM invocation failed for agent '{self._contract.role_id}': {exc}"
            ) from exc

        try:
            parsed = parse_artifacts(
                response=response,
                expected_names=self._contract.output_artifacts,
            )
        except ArtifactParseError as exc:
            raise LLMAdapterError(
                f"Failed to parse LLM response for agent '{self._contract.role_id}': {exc}"
            ) from exc

        return self._write_artifacts(parsed, output_dir)

    def _extract_output_schemas(self) -> dict[str, ArtifactSchema]:
        """
        Build a mapping of artifact_type -> schema for each declared output artifact.

        Artifact type is derived from the filename: `implementation_plan.yaml` → `implementation_plan`.
        """
        output_schemas: dict[str, ArtifactSchema] = {}
        for artifact_name in self._contract.output_artifacts:
            artifact_type = _artifact_type_from_name(artifact_name)
            schema = self._schemas.get(artifact_type)
            if schema is not None:
                output_schemas[artifact_type] = schema
        return output_schemas

    def _write_artifacts(
        self,
        parsed: list[ParsedArtifact],
        output_dir: Path,
    ) -> dict[str, Path]:
        """
        Write each parsed artifact to output_dir.

        Only writes artifacts whose names are declared in contract.output_artifacts.
        Returns mapping of artifact_name -> written path.
        Raises MissingLLMOutputError if any declared output is absent from the parsed list.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, Path] = {}
        parsed_by_name = {artifact.name: artifact for artifact in parsed}

        for artifact_name in self._contract.output_artifacts:
            artifact = parsed_by_name.get(artifact_name)
            if artifact is None:
                raise MissingLLMOutputError(
                    f"Agent '{self._contract.role_id}': LLM response did not produce "
                    f"required output artifact '{artifact_name}'. "
                    f"Artifacts present in response: {sorted(parsed_by_name.keys())}."
                )
            output_path = output_dir / artifact_name
            output_path.write_text(artifact.content, encoding="utf-8")
            written[artifact_name] = output_path

        return written


def _artifact_type_from_name(artifact_name: str) -> str:
    path = Path(artifact_name)
    suffix = path.suffix
    return path.name[: -len(suffix)] if suffix else path.name
