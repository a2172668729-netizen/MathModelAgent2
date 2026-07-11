from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from mmagent.artifacts import atomic_json, read_json
from mmagent.benchmark_models import BenchmarkCase, StructuralExpectations
from mmagent.benchmark_process import run_recorded_process
from mmagent.benchmark_runner import compare_attempts, compare_suite_reports, load_cases, run_attempt, select_cases
from mmagent.benchmark_worker import validate_numeric
from mmagent.benchmark_cases import _optimization


REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = REPO_ROOT / "benchmarks" / "cases"


def _run(script: str, root: Path, timeout: float = 10) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    return run_recorded_process(
        [sys.executable, "-c", script],
        cwd=root,
        timeout_seconds=timeout,
        environment=os.environ.copy(),
        record_path=root / "logs" / "record.json",
        stdout_path=root / "logs" / "stdout.log",
        stderr_path=root / "logs" / "stderr.log",
    )


def test_case_catalog_covers_required_problem_types() -> None:
    cases = load_cases(CASES_ROOT)
    tags = {tag for case, _ in cases.values() for tag in case.tags}

    assert {"forecasting", "evaluation", "optimization", "clustering", "ode", "data-quality", "comprehensive"} <= tags
    assert any("chinese-long-form" in case.tags for case, _ in cases.values())
    assert any(case.known_ambiguities for case, _ in cases.values())
    assert any(case.expected_outcome == "failed" for case, _ in cases.values())


def test_case_catalog_paths_and_unicode_problem_are_real() -> None:
    cases = load_cases(CASES_ROOT)
    case, directory = cases["comprehensive_city_planning"]

    assert (directory / case.problem_file).is_file()
    assert "城市群" in (directory / case.problem_file).read_text(encoding="utf-8")
    assert case.structural_expectations.minimum_figures == 4


def test_selection_supports_single_tag_smoke_all_and_full() -> None:
    cases = load_cases(CASES_ROOT)

    assert select_cases(cases, case_id="forecasting_seasonal")[0] == "single"
    assert all("ode" in case.tags for case, _ in select_cases(cases, tag="ode")[1])
    assert all(case.smoke for case, _ in select_cases(cases, smoke=True)[1])
    assert select_cases(cases, all_cases=True)[0] == "all"
    assert select_cases(cases, full=True)[0] == "full"
    with pytest.raises(ValueError, match="select exactly one"):
        select_cases(cases, smoke=True, full=True)


def test_structural_contract_rejects_path_escape() -> None:
    with pytest.raises(ValueError, match="workspace-relative path"):
        StructuralExpectations(
            required_files=["../outside.txt"],
            minimum_figures=0,
            minimum_tables=0,
            minimum_pdf_pages=1,
            maximum_pdf_pages=1,
        )


def test_recorded_process_persists_unicode_stdout_and_exit_code(tmp_path: Path) -> None:
    root = tmp_path / "中文 路径"
    record = _run("print('真实执行：通过')", root)

    assert record["exit_code"] == 0
    assert "真实执行" in (root / "logs" / "stdout.log").read_text(encoding="utf-8")
    assert read_json(root / "logs" / "record.json")["status"] == "passed"


def test_recorded_process_persists_nonzero_exit(tmp_path: Path) -> None:
    root = tmp_path / "nonzero"
    record = _run("import sys; print('boom', file=sys.stderr); raise SystemExit(7)", root)

    assert record["exit_code"] == 7
    assert record["status"] == "failed"
    assert "boom" in (root / "logs" / "stderr.log").read_text(encoding="utf-8")


def _pid_is_alive(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def test_timeout_kills_spawned_process_tree(tmp_path: Path) -> None:
    root = tmp_path / "timeout"
    script = "import pathlib,subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); pathlib.Path('child.pid').write_text(str(p.pid)); time.sleep(60)"
    record = _run(script, root, timeout=0.5)
    child_pid = int((root / "child.pid").read_text())

    assert record["timed_out"] is True
    assert record["exit_code"] != 0
    assert not _pid_is_alive(child_pid)


def test_numeric_validator_accepts_ranges_and_rejects_tampering(tmp_path: Path) -> None:
    case, _ = load_cases(CASES_ROOT)["forecasting_seasonal"]
    (tmp_path / "input").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "input" / "data.csv").write_text("x\n1\n", encoding="utf-8")
    atomic_json(tmp_path / "outputs" / "metrics.json", {"metrics": {"holdout_rmse": 0.5, "next_period_forecast": 44, "train_rows": 48}})
    assert validate_numeric(tmp_path, case.model_dump(mode="json"))["status"] == "passed"

    atomic_json(tmp_path / "outputs" / "metrics.json", {"metrics": {"holdout_rmse": 99, "next_period_forecast": 44, "train_rows": 48}})
    report = validate_numeric(tmp_path, case.model_dump(mode="json"))
    assert report["status"] == "failed"
    assert any(not check["passed"] for check in report["checks"])


def test_optimization_preserves_product_column_not_dataframe_method() -> None:
    frame = pd.DataFrame(
        {"product": ["A", "B", "C"], "profit": [38, 31, 44], "labor": [2, 1, 3], "material": [1, 2, 2], "capacity": [40, 45, 30]}
    )
    metrics, detail = _optimization(frame)

    assert detail["product"].tolist() == ["A", "B", "C"]
    assert metrics["objective_value"] == pytest.approx(1800)


def _attempt(root: Path, value: float) -> Path:
    (root / "outputs").mkdir(parents=True)
    atomic_json(root / "outputs" / "metrics.json", {"metrics": {"value": value}})
    pd.DataFrame({"x": [1, 2], "y": [value, value + 1]}).to_csv(root / "outputs" / "details.csv", index=False)
    return root


def test_reproduction_comparison_uses_numeric_tolerance(tmp_path: Path) -> None:
    first = _attempt(tmp_path / "a", 1.0)
    second = _attempt(tmp_path / "b", 1.0 + 1e-10)
    third = _attempt(tmp_path / "c", 1.1)

    assert compare_attempts([first, second], 1e-8).status == "passed"
    assert compare_attempts([first, third], 1e-8).status == "failed"


def test_report_comparison_detects_status_and_score_regression(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    atomic_json(first, {"cases": [{"case_id": "one", "status": "passed", "quality_score": 100}]})
    atomic_json(second, {"cases": [{"case_id": "one", "status": "failed", "quality_score": 80}]})

    comparison = compare_suite_reports(first, second)
    assert comparison["status"] == "regression"
    assert len(comparison["regressions"]) == 2


def test_json_report_round_trip_preserves_chinese_and_backslashes(tmp_path: Path) -> None:
    target = tmp_path / "报告.json"
    atomic_json(target, {"title": "中文", "path": r"D:\临时\文件"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"title": "中文", "path": r"D:\临时\文件"}


def test_intentional_failure_case_is_diagnostic(tmp_path: Path) -> None:
    case, directory = load_cases(CASES_ROOT)["intentional_failure_diagnostic"]
    attempt = tmp_path / "负向案例" / "attempt-1"
    metrics, failed = run_attempt(case, directory, attempt, tmp_path / "review-copy", REPO_ROOT)

    assert failed
    assert metrics[0].id == "intentional_failure_observed"
    assert (attempt / "diagnostic.json").is_file()
    assert read_json(attempt / "attempt_state.json")["current_state"] == "FAILED"
    assert read_json(attempt / "logs" / "solver_execution.json")["exit_code"] != 0
