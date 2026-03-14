# STORY QUALITY CHECKLIST

A Story is considered DevOS-ready only if all checks pass.

## Problem Statement

□ Clearly describes the system problem
□ Explains why the problem matters
□ Does not propose a solution

## Scope

□ Defines the capability being implemented
□ Does not include unrelated changes
□ Avoids implementation details

## Constraints

□ Architectural constraints defined
□ Performance or compatibility rules defined if relevant

## Architecture Context

□ Affected modules identified
□ Layer boundaries respected

## Non-Goals

□ Explicitly defines what is excluded
□ Prevents scope creep

## Design Freedom

□ Field is present and non-empty (required by STORY_DESIGN_FREEDOM_REQUIRED)
□ Value is exactly "high" or "restricted" (required by STORY_DESIGN_FREEDOM)
□ Value matches the nature of the problem

## Acceptance Criteria

□ Uses "- [ ]" checkbox format for every criterion (required by STORY_AC_CHECKBOX_FORMAT)
□ Each criterion describes an observable, independently verifiable outcome
□ Criteria are testable without ambiguity

## Granularity

□ Story represents one capability
□ Story fits within one iteration

## Vertical Slice

□ Story delivers a testable, end-to-end verifiable increment — not just a
  horizontal layer (types only, interface only, etc.)
□ When the story is done, there is an observable result that can be verified
  in isolation (e.g. a passing test, a working module, an observable state)
□ If the story only enables other stories without producing an observable
  result of its own, consider restructuring it or merging it with a dependent

## Dependency Declaration

□ If this story has hard dependencies on other stories, the blocking stories
  declare those dependencies via their `blocks` field
□ `blocks` references exact story names as they appear in the YAML file
□ No `blocks` entries are added for soft ordering preferences (only hard dependencies)
