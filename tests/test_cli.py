from __future__ import annotations

from pathlib import Path

from mmagent import cli
from mmagent.environment import ToolDiscovery


def test_cli_exit_codes(tmp_path: Path, capsys) -> None:
    root = tmp_path / "cli_workspace"
    assert cli.main(["init", str(root)]) == 0
    capsys.readouterr()
    assert cli.main(["status", str(root)]) == 0
    capsys.readouterr()
    assert cli.main(["validate-workspace", str(root)]) == 0
    assert "PASS" in capsys.readouterr().out

    (root / "problem_spec.yaml").write_text("not: [valid", encoding="utf-8")
    assert cli.main(["validate-workspace", str(root)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_doctor_reports_missing_optional_tools(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "discover_tool",
        lambda name, project_root=None: ToolDiscovery(
            name=name,
            path=None,
            source=None,
            diagnostics=(f"{name} unavailable for test",),
        ),
    )
    monkeypatch.setattr(
        cli,
        "inspect_git",
        lambda _root: {
            "status": "git_unavailable",
            "git_path": None,
            "source": None,
            "repository": "not_run",
            "commit": "not_run",
            "branch": "not_run",
            "worktree": "not_run",
            "diagnostics": ["git unavailable for test"],
            "remedy": "install Git",
        },
    )

    assert cli.main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert "MISSING (optional): Git" in output
    assert "MISSING (optional): XeLaTeX" in output
    assert "Git status: git_unavailable" in output
    assert "Git worktree: not_run" in output


def test_init_collision_returns_clear_nonzero_error(tmp_path: Path, capsys) -> None:
    target = tmp_path / "not-a-directory"
    target.write_text("occupied", encoding="utf-8")

    assert cli.main(["init", str(target)]) == 1

    assert "ERROR: workspace path exists but is not a directory" in capsys.readouterr().out
