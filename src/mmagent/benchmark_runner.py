"""Unified executable benchmark runner and regression report comparison."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from mmagent.artifacts import atomic_json, atomic_text, read_json, sha256_file
from mmagent.benchmark_evaluator import evaluate_attempt
from mmagent.benchmark_models import BenchmarkCase, CaseReport, MetricResult, SuiteReport
from mmagent.benchmark_process import run_recorded_process
from mmagent.environment import inspect_git
from mmagent.pdf import PdfPipelineError, compile_paper, tex_tool_versions, validate_pdf


class BenchmarkRunError(RuntimeError):
    """A benchmark attempt failed after diagnostic evidence was persisted."""


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _run_id() -> str:
    return "benchmark-" + datetime.now(UTC).strftime("%Y%m%dt%H%M%S%fZ").lower()


def load_cases(cases_root: Path) -> dict[str, tuple[BenchmarkCase, Path]]:
    loaded: dict[str, tuple[BenchmarkCase, Path]] = {}
    for path in sorted(cases_root.resolve().glob("*/case.yaml")):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        case = BenchmarkCase.model_validate(value)
        if case.id in loaded:
            raise ValueError(f"duplicate benchmark case id: {case.id}")
        if not (path.parent / case.problem_file).is_file():
            raise ValueError(f"{case.id}: problem file is missing")
        if not (path.parent / case.data_generator).is_file():
            raise ValueError(f"{case.id}: data generator is missing")
        loaded[case.id] = (case, path.parent)
    if not loaded:
        raise ValueError(f"no executable benchmark cases found under {cases_root}")
    return loaded


def select_cases(
    loaded: dict[str, tuple[BenchmarkCase, Path]],
    *,
    case_id: str | None = None,
    tag: str | None = None,
    all_cases: bool = False,
    smoke: bool = False,
    full: bool = False,
) -> tuple[str, list[tuple[BenchmarkCase, Path]]]:
    requested = sum(value is not None and value is not False for value in (case_id, tag, all_cases, smoke, full))
    if requested != 1:
        raise ValueError("select exactly one of case_id, tag, smoke, or full")
    if case_id is not None:
        if case_id not in loaded:
            raise ValueError(f"unknown benchmark case: {case_id}")
        return "single", [loaded[case_id]]
    if tag is not None:
        selected = [value for value in loaded.values() if tag in value[0].tags]
        if not selected:
            raise ValueError(f"no benchmark cases match tag: {tag}")
        return "tag", selected
    if smoke:
        return "smoke", [value for value in loaded.values() if value[0].smoke and value[0].expected_outcome == "passed"]
    if all_cases:
        return "all", [value for value in loaded.values() if value[0].expected_outcome == "passed"]
    return "full", [value for value in loaded.values() if value[0].expected_outcome == "passed"]


def _dependencies() -> dict[str, str]:
    names = ("mathmodelagent", "numpy", "pandas", "scipy", "matplotlib", "pypdf", "PyMuPDF", "Pillow", "PyYAML")
    values: dict[str, str] = {}
    for name in names:
        try:
            values[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            values[name] = "not_installed"
    return values


def _tree_hash(root: Path, directories: Iterable[str]) -> str:
    digest = hashlib.sha256()
    paths = [path for name in directories for path in (root / name).rglob("*") if path.is_file()]
    for path in sorted(set(paths)):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _inventory_hashes(root: Path, *, exclude_review: bool = False) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if exclude_review and relative.startswith("review/"):
            continue
        values[relative] = sha256_file(path)
    return values


def _controlled_environment(repo_root: Path, seed: int) -> dict[str, str]:
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(repo_root / "src") + (os.pathsep + existing if existing else "")
    environment.update(
        {
            "PYTHONHASHSEED": str(seed),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "MPLBACKEND": "Agg",
            "MMAGENT_NETWORK_DISABLED": "1",
        }
    )
    return environment


def _write_state(root: Path, history: list[str], current: str, failure: str | None = None) -> None:
    if not history or history[-1] != current:
        history.append(current)
    atomic_json(root / "attempt_state.json", {"schema_version": "1.0", "history": history, "current_state": current, "failure_reason": failure})


def _run_step(root: Path, name: str, command: list[str], timeout: float, environment: dict[str, str]) -> dict[str, object]:
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return run_recorded_process(
        command,
        cwd=root,
        timeout_seconds=timeout,
        environment=environment,
        record_path=logs / f"{name}_execution.json",
        stdout_path=logs / f"{name}_stdout.log",
        stderr_path=logs / f"{name}_stderr.log",
    )


def _prepare_attempt(case: BenchmarkCase, case_dir: Path, attempt: Path) -> None:
    attempt.mkdir(parents=True, exist_ok=False)
    shutil.copy2(case_dir / case.problem_file, attempt / "problem.md")
    shutil.copy2(case_dir / case.data_generator, attempt / "generate_data.py")
    atomic_json(attempt / "case.json", case.model_dump(mode="json"))


def _run_reviewer(attempt: Path, snapshot: Path, repo_root: Path, case: BenchmarkCase) -> None:
    before = _inventory_hashes(attempt, exclude_review=True)
    shutil.copytree(attempt, snapshot)
    environment = _controlled_environment(repo_root, case.random_seed)
    record = _run_step(
        snapshot,
        "reviewer",
        [sys.executable, "-m", "mmagent.benchmark_worker", "review", "--run-root", "."],
        case.timeout_seconds,
        environment,
    )
    report_source = snapshot / "review" / "review_report.json"
    (attempt / "review").mkdir(exist_ok=True)
    if report_source.is_file():
        shutil.copy2(report_source, attempt / "review" / "review_report.json")
    after = _inventory_hashes(attempt, exclude_review=True)
    atomic_json(
        attempt / "review" / "isolation.json",
        {
            "schema_version": "1.0",
            "strategy": "separate_process_with_copied_persisted_artifacts",
            "snapshot_path": str(snapshot),
            "reviewer_exit_code": record["exit_code"],
            "main_workspace_unchanged": before == after,
        },
    )
    if record["exit_code"] != 0:
        raise BenchmarkRunError("isolated reviewer reported a failure")


def run_attempt(case: BenchmarkCase, case_dir: Path, attempt: Path, snapshot: Path, repo_root: Path) -> tuple[list[MetricResult], bool]:
    _prepare_attempt(case, case_dir, attempt)
    history: list[str] = []
    _write_state(attempt, history, "CREATED")
    environment = _controlled_environment(repo_root, case.random_seed)
    failed = False
    failure_stage = ""
    failure_message = ""
    try:
        generator = _run_step(attempt, "generator", [sys.executable, "generate_data.py", "--run-root", ".", "--seed", str(case.random_seed)], case.timeout_seconds, environment)
        if generator["exit_code"] != 0:
            raise BenchmarkRunError("data generator failed")
        _write_state(attempt, history, "DATA_GENERATED")
        solver = _run_step(attempt, "solver", [sys.executable, "-m", "mmagent.benchmark_worker", "solve", "--run-root", "."], case.timeout_seconds, environment)
        if solver["exit_code"] != 0:
            raise BenchmarkRunError("solver failed")
        _write_state(attempt, history, "CODE_EXECUTED")
        validator = _run_step(attempt, "validator", [sys.executable, "-m", "mmagent.benchmark_worker", "validate", "--run-root", "."], case.timeout_seconds, environment)
        if validator["exit_code"] != 0:
            raise BenchmarkRunError("independent numeric validation failed")
        _write_state(attempt, history, "NUMERIC_VALIDATED")
        execution = compile_paper(attempt, timeout_seconds=case.timeout_seconds)
        if execution["exit_code"] != 0:
            raise BenchmarkRunError("LaTeX compilation failed")
        _write_state(attempt, history, "PDF_COMPILED")
        validation = validate_pdf(attempt)
        if validation["status"] != "passed":
            raise BenchmarkRunError("PDF validation failed")
        _write_state(attempt, history, "PDF_VALIDATED")
        _run_reviewer(attempt, snapshot, repo_root, case)
        _write_state(attempt, history, "REVIEWED")
        _write_state(attempt, history, "COMPLETED")
    except Exception as exc:
        failed = True
        failure_stage = history[-1] if history else "CREATED"
        failure_message = str(exc)
        _write_state(attempt, history, "FAILED", failure_message)
        atomic_json(
            attempt / "diagnostic.json",
            {
                "schema_version": "1.0",
                "case_id": case.id,
                "failed_after_stage": failure_stage,
                "error_type": type(exc).__name__,
                "message": failure_message,
                "logs": [path.relative_to(attempt).as_posix() for path in sorted((attempt / "logs").glob("*")) if path.is_file()],
            },
        )
    metrics, _ = evaluate_attempt(attempt, case)
    if failed and case.expected_outcome == "failed":
        metrics = [
            MetricResult(id="intentional_failure_observed", tier="hard", status="passed", message=failure_message, evidence=["diagnostic.json", "attempt_state.json"]),
            MetricResult(id="failure_is_diagnostic", tier="quality", status="passed", message=f"failure persisted after {failure_stage}", evidence=["diagnostic.json"], points_awarded=100, points_available=100),
        ]
    return metrics, failed


def _numeric_values(value: Any, prefix: str = "") -> dict[str, float]:
    values: dict[str, float] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            values.update(_numeric_values(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        values[prefix] = float(value)
    return values


def compare_attempts(attempts: list[Path], tolerance: float) -> MetricResult:
    if len(attempts) < 2:
        return MetricResult(id="reproduction_consistent", tier="warning", status="not_run", message="this benchmark mode ran one attempt; full mode runs repeats", evidence=[])
    first_metrics = _numeric_values(read_json(attempts[0] / "outputs" / "metrics.json"))
    first_detail = pd.read_csv(attempts[0] / "outputs" / "details.csv", encoding="utf-8-sig")
    failures: list[str] = []
    for attempt in attempts[1:]:
        other_metrics = _numeric_values(read_json(attempt / "outputs" / "metrics.json"))
        if set(first_metrics) != set(other_metrics):
            failures.append(f"{attempt.name}: metric keys differ")
        else:
            for key in first_metrics:
                if not np.isclose(first_metrics[key], other_metrics[key], rtol=tolerance, atol=tolerance):
                    failures.append(f"{attempt.name}: {key} differs")
        other_detail = pd.read_csv(attempt / "outputs" / "details.csv", encoding="utf-8-sig")
        if list(first_detail.columns) != list(other_detail.columns) or first_detail.shape != other_detail.shape:
            failures.append(f"{attempt.name}: detail table structure differs")
        else:
            numeric_columns = first_detail.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) and not np.allclose(first_detail[numeric_columns], other_detail[numeric_columns], rtol=tolerance, atol=tolerance, equal_nan=True):
                failures.append(f"{attempt.name}: detail numeric values differ")
    return _reproduction_metric(not failures, failures, attempts)


def _reproduction_metric(passed: bool, failures: list[str], attempts: list[Path]) -> MetricResult:
    return MetricResult(
        id="reproduction_consistent",
        tier="hard",
        status="passed" if passed else "failed",
        message="numeric metrics and detail tables agree within tolerance" if passed else "; ".join(failures),
        evidence=[f"{path.name}/outputs/metrics.json" for path in attempts],
    )


def _case_report(case: BenchmarkCase, case_root: Path, attempts: list[Path], metrics: list[MetricResult], failures: list[bool], started: str, duration: float) -> CaseReport:
    hard_failures = [item.id for item in metrics if item.tier == "hard" and item.status != "passed"]
    quality = [item for item in metrics if item.tier == "quality" and item.points_available]
    available = sum(float(item.points_available or 0) for item in quality)
    awarded = sum(float(item.points_awarded or 0) for item in quality)
    score = 0.0 if not available else 100 * awarded / available
    if case.expected_outcome == "failed":
        status = "expected_failure_observed" if all(failures) and all((path / "diagnostic.json").is_file() for path in attempts) else "unexpected_pass"
    else:
        status = "failed" if hard_failures or any(failures) else "passed"
    return CaseReport(
        case_id=case.id,
        title=case.title,
        expected_outcome=case.expected_outcome,
        status=status,
        started_at=started,
        finished_at=_timestamp(),
        duration_seconds=round(duration, 6),
        attempts=[str(path) for path in attempts],
        metrics=metrics,
        quality_score=round(score, 2),
        hard_failures=hard_failures,
        warnings=[item.id for item in metrics if item.tier == "warning"],
        artifact_root=str(case_root),
        diagnostic_report=str(attempts[0] / "diagnostic.json") if failures and (attempts[0] / "diagnostic.json").is_file() else None,
    )


def run_suite(
    repo_root: Path,
    selected: list[tuple[BenchmarkCase, Path]],
    *,
    mode: str,
    output_root: Path,
    repetitions: int,
) -> tuple[SuiteReport, Path]:
    root = repo_root.resolve()
    suite_root = output_root.resolve() / _run_id()
    suite_root.mkdir(parents=True, exist_ok=False)
    started_at = _timestamp()
    timer = perf_counter()
    git = inspect_git(root)
    configuration = {"mode": mode, "repetitions": repetitions, "case_ids": [case.id for case, _ in selected], "output_root": str(output_root.resolve())}
    environment = {"platform": platform.platform(), "python_executable": sys.executable, "python_version": platform.python_version(), "dependencies": _dependencies(), "tex_tools": tex_tool_versions()}
    code_version = {"git": git, "source_tree_sha256": _tree_hash(root, ("src/mmagent", "benchmarks/cases", "benchmarks/runtime"))}
    atomic_json(suite_root / "configuration.json", configuration)
    atomic_json(suite_root / "environment.json", environment)
    atomic_json(suite_root / "code_version.json", code_version)
    reports: list[CaseReport] = []
    for case, case_dir in selected:
        case_started = _timestamp()
        case_timer = perf_counter()
        case_root = suite_root / "cases" / case.id
        case_root.mkdir(parents=True)
        attempt_paths: list[Path] = []
        failures: list[bool] = []
        aggregate: list[MetricResult] = []
        for index in range(1, repetitions + 1):
            attempt = case_root / f"attempt-{index}"
            snapshot = case_root / f"review-snapshot-{index}"
            metrics, failed = run_attempt(case, case_dir, attempt, snapshot, root)
            for metric in metrics:
                metric.id = f"attempt_{index}.{metric.id}"
            aggregate.extend(metrics)
            attempt_paths.append(attempt)
            failures.append(failed)
        if case.expected_outcome == "passed" and not any(failures):
            tolerance = max([item.absolute_tolerance for item in case.numeric_expectations] or [1e-8])
            aggregate.append(compare_attempts(attempt_paths, tolerance))
        report = _case_report(case, case_root, attempt_paths, aggregate, failures, case_started, perf_counter() - case_timer)
        atomic_json(case_root / "case_report.json", report.model_dump(mode="json"))
        reports.append(report)
    suite_failed = any(report.status in {"failed", "unexpected_pass"} for report in reports)
    suite = SuiteReport(
        run_id=suite_root.name,
        mode=mode,
        status="failed" if suite_failed else "passed",
        started_at=started_at,
        finished_at=_timestamp(),
        duration_seconds=round(perf_counter() - timer, 6),
        configuration=configuration,
        code_version=code_version,
        environment=environment,
        cases=reports,
        totals={
            "cases": len(reports),
            "passed": sum(report.status == "passed" for report in reports),
            "failed": sum(report.status == "failed" for report in reports),
            "expected_failure_observed": sum(report.status == "expected_failure_observed" for report in reports),
            "unexpected_pass": sum(report.status == "unexpected_pass" for report in reports),
        },
    )
    atomic_json(suite_root / "summary.json", suite.model_dump(mode="json"))
    atomic_text(suite_root / "summary.md", suite_markdown(suite))
    return suite, suite_root


def suite_markdown(report: SuiteReport) -> str:
    lines = [
        f"# Benchmark {report.run_id}",
        "",
        f"- Status: **{report.status}**",
        f"- Mode: `{report.mode}`",
        f"- Duration: {report.duration_seconds:.2f} seconds",
        f"- Source tree: `{report.code_version['source_tree_sha256']}`",
        "",
        "| Case | Result | Score | Duration (s) | Hard failures |",
        "|---|---:|---:|---:|---|",
    ]
    for case in report.cases:
        lines.append(f"| {case.case_id} | {case.status} | {case.quality_score:.1f} | {case.duration_seconds:.2f} | {', '.join(case.hard_failures) or '-'} |")
    lines.extend(["", "## Artifacts", "", "Each case directory contains attempts, complete logs, machine-readable metrics, PDF previews, reviewer snapshots, and diagnostics for failures.", ""])
    return "\n".join(lines)


def compare_suite_reports(first_path: Path, second_path: Path) -> dict[str, Any]:
    first = read_json(first_path)
    second = read_json(second_path)
    first_cases = {str(item["case_id"]): item for item in first.get("cases", [])}
    second_cases = {str(item["case_id"]): item for item in second.get("cases", [])}
    rows: list[dict[str, Any]] = []
    regressions: list[str] = []
    for case_id in sorted(set(first_cases) | set(second_cases)):
        left, right = first_cases.get(case_id), second_cases.get(case_id)
        row = {
            "case_id": case_id,
            "first_status": None if left is None else left.get("status"),
            "second_status": None if right is None else right.get("status"),
            "first_score": None if left is None else left.get("quality_score"),
            "second_score": None if right is None else right.get("quality_score"),
        }
        if left is not None and right is not None:
            row["score_delta"] = float(right.get("quality_score", 0)) - float(left.get("quality_score", 0))
            if left.get("status") == "passed" and right.get("status") != "passed":
                regressions.append(f"{case_id}: status regressed from passed to {right.get('status')}")
            if row["score_delta"] < -1e-9:
                regressions.append(f"{case_id}: quality score decreased by {abs(row['score_delta']):.2f}")
        elif left is not None:
            regressions.append(f"{case_id}: case disappeared")
        rows.append(row)
    return {"schema_version": "1.0", "status": "regression" if regressions else "no_regression", "first": str(first_path.resolve()), "second": str(second_path.resolve()), "cases": rows, "regressions": regressions}
