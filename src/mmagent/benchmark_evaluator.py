"""Evidence-based hard, quality, and warning metrics for benchmark attempts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz
import pandas as pd
from PIL import Image

from mmagent.artifacts import read_json
from mmagent.benchmark_models import BenchmarkCase, MetricResult


def _metric(identifier: str, tier: str, passed: bool, message: str, evidence: list[str], *, points: float | None = None) -> MetricResult:
    return MetricResult(
        id=identifier,
        tier=tier,
        status="passed" if passed else ("warning" if tier == "warning" else "failed"),
        message=message,
        evidence=evidence,
        points_awarded=points if passed else (0 if points is not None else None),
        points_available=points,
    )


def _valid_images(root: Path) -> tuple[list[Path], list[str]]:
    images = sorted((root / "figures").glob("*.png")) if (root / "figures").is_dir() else []
    errors: list[str] = []
    for path in images:
        try:
            with Image.open(path) as image:
                image.verify()
            if path.stat().st_size < 1024:
                errors.append(f"{path.name}: file is smaller than 1024 bytes")
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    return images, errors


def _valid_tables(root: Path) -> tuple[list[Path], list[str]]:
    csv_paths = sorted((root / "tables").glob("*.csv")) if (root / "tables").is_dir() else []
    errors: list[str] = []
    for path in csv_paths:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
            if frame.empty or len(frame.columns) == 0:
                errors.append(f"{path.name}: empty table")
            if not path.with_suffix(".tex").is_file() or path.with_suffix(".tex").stat().st_size == 0:
                errors.append(f"{path.name}: matching LaTeX table is missing")
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    return csv_paths, errors


def _pdf_findings(root: Path, case: BenchmarkCase) -> dict[str, Any]:
    pdf = root / "paper" / "main.pdf"
    findings: dict[str, Any] = {
        "valid": False,
        "page_count": 0,
        "blank_pages": [],
        "garbled_text": False,
        "required_text_missing": [],
        "missing_figure_sources": [],
        "overfull_boxes": 0,
    }
    if not pdf.is_file():
        return findings
    try:
        document = fitz.open(pdf)
        findings["page_count"] = document.page_count
        text = "\n".join(page.get_text() for page in document)
        for index, page in enumerate(document):
            if len(page.get_text().strip()) < 8 and not page.get_images(full=True) and not page.get_drawings():
                findings["blank_pages"].append(index + 1)
        document.close()
        findings["garbled_text"] = "�" in text or "\ufffd" in text
        findings["required_text_missing"] = [value for value in case.structural_expectations.required_pdf_text if value not in text]
        source = (root / "paper" / "main.tex").read_text(encoding="utf-8")
        for reference in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", source):
            if not (root / "paper" / reference).resolve().is_file():
                findings["missing_figure_sources"].append(reference)
        log = (root / "logs" / "xelatex.log").read_text(encoding="utf-8", errors="replace") if (root / "logs" / "xelatex.log").is_file() else ""
        findings["overfull_boxes"] = len(re.findall(r"Overfull \\[hv]box", log))
        findings["valid"] = pdf.stat().st_size > 1024 and pdf.read_bytes()[:5] == b"%PDF-" and findings["page_count"] > 0
    except Exception as exc:
        findings["error"] = str(exc)
    return findings


def evaluate_attempt(root: Path, case: BenchmarkCase) -> tuple[list[MetricResult], dict[str, Any]]:
    state = read_json(root / "attempt_state.json") if (root / "attempt_state.json").is_file() else {}
    solver = read_json(root / "logs" / "solver_execution.json") if (root / "logs" / "solver_execution.json").is_file() else {}
    oracle = read_json(root / "oracle_validation.json") if (root / "oracle_validation.json").is_file() else {}
    latex = read_json(root / "logs" / "latex_execution.json") if (root / "logs" / "latex_execution.json").is_file() else {}
    pdf_validation = read_json(root / "validation_report.json") if (root / "validation_report.json").is_file() else {}
    reviewer = read_json(root / "review" / "review_report.json") if (root / "review" / "review_report.json").is_file() else {}
    isolation = read_json(root / "review" / "isolation.json") if (root / "review" / "isolation.json").is_file() else {}
    images, image_errors = _valid_images(root)
    tables, table_errors = _valid_tables(root)
    pdf = _pdf_findings(root, case)
    required_missing = [relative for relative in case.structural_expectations.required_files if not (root / relative).is_file()]
    claims = read_json(root / "outputs" / "claims.json") if (root / "outputs" / "claims.json").is_file() else {}
    referenced_missing = [str(value) for value in claims.get("referenced_files", []) if not (root / str(value)).is_file()]
    hard = [
        _metric("task_completed", "hard", state.get("current_state") == "COMPLETED", f"terminal state={state.get('current_state', 'missing')}", ["attempt_state.json"]),
        _metric("python_really_executed", "hard", solver.get("exit_code") == 0 and bool(solver.get("pid")), f"solver exit={solver.get('exit_code')}; pid={solver.get('pid')}", ["logs/solver_execution.json"]),
        _metric("no_untraceable_results", "hard", solver.get("exit_code") == 0 and bool(claims.get("claims")), "numeric claims have a successful process record and structured evidence map", ["logs/solver_execution.json", "outputs/claims.json"]),
        _metric("independent_numeric_validation", "hard", oracle.get("status") == "passed", f"oracle status={oracle.get('status', 'missing')}", ["oracle_validation.json"]),
        _metric("figures_exist_and_valid", "hard", len(images) >= case.structural_expectations.minimum_figures and not image_errors, f"valid PNG figures={len(images)}; errors={image_errors}", ["figures/"]),
        _metric("tables_complete", "hard", len(tables) >= case.structural_expectations.minimum_tables and not table_errors, f"CSV/LaTeX table pairs={len(tables)}; errors={table_errors}", ["tables/"]),
        _metric("latex_compiled", "hard", latex.get("exit_code") == 0, f"latex exit={latex.get('exit_code')}", ["logs/latex_execution.json", "logs/xelatex.log"]),
        _metric("pdf_structurally_valid", "hard", pdf_validation.get("status") == "passed" and pdf["valid"], f"PDF validation={pdf_validation.get('status', 'missing')}", ["validation_report.json", "paper/main.pdf"]),
        _metric("referenced_files_exist", "hard", not required_missing and not referenced_missing, f"required missing={required_missing}; referenced missing={referenced_missing}", ["case.json", "outputs/claims.json"]),
        _metric("reviewer_isolated", "hard", reviewer.get("reviewer_context") == "isolated_snapshot_process" and reviewer.get("write_scope") == "review" and isolation.get("main_workspace_unchanged") is True, "review ran in a copied workspace and main artifact hashes were unchanged", ["review/review_report.json", "review/isolation.json"]),
        _metric("state_machine_terminal", "hard", state.get("history", [])[-1:] == ["COMPLETED"], f"history={state.get('history', [])}", ["attempt_state.json"]),
        _metric("diagnostic_report_on_failure", "hard", state.get("current_state") == "COMPLETED" or (root / "diagnostic.json").is_file(), "failed attempts must persist diagnostic.json", ["diagnostic.json"]),
    ]
    page_ok = case.structural_expectations.minimum_pdf_pages <= int(pdf["page_count"]) <= case.structural_expectations.maximum_pdf_pages
    quality = [
        _metric("pdf_page_range", "quality", page_ok, f"pages={pdf['page_count']}; allowed={case.structural_expectations.minimum_pdf_pages}-{case.structural_expectations.maximum_pdf_pages}", ["paper/main.pdf"], points=20),
        _metric("pdf_no_blank_pages", "quality", not pdf["blank_pages"], f"blank pages={pdf['blank_pages']}", ["paper/main.pdf"], points=20),
        _metric("pdf_no_missing_figures", "quality", not pdf["missing_figure_sources"], f"missing figure sources={pdf['missing_figure_sources']}", ["paper/main.tex"], points=20),
        _metric("pdf_text_not_garbled", "quality", not pdf["garbled_text"] and not pdf["required_text_missing"], f"required text missing={pdf['required_text_missing']}; replacement chars={pdf['garbled_text']}", ["paper/main.pdf"], points=20),
        _metric("latex_no_overflow", "quality", pdf["overfull_boxes"] == 0, f"overfull boxes={pdf['overfull_boxes']}", ["logs/xelatex.log"], points=20),
    ]
    warnings = [
        MetricResult(id="human_visual_acceptance", tier="warning", status="warning", message="automated rendering checks passed or failed above; final page-by-page human acceptance is not inferred", evidence=["paper/preview/"]),
    ]
    return hard + quality + warnings, pdf
