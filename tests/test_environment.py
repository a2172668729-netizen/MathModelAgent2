from __future__ import annotations

import subprocess
from pathlib import Path

from mmagent import environment
from mmagent.environment import ToolDiscovery, discover_tool, inspect_git


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test executable")
    return path


def _disable_external_discovery(monkeypatch) -> None:
    monkeypatch.setattr(environment.shutil, "which", lambda _name: None)
    monkeypatch.setattr(environment, "_where_candidates", lambda _name: [])
    monkeypatch.setattr(environment, "_windows_tex_candidates", lambda _name: [])
    monkeypatch.setattr(environment, "_windows_git_candidates", lambda: [])
    monkeypatch.setattr(environment, "_environment_candidates", lambda _name: ())


def test_discovery_prefers_process_path(monkeypatch, tmp_path: Path) -> None:
    path_tool = _executable(tmp_path / "path/xelatex.exe")
    monkeypatch.setattr(environment.shutil, "which", lambda _name: str(path_tool))
    monkeypatch.setattr(environment, "_where_candidates", lambda _name: [tmp_path / "where/xelatex.exe"])

    result = discover_tool("xelatex", project_root=tmp_path)

    assert result.path == path_tool.resolve()
    assert result.source == "process_path"


def test_config_overrides_environment_and_accepts_relative_path(monkeypatch, tmp_path: Path) -> None:
    _disable_external_discovery(monkeypatch)
    configured = _executable(tmp_path / "tools/xelatex.exe")
    environment_tool = _executable(tmp_path / "environment/xelatex.exe")
    (tmp_path / "config").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (tmp_path / "config/environment.yaml").write_text(
        "tools:\n  xelatex:\n    path: tools/xelatex.exe\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        environment,
        "_environment_candidates",
        lambda _name: ((str(environment_tool), "environment:MMAGENT_XELATEX"),),
    )

    result = discover_tool("xelatex", project_root=tmp_path)

    assert result.path == configured.resolve()
    assert result.source == "project_config"


def test_missing_and_non_executable_configuration_are_diagnostic(monkeypatch, tmp_path: Path) -> None:
    _disable_external_discovery(monkeypatch)
    (tmp_path / "config").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    bad = tmp_path / "tools/xelatex.txt"
    bad.parent.mkdir()
    bad.write_text("not executable", encoding="utf-8")
    (tmp_path / "config/environment.yaml").write_text(
        "tools:\n  xelatex:\n    path: tools/xelatex.txt\n",
        encoding="utf-8",
    )

    result = discover_tool("xelatex", project_root=tmp_path)

    assert result.path is None
    assert result.source is None
    assert any("not executable" in item for item in result.diagnostics)
    assert any("was not found" in item for item in result.diagnostics)


def test_multiple_texlive_versions_choose_newest(monkeypatch, tmp_path: Path) -> None:
    _disable_external_discovery(monkeypatch)
    old = _executable(tmp_path / "texlive/2025/bin/windows/xelatex.exe")
    newest = _executable(tmp_path / "texlive/2026/bin/windows/xelatex.exe")
    candidates = sorted(
        [(old, "windows_texlive_versioned"), (newest, "windows_texlive_versioned")],
        key=lambda item: environment._version_key(item[0]),
        reverse=True,
    )
    monkeypatch.setattr(environment, "_windows_tex_candidates", lambda _name: candidates)

    result = discover_tool("xelatex", project_root=tmp_path)

    assert result.path == newest.resolve()
    assert result.source == "windows_texlive_versioned"


def test_git_config_is_checked_after_common_locations(monkeypatch, tmp_path: Path) -> None:
    _disable_external_discovery(monkeypatch)
    common = _executable(tmp_path / "common/git.exe")
    configured = _executable(tmp_path / "configured/git.exe")
    (tmp_path / "config").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (tmp_path / "config/environment.yaml").write_text(
        f"tools:\n  git:\n    path: {configured.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(environment, "_windows_git_candidates", lambda: [(common, "git_for_windows_common")])

    result = discover_tool("git", project_root=tmp_path)

    assert result.path == common.resolve()
    assert result.source == "git_for_windows_common"


def test_git_unavailable_keeps_worktree_not_run(tmp_path: Path) -> None:
    discovery = ToolDiscovery("git", None, None, ("not found",))

    result = inspect_git(tmp_path, discovery)

    assert result["status"] == "git_unavailable"
    assert result["worktree"] == "not_run"
    assert result["commit"] == "not_run"


def test_git_metadata_records_commit_branch_and_dirty_state(monkeypatch, tmp_path: Path) -> None:
    git = _executable(tmp_path / "git.exe")
    responses = iter(
        (
            subprocess.CompletedProcess([], 0, "true\n", ""),
            subprocess.CompletedProcess([], 0, "abc123\n", ""),
            subprocess.CompletedProcess([], 0, "feature/test\n", ""),
            subprocess.CompletedProcess([], 0, " M src/file.py\n", ""),
        )
    )
    monkeypatch.setattr(environment, "_run_git", lambda *_args: next(responses))

    result = inspect_git(tmp_path, ToolDiscovery("git", git, "test"))

    assert result["status"] == "available"
    assert result["commit"] == "abc123"
    assert result["branch"] == "feature/test"
    assert result["worktree"] == "dirty"


def test_git_unborn_repository_is_explicit_and_worktree_is_still_checked(monkeypatch, tmp_path: Path) -> None:
    git = _executable(tmp_path / "git.exe")
    responses = iter(
        (
            subprocess.CompletedProcess([], 0, "true\n", ""),
            subprocess.CompletedProcess([], 128, "", "fatal: ambiguous argument 'HEAD'"),
            subprocess.CompletedProcess([], 0, "feature/unborn\n", ""),
            subprocess.CompletedProcess([], 0, "?? src/\n", ""),
        )
    )
    monkeypatch.setattr(environment, "_run_git", lambda *_args: next(responses))

    result = inspect_git(tmp_path, ToolDiscovery("git", git, "test"))

    assert result["status"] == "available"
    assert result["commit"] == "unborn (repository has no commits)"
    assert result["branch"] == "feature/unborn"
    assert result["worktree"] == "dirty"
