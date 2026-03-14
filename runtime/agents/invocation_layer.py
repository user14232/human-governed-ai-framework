from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Protocol

from runtime.events import metrics_writer
from runtime.events.event_system import EventSystem
from runtime.artifacts.artifact_system import ArtifactSystem
from runtime.framework.agent_loader import AgentContract
from runtime.store.run_store import run_metrics_path
from runtime.types.artifact import ArtifactRef, ArtifactSchema
from runtime.types.event import EventType
from runtime.types.run import RunContext


class InvocationError(RuntimeError):
    """Base class for invocation layer errors."""


class UnknownAgentRoleError(InvocationError):
    """Raised when no agent contract exists for the requested role."""


class MissingAdapterError(InvocationError):
    """Raised when AUTOMATED mode is selected without an adapter."""


class MissingInputArtifactError(InvocationError):
    """Raised when a declared input artifact file is missing."""


class MissingOutputArtifactError(InvocationError):
    """Raised when a declared output artifact file is missing."""


class UnexpectedAdapterOutputError(InvocationError):
    """Raised when adapter output mapping violates contract outputs."""


class SingleShotViolationError(InvocationError):
    """Raised when a role is re-invoked in the same state without rework."""


class InvocationMode(str, Enum):
    HUMAN_AS_AGENT = "human_as_agent"
    AUTOMATED = "automated"


class InvocationOutcome(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class InvocationResult:
    agent_role: str
    outcome: InvocationOutcome
    output_refs: tuple[ArtifactRef, ...]
    duration_seconds: float
    invocation_record: dict


class AgentAdapter(Protocol):
    def invoke(self, input_paths: dict[str, Path], output_dir: Path) -> dict[str, Path]:
        """
        Execute one single-shot agent invocation.

        Returns mapping output artifact name -> output path.
        """


class AgentInvocationLayer:
    def __init__(
        self,
        artifact_system: ArtifactSystem | None = None,
        event_system: EventSystem | None = None,
    ) -> None:
        self._artifact_system = artifact_system or ArtifactSystem()
        self._events = event_system or EventSystem()

    def invoke(
        self,
        ctx: RunContext,
        agent_role: str,
        agent_contracts: dict[str, AgentContract],
        schemas: dict[str, ArtifactSchema],
        mode: InvocationMode,
        adapter: AgentAdapter | None = None,
    ) -> InvocationResult:
        contract = agent_contracts.get(agent_role)
        if contract is None:
            raise UnknownAgentRoleError(f"No contract found for agent role '{agent_role}'.")

        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        metrics_path = run_metrics_path(ctx.run_dir)
        last_event_id = self._events.last_event_id(metrics_path)

        self.check_single_shot(
            ctx=ctx,
            agent_role=agent_role,
            workflow_state=ctx.current_state,
            metrics_path=metrics_path,
        )

        input_paths = self._resolve_inputs(ctx, contract)
        started_event = self._events.emit(
            run_metrics_path=metrics_path,
            run_id=ctx.run_id,
            event_type=EventType.AGENT_INVOCATION_STARTED,
            producer="runtime",
            workflow_state=ctx.current_state,
            causation_event_id=last_event_id,
            payload={
                "agent_role": agent_role,
                "mode": mode.value,
                "input_artifacts": list(contract.input_artifacts),
                "output_artifacts_declared": list(contract.output_artifacts),
            },
        )
        last_event_id = started_event.event_id

        if mode == InvocationMode.AUTOMATED:
            adapter_outputs = self._run_automated(adapter, input_paths, ctx.artifacts_dir, contract)
        elif mode == InvocationMode.HUMAN_AS_AGENT:
            adapter_outputs = self._run_human_mode(ctx, contract)
        else:
            raise InvocationError(f"Unsupported invocation mode: {mode}")

        output_refs = self._register_outputs(
            ctx=ctx,
            contract=contract,
            schemas=schemas,
            owner_role=agent_role,
            resolved_outputs=adapter_outputs,
            metrics_path=metrics_path,
            causation_event_id=last_event_id,
        )

        duration_seconds = perf_counter() - started_clock
        invocation_record = self.build_invocation_record(
            ctx=ctx,
            agent_role=agent_role,
            input_refs=tuple(
                ArtifactRef(name=name, artifact_id=None, artifact_hash=None)
                for name in contract.input_artifacts
            ),
            output_refs=output_refs,
            outcome=InvocationOutcome.COMPLETED,
            mode=mode,
            invoked_at=started_at.isoformat(),
            duration_seconds=duration_seconds,
            notes=None,
        )
        metrics_writer.append_event(metrics_path, invocation_record, "invocation_records")
        self._events.emit(
            run_metrics_path=metrics_path,
            run_id=ctx.run_id,
            event_type=EventType.AGENT_INVOCATION_COMPLETED,
            producer="runtime",
            workflow_state=ctx.current_state,
            causation_event_id=started_event.event_id,
            payload={
                "agent_role": agent_role,
                "mode": mode.value,
                "outcome": InvocationOutcome.COMPLETED.value,
                "duration_seconds": round(duration_seconds, 6),
                "output_artifacts": [self._artifact_ref_to_dict(ref) for ref in output_refs],
            },
        )

        return InvocationResult(
            agent_role=agent_role,
            outcome=InvocationOutcome.COMPLETED,
            output_refs=output_refs,
            duration_seconds=duration_seconds,
            invocation_record=invocation_record,
        )

    def check_single_shot(
        self,
        ctx: RunContext,
        agent_role: str,
        workflow_state: str,
        metrics_path: Path,
    ) -> None:
        if not metrics_path.is_file():
            return
        payload = metrics_writer._load_or_init(metrics_path)
        records = payload.get("invocation_records", [])
        if not isinstance(records, list):
            return
        prior_timestamps = self._prior_invocations(records, agent_role, workflow_state)
        if not prior_timestamps:
            return
        if self._has_rework_after(payload, prior_timestamps):
            return
        raise SingleShotViolationError(
            f"Single-shot violation for role '{agent_role}' in state '{workflow_state}'."
        )

    def build_invocation_record(
        self,
        ctx: RunContext,
        agent_role: str,
        input_refs: tuple[ArtifactRef, ...],
        output_refs: tuple[ArtifactRef, ...],
        outcome: InvocationOutcome,
        mode: InvocationMode,
        invoked_at: str,
        duration_seconds: float,
        notes: str | None,
    ) -> dict:
        # Deterministic record shape and ordering for auditability.
        return {
            "run_id": ctx.run_id,
            "workflow_state": ctx.current_state,
            "agent_role": agent_role,
            "mode": mode.value,
            "outcome": outcome.value,
            "invoked_at": invoked_at,
            "duration_seconds": round(duration_seconds, 6),
            "inputs": [self._artifact_ref_to_dict(ref) for ref in input_refs],
            "outputs": [self._artifact_ref_to_dict(ref) for ref in output_refs],
            "notes": notes,
        }

    def _resolve_inputs(self, ctx: RunContext, contract: AgentContract) -> dict[str, Path]:
        input_paths: dict[str, Path] = {}
        for name in contract.input_artifacts:
            path = ctx.artifacts_dir / name
            if not path.is_file():
                raise MissingInputArtifactError(f"Required input artifact missing: {path}")
            input_paths[name] = path
        return input_paths

    def _run_automated(
        self,
        adapter: AgentAdapter | None,
        input_paths: dict[str, Path],
        output_dir: Path,
        contract: AgentContract,
    ) -> dict[str, Path]:
        if adapter is None:
            raise MissingAdapterError("AUTOMATED mode requires an adapter.")
        result = adapter.invoke(input_paths=input_paths, output_dir=output_dir)
        self._validate_adapter_outputs(result, contract)
        return result

    def _run_human_mode(self, ctx: RunContext, contract: AgentContract) -> dict[str, Path]:
        # Human mode is deterministic: runtime only checks for declared outputs.
        return {name: ctx.artifacts_dir / name for name in contract.output_artifacts}

    def _validate_adapter_outputs(
        self,
        adapter_outputs: dict[str, Path],
        contract: AgentContract,
    ) -> None:
        expected = set(contract.output_artifacts)
        for artifact_name in adapter_outputs:
            if artifact_name not in expected:
                raise UnexpectedAdapterOutputError(
                    f"Adapter returned undeclared output artifact '{artifact_name}'."
                )

    def _register_outputs(
        self,
        ctx: RunContext,
        contract: AgentContract,
        schemas: dict[str, ArtifactSchema],
        owner_role: str,
        resolved_outputs: dict[str, Path],
        metrics_path: Path,
        causation_event_id: str | None,
    ) -> tuple[ArtifactRef, ...]:
        registered: list[ArtifactRef] = []
        last_event_id = causation_event_id
        for artifact_name in contract.output_artifacts:
            resolved_path = resolved_outputs.get(artifact_name, ctx.artifacts_dir / artifact_name)
            if resolved_path.parent.resolve() != ctx.artifacts_dir.resolve():
                raise UnexpectedAdapterOutputError(
                    f"Output artifact '{artifact_name}' must be written into {ctx.artifacts_dir}."
                )
            if not resolved_path.is_file():
                raise MissingOutputArtifactError(f"Required output artifact missing: {resolved_path}")
            if resolved_path.name != artifact_name:
                raise UnexpectedAdapterOutputError(
                    f"Output artifact path name mismatch for '{artifact_name}': {resolved_path.name}"
                )
            ref = self._artifact_system.register(
                ctx=ctx,
                artifact_name=artifact_name,
                owner_role=owner_role,
                schemas=schemas,
            )
            registered.append(ref)
            created_event = self._events.emit(
                run_metrics_path=metrics_path,
                run_id=ctx.run_id,
                event_type=EventType.ARTIFACT_CREATED,
                producer=owner_role,
                workflow_state=ctx.current_state,
                causation_event_id=last_event_id,
                payload={
                    "artifact_name": ref.name,
                    "artifact_id": ref.artifact_id,
                    "artifact_hash": ref.artifact_hash,
                    "owner_role": owner_role,
                },
            )
            last_event_id = created_event.event_id
        return tuple(registered)

    @staticmethod
    def _artifact_ref_to_dict(ref: ArtifactRef) -> dict:
        return {
            "name": ref.name,
            "artifact_id": ref.artifact_id,
            "artifact_hash": ref.artifact_hash,
        }

    @staticmethod
    def _prior_invocations(
        records: list[object],
        agent_role: str,
        workflow_state: str,
    ) -> list[str]:
        timestamps: list[str] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            if str(item.get("agent_role", "")) != agent_role:
                continue
            if str(item.get("workflow_state", "")) != workflow_state:
                continue
            invoked_at = item.get("invoked_at")
            if isinstance(invoked_at, str) and invoked_at:
                timestamps.append(invoked_at)
        return timestamps

    @staticmethod
    def _has_rework_after(payload: dict, prior_timestamps: list[str]) -> bool:
        events = payload.get("events", [])
        if not isinstance(events, list):
            return False
        latest_prior = max(prior_timestamps)
        for event in events:
            if not isinstance(event, dict):
                continue
            if str(event.get("event_type", "")) != "run.rework_started":
                continue
            ts = event.get("timestamp")
            if isinstance(ts, str) and ts > latest_prior:
                return True
        return False

