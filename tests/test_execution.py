from __future__ import annotations

import json
from pathlib import Path

import pytest

from mmagent.artifacts import sha256_file
from mmagent.execution import ExecutionError, execute_python_script


def _run_root(tmp_path: Path, source: str) -> Path:
    root = tmp_path / "run-test"
    (root / "src").mkdir(parents=True)
    (root / "input").mkdir()
    (root / "input" / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (root / "input" / "problem.md").write_text("# test\n", encoding="utf-8")
    (root / "src" / "solve.py").write_text(source, encoding="utf-8")
    return root


def test_python_success_stdout_stderr_hashes_and_json_csv_outputs(tmp_path: Path) -> None:
    root = _run_root(
        tmp_path,
        """from pathlib import Path
import argparse, json, sys
p=argparse.ArgumentParser(); p.add_argument('--run-root', type=Path, required=True); a=p.parse_args()
out=a.run_root/'outputs'; out.mkdir()
(out/'metrics.json').write_text(json.dumps({'value': 2}), encoding='utf-8')
(out/'values.csv').write_text('value\\n2\\n', encoding='utf-8')
print('solver stdout')
print('solver stderr', file=sys.stderr)
""",
    )

    result = execute_python_script(root)

    assert result.exit_code == 0
    assert (root / "outputs" / "metrics.json").is_file()
    assert (root / "outputs" / "values.csv").is_file()
    assert "solver stdout" in (root / "logs" / "python_stdout.log").read_text(encoding="utf-8")
    assert "solver stderr" in (root / "logs" / "python_stderr.log").read_text(encoding="utf-8")
    record = json.loads((root / "logs" / "execution.json").read_text(encoding="utf-8"))
    assert record["source"]["sha256"] == sha256_file(root / "src" / "solve.py")
    assert record["inputs"][0]["sha256"]
    assert record["environment"]["network_policy"] == "python_socket_blocked_by_sitecustomize"


@pytest.mark.parametrize(
    ("source", "message", "expects_stderr"),
    [
        ("def broken(:\n", "solver exited with code", True),
        ("raise RuntimeError('boom')\n", "solver exited with code", True),
        ("raise SystemExit(7)\n", "solver exited with code 7", False),
    ],
)
def test_python_failures_are_persisted(
    tmp_path: Path,
    source: str,
    message: str,
    expects_stderr: bool,
) -> None:
    root = _run_root(tmp_path, source)

    with pytest.raises(ExecutionError, match=message):
        execute_python_script(root)

    record = json.loads((root / "logs" / "execution.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["exit_code"] != 0
    assert record["failure_reason"]
    stderr_log = root / "logs" / "python_stderr.log"
    assert stderr_log.is_file()
    if expects_stderr:
        assert stderr_log.read_text(encoding="utf-8").strip()


def test_python_timeout_terminates_and_records_timeout(tmp_path: Path) -> None:
    root = _run_root(tmp_path, "import time\ntime.sleep(5)\n")

    with pytest.raises(ExecutionError, match="timed out"):
        execute_python_script(root, timeout_seconds=0.2)

    record = json.loads((root / "logs" / "execution.json").read_text(encoding="utf-8"))
    assert record["timed_out"] is True
    assert record["exit_code"] is None


def test_executor_rejects_script_outside_run(tmp_path: Path) -> None:
    root = _run_root(tmp_path, "print('ok')\n")
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes allowed root"):
        execute_python_script(root, script=Path("../outside.py"))


def test_network_socket_is_blocked_by_default(tmp_path: Path) -> None:
    root = _run_root(
        tmp_path,
        """import socket
try:
    socket.create_connection(('example.com', 80), timeout=1)
except PermissionError:
    print('blocked')
else:
    raise SystemExit(9)
""",
    )

    execute_python_script(root)

    assert "blocked" in (root / "logs" / "python_stdout.log").read_text(encoding="utf-8")


def test_solver_cannot_spawn_external_network_helper(tmp_path: Path) -> None:
    root = _run_root(
        tmp_path,
        """import subprocess
try:
    subprocess.run(['curl.exe', 'https://example.com'])
except PermissionError:
    print('process blocked')
else:
    raise SystemExit(9)
""",
    )

    execute_python_script(root)

    assert "process blocked" in (root / "logs" / "python_stdout.log").read_text(encoding="utf-8")
