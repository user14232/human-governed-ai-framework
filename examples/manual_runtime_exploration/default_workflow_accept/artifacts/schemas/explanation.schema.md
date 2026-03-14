# Schema: `explanation.md` (v1)

## Schema metadata

- **schema_id**: `explanation`
- **version**: `v1`
- **artifact_name**: `explanation.md`

## Responsibility

Record a human-readable explanation of domain rules, glossary terms, or source policy
produced by the `domain_explanation` capability. All statements must be traceable to
the provided domain inputs; no new domain facts may be created.

## Owner roles

- Project-provided `domain_explanation` capability agent

## Allowed readers

- `human`
- `agent_planner`
- `agent_test_designer`
- `agent_reviewer`

## Write policy

- **Mutability**: versioned (one explanation per question/invocation)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version (null if first explanation for this question)

## Required sections (MUST appear in this order)

### 1) Question

- Exact question or topic that was explained.

### 2) Domain inputs consulted

- `domain_rules.md` (version/ref, if applicable)
- `glossary.md` (version/ref, if applicable)
- `source_policy.md` (version/ref, if applicable)

### 3) Explanation

- Human-readable explanation.
- Each statement that derives from a domain input must include an inline reference in the form
  `[rule_id_or_section]` or `(glossary: term)`.

### 4) Limitations

- Explicitly state any aspects of the question that could not be answered from the provided inputs.
- Do not speculate beyond what is stated in the domain inputs.

## Determinism requirements

- Every factual claim must be traceable to a cited section or term in the consulted inputs.
- Must not create new domain facts, new rules, or new glossary terms.
