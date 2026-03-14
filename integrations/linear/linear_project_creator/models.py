"""
Pure value objects for the Linear project hierarchy.

No behaviour. No defaults. No mutable state.
All objects are frozen — mutation after construction is a programmer error.

Field semantics:
  - Optional fields (str | None, int | None, etc.) are None when absent in the YAML.
  - tuple[] is used instead of list[] to preserve immutability across the dataclass graph.
  - priority: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low  (Linear standard)
  - Labels are stored as names; resolution to IDs happens in project_builder.py.
  - Dates are stored as ISO-8601 strings (YYYY-MM-DD); validation is the API's responsibility.

Quality contract:
  - EpicModel.acceptance_criteria is required; the parser rejects epics without it.
  - EpicModel.blocks: optional; names of epics that cannot start until this epic is
    complete. Resolved to Linear issue relations by project_builder.py.
  - StoryModel.effort and StoryModel.complexity are required bounded integers (1-5).
  - StoryModel.estimate is always derived as effort + complexity (range 2-10); explicit
    overrides in YAML that conflict with the computed value are rejected by the parser.
  - StoryModel.design_freedom: required; declares agent latitude for solution design.
    Allowed values: "high" | "restricted". Linted by STORY_DESIGN_FREEDOM_REQUIRED.
  - TaskModel.done_criteria: optional but linted; describes the verifiable outcome of
    the task (output artifact, test result, or observable state).
  - TaskModel.task_type: optional; semantic classification of the task role in the
    DevOS pipeline. Allowed values: "implementation" | "verification". When set to
    "verification", satisfies STORY_MISSING_TEST_TASK without keyword matching.
    Applied as an additional label in Linear so agents can filter by task role.
  - StoryModel.blocks: optional; names of stories that cannot start until this story is
    complete. Resolved to Linear issue relations by project_builder.py.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Shared sub-objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinkModel:
    """A URL attachment that will be added to an issue."""
    url: str
    title: str


@dataclass(frozen=True)
class LabelDefinitionModel:
    """
    Declarative label metadata used when creating missing labels in Linear.
    """
    name: str
    description: str
    color: str | None
    is_group: bool


# ---------------------------------------------------------------------------
# Project-level
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MilestoneModel:
    """A project milestone (Linear: ProjectMilestone)."""
    name: str
    description: str
    target_date: str | None


@dataclass(frozen=True)
class ProjectModel:
    """Top-level Linear project."""
    name: str
    description: str
    summary: str | None          # Short summary ≤255 chars shown in project list
    icon: str | None             # Emoji slug, e.g. ":rocket:"
    color: str | None            # Hex colour, e.g. "#4F46E5"
    priority: int | None         # 0–4
    state: str | None            # "planned" | "started" | "paused" | "completed" | "cancelled"
    start_date: str | None       # ISO-8601 date string
    target_date: str | None      # ISO-8601 date string
    lead: str | None             # User name, email, or Linear ID
    labels: tuple[str, ...]      # Label names
    issue_label_definitions: tuple[LabelDefinitionModel, ...]
    project_label_definitions: tuple[LabelDefinitionModel, ...]
    milestones: tuple[MilestoneModel, ...]
    epics: tuple[EpicModel, ...]


# ---------------------------------------------------------------------------
# Issue hierarchy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskModel:
    """
    Leaf-level issue: Task or Bug directly under a Story.

    type: "task" | "bug" | "improvement" | "chore"
          Passed as a label to Linear (Linear has no native type field in standard API).
    task_type: Optional. Semantic role of this task in the DevOS pipeline.
               Allowed values: "implementation" | "verification".
               "implementation" — produces a code artifact or system change.
               "verification"   — produces test evidence; satisfies STORY_MISSING_TEST_TASK
                                  without relying on keyword matching in the task name.
               Applied as an additional label in Linear for agent-side filtering.
               Validated by TASK_TYPE_VALID when present.
    done_criteria: Optional. Describes the verifiable outcome that defines task completion
                   (output artifact, test result, or observable system state). Linted by
                   TASK_MISSING_DOD when absent.
    """
    name: str
    type: str                    # issue type → applied as label
    task_type: str | None        # "implementation" | "verification" — DevOS pipeline role
    description: str
    priority: int | None         # 0–4
    labels: tuple[str, ...]      # Additional labels beyond the type label
    estimate: float | None       # Story points / complexity
    due_date: str | None         # ISO-8601
    assignee: str | None         # User name, email, or Linear ID
    state: str | None            # Workflow state name, e.g. "Todo", "In Progress"
    links: tuple[LinkModel, ...]
    done_criteria: str | None    # Explicit definition of done for this task


@dataclass(frozen=True)
class StoryModel:
    """
    Mid-level issue under an Epic.

    type: "story" | "bug" | "feature"
    effort: Required. Integer 1-5. See EFFORT SCALE in template.yaml.
    complexity: Required. Integer 1-5. See COMPLEXITY SCALE in template.yaml.
    estimate: Derived as effort + complexity (2-10). Never set manually.
    acceptance_criteria: Optional Markdown block appended to the description body.

    DevOS planning fields (all optional):
      problem_statement:    Clear problem being solved. Input to PLANNING stage.
      scope:                What is included in the story. Bounds the plan.
      constraints:          Technical/architectural constraints. Enforced at ARCH_CHECK.
      architecture_context: Affected modules/contracts. Used at ARCH_CHECK.
      non_goals:            Explicit exclusions. Prevents scope creep in planning output.
      design_freedom:       "high" | "restricted". Agent latitude for solution design.
    """
    name: str
    type: str
    description: str
    effort: int                  # 1-5, required
    complexity: int              # 1-5, required
    priority: int | None
    labels: tuple[str, ...]
    estimate: float | None       # Always computed as effort + complexity
    due_date: str | None
    assignee: str | None
    milestone: str | None        # Milestone name (resolved to ID at build time)
    state: str | None
    acceptance_criteria: str | None
    links: tuple[LinkModel, ...]
    tasks: tuple[TaskModel, ...]
    # DevOS planning fields
    problem_statement: str | None
    scope: str | None
    constraints: str | None
    architecture_context: str | None
    non_goals: str | None
    design_freedom: str | None   # "high" | "restricted"
    # Dependency modeling
    blocks: tuple[str, ...]      # Names of stories that cannot start until this story is done


@dataclass(frozen=True)
class EpicModel:
    """
    Top-level feature container issue.

    type: "epic" | "feature"  (always applied as a label)
    acceptance_criteria: Required. Markdown block with verifiable done conditions.
    blocks: Optional. Names of epics that cannot start until this epic is complete.
            Resolved to Linear 'blocks' issue relations by project_builder.py.
            Cross-epic dependency sequencing must be declared here; it is not inferred.
    """
    name: str
    description: str
    acceptance_criteria: str     # Required; rendered under '## Acceptance Criteria' heading
    priority: int | None
    labels: tuple[str, ...]
    due_date: str | None
    assignee: str | None
    milestone: str | None
    state: str | None
    links: tuple[LinkModel, ...]
    stories: tuple[StoryModel, ...]
    blocks: tuple[str, ...]      # Names of epics that cannot start until this epic is done
