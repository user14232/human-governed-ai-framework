# contracts/

Normative framework specifications. These documents bind runtime implementations, agent roles,
artifact schemas, and project configurations.

## For runtime implementers — start here

| Document | Purpose |
| --- | --- |
| [`runtime_contract.md`](./runtime_contract.md) | **Primary runtime spec** — run identity, artifact layout, gate checks, rework, events |
| [`system_invariants.md`](./system_invariants.md) | Non-negotiable invariants that no agent, workflow, or human may override |
| [`framework_validation_contract.md`](./framework_validation_contract.md) | 35 self-consistency criteria; basis for the readiness assessment |

## For project owners — start here

| Document | Purpose |
| --- | --- |
| [`domain_input_contracts.md`](./domain_input_contracts.md) | Mandatory project inputs the workflow requires |
| [`capabilities.yaml`](./capabilities.yaml) | Capability interface definitions projects may implement |
| [`capability_integration_contract.md`](./capability_integration_contract.md) | How capabilities integrate into the workflow |

## Framework evolution

| Document | Purpose |
| --- | --- |
| [`framework_versioning_policy.md`](./framework_versioning_policy.md) | Version scheme, breaking vs compatible changes |
| [`migration_contract.md`](./migration_contract.md) | Major version migration process |
| [`artifact_status_model.md`](./artifact_status_model.md) | Optional lifecycle vocabulary for versioned artifacts |
