"""
HTTP client for the Linear GraphQL API.

Responsibilities:
  - Execute GraphQL queries and mutations.
  - Authenticate every request with the API key from Config.
  - Raise LinearAPIError on HTTP errors, GraphQL-level errors, and unexpected payloads.
  - Retry transient failures (HTTP 429, 5xx) with exponential backoff.
  - Honour the X-RateLimit-Remaining header; pause proactively when budget is low.
  - Resolve human-readable names (labels, users, states) to Linear UUIDs, with in-memory caching.

Design decisions:
  - All public methods return scalar IDs (str). Raw dicts never escape this module.
  - MAX_RETRIES=3 with base_delay=1s → delays of 1s, 2s, 4s before giving up.
  - Rate-limit threshold is 5 remaining requests; sleep is READ from Retry-After header
    when present, otherwise DEFAULT_RATE_LIMIT_SLEEP_S.
  - Name→ID resolution is cached per client instance; no re-fetches within a single run.
  - Missing labels can be auto-created deterministically before issue/project creation.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import requests

try:
    from .config import Config
except ImportError:  # pragma: no cover - script execution fallback
    from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
BASE_RETRY_DELAY_S = 1.0
RATE_LIMIT_THRESHOLD = 5
DEFAULT_RATE_LIMIT_SLEEP_S = 60.0


# ---------------------------------------------------------------------------
# GraphQL operation strings
# ---------------------------------------------------------------------------

_PROJECT_CREATE = """
mutation ProjectCreate($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    success
    project { id name }
  }
}
"""

_ISSUE_CREATE = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id title }
  }
}
"""

_MILESTONE_CREATE = """
mutation ProjectMilestoneCreate($input: ProjectMilestoneCreateInput!) {
  projectMilestoneCreate(input: $input) {
    success
    projectMilestone { id name }
  }
}
"""

_QUERY_LABELS = """
query TeamLabels($teamId: String!) {
  team(id: $teamId) {
    labels(first: 250) {
      nodes { id name }
    }
  }
}
"""

_QUERY_STATES = """
query TeamStates($teamId: String!) {
  workflowStates(filter: { team: { id: { eq: $teamId } } }, first: 250) {
    nodes { id name type }
  }
}
"""

_QUERY_USERS = """
query Users {
  users(first: 250) {
    nodes { id name email }
  }
}
"""

_QUERY_PROJECT_LABELS = """
query ProjectLabels {
  projectLabels(first: 250) {
    nodes { id name }
  }
}
"""

_QUERY_PROJECT_STATUSES = """
query ProjectStatuses {
  projectStatuses(first: 250) {
    nodes { id name }
  }
}
"""

_ISSUE_LABEL_CREATE = """
mutation IssueLabelCreate($input: IssueLabelCreateInput!) {
  issueLabelCreate(input: $input) {
    success
    issueLabel { id name }
  }
}
"""

_PROJECT_LABEL_CREATE = """
mutation ProjectLabelCreate($input: ProjectLabelCreateInput!) {
  projectLabelCreate(input: $input) {
    success
    projectLabel { id name }
  }
}
"""

_ISSUE_RELATION_CREATE = """
mutation IssueRelationCreate($input: IssueRelationCreateInput!) {
  issueRelationCreate(input: $input) {
    success
    issueRelation { id }
  }
}
"""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LinearAPIError(Exception):
    """Raised when the Linear API returns an error or an unexpected payload."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LinearClient:
    """
    Thin GraphQL client for the Linear API.

    Args:
        config: Loaded Config containing api_key, team_id, and api_url.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": config.api_key,
                "Content-Type": "application/json",
            }
        )
        # Lazy-loaded lookup caches — populated on first use.
        self._issue_label_cache: dict[str, str] | None = None   # name.lower() → id
        self._project_label_cache: dict[str, str] | None = None  # name.lower() → id
        self._project_status_cache: dict[str, str] | None = None  # name.lower() → id
        self._state_cache: dict[str, str] | None = None   # name.lower() → id
        self._user_cache: dict[str, str] | None = None    # name/email.lower() → id
        self._unknown_labels_warned: set[str] = set()

    # ------------------------------------------------------------------
    # Public creation interface
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        description: str,
        *,
        summary: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        priority: int | None = None,
        state: str | None = None,
        start_date: str | None = None,
        target_date: str | None = None,
        lead: str | None = None,
        label_ids: list[str] | None = None,
    ) -> str:
        """
        Create a Linear project.

        Returns:
            The newly created project's Linear ID.
        """
        input_payload: dict[str, Any] = {
            "name": name,
            "description": _project_summary(summary, max_len=255),
            "content": description,
            "teamIds": [self._config.team_id],
        }
        _set_if_not_none(input_payload, "icon", icon)
        _set_if_not_none(input_payload, "color", color)
        _set_if_not_none(input_payload, "priority", priority)
        if state is not None:
            status_id = self.resolve_project_status_id(state)
            if status_id is None:
                logger.warning(
                    "Project state '%s' not found in project statuses; creating project "
                    "without explicit status.",
                    state,
                )
            else:
                input_payload["statusId"] = status_id
        _set_if_not_none(input_payload, "startDate", start_date)
        _set_if_not_none(input_payload, "targetDate", target_date)
        if lead is not None:
            lead_id = self._resolve_user(lead)
            _set_if_not_none(input_payload, "leadId", lead_id)
        if label_ids:
            input_payload["labelIds"] = label_ids

        logger.debug("Creating project: %s", name)
        data = self.run_query(_PROJECT_CREATE, {"input": input_payload})

        result = data.get("projectCreate", {})
        if not result.get("success"):
            raise LinearAPIError(f"projectCreate returned success=false for '{name}'.")

        project_id: str | None = result.get("project", {}).get("id")
        if not project_id:
            raise LinearAPIError(
                f"projectCreate succeeded but returned no project.id for '{name}'."
            )

        logger.info("Created project '%s' → %s", name, project_id)
        return project_id

    def create_milestone(
        self,
        name: str,
        project_id: str,
        description: str = "",
        target_date: str | None = None,
    ) -> str:
        """
        Create a project milestone.

        Returns:
            The newly created milestone's Linear ID.
        """
        input_payload: dict[str, Any] = {
            "name": name,
            "projectId": project_id,
        }
        if description:
            input_payload["description"] = description
        _set_if_not_none(input_payload, "targetDate", target_date)

        logger.debug("Creating milestone: %s", name)
        data = self.run_query(_MILESTONE_CREATE, {"input": input_payload})

        result = data.get("projectMilestoneCreate", {})
        if not result.get("success"):
            raise LinearAPIError(f"projectMilestoneCreate returned success=false for '{name}'.")

        milestone_id: str | None = result.get("projectMilestone", {}).get("id")
        if not milestone_id:
            raise LinearAPIError(
                f"projectMilestoneCreate succeeded but returned no id for '{name}'."
            )

        logger.info("Created milestone '%s' → %s", name, milestone_id)
        return milestone_id

    def create_issue(
        self,
        title: str,
        description: str,
        project_id: str,
        parent_id: str | None = None,
        *,
        priority: int | None = None,
        label_ids: list[str] | None = None,
        estimate: float | None = None,
        due_date: str | None = None,
        assignee_id: str | None = None,
        state_id: str | None = None,
        milestone_id: str | None = None,
        links: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Create a Linear issue (epic, story, task, or bug).

        Returns:
            The newly created issue's Linear ID.
        """
        input_payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "teamId": self._config.team_id,
            "projectId": project_id,
        }
        _set_if_not_none(input_payload, "parentId", parent_id)
        _set_if_not_none(input_payload, "priority", priority)
        _set_if_not_none(input_payload, "estimate", estimate)
        _set_if_not_none(input_payload, "dueDate", due_date)
        _set_if_not_none(input_payload, "assigneeId", assignee_id)
        _set_if_not_none(input_payload, "stateId", state_id)
        _set_if_not_none(input_payload, "projectMilestoneId", milestone_id)
        if label_ids:
            input_payload["labelIds"] = label_ids

        logger.debug("Creating issue: '%s' (parent=%s)", title, parent_id or "none")
        data = self.run_query(_ISSUE_CREATE, {"input": input_payload})

        result = data.get("issueCreate", {})
        if not result.get("success"):
            raise LinearAPIError(f"issueCreate returned success=false for '{title}'.")

        issue_id: str | None = result.get("issue", {}).get("id")
        if not issue_id:
            raise LinearAPIError(
                f"issueCreate succeeded but returned no issue.id for '{title}'."
            )

        logger.info("Created issue '%s' → %s", title, issue_id)

        # Add link attachments after creation (separate API calls).
        if links:
            for link in links:
                self._create_attachment(issue_id, link["url"], link.get("title", link["url"]))

        return issue_id

    # ------------------------------------------------------------------
    # Name → ID resolution (with caching)
    # ------------------------------------------------------------------

    def resolve_issue_label_ids(
        self,
        names: list[str],
        *,
        create_missing: bool = False,
        label_meta: dict[str, dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Resolve issue label names to IDs; optionally create missing labels.
        """
        if not names:
            return []
        cache = self._get_issue_label_cache()
        resolved: list[str] = []
        for name in names:
            key = name.lower()
            label_id = cache.get(key)
            if label_id:
                resolved.append(label_id)
            else:
                if create_missing:
                    meta = (label_meta or {}).get(key, {})
                    created_id = self.create_issue_label(
                        name=name,
                        description=str(
                            meta.get("description") or f"Auto-created issue label: {name}"
                        ),
                        color=meta.get("color"),
                        is_group=bool(meta.get("is_group", False)),
                    )
                    cache[key] = created_id
                    resolved.append(created_id)
                elif key not in self._unknown_labels_warned:
                    logger.warning("Issue label '%s' not found; skipping it.", name)
                    self._unknown_labels_warned.add(key)
        return resolved

    def resolve_project_label_ids(
        self,
        names: list[str],
        *,
        create_missing: bool = False,
        label_meta: dict[str, dict[str, Any]] | None = None,
    ) -> list[str]:
        """Resolve project label names to IDs; optionally create missing labels."""
        if not names:
            return []
        cache = self._get_project_label_cache()
        resolved: list[str] = []
        for name in names:
            key = name.lower()
            label_id = cache.get(key)
            if label_id:
                resolved.append(label_id)
            else:
                if create_missing:
                    meta = (label_meta or {}).get(key, {})
                    created_id = self.create_project_label(
                        name=name,
                        description=str(
                            meta.get("description") or f"Auto-created project label: {name}"
                        ),
                        color=meta.get("color"),
                        is_group=bool(meta.get("is_group", False)),
                    )
                    cache[key] = created_id
                    resolved.append(created_id)
                elif key not in self._unknown_labels_warned:
                    logger.warning("Project label '%s' not found; skipping it.", name)
                    self._unknown_labels_warned.add(key)
        return resolved

    def resolve_state_id(self, name: str) -> str | None:
        """Resolve a workflow state name to its Linear ID."""
        return self._get_state_cache().get(name.lower())

    def resolve_user_id(self, name_or_email: str) -> str | None:
        """Resolve a user name or email to their Linear ID."""
        return self._get_user_cache().get(name_or_email.lower())

    def resolve_project_status_id(self, status_name: str) -> str | None:
        """Resolve a project status name to its Linear status ID."""
        return self._get_project_status_cache().get(status_name.lower())

    def create_issue_label(
        self,
        *,
        name: str,
        description: str,
        color: str | None = None,
        is_group: bool = False,
    ) -> str:
        """Create an issue label and return its ID."""
        input_payload: dict[str, Any] = {
            "name": name,
            "description": description,
            "teamId": self._config.team_id,
            "isGroup": is_group,
            "color": color or _default_label_color(name),
        }
        data = self.run_query(_ISSUE_LABEL_CREATE, {"input": input_payload})
        result = data.get("issueLabelCreate", {})
        if not result.get("success"):
            raise LinearAPIError(f"issueLabelCreate returned success=false for '{name}'.")
        label_id: str | None = result.get("issueLabel", {}).get("id")
        if not label_id:
            raise LinearAPIError(
                f"issueLabelCreate succeeded but returned no id for '{name}'."
            )
        logger.info("Created missing issue label '%s' → %s", name, label_id)
        return label_id

    def create_project_label(
        self,
        *,
        name: str,
        description: str,
        color: str | None = None,
        is_group: bool = False,
    ) -> str:
        """Create a project label and return its ID."""
        input_payload: dict[str, Any] = {
            "name": name,
            "description": description,
            "isGroup": is_group,
            "color": color or _default_label_color(name),
        }
        data = self.run_query(_PROJECT_LABEL_CREATE, {"input": input_payload})
        result = data.get("projectLabelCreate", {})
        if not result.get("success"):
            raise LinearAPIError(f"projectLabelCreate returned success=false for '{name}'.")
        label_id: str | None = result.get("projectLabel", {}).get("id")
        if not label_id:
            raise LinearAPIError(
                f"projectLabelCreate succeeded but returned no id for '{name}'."
            )
        logger.info("Created missing project label '%s' → %s", name, label_id)
        return label_id

    def create_issue_relation(
        self,
        issue_id: str,
        related_issue_id: str,
        relation_type: str = "blocks",
    ) -> None:
        """
        Create a directional relation between two issues (best-effort).

        relation_type: "blocks" means issue_id blocks related_issue_id —
                       i.e. related_issue_id cannot start until issue_id is done.

        Errors are logged as warnings and not re-raised; relation creation is
        non-critical and must not interrupt the main build.
        """
        input_payload: dict[str, Any] = {
            "issueId": issue_id,
            "relatedIssueId": related_issue_id,
            "type": relation_type,
        }
        try:
            data = self.run_query(_ISSUE_RELATION_CREATE, {"input": input_payload})
            result = data.get("issueRelationCreate", {})
            if not result.get("success"):
                logger.warning(
                    "issueRelationCreate returned success=false for %s → %s (%s).",
                    issue_id, related_issue_id, relation_type,
                )
            else:
                logger.info(
                    "Created relation %s blocks %s.", issue_id, related_issue_id
                )
        except LinearAPIError as exc:
            logger.warning(
                "Could not create relation %s → %s (%s): %s",
                issue_id, related_issue_id, relation_type, exc,
            )

    # ------------------------------------------------------------------
    # Core HTTP / GraphQL execution
    # ------------------------------------------------------------------

    def run_query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a GraphQL operation with retry and rate-limit handling.

        Returns:
            The 'data' field of the GraphQL response.

        Raises:
            LinearAPIError: On HTTP errors, GraphQL errors, or unexpected payloads.
        """
        payload = {"query": query, "variables": variables}
        last_exception: LinearAPIError | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.post(
                    self._config.api_url, json=payload, timeout=30
                )
            except requests.RequestException as exc:
                raise LinearAPIError(
                    f"Network error contacting Linear API: {exc}"
                ) from exc

            self._check_rate_limit(response)

            if response.status_code == 429:
                delay = self._retry_after(response, DEFAULT_RATE_LIMIT_SLEEP_S)
                logger.warning(
                    "Rate-limited (HTTP 429). Sleeping %.1fs before retry %d/%d.",
                    delay, attempt, MAX_RETRIES,
                )
                time.sleep(delay)
                last_exception = LinearAPIError("Rate limited (HTTP 429).", status_code=429)
                continue

            if response.status_code >= 500:
                delay = BASE_RETRY_DELAY_S * (2 ** (attempt - 1))
                logger.warning(
                    "Server error (HTTP %d). Sleeping %.1fs before retry %d/%d.",
                    response.status_code, delay, attempt, MAX_RETRIES,
                )
                time.sleep(delay)
                last_exception = LinearAPIError(
                    f"Server error (HTTP {response.status_code}).",
                    status_code=response.status_code,
                )
                continue

            if response.status_code != 200:
                raise LinearAPIError(
                    f"Unexpected HTTP status {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                )

            try:
                body: dict[str, Any] = response.json()
            except ValueError as exc:
                raise LinearAPIError(
                    f"Response body is not valid JSON: {response.text[:500]}"
                ) from exc

            if "errors" in body:
                messages = "; ".join(
                    e.get("message", str(e)) for e in body["errors"]
                )
                raise LinearAPIError(f"GraphQL error(s): {messages}")

            if "data" not in body:
                raise LinearAPIError(
                    f"GraphQL response missing 'data' field: {body}"
                )

            return body["data"]

        raise last_exception or LinearAPIError("All retries exhausted.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_user(self, name_or_email: str) -> str | None:
        resolved = self.resolve_user_id(name_or_email)
        if resolved is None:
            logger.warning(
                "User '%s' not found — lead will not be set.", name_or_email
            )
        return resolved

    def _create_attachment(self, issue_id: str, url: str, title: str) -> None:
        """Add a URL attachment to an issue (best-effort; errors are logged, not raised)."""
        mutation = """
        mutation AttachmentCreate($input: AttachmentCreateInput!) {
          attachmentCreate(input: $input) {
            success
            attachment { id }
          }
        }
        """
        try:
            self.run_query(mutation, {
                "input": {"issueId": issue_id, "url": url, "title": title}
            })
            logger.debug("Added attachment '%s' to issue %s", title, issue_id)
        except LinearAPIError as exc:
            logger.warning("Could not add attachment '%s' to %s: %s", url, issue_id, exc)

    def _get_issue_label_cache(self) -> dict[str, str]:
        if self._issue_label_cache is None:
            self._issue_label_cache = self._fetch_issue_labels()
        return self._issue_label_cache

    def _get_project_label_cache(self) -> dict[str, str]:
        if self._project_label_cache is None:
            self._project_label_cache = self._fetch_project_labels()
        return self._project_label_cache

    def _get_project_status_cache(self) -> dict[str, str]:
        if self._project_status_cache is None:
            self._project_status_cache = self._fetch_project_statuses()
        return self._project_status_cache

    def _get_state_cache(self) -> dict[str, str]:
        if self._state_cache is None:
            self._state_cache = self._fetch_states()
        return self._state_cache

    def _get_user_cache(self) -> dict[str, str]:
        if self._user_cache is None:
            self._user_cache = self._fetch_users()
        return self._user_cache

    def _fetch_issue_labels(self) -> dict[str, str]:
        try:
            data = self.run_query(_QUERY_LABELS, {"teamId": self._config.team_id})
            nodes = data.get("team", {}).get("labels", {}).get("nodes", [])
            result = {n["name"].lower(): n["id"] for n in nodes}
            logger.debug("Loaded %d issue labels from Linear team.", len(result))
            return result
        except LinearAPIError as exc:
            logger.warning(
                "Could not fetch issue labels: %s — issue label resolution disabled.",
                exc,
            )
            return {}

    def _fetch_project_labels(self) -> dict[str, str]:
        try:
            data = self.run_query(_QUERY_PROJECT_LABELS, {})
            nodes = data.get("projectLabels", {}).get("nodes", [])
            result = {n["name"].lower(): n["id"] for n in nodes}
            logger.debug("Loaded %d project labels from Linear workspace.", len(result))
            return result
        except LinearAPIError as exc:
            logger.warning(
                "Could not fetch project labels: %s — project label resolution disabled.",
                exc,
            )
            return {}

    def _fetch_project_statuses(self) -> dict[str, str]:
        try:
            data = self.run_query(_QUERY_PROJECT_STATUSES, {})
            nodes = data.get("projectStatuses", {}).get("nodes", [])
            result = {n["name"].lower(): n["id"] for n in nodes}
            logger.debug("Loaded %d project statuses from Linear workspace.", len(result))
            return result
        except LinearAPIError as exc:
            logger.warning(
                "Could not fetch project statuses: %s — status resolution disabled.",
                exc,
            )
            return {}

    def _fetch_states(self) -> dict[str, str]:
        try:
            data = self.run_query(_QUERY_STATES, {"teamId": self._config.team_id})
            nodes = data.get("workflowStates", {}).get("nodes", [])
            result = {n["name"].lower(): n["id"] for n in nodes}
            logger.debug("Loaded %d workflow states from Linear.", len(result))
            return result
        except LinearAPIError as exc:
            logger.warning("Could not fetch states: %s — state resolution disabled.", exc)
            return {}

    def _fetch_users(self) -> dict[str, str]:
        try:
            data = self.run_query(_QUERY_USERS, {})
            nodes = data.get("users", {}).get("nodes", [])
            result: dict[str, str] = {}
            for n in nodes:
                result[n["name"].lower()] = n["id"]
                result[n["email"].lower()] = n["id"]
            logger.debug("Loaded %d users from Linear.", len(nodes))
            return result
        except LinearAPIError as exc:
            logger.warning("Could not fetch users: %s — user resolution disabled.", exc)
            return {}

    def _check_rate_limit(self, response: requests.Response) -> None:
        remaining_header = response.headers.get("X-RateLimit-Remaining")
        if remaining_header is None:
            return
        try:
            remaining = int(remaining_header)
        except ValueError:
            return
        if remaining <= RATE_LIMIT_THRESHOLD:
            sleep_s = self._retry_after(response, DEFAULT_RATE_LIMIT_SLEEP_S)
            logger.warning(
                "Rate-limit budget low (%d remaining). Sleeping %.1fs.", remaining, sleep_s
            )
            time.sleep(sleep_s)

    @staticmethod
    def _retry_after(response: requests.Response, default: float) -> float:
        header = response.headers.get("Retry-After")
        if header is None:
            return default
        try:
            return float(header)
        except ValueError:
            return default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_if_not_none(d: dict[str, Any], key: str, value: Any) -> None:
    """Add *key*=*value* to *d* only when *value* is not None."""
    if value is not None:
        d[key] = value


def _default_label_color(name: str) -> str:
    """
    Return a deterministic hex color for a label name.
    """
    palette = (
        "#4F46E5",
        "#0EA5E9",
        "#10B981",
        "#F59E0B",
        "#EF4444",
        "#8B5CF6",
        "#14B8A6",
        "#F97316",
        "#22C55E",
        "#EC4899",
    )
    digest = hashlib.sha256(name.lower().encode("utf-8")).digest()
    return palette[digest[0] % len(palette)]


def _project_summary(summary: str | None, max_len: int) -> str:
    """
    Build the short project summary for ProjectCreateInput.description.

    Rule:
      1) Use summary when present.
      2) If absent, return empty string (no implicit fallback).
      3) Enforce max_len with explicit truncation.
    """
    candidate = summary.strip() if summary and summary.strip() else ""

    if len(candidate) > max_len:
        logger.warning(
            "Project summary exceeds %d chars; truncating deterministically.",
            max_len,
        )
        return candidate[:max_len]
    return candidate
