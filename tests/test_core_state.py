from __future__ import annotations

from pathlib import Path

import pytest

from mmagent.artifacts import sha256_file
from mmagent.core_models import CoreStage, CoreStateError, advance_core_stage, approve_final
from mmagent.demo_assets import prepare_curve_fitting_workspace


def test_core_state_rejects_skipped_stage() -> None:
    history: list[str] = []
    advance_core_stage(history, CoreStage.CREATED)

    with pytest.raises(CoreStateError, match="expected next stage INPUT_READY"):
        advance_core_stage(history, CoreStage.CODE_EXECUTED)


def test_final_requires_explicit_human_approval() -> None:
    history = [CoreStage.AWAITING_HUMAN_APPROVAL.value]

    with pytest.raises(CoreStateError, match="explicit human approval"):
        approve_final(history, approved=False)

    approve_final(history, approved=True)
    assert history[-1] == CoreStage.FINAL.value


def test_demo_input_and_source_are_fixed_across_workspaces(tmp_path: Path) -> None:
    first = prepare_curve_fitting_workspace(tmp_path / "first")
    second = prepare_curve_fitting_workspace(tmp_path / "second")

    assert sha256_file(first / "input" / "data.csv") == sha256_file(second / "input" / "data.csv")
    assert sha256_file(first / "src" / "solve.py") == sha256_file(second / "src" / "solve.py")
