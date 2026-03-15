from __future__ import annotations

import re
from dataclasses import dataclass


class ArtifactParseError(ValueError):
    """Raised when the LLM response cannot be parsed into the expected artifacts."""


@dataclass(frozen=True)
class ParsedArtifact:
    """
    One artifact extracted from an LLM response block.

    Fields:
        name     — artifact filename (e.g. implementation_plan.yaml)
        content  — raw text content of the artifact
    """

    name: str
    content: str


# Delimiter pattern: a line containing exactly `--- <artifact_name> ---`
# where artifact_name is a filename with a known extension.
_DELIMITER_PATTERN = re.compile(
    r"^---\s+([\w\-.]+\.(?:yaml|yml|json|md))\s+---\s*$",
    flags=re.IGNORECASE,
)


def parse_artifacts(
    response: str,
    expected_names: tuple[str, ...],
) -> list[ParsedArtifact]:
    """
    Parse LLM response text into a list of ParsedArtifact objects.

    Expected delimiter format:
        --- artifact_name ---
        <content lines>
        --- next_artifact_name ---
        <content lines>

    Rules:
    - Only artifact names that appear in `expected_names` are accepted.
    - Unknown artifact names in delimiters are silently ignored.
    - Content is trimmed of leading/trailing whitespace.
    - Each expected name must appear at most once (first occurrence wins).

    Args:
        response:       Raw text string returned by the LLM.
        expected_names: Tuple of artifact filenames the caller expects.

    Returns:
        List of ParsedArtifact, one per expected_name found in the response.
        Order matches the order in which delimiters appear in the response.

    Raises:
        ArtifactParseError: If no expected artifact delimiters are found at all.
    """
    expected_set = set(expected_names)
    result: list[ParsedArtifact] = []
    seen: set[str] = set()

    current_name: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_name is not None and current_name in expected_set and current_name not in seen:
            content = "\n".join(current_lines).strip()
            result.append(ParsedArtifact(name=current_name, content=content))
            seen.add(current_name)

    for line in response.splitlines():
        match = _DELIMITER_PATTERN.match(line)
        if match:
            _flush()
            candidate = match.group(1)
            if candidate in expected_set:
                current_name = candidate
                current_lines = []
            else:
                current_name = None
                current_lines = []
        else:
            if current_name is not None:
                current_lines.append(line)

    _flush()

    if not result:
        available = _find_any_delimiters(response)
        if available:
            raise ArtifactParseError(
                f"No expected artifact delimiters found in LLM response. "
                f"Expected: {sorted(expected_names)}. "
                f"Found delimiters: {sorted(available)}."
            )
        raise ArtifactParseError(
            f"No artifact delimiters found in LLM response. "
            f"Expected format: '--- <artifact_name> ---'. "
            f"Expected artifacts: {sorted(expected_names)}."
        )

    return result


def _find_any_delimiters(response: str) -> list[str]:
    """Extract all delimiter names found, for diagnostic purposes."""
    found: list[str] = []
    for line in response.splitlines():
        match = _DELIMITER_PATTERN.match(line)
        if match:
            found.append(match.group(1))
    return found
