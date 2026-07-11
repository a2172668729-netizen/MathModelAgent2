"""Auditable subprocess execution with process-tree cleanup on timeout."""

from __future__ import annotations

import os
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from mmagent.artifacts import atomic_json, atomic_text


def _terminate_tree(process: subprocess.Popen[str]) -> str:
    if process.poll() is not None:
        return "already_exited"
    if os.name == "nt":
        cleanup = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
        )
        return f"taskkill_exit_{cleanup.returncode}"
    try:
        os.killpg(process.pid, signal.SIGKILL)
        return "process_group_killed"
    except ProcessLookupError:
        return "already_exited"


def run_recorded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    environment: Mapping[str, str] | None,
    record_path: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, object]:
    """Run without a shell and always persist exit, timing, logs, and cleanup evidence."""
    root = cwd.resolve()
    started = datetime.now(UTC)
    timer = perf_counter()
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    effective_environment = None if environment is None else dict(environment)
    if effective_environment is not None and Path(command[0]).name.casefold().startswith("python"):
        effective_environment.setdefault("PYTHONUTF8", "1")
        effective_environment.setdefault("PYTHONIOENCODING", "utf-8")
    process = subprocess.Popen(
        list(command),
        cwd=root,
        env=effective_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        start_new_session=os.name != "nt",
        creationflags=creationflags,
    )
    timed_out = False
    cleanup = "not_needed"
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        cleanup = _terminate_tree(process)
        stdout, stderr = process.communicate()
    duration = perf_counter() - timer
    atomic_text(stdout_path, stdout)
    atomic_text(stderr_path, stderr)
    record: dict[str, object] = {
        "schema_version": "1.0",
        "command": list(command),
        "working_directory": str(root),
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 6),
        "timeout_seconds": timeout_seconds,
        "pid": process.pid,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "cleanup": cleanup,
        "status": "passed" if process.returncode == 0 and not timed_out else "failed",
        "stdout_path": stdout_path.relative_to(root).as_posix(),
        "stderr_path": stderr_path.relative_to(root).as_posix(),
    }
    atomic_json(record_path, record)
    return record
