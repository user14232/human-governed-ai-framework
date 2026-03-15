from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kernel.framework.agent_loader import AgentContract
from kernel.types.artifact import ArtifactSchema

# Canonical location of filled example artifacts in the DevOS repository.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES_DIR = _REPO_ROOT / "examples" / "filled" / "run_example"


@dataclass(frozen=True)
class PromptContext:
    """
    All data required to construct an agent prompt.

    Fields:
        agent_role         — role_id from agent contract
        agent_contract     — fully parsed agent contract
        input_contents     — mapping of artifact filename -> file text content
        output_schemas     — mapping of output artifact type -> schema
        example_artifacts  — optional mapping of artifact filename -> example file content
    """

    agent_role: str
    agent_contract: AgentContract
    input_contents: dict[str, str]
    output_schemas: dict[str, ArtifactSchema]
    example_artifacts: dict[str, str] | None = None


def build_prompt(ctx: PromptContext) -> str:
    """
    Build a deterministic prompt string from agent contract, inputs, and schemas.

    Prompt structure (fixed):
    1. Role declaration
    2. Input artifacts (each with filename and content)
    3. Task declaration listing expected output artifacts
    4. Schema requirements for each output artifact (summary + full schema text)
    5. Example artifacts (when available)
    6. Response format instructions

    The format is explicit and deterministic. No heuristics or dynamic sections.
    """
    parts: list[str] = []

    parts.append(_role_section(ctx.agent_role))
    parts.append(_inputs_section(ctx.input_contents))
    parts.append(_task_section(ctx.agent_contract))
    parts.append(_schema_section(ctx.output_schemas, ctx.agent_contract))
    examples_section = _examples_section(ctx.example_artifacts or {}, ctx.agent_contract)
    if examples_section:
        parts.append(examples_section)
    parts.append(_format_section(ctx.agent_contract))

    return "\n\n".join(part for part in parts if part.strip())


def load_input_contents(
    input_paths: dict[str, Path],
) -> dict[str, str]:
    """
    Read all input artifact files and return their text content.

    Each value is the raw UTF-8 text of the file.
    Raises FileNotFoundError if any path is missing.
    """
    contents: dict[str, str] = {}
    for name, path in input_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Input artifact not found: {path}")
        contents[name] = path.read_text(encoding="utf-8")
    return contents


def load_example_artifacts(output_artifacts: tuple[str, ...]) -> dict[str, str]:
    """
    Load example artifact content from the canonical examples directory.

    Searches ``examples/filled/run_example/`` for files whose names match
    the declared output artifacts. Returns only the artifacts that are found.
    Missing examples are silently skipped — examples are optional guidance only.

    Args:
        output_artifacts: Tuple of artifact filenames declared by the agent contract.

    Returns:
        Mapping of artifact_filename -> raw file text for each found example.
        Empty dict if no examples are found or the examples directory does not exist.
    """
    if not _EXAMPLES_DIR.is_dir():
        return {}

    found: dict[str, str] = {}
    for artifact_name in output_artifacts:
        example_path = _EXAMPLES_DIR / artifact_name
        if example_path.is_file():
            found[artifact_name] = example_path.read_text(encoding="utf-8")
    return found


def _role_section(agent_role: str) -> str:
    return (
        f"You are the DevOS agent: `{agent_role}`.\n"
        "Your task is deterministic: produce structured artifacts as specified below.\n"
        "Do not invent requirements. Document all assumptions explicitly inside the artifacts.\n"
        "Do not interpret ambiguity — record unknowns as explicit assumptions."
    )


def _inputs_section(input_contents: dict[str, str]) -> str:
    if not input_contents:
        return "## Inputs\n\nNo input artifacts provided."

    lines: list[str] = ["## Inputs"]
    for name, content in sorted(input_contents.items()):
        lines.append(f"\n### {name}\n")
        lines.append("```")
        lines.append(content.rstrip())
        lines.append("```")
    return "\n".join(lines)


def _task_section(contract: AgentContract) -> str:
    lines: list[str] = ["## Your task"]
    lines.append("Produce the following output artifacts:")
    for artifact in sorted(contract.output_artifacts):
        lines.append(f"  - `{artifact}`")
    return "\n".join(lines)


def _schema_section(
    output_schemas: dict[str, ArtifactSchema],
    contract: AgentContract,
) -> str:
    lines: list[str] = ["## Schema requirements"]
    lines.append(
        "Each output artifact MUST conform exactly to its schema.\n"
        "Required fields and sections are listed below."
    )

    for artifact_name in sorted(contract.output_artifacts):
        artifact_type = _artifact_type_from_name(artifact_name)
        schema = output_schemas.get(artifact_type)

        lines.append(f"\n### `{artifact_name}`")

        if schema is None:
            lines.append("  No schema registered. Produce a well-structured artifact.")
            continue

        lines.append(f"  - Format: `{schema.file_format}`")

        if schema.required_fields:
            lines.append(f"  - Required fields: {', '.join(f'`{f}`' for f in schema.required_fields)}")

        if schema.required_sections:
            lines.append("  - Required sections (must appear in this order):")
            for section in schema.required_sections:
                lines.append(f"    - {section}")

        if schema.allowed_outcomes:
            lines.append(
                f"  - Allowed `outcome` values: {', '.join(f'`{o}`' for o in schema.allowed_outcomes)}"
            )

        if schema.raw_text:
            lines.append("\nFull schema definition:")
            lines.append("```")
            lines.append(schema.raw_text.strip())
            lines.append("```")

    return "\n".join(lines)


def _examples_section(
    example_artifacts: dict[str, str],
    contract: AgentContract,
) -> str:
    """
    Build the example artifacts section of the prompt.

    Only includes artifacts whose names are declared in the agent contract outputs
    and for which example content was found. Returns an empty string if no examples
    are available so that ``build_prompt`` can skip the section entirely.
    """
    relevant = {
        name: content
        for name, content in example_artifacts.items()
        if name in contract.output_artifacts
    }
    if not relevant:
        return ""

    lines: list[str] = ["## Example artifacts"]
    lines.append(
        "The following examples show valid artifacts.\n"
        "Use them as structural guidance but do not copy content directly."
    )

    for artifact_name in sorted(relevant.keys()):
        lines.append(f"\n### example: {artifact_name}\n")
        lines.append("```")
        lines.append(relevant[artifact_name].rstrip())
        lines.append("```")

    return "\n".join(lines)


def _format_section(contract: AgentContract) -> str:
    lines: list[str] = ["## Response format"]
    lines.append(
        "Return each artifact as a separate block using this exact delimiter format:\n"
    )
    lines.append("```")
    for artifact_name in sorted(contract.output_artifacts):
        lines.append(f"--- {artifact_name} ---")
        lines.append("<artifact content here>")
        lines.append("")
    lines.append("```")
    lines.append(
        "\nRules:\n"
        "- Use exactly `--- <artifact_name> ---` as the delimiter line.\n"
        "- The artifact name in the delimiter must match the filename exactly "
        "(e.g., `implementation_plan.yaml`).\n"
        "- Write the complete artifact content after the delimiter.\n"
        "- Do not include any explanatory text between artifact blocks.\n"
        "- Each artifact block ends when the next `--- <name> ---` delimiter appears "
        "or at end of response."
    )
    return "\n".join(lines)


def _artifact_type_from_name(artifact_name: str) -> str:
    path = Path(artifact_name)
    suffix = path.suffix
    return path.name[: -len(suffix)] if suffix else path.name
