"""Real Python-to-PDF core pipeline for the curve-fitting fixture."""

from __future__ import annotations

import importlib.metadata
import math
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from mmagent import __version__
from mmagent.artifacts import atomic_json, file_records, files_under, read_json, sha256_file
from mmagent.core_models import CoreStage, advance_core_stage, mark_core_failed
from mmagent.demo_assets import DEMO_RANDOM_SEED, prepare_curve_fitting_workspace
from mmagent.execution import execute_python_script
from mmagent.latex import render_curve_fitting_paper
from mmagent.pdf import PdfPipelineError, compile_paper, tex_tool_versions, validate_pdf
from mmagent.plotting import generate_curve_fitting_figures
from mmagent.tables import generate_result_tables


class CorePipelineError(RuntimeError):
    """A core stage failed after evidence was written."""


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _new_run_id() -> str:
    return "run-" + datetime.now(UTC).strftime("%Y%m%dt%H%M%S%fZ").lower()


def _dependency_versions() -> dict[str, str]:
    names = ("mathmodelagent", "numpy", "pandas", "scipy", "matplotlib", "pypdf", "PyMuPDF")
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def _persist_manifest(run_root: Path, manifest: dict[str, Any]) -> None:
    manifest["current_state"] = manifest["state_history"][-1]
    atomic_json(run_root / "manifest.json", manifest)


def _advance(run_root: Path, manifest: dict[str, Any], target: CoreStage) -> None:
    advance_core_stage(manifest["state_history"], target)
    _persist_manifest(run_root, manifest)


def _copy_base_assets(workspace: Path, run_root: Path) -> None:
    for relative in (Path("input/problem.md"), Path("input/data.csv"), Path("src/solve.py"), Path("src/validate.py")):
        source = workspace / relative
        target = run_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    package_root = Path(__file__).resolve().parent
    for name in ("artifacts.py", "core_models.py", "core_pipeline.py", "execution.py", "latex.py", "pdf.py", "plotting.py", "tables.py"):
        target = run_root / "src" / "pipeline" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package_root / name, target)


def _records_for_suffixes(root: Path, paths: Iterable[Path], suffixes: set[str]) -> list[dict[str, Any]]:
    return file_records(root, [path for path in paths if path.suffix.casefold() in suffixes])


def _refresh_manifest_inventory(run_root: Path, manifest: dict[str, Any]) -> None:
    manifest["inputs"] = file_records(run_root, [run_root / "input/problem.md", run_root / "input/data.csv"])
    manifest["python_sources"] = file_records(run_root, [path for path in (run_root / "src").rglob("*.py") if path.is_file()])
    output_files = files_under(run_root, "outputs")
    figure_files = files_under(run_root, "figures")
    table_files = files_under(run_root, "tables")
    paper_files = files_under(run_root, "paper")
    manifest["numeric_outputs"] = _records_for_suffixes(run_root, output_files, {".json", ".csv"})
    manifest["figures"] = _records_for_suffixes(run_root, figure_files, {".png", ".svg", ".pdf"})
    manifest["tables"] = _records_for_suffixes(run_root, table_files, {".csv", ".tex"})
    manifest["latex_sources"] = _records_for_suffixes(run_root, paper_files, {".tex"})
    manifest["pdf_files"] = _records_for_suffixes(run_root, paper_files, {".pdf"})
    manifest["logs"] = file_records(run_root, files_under(run_root, "logs"))
    report_paths = [
        run_root / name
        for name in ("validation_report.json", "reproducibility_report.json", "human_approval.json", "paper/report_manifest.json")
        if (run_root / name).is_file()
    ]
    manifest["reports"] = file_records(run_root, report_paths)


def execute_curve_fitting_run(workspace: Path, *, timeout_seconds: float = 120) -> Path:
    workspace_root = prepare_curve_fitting_workspace(workspace)
    run_root = workspace_root / "runs" / _new_run_id()
    run_root.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "schema_version": "2.0",
        "project_version": __version__,
        "run_id": run_root.name,
        "created_at": _timestamp(),
        "operating_system": platform.platform(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "dependencies": _dependency_versions(),
        "random_seed": DEMO_RANDOM_SEED,
        "working_directory": ".",
        "state_history": [],
        "status": "running",
        "validation": {},
        "failure_reason": None,
        "human_approval_status": "pending",
    }
    try:
        _advance(run_root, manifest, CoreStage.CREATED)
        _copy_base_assets(workspace_root, run_root)
        _advance(run_root, manifest, CoreStage.INPUT_READY)
        _advance(run_root, manifest, CoreStage.CODE_READY)

        solver = execute_python_script(
            run_root,
            timeout_seconds=timeout_seconds,
            random_seed=DEMO_RANDOM_SEED,
        )
        manifest["execution"] = solver.record
        _advance(run_root, manifest, CoreStage.CODE_EXECUTED)

        validator = execute_python_script(
            run_root,
            script=Path("src/validate.py"),
            input_files=(Path("input/data.csv"), Path("outputs/metrics.json"), Path("outputs/predictions.csv")),
            timeout_seconds=timeout_seconds,
            random_seed=DEMO_RANDOM_SEED,
            log_prefix="validator",
        )
        result_validation = read_json(run_root / "outputs" / "validation.json")
        if result_validation.get("status") != "passed":
            raise CorePipelineError("independent result validation failed")
        manifest["validator_execution"] = validator.record
        manifest["validation"]["numeric_results"] = result_validation
        _advance(run_root, manifest, CoreStage.RESULTS_VALIDATED)

        figure_paths, selected_font = generate_curve_fitting_figures(run_root)
        if len(figure_paths) != 4 or any(not path.is_file() or path.stat().st_size == 0 for path in figure_paths):
            raise CorePipelineError("required PNG and SVG curve-fitting figures were not generated")
        manifest["selected_cjk_font"] = selected_font
        _advance(run_root, manifest, CoreStage.FIGURES_GENERATED)

        table_paths = generate_result_tables(run_root)
        if len(table_paths) != 4 or any(not path.is_file() or path.stat().st_size == 0 for path in table_paths):
            raise CorePipelineError("required CSV and LaTeX tables were not generated")
        _advance(run_root, manifest, CoreStage.TABLES_GENERATED)

        paper_source = render_curve_fitting_paper(run_root)
        if not paper_source.is_file() or paper_source.stat().st_size == 0:
            raise CorePipelineError("paper/main.tex was not generated")
        _advance(run_root, manifest, CoreStage.PAPER_DRAFTED)

        latex_execution = compile_paper(run_root)
        manifest["latex_execution"] = latex_execution
        _advance(run_root, manifest, CoreStage.PDF_COMPILED)

        pdf_validation = validate_pdf(run_root)
        manifest["validation"]["pdf"] = pdf_validation
        _advance(run_root, manifest, CoreStage.PDF_VALIDATED)
        manifest["tex_tools"] = tex_tool_versions()
        manifest["execution_commands"] = {
            "python": solver.record["command"],
            "validator": validator.record["command"],
            "latex": latex_execution["command"],
        }
        manifest["exit_codes"] = {
            "python": solver.record["exit_code"],
            "validator": validator.record["exit_code"],
            "latex": latex_execution["exit_code"],
        }
        manifest["status"] = "passed"
        _refresh_manifest_inventory(run_root, manifest)
        _persist_manifest(run_root, manifest)
        atomic_json(
            run_root / "human_approval.json",
            {
                "schema_version": "1.0",
                "status": "pending",
                "required_for": "FINAL",
                "message": "Structural checks passed; page-by-page visual acceptance and final approval remain human gates.",
            },
        )
        _refresh_manifest_inventory(run_root, manifest)
        _persist_manifest(run_root, manifest)
        atomic_json(
            workspace_root / "latest_run.json",
            {"run_id": run_root.name, "state": CoreStage.PDF_VALIDATED.value},
        )
        return run_root
    except Exception as exc:
        mark_core_failed(manifest["state_history"])
        manifest["status"] = "failed"
        manifest["failure_reason"] = str(exc)
        _refresh_manifest_inventory(run_root, manifest)
        _persist_manifest(run_root, manifest)
        if isinstance(exc, CorePipelineError):
            raise
        raise CorePipelineError(str(exc)) from exc


def _numeric_mapping_close(first: dict[str, Any], second: dict[str, Any], tolerance: float) -> dict[str, bool]:
    keys = sorted(set(first) | set(second))
    return {
        key: key in first
        and key in second
        and math.isclose(float(first[key]), float(second[key]), rel_tol=tolerance, abs_tol=tolerance)
        for key in keys
    }


def _essential_generated_set(root: Path) -> set[str]:
    essential_roots = ("outputs", "figures", "tables", "paper")
    ignored_suffixes = {".aux", ".fdb_latexmk", ".fls", ".log", ".out", ".xdv"}
    return {
        path.relative_to(root).as_posix()
        for path in files_under(root, *essential_roots)
        if path.suffix.casefold() not in ignored_suffixes and "/preview/" not in path.as_posix().replace("\\", "/")
    }


def compare_runs(first_run: Path, second_run: Path, *, tolerance: float = 1e-10) -> dict[str, Any]:
    first = first_run.resolve()
    second = second_run.resolve()
    first_result = read_json(first / "outputs" / "metrics.json")
    second_result = read_json(second / "outputs" / "metrics.json")
    parameter_checks = _numeric_mapping_close(first_result["parameters"], second_result["parameters"], tolerance)
    metric_checks = _numeric_mapping_close(first_result["metrics"], second_result["metrics"], tolerance)
    first_predictions = pd.read_csv(first / "outputs" / "predictions.csv")
    second_predictions = pd.read_csv(second / "outputs" / "predictions.csv")
    predictions_equal = list(first_predictions.columns) == list(second_predictions.columns) and np.allclose(
        first_predictions.to_numpy(dtype=float),
        second_predictions.to_numpy(dtype=float),
        rtol=tolerance,
        atol=tolerance,
    )
    first_figure_data = pd.read_csv(first / "outputs" / "figure_data.csv")
    second_figure_data = pd.read_csv(second / "outputs" / "figure_data.csv")
    figure_data_equal = list(first_figure_data.columns) == list(second_figure_data.columns) and np.allclose(
        first_figure_data.to_numpy(dtype=float),
        second_figure_data.to_numpy(dtype=float),
        rtol=tolerance,
        atol=tolerance,
    )
    input_hashes_equal = all(
        sha256_file(first / relative) == sha256_file(second / relative)
        for relative in (Path("input/problem.md"), Path("input/data.csv"))
    )
    first_sources = {path.relative_to(first).as_posix(): sha256_file(path) for path in (first / "src").rglob("*.py")}
    second_sources = {path.relative_to(second).as_posix(): sha256_file(path) for path in (second / "src").rglob("*.py")}
    source_hashes_equal = first_sources == second_sources
    generated_set_equal = _essential_generated_set(first) == _essential_generated_set(second)
    first_execution = read_json(first / "logs" / "execution.json")
    second_execution = read_json(second / "logs" / "execution.json")
    first_latex = read_json(first / "logs" / "latex_execution.json")
    second_latex = read_json(second / "logs" / "latex_execution.json")
    binary_comparison: dict[str, str] = {}
    for relative in (
        Path("figures/fit_curve.png"),
        Path("figures/fit_curve.svg"),
        Path("figures/residuals.png"),
        Path("figures/residuals.svg"),
        Path("paper/main.pdf"),
    ):
        identical = sha256_file(first / relative) == sha256_file(second / relative)
        binary_comparison[relative.as_posix()] = "binary_identical" if identical else "binary_diff_content_equivalent"
    conditions = {
        "input_hashes_equal": input_hashes_equal,
        "source_hashes_equal": source_hashes_equal,
        "parameters_within_tolerance": all(parameter_checks.values()),
        "metrics_within_tolerance": all(metric_checks.values()),
        "predictions_within_tolerance": bool(predictions_equal),
        "figure_data_within_tolerance": bool(figure_data_equal),
        "generated_file_set_equal": generated_set_equal,
        "python_exit_codes_zero": first_execution["exit_code"] == second_execution["exit_code"] == 0,
        "latex_exit_codes_zero": first_latex["exit_code"] == second_latex["exit_code"] == 0,
        "both_pdfs_valid": read_json(first / "validation_report.json")["status"] == read_json(second / "validation_report.json")["status"] == "passed",
    }
    return {
        "schema_version": "1.0",
        "checked_at": _timestamp(),
        "source_run_id": first.name,
        "reproduction_run_id": second.name,
        "float_tolerance": tolerance,
        "status": "passed" if all(conditions.values()) else "failed",
        "classification": "numerically_reproducible" if all(conditions.values()) else "not_reproducible",
        "conditions": conditions,
        "parameter_checks": parameter_checks,
        "metric_checks": metric_checks,
        "binary_comparison": binary_comparison,
        "note": "Binary differences are not failures when numerical results and plot source data agree and both PDFs validate.",
    }


def reproduce_curve_fitting(
    workspace: Path,
    *,
    source_run_id: str | None = None,
    timeout_seconds: float = 120,
) -> tuple[Path, dict[str, Any]]:
    root = prepare_curve_fitting_workspace(workspace)
    runs = root / "runs"
    candidates = sorted(path for path in runs.iterdir() if path.is_dir()) if runs.is_dir() else []
    if source_run_id is None:
        if not candidates:
            raise CorePipelineError("no source run exists to reproduce")
        source = candidates[-1]
    else:
        source = runs / source_run_id
    if not source.is_dir() or not (source / "manifest.json").is_file():
        raise CorePipelineError(f"source run does not exist: {source_run_id}")
    reproduction = execute_curve_fitting_run(root, timeout_seconds=timeout_seconds)
    report = compare_runs(source, reproduction)
    atomic_json(reproduction / "reproducibility_report.json", report)
    atomic_json(root / "reproducibility_report.json", report)
    manifest = read_json(reproduction / "manifest.json")
    if report["status"] != "passed":
        mark_core_failed(manifest["state_history"])
        manifest["status"] = "failed"
        manifest["failure_reason"] = "reproducibility validation failed"
        _persist_manifest(reproduction, manifest)
        raise CorePipelineError("reproducibility validation failed")
    _advance(reproduction, manifest, CoreStage.REPRODUCIBILITY_VALIDATED)
    _advance(reproduction, manifest, CoreStage.AWAITING_HUMAN_APPROVAL)
    manifest["human_approval_status"] = "pending"
    manifest["reproducibility"] = report
    _refresh_manifest_inventory(reproduction, manifest)
    _persist_manifest(reproduction, manifest)
    atomic_json(
        root / "latest_run.json",
        {
            "run_id": reproduction.name,
            "source_run_id": source.name,
            "state": CoreStage.AWAITING_HUMAN_APPROVAL.value,
        },
    )
    return reproduction, report


def run_curve_fitting_demo(workspace: Path, *, timeout_seconds: float = 120) -> dict[str, Any]:
    root = prepare_curve_fitting_workspace(workspace)
    first = execute_curve_fitting_run(root, timeout_seconds=timeout_seconds)
    second, report = reproduce_curve_fitting(root, source_run_id=first.name, timeout_seconds=timeout_seconds)
    return {
        "workspace": root,
        "first_run": first,
        "reproduction_run": second,
        "reproducibility": report,
        "state": CoreStage.AWAITING_HUMAN_APPROVAL.value,
    }


def core_status(workspace: Path) -> dict[str, Any]:
    root = workspace.expanduser().resolve()
    latest = read_json(root / "latest_run.json")
    manifest = read_json(root / "runs" / str(latest["run_id"]) / "manifest.json")
    return {"workspace": root, "latest": latest, "manifest": manifest}


def resolve_core_run(workspace: Path, run_id: str | None = None) -> Path:
    root = workspace.expanduser().resolve()
    selected = run_id
    if selected is None:
        selected = str(read_json(root / "latest_run.json")["run_id"])
    run = root / "runs" / selected
    if not run.is_dir() or not (run / "manifest.json").is_file():
        raise CorePipelineError(f"core run does not exist: {selected}")
    return run


def validate_core_run(workspace: Path, run_id: str | None = None) -> dict[str, Any]:
    run = resolve_core_run(workspace, run_id)
    manifest = read_json(run / "manifest.json")
    numeric = read_json(run / "outputs" / "validation.json")
    pdf_report = read_json(run / "validation_report.json")
    hash_checks: dict[str, bool] = {}
    for group in ("inputs", "python_sources", "numeric_outputs", "figures", "tables", "latex_sources", "pdf_files", "reports"):
        for record in manifest.get(group, []):
            relative = str(record["path"])
            path = run / relative
            hash_checks[relative] = path.is_file() and sha256_file(path) == record["sha256"]
    passed = (
        manifest.get("status") == "passed"
        and numeric.get("status") == "passed"
        and pdf_report.get("status") == "passed"
        and bool(hash_checks)
        and all(hash_checks.values())
        and manifest.get("current_state") not in {CoreStage.FAILED.value, CoreStage.FINAL.value}
    )
    return {
        "run_id": run.name,
        "status": "passed" if passed else "failed",
        "current_state": manifest.get("current_state"),
        "numeric_validation": numeric.get("status"),
        "pdf_validation": pdf_report.get("status"),
        "hash_checks": hash_checks,
    }


def recompile_core_run(workspace: Path, run_id: str | None = None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Recompile an existing drafted run and refresh its manifest evidence."""
    run = resolve_core_run(workspace, run_id)
    manifest = read_json(run / "manifest.json")
    history = manifest["state_history"]
    if history and history[-1] == CoreStage.FAILED.value:
        history.pop()
    current = CoreStage(history[-1]) if history else None
    allowed = {
        CoreStage.PAPER_DRAFTED,
        CoreStage.PDF_COMPILED,
        CoreStage.PDF_VALIDATED,
        CoreStage.REPRODUCIBILITY_VALIDATED,
        CoreStage.AWAITING_HUMAN_APPROVAL,
    }
    if current not in allowed:
        raise CorePipelineError(f"compile requires a drafted paper, found {current.value if current else 'empty'}")
    try:
        execution = compile_paper(run)
        manifest["latex_execution"] = execution
        if current is CoreStage.PAPER_DRAFTED:
            _advance(run, manifest, CoreStage.PDF_COMPILED)
        validation = validate_pdf(run)
        manifest.setdefault("validation", {})["pdf"] = validation
        if manifest["state_history"][-1] == CoreStage.PDF_COMPILED.value:
            _advance(run, manifest, CoreStage.PDF_VALIDATED)
    except PdfPipelineError as exc:
        mark_core_failed(manifest["state_history"])
        manifest["status"] = "failed"
        manifest["failure_reason"] = str(exc)
        if exc.record:
            manifest["latex_execution"] = exc.record
        _refresh_manifest_inventory(run, manifest)
        _persist_manifest(run, manifest)
        raise
    manifest["tex_tools"] = tex_tool_versions()
    manifest.setdefault("exit_codes", {})["latex"] = execution["exit_code"]
    manifest.setdefault("execution_commands", {})["latex"] = execution["command"]
    manifest["status"] = "passed"
    manifest["failure_reason"] = None
    _refresh_manifest_inventory(run, manifest)
    _persist_manifest(run, manifest)
    return run, execution, validation
