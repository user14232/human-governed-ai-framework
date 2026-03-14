from __future__ import annotations

import dataclasses
import unittest
from pathlib import Path

from runtime.types.artifact import ArtifactRef, ArtifactSchema
from runtime.types.gate import CheckResult, CheckType, GateCheckDetail
from runtime.types.run import RunState
from runtime.types.workflow import RequiresBlock, Transition, WorkflowDefinition


class RuntimeTypesTest(unittest.TestCase):
    def test_dataclasses_are_frozen(self) -> None:
        run_state = RunState(
            run_id="RUN-20260314-0001",
            current_state="INIT",
            is_terminal=False,
            last_event_id=None,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            run_state.current_state = "PLANNING"  # type: ignore[misc]

    def test_basic_composition(self) -> None:
        wf = WorkflowDefinition(
            workflow_id="default_workflow",
            version="v1",
            states=("INIT", "PLANNING"),
            transitions=(
                Transition(
                    from_state="INIT",
                    to_state="PLANNING",
                    requires=RequiresBlock(
                        inputs_present=True,
                        artifacts=(),
                        human_approval=(),
                        conditions={},
                    ),
                    notes=None,
                ),
            ),
            artifacts_used=("change_intent.yaml",),
        )
        detail = GateCheckDetail(
            check_type=CheckType.INPUT_PRESENCE,
            subject="change_intent.yaml",
            result=CheckResult.PASS,
            detail=None,
        )
        schema = ArtifactSchema(
            artifact_type="implementation_plan",
            file_format="yaml",
            required_fields=("id",),
            required_sections=(),
            allowed_outcomes=None,
            owner_roles=("agent_planner",),
        )
        ref = ArtifactRef(name="implementation_plan.yaml", artifact_id="IP-1", artifact_hash="abc")

        self.assertEqual(wf.workflow_id, "default_workflow")
        self.assertEqual(detail.result, CheckResult.PASS)
        self.assertEqual(schema.file_format, "yaml")
        self.assertEqual(Path(ref.name).suffix, ".yaml")


if __name__ == "__main__":
    unittest.main()

