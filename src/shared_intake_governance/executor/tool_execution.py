"""Explicit local command runner for governed tool intents."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence

from shared_intake_governance.governance import validate_tool_intent
from shared_intake_governance.runtime import RuntimePaths, validate_execution_mediation


_EXECUTION_STATUSES = {"succeeded", "failed", "blocked"}


def execute_tool_intent(
    *,
    paths: RuntimePaths,
    run_id: str,
    execution_id: str,
    intent: dict[str, Any],
    tool_intent_path: str,
    mediation_record: dict[str, Any],
    mediation_record_path: str,
    command: Sequence[str],
    executed_by: str,
    timeout_seconds: float,
    execution_metadata: dict[str, str],
    executed_at: str,
) -> dict[str, Any]:
    """Run an explicit local command only after matching ready mediation."""
    validate_tool_intent(intent)
    validate_execution_mediation(mediation_record)
    if not command:
        raise ValueError("tool command must not be empty")

    metadata = dict(execution_metadata)
    if not _same_intent_scope(intent, mediation_record):
        return _result(
            run_id=run_id,
            execution_id=execution_id,
            intent=intent,
            tool_intent_path=tool_intent_path,
            mediation_record_path=mediation_record_path,
            executed_by=executed_by,
            executed_at=executed_at,
            execution_status="blocked",
            summary="Execution mediation does not match tool intent scope.",
            output_refs=[],
            execution_metadata=metadata,
            error={
                "kind": "mediation_scope_mismatch",
                "message": "execution mediation does not match tool intent scope",
            },
        )

    if mediation_record["mediation_decision"] != "ready":
        return _result(
            run_id=run_id,
            execution_id=execution_id,
            intent=intent,
            tool_intent_path=tool_intent_path,
            mediation_record_path=mediation_record_path,
            executed_by=executed_by,
            executed_at=executed_at,
            execution_status="blocked",
            summary="Execution mediation is blocked.",
            output_refs=[],
            execution_metadata=metadata,
            error={
                "kind": "mediation_not_ready",
                "message": "execution mediation is blocked",
            },
        )

    intent_json = json.dumps(intent, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            input=intent_json,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        metadata["timeout_seconds"] = _format_timeout(timeout_seconds)
        output_refs = _write_output_artifacts(
            paths=paths,
            run_id=run_id,
            execution_id=execution_id,
            stdout=_coerce_output(exc.stdout),
            stderr=_coerce_output(exc.stderr),
        )
        return _result(
            run_id=run_id,
            execution_id=execution_id,
            intent=intent,
            tool_intent_path=tool_intent_path,
            mediation_record_path=mediation_record_path,
            executed_by=executed_by,
            executed_at=executed_at,
            execution_status="failed",
            summary=f"Tool command timed out after {metadata['timeout_seconds']} seconds.",
            output_refs=output_refs,
            execution_metadata=metadata,
            error={
                "kind": "tool_command_timeout",
                "message": (
                    "tool command timed out after "
                    f"{metadata['timeout_seconds']} seconds"
                ),
            },
        )
    except OSError as exc:
        metadata["command_error"] = exc.__class__.__name__
        return _result(
            run_id=run_id,
            execution_id=execution_id,
            intent=intent,
            tool_intent_path=tool_intent_path,
            mediation_record_path=mediation_record_path,
            executed_by=executed_by,
            executed_at=executed_at,
            execution_status="failed",
            summary="Tool command could not be started.",
            output_refs=[],
            execution_metadata=metadata,
            error={
                "kind": "tool_command_error",
                "message": str(exc),
            },
        )

    metadata["exit_code"] = str(completed.returncode)
    output_refs = _write_output_artifacts(
        paths=paths,
        run_id=run_id,
        execution_id=execution_id,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if completed.returncode == 0:
        return _result(
            run_id=run_id,
            execution_id=execution_id,
            intent=intent,
            tool_intent_path=tool_intent_path,
            mediation_record_path=mediation_record_path,
            executed_by=executed_by,
            executed_at=executed_at,
            execution_status="succeeded",
            summary="Tool command exited 0.",
            output_refs=output_refs,
            execution_metadata=metadata,
            error=None,
        )

    return _result(
        run_id=run_id,
        execution_id=execution_id,
        intent=intent,
        tool_intent_path=tool_intent_path,
        mediation_record_path=mediation_record_path,
        executed_by=executed_by,
        executed_at=executed_at,
        execution_status="failed",
        summary=f"Tool command exited {completed.returncode}.",
        output_refs=output_refs,
        execution_metadata=metadata,
        error={
            "kind": "tool_command_failed",
            "message": f"tool command exited {completed.returncode}",
        },
    )


def _result(
    *,
    run_id: str,
    execution_id: str,
    intent: dict[str, Any],
    tool_intent_path: str,
    mediation_record_path: str,
    executed_by: str,
    executed_at: str,
    execution_status: str,
    summary: str,
    output_refs: list[str],
    execution_metadata: dict[str, str],
    error: dict[str, str] | None,
) -> dict[str, Any]:
    if execution_status not in _EXECUTION_STATUSES:
        raise ValueError(f"unsupported execution_status: {execution_status}")
    if execution_status == "succeeded" and error is not None:
        raise ValueError("succeeded tool executions must not include an error")
    if execution_status in {"failed", "blocked"} and error is None:
        raise ValueError("failed or blocked tool executions require an error")

    return {
        "schema_version": "tool-execution-result.v1",
        "run_id": run_id,
        "execution_id": execution_id,
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": intent["action_class"],
        "tool_name": intent["tool_name"],
        "executed_by": executed_by,
        "executed_at": executed_at,
        "execution_status": execution_status,
        "summary": summary,
        "tool_intent_path": tool_intent_path,
        "mediation_record_path": mediation_record_path,
        "output_refs": output_refs,
        "execution_metadata": execution_metadata,
        "error": error,
        "evidence_refs": intent["evidence_refs"],
    }


def _same_intent_scope(intent: dict[str, Any], record: dict[str, Any]) -> bool:
    return all(
        intent[field] == record.get(field)
        for field in ("intent_id", "profile_id", "action_class", "tool_name")
    )


def _write_output_artifacts(
    *,
    paths: RuntimePaths,
    run_id: str,
    execution_id: str,
    stdout: str,
    stderr: str,
) -> list[str]:
    output_refs: list[str] = []
    if stdout:
        stdout_path = paths.tool_execution_artifact_path(
            run_id, execution_id, "stdout.txt"
        )
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        output_refs.append(str(stdout_path))
    if stderr:
        stderr_path = paths.tool_execution_artifact_path(
            run_id, execution_id, "stderr.txt"
        )
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.write_text(stderr, encoding="utf-8")
        output_refs.append(str(stderr_path))
    return output_refs


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _format_timeout(value: float) -> str:
    return f"{value:g}"
