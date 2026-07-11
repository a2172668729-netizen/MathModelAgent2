"""Controlled, evidence-preserving Python subprocess execution."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence

from mmagent.artifacts import atomic_json, atomic_text, ensure_within, file_records, files_under, sha256_file


class ExecutionError(RuntimeError):
    """A solver process failed after its evidence was persisted."""

    def __init__(self, message: str, record: dict[str, Any]):
        super().__init__(message)
        self.record = record


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    record: dict[str, Any]

    @property
    def exit_code(self) -> int | None:
        value = self.record.get("exit_code")
        return value if isinstance(value, int) else None


_NETWORK_GUARD = '''"""Imported automatically to block Python socket networking for solver runs."""
import os as _os
import socket as _socket
import subprocess as _subprocess


class _BlockedSocket(_socket.socket):
    def connect(self, address):
        raise PermissionError("network access is disabled by MathModelAgent")

    def connect_ex(self, address):
        raise PermissionError("network access is disabled by MathModelAgent")


def _blocked(*args, **kwargs):
    raise PermissionError("network access is disabled by MathModelAgent")


_socket.socket = _BlockedSocket
_socket.create_connection = _blocked
_subprocess.Popen = _blocked
_subprocess.run = _blocked
_subprocess.call = _blocked
_subprocess.check_call = _blocked
_subprocess.check_output = _blocked
_os.system = _blocked
_os.popen = _blocked
'''


def _controlled_environment(run_root: Path, random_seed: int) -> tuple[dict[str, str], dict[str, Any]]:
    allowed = (
        "COMSPEC",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
    )
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    runtime = run_root / "logs" / "runtime_site"
    runtime.mkdir(parents=True, exist_ok=True)
    atomic_text(runtime / "sitecustomize.py", _NETWORK_GUARD)
    home = runtime / "home"
    mpl_config = runtime / "matplotlib"
    home.mkdir(exist_ok=True)
    mpl_config.mkdir(exist_ok=True)
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "PYTHONHASHSEED": str(random_seed),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(runtime),
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(mpl_config),
            "MMAGENT_NETWORK_DISABLED": "1",
            "MMAGENT_RUN_ROOT": str(run_root),
        }
    )
    summary = {
        "inherited_keys": sorted(name for name in allowed if name in os.environ),
        "set_keys": [
            "HOME",
            "USERPROFILE",
            "PYTHONHASHSEED",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONPATH",
            "MPLBACKEND",
            "MPLCONFIGDIR",
            "MMAGENT_NETWORK_DISABLED",
            "MMAGENT_RUN_ROOT",
        ],
        "network_policy": "python_socket_blocked_by_sitecustomize",
        "output_policy": "solver cwd and declared output root are the current run workspace",
    }
    return environment, summary


def execute_python_script(
    run_root: Path,
    *,
    script: Path = Path("src/solve.py"),
    input_files: Sequence[Path] = (Path("input/data.csv"), Path("input/problem.md")),
    timeout_seconds: float = 120,
    random_seed: int = 20260710,
    extra_args: Sequence[str] = (),
    log_prefix: str = "python",
) -> ExecutionResult:
    """Execute a run-local Python script without a shell and persist complete logs."""
    root = run_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"run workspace does not exist: {root}")
    script_path = ensure_within(root, root / script)
    if not script_path.is_file():
        raise ValueError(f"solver script does not exist: {script.as_posix()}")
    resolved_inputs: list[Path] = []
    for relative in input_files:
        candidate = ensure_within(root, root / relative)
        if not candidate.is_file():
            raise ValueError(f"declared input does not exist: {relative.as_posix()}")
        resolved_inputs.append(candidate)

    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if not log_prefix.replace("_", "").isalnum():
        raise ValueError("log_prefix must contain only letters, digits, and underscores")
    role = "solver" if log_prefix == "python" else log_prefix
    stdout_path = logs / f"{log_prefix}_stdout.log"
    stderr_path = logs / f"{log_prefix}_stderr.log"
    execution_path = logs / ("execution.json" if log_prefix == "python" else f"{log_prefix}_execution.json")
    environment, environment_summary = _controlled_environment(root, random_seed)
    script_relative = script_path.relative_to(root).as_posix()
    command = [sys.executable, script_relative, "--run-root", ".", *extra_args]
    started = datetime.now(UTC)
    timer = perf_counter()
    timed_out = False
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    failure_reason: str | None = None
    try:
        process = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        stdout = process.stdout
        stderr = process.stderr
        exit_code = process.returncode
        if exit_code != 0:
            failure_reason = f"{role} exited with code {exit_code}"
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        failure_reason = f"{role} timed out after {timeout_seconds} seconds"
    except OSError as exc:
        stderr = str(exc)
        failure_reason = f"{role} could not start: {exc}"
    finished = datetime.now(UTC)
    duration = perf_counter() - timer
    atomic_text(stdout_path, stdout)
    atomic_text(stderr_path, stderr)

    produced = files_under(root, "outputs", "figures", "tables", "paper")
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": root.name,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "command": command,
        "working_directory": ".",
        "environment": environment_summary,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": finished.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 6),
        "timeout_seconds": timeout_seconds,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "status": "failed" if failure_reason else "passed",
        "failure_reason": failure_reason,
        "source": {
            "path": script_relative,
            "sha256": sha256_file(script_path),
        },
        "inputs": file_records(root, resolved_inputs),
        "produced_outputs": file_records(root, produced),
        "stdout_path": stdout_path.relative_to(root).as_posix(),
        "stderr_path": stderr_path.relative_to(root).as_posix(),
    }
    atomic_json(execution_path, record)
    if failure_reason:
        raise ExecutionError(failure_reason, record)
    return ExecutionResult(record)
