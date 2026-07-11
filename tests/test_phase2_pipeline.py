from __future__ import annotations

import math
from pathlib import Path

import yaml

from mmagent.models import Experiment, PdfAcceptance, Stage, Status, WorkspaceState
from mmagent.pipeline import (
    PipelineError,
    compile_report,
    create_demo_workspace,
    render_report,
    resume_phase2,
    run_solver,
    validate_results,
)
from mmagent.workspace import validate_workspace


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_demo_solver_validation_and_report_use_real_artifacts(tmp_path: Path) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    assert validate_workspace(root).passed

    manifest = run_solver(root)
    experiment = Experiment.model_validate(_load(root / "results" / "experiment.yaml"))
    metrics = {metric.name: metric.value for metric in experiment.metrics}

    assert manifest.status is Status.PASSED
    assert math.isclose(metrics["slope"], 2.0)
    assert math.isclose(metrics["intercept"], 1.0)
    assert math.isclose(metrics["linear_rmse"], 0.0)
    assert metrics["baseline_rmse"] > metrics["linear_rmse"]

    validation = validate_results(root)
    assert validation.status is Status.PASSED
    assert any(finding.status is Status.NOT_RUN for finding in validation.findings)

    report = render_report(root)
    markdown = (root / "reports" / "evidence_report.md").read_text(encoding="utf-8")
    assert report.status is Status.PASSED
    assert "y = 2x + 1" in markdown
    assert "results/experiment.yaml" in markdown
    state = WorkspaceState.model_validate(_load(root / "state.yaml"))
    assert state.current_stage is Stage.PAPER_DRAFTED


def test_compile_gate_records_blocked_without_xelatex(tmp_path: Path, monkeypatch) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    run_solver(root)
    validate_results(root)
    render_report(root)
    monkeypatch.setattr("mmagent.pipeline.shutil.which", lambda _name: None)

    acceptance = compile_report(root)

    assert acceptance.status is Status.BLOCKED
    assert acceptance.attempts == 0
    saved = PdfAcceptance.model_validate(_load(root / "reports" / "pdf_acceptance.yaml"))
    assert saved.visual_check is Status.NOT_RUN
    state = WorkspaceState.model_validate(_load(root / "state.yaml"))
    assert state.current_stage is Stage.PAPER_DRAFTED


def test_resume_runs_bounded_pipeline_to_compile_gate(tmp_path: Path, monkeypatch) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    monkeypatch.setattr("mmagent.pipeline.shutil.which", lambda _name: None)

    assert resume_phase2(root) == 2

    assert (root / "results" / "experiment.yaml").is_file()
    assert (root / "results" / "validation.yaml").is_file()
    assert (root / "paper" / "main.tex").is_file()
    assert (root / "reports" / "pdf_acceptance.yaml").is_file()


def test_solver_failure_is_persisted_for_recovery(tmp_path: Path) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    (root / "code" / "solve.py").write_text("raise SystemExit(7)\n", encoding="utf-8")

    try:
        run_solver(root)
    except PipelineError as exc:
        assert "code 7" in str(exc)
    else:
        raise AssertionError("run_solver should have failed")

    state = WorkspaceState.model_validate(_load(root / "state.yaml"))
    manifest = _load(root / "run_manifest.yaml")
    assert state.current_stage is Stage.FAILED
    assert state.failed_stage is Stage.IMPLEMENTED
    assert manifest["status"] == "failed"

    (root / "code" / "solve.py").write_text(
        "from mmagent.demo_solver import main\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        encoding="utf-8",
    )
    recovered = run_solver(root)
    assert recovered.status is Status.PASSED
    recovered_state = WorkspaceState.model_validate(_load(root / "state.yaml"))
    assert recovered_state.current_stage is Stage.IMPLEMENTED


def test_validation_mismatch_is_persisted_as_failed(tmp_path: Path) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    run_solver(root)
    experiment = _load(root / "results" / "experiment.yaml")
    experiment["metrics"][0]["value"] = 99.0
    (root / "results" / "experiment.yaml").write_text(
        yaml.safe_dump(experiment, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    validation = validate_results(root)

    assert validation.status is Status.FAILED
    state = WorkspaceState.model_validate(_load(root / "state.yaml"))
    assert state.current_stage is Stage.FAILED
    assert state.failed_stage is Stage.VALIDATED


def test_workspace_validation_checks_optional_phase2_schemas(tmp_path: Path) -> None:
    root = create_demo_workspace(tmp_path / "linear_demo")
    (root / "results" / "experiment.yaml").write_text("metrics: [", encoding="utf-8")

    report = validate_workspace(root)

    assert not report.passed
    assert any("results/experiment.yaml" in error for error in report.errors)
