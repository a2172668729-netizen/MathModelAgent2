"""XeLaTeX compilation, PDF structure checks, and preview rendering."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import fitz
from pypdf import PdfReader

from mmagent.artifacts import atomic_json, atomic_text, sha256_file
from mmagent.environment import discover_tool


class PdfPipelineError(RuntimeError):
    def __init__(self, message: str, record: dict[str, Any]):
        super().__init__(message)
        self.record = record


def resolve_tool(name: str, *, project_root: Path | None = None) -> Path | None:
    """Backward-compatible path-only wrapper around auditable discovery."""
    return discover_tool(name, project_root=project_root).path


def tool_version(tool: Path, *arguments: str) -> dict[str, Any]:
    process = subprocess.run(
        [str(tool), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        shell=False,
    )
    output = (process.stdout + "\n" + process.stderr).strip()
    return {
        "path": str(tool),
        "exit_code": process.returncode,
        "version": output.splitlines()[0] if output else "",
        "output": output,
    }


def tex_tool_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {}
    for name, arguments in (("xelatex", ("--version",)), ("latexmk", ("-v",)), ("kpsewhich", ("--version",))):
        tool = resolve_tool(name)
        versions[name] = None if tool is None else tool_version(tool, *arguments)
    return versions


def compile_paper(run_root: Path, *, timeout_seconds: float = 300) -> dict[str, Any]:
    root = run_root.resolve()
    source = root / "paper" / "main.tex"
    if not source.is_file():
        raise ValueError("paper/main.tex does not exist")
    latexmk_discovery = discover_tool("latexmk", project_root=root)
    latexmk = latexmk_discovery.path
    if latexmk is None:
        raise PdfPipelineError(
            "latexmk is unavailable; " + "; ".join(latexmk_discovery.diagnostics),
            {"status": "blocked", "tool_discovery": list(latexmk_discovery.diagnostics)},
        )
    command = [
        str(latexmk),
        "-xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        source.name,
    ]
    started = datetime.now(UTC)
    timer = perf_counter()
    timed_out = False
    try:
        process = subprocess.run(
            command,
            cwd=source.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        exit_code: int | None = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except OSError as exc:
        exit_code = None
        stdout = ""
        stderr = str(exc)
    duration = perf_counter() - timer
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    latexmk_log = logs / "latexmk.log"
    atomic_text(latexmk_log, stdout + ("\n" if stdout and stderr else "") + stderr)
    engine_log = source.parent / "main.log"
    xelatex_log = logs / "xelatex.log"
    atomic_text(xelatex_log, engine_log.read_text(encoding="utf-8", errors="replace") if engine_log.is_file() else "")
    pdf = source.parent / "main.pdf"
    success = exit_code == 0 and pdf.is_file() and pdf.stat().st_size > 8 and pdf.read_bytes()[:5] == b"%PDF-"
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "command": command,
        "working_directory": "paper",
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 6),
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "status": "passed" if success else "failed",
        "source_path": "paper/main.tex",
        "pdf_path": "paper/main.pdf" if pdf.is_file() else None,
        "latexmk_log": "logs/latexmk.log",
        "xelatex_log": "logs/xelatex.log",
    }
    atomic_json(logs / "latex_execution.json", record)
    if not success:
        raise PdfPipelineError(
            "latexmk timed out" if timed_out else f"latexmk failed with exit code {exit_code}",
            record,
        )
    return record


def _page_with_figure(document: fitz.Document) -> int:
    for index, page in enumerate(document):
        text = page.get_text()
        if "原始数据与实际拟合曲线" in text or "残差分布" in text:
            return index
    return max(0, min(len(document) - 1, len(document) // 2))


def render_pdf_previews(pdf_path: Path, preview_dir: Path) -> dict[str, Any]:
    document = fitz.open(pdf_path)
    if document.page_count < 1:
        raise ValueError("PDF contains no pages")
    preview_dir.mkdir(parents=True, exist_ok=True)
    all_pages = preview_dir / "all"
    all_pages.mkdir(parents=True, exist_ok=True)
    zoom = fitz.Matrix(1.6, 1.6)
    rendered: list[str] = []
    for index in range(document.page_count):
        target = all_pages / f"page-{index + 1:03d}.png"
        document.load_page(index).get_pixmap(matrix=zoom, alpha=False).save(target)
        rendered.append(target.as_posix())
    figure_index = _page_with_figure(document)
    selections = {
        "first": 0,
        "main_figure": figure_index,
        "last": document.page_count - 1,
    }
    selected_paths: dict[str, str] = {}
    for name, index in selections.items():
        target = preview_dir / f"{name}-page-{index + 1:03d}.png"
        document.load_page(index).get_pixmap(matrix=zoom, alpha=False).save(target)
        selected_paths[name] = target.as_posix()
    page_count = document.page_count
    document.close()
    return {"page_count": page_count, "all_pages": rendered, "selected_pages": selected_paths}


def validate_pdf(run_root: Path) -> dict[str, Any]:
    root = run_root.resolve()
    source = root / "paper" / "main.tex"
    pdf = root / "paper" / "main.pdf"
    if not pdf.is_file():
        raise PdfPipelineError("compiled PDF does not exist", {"status": "failed"})
    header_valid = pdf.read_bytes()[:5] == b"%PDF-"
    reader = PdfReader(pdf)
    page_count = len(reader.pages)
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    metadata_text = " ".join(str(value) for value in (reader.metadata or {}).values())
    source_text = source.read_text(encoding="utf-8")
    xelatex_log_path = root / "logs" / "xelatex.log"
    xelatex_log = xelatex_log_path.read_text(encoding="utf-8", errors="replace") if xelatex_log_path.is_file() else ""
    severe_patterns = {
        "latex_errors": r"! LaTeX Error|Undefined control sequence|Emergency stop|Fatal error occurred",
        "missing_files": r"LaTeX Error: File `[^']+' not found",
        "undefined_references": r"There were undefined references|Reference `[^']+' .* undefined",
        "undefined_citations": r"Citation `[^']+' .* undefined|There were undefined citations",
    }
    serious = {name: len(re.findall(pattern, xelatex_log, flags=re.IGNORECASE)) for name, pattern in severe_patterns.items()}
    warnings = {
        "overfull_boxes": len(re.findall(r"Overfull \\hbox|Overfull \\vbox", xelatex_log)),
        "underfull_boxes": len(re.findall(r"Underfull \\hbox|Underfull \\vbox", xelatex_log)),
    }
    identity_candidates = {os.environ.get("USERNAME", ""), os.environ.get("USER", "")}
    identity_candidates.discard("")
    checked_content = source_text + "\n" + extracted_text + "\n" + metadata_text
    identity_hits = sorted(value for value in identity_candidates if value.casefold() in checked_content.casefold())
    absolute_path_hits = sorted(
        set(re.findall(r"(?:[A-Za-z]:[\\/][^\s}}]+|/(?:Users|home)/[^\s}}]+)", checked_content))
    )
    preview = render_pdf_previews(pdf, root / "paper" / "preview")
    passed = (
        header_valid
        and pdf.stat().st_size > 1024
        and page_count > 0
        and not any(serious.values())
        and not identity_hits
        and not absolute_path_hits
    )
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "pdf_path": "paper/main.pdf",
        "size_bytes": pdf.stat().st_size,
        "sha256": sha256_file(pdf),
        "header_valid": header_valid,
        "page_count": page_count,
        "serious_log_findings": serious,
        "box_warnings": warnings,
        "identity_hits": identity_hits,
        "absolute_path_hits": absolute_path_hits,
        "preview": {
            "page_count": preview["page_count"],
            "all_pages": [Path(path).relative_to(root).as_posix() for path in preview["all_pages"]],
            "selected_pages": {
                name: Path(path).relative_to(root).as_posix() for name, path in preview["selected_pages"].items()
            },
        },
        "visual_check": "awaiting_human_approval",
    }
    atomic_json(root / "validation_report.json", report)
    if not passed:
        raise PdfPipelineError("PDF structure or leak validation failed", report)
    return report
