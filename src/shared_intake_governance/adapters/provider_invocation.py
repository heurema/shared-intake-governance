"""Explicit local provider command invocation."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence

from shared_intake_governance.runtime import RuntimePaths

from .provider_result import record_provider_result


def invoke_provider_request(
    *,
    paths: RuntimePaths,
    run_id: str,
    result_id: str,
    provider_request: dict[str, Any],
    provider_request_path: str,
    command: Sequence[str],
    recorded_by: str,
    timeout_seconds: float,
    usage_metadata: dict[str, str],
    recorded_at: str,
) -> dict[str, Any]:
    """Run an explicit command with provider-request JSON on stdin."""
    if not command:
        raise ValueError("provider command must not be empty")

    request_json = json.dumps(
        provider_request, sort_keys=True, ensure_ascii=False
    ) + "\n"
    metadata = dict(usage_metadata)

    try:
        completed = subprocess.run(
            [str(item) for item in command],
            input=request_json,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        metadata["timeout_seconds"] = _format_timeout(timeout_seconds)
        stdout = _coerce_output(exc.stdout)
        stderr = _coerce_output(exc.stderr)
        response_refs = _write_response_artifacts(
            paths=paths,
            run_id=run_id,
            result_id=result_id,
            stdout=stdout,
            stderr=stderr,
        )
        return record_provider_result(
            run_id=run_id,
            result_id=result_id,
            provider_request=provider_request,
            provider_request_path=provider_request_path,
            result_status="failed",
            recorded_by=recorded_by,
            summary=f"Provider command timed out after {metadata['timeout_seconds']} seconds.",
            response_refs=response_refs,
            usage_metadata=metadata,
            error={
                "kind": "provider_command_timeout",
                "message": (
                    "provider command timed out after "
                    f"{metadata['timeout_seconds']} seconds"
                ),
            },
            recorded_at=recorded_at,
        )
    except OSError as exc:
        metadata["command_error"] = exc.__class__.__name__
        return record_provider_result(
            run_id=run_id,
            result_id=result_id,
            provider_request=provider_request,
            provider_request_path=provider_request_path,
            result_status="failed",
            recorded_by=recorded_by,
            summary="Provider command could not be started.",
            response_refs=[],
            usage_metadata=metadata,
            error={
                "kind": "provider_command_error",
                "message": str(exc),
            },
            recorded_at=recorded_at,
        )

    metadata["exit_code"] = str(completed.returncode)
    response_refs = _write_response_artifacts(
        paths=paths,
        run_id=run_id,
        result_id=result_id,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if completed.returncode == 0:
        return record_provider_result(
            run_id=run_id,
            result_id=result_id,
            provider_request=provider_request,
            provider_request_path=provider_request_path,
            result_status="succeeded",
            recorded_by=recorded_by,
            summary="Provider command exited 0.",
            response_refs=response_refs,
            usage_metadata=metadata,
            error=None,
            recorded_at=recorded_at,
        )

    return record_provider_result(
        run_id=run_id,
        result_id=result_id,
        provider_request=provider_request,
        provider_request_path=provider_request_path,
        result_status="failed",
        recorded_by=recorded_by,
        summary=f"Provider command exited {completed.returncode}.",
        response_refs=response_refs,
        usage_metadata=metadata,
        error={
            "kind": "provider_command_failed",
            "message": f"provider command exited {completed.returncode}",
        },
        recorded_at=recorded_at,
    )


def _write_response_artifacts(
    *,
    paths: RuntimePaths,
    run_id: str,
    result_id: str,
    stdout: str,
    stderr: str,
) -> list[str]:
    response_refs: list[str] = []
    if stdout:
        stdout_path = paths.provider_result_artifact_path(
            run_id, result_id, "stdout.txt"
        )
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        response_refs.append(str(stdout_path))
    if stderr:
        stderr_path = paths.provider_result_artifact_path(
            run_id, result_id, "stderr.txt"
        )
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.write_text(stderr, encoding="utf-8")
        response_refs.append(str(stderr_path))
    return response_refs


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _format_timeout(value: float) -> str:
    return f"{value:g}"
