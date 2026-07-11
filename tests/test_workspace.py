from __future__ import annotations

from pathlib import Path

import pytest

from mmagent.workspace import WORKSPACE_DIRECTORIES, initialize_workspace, read_status, validate_workspace


def test_initialize_and_validate_workspace(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    result = initialize_workspace(root)
    assert result.created
    assert validate_workspace(root).passed


def test_repeated_init_preserves_existing_file(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    initialize_workspace(root)
    decisions = root / "decisions.md"
    decisions.write_text("# User decision\n", encoding="utf-8")

    second = initialize_workspace(root)

    assert decisions.read_text(encoding="utf-8") == "# User decision\n"
    assert decisions in second.existing


def test_status_is_read_only(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    initialize_workspace(root)
    before = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}

    state, report = read_status(root)

    after = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
    assert state is not None
    assert report.passed
    assert before == after


def test_missing_directory_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    initialize_workspace(root)
    target = root / WORKSPACE_DIRECTORIES[0]
    target.rmdir()

    report = validate_workspace(root)

    assert not report.passed
    assert f"missing directory: {WORKSPACE_DIRECTORIES[0]}" in report.errors


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    initialize_workspace(root)
    (root / "state.yaml").write_text("current_stage: [", encoding="utf-8")

    report = validate_workspace(root)

    assert not report.passed
    assert any("state.yaml: cannot read YAML" in error for error in report.errors)


def test_single_character_workspace_name_is_supported(tmp_path: Path) -> None:
    root = tmp_path / "x"
    initialize_workspace(root)
    assert validate_workspace(root).passed


def test_init_rejects_file_directory_collision(tmp_path: Path) -> None:
    root = tmp_path / "demo_workspace"
    root.mkdir()
    (root / WORKSPACE_DIRECTORIES[0]).write_text("collision", encoding="utf-8")

    with pytest.raises(ValueError, match="occupied by a file"):
        initialize_workspace(root)
