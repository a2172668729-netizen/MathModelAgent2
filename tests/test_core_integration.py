from __future__ import annotations

from pathlib import Path

import pytest

from mmagent.artifacts import read_json
from mmagent.core_pipeline import run_curve_fitting_demo, validate_core_run
from mmagent.pdf import compile_paper, resolve_tool, validate_pdf
from mmagent.plotting import line_chart


@pytest.mark.integration
def test_xelatex_chinese_formula_table_and_real_image_compilation(tmp_path: Path) -> None:
    assert resolve_tool("xelatex") is not None, "XeLaTeX is required for the real integration suite"
    assert resolve_tool("latexmk") is not None, "latexmk is required for the real integration suite"
    root = tmp_path / "chinese-tex"
    (root / "paper").mkdir(parents=True)
    line_chart([0, 1, 2], [1, 2, 4], root / "paper" / "acceptance-image", title="中文验收图")
    (root / "paper" / "main.tex").write_text(
        r"""\documentclass[UTF8]{ctexart}
\usepackage{amsmath,booktabs,graphicx}
\title{中文 XeLaTeX 集成验收}
\author{匿名}
\date{}
\begin{document}
\maketitle
中文正文与公式 $y=ax+b$。
\begin{center}\begin{tabular}{lr}\toprule 参数 & 数值 \\ \midrule 斜率 & 2.0 \\ \bottomrule\end{tabular}\end{center}
\includegraphics[width=.7\linewidth]{acceptance-image.png}
\end{document}
""",
        encoding="utf-8",
    )

    execution = compile_paper(root)
    report = validate_pdf(root)

    assert execution["exit_code"] == 0
    assert report["status"] == "passed"
    assert report["page_count"] >= 1
    assert (root / "paper" / "main.pdf").stat().st_size > 1024


@pytest.mark.integration
@pytest.mark.end_to_end
def test_curve_fitting_demo_real_end_to_end_and_reproduction(tmp_path: Path) -> None:
    summary = run_curve_fitting_demo(tmp_path / "curve-fitting", timeout_seconds=120)
    first = summary["first_run"]
    second = summary["reproduction_run"]
    required = (
        "input/data.csv",
        "src/solve.py",
        "outputs/metrics.json",
        "outputs/predictions.csv",
        "outputs/validation.json",
        "outputs/claim_evidence.json",
        "figures/fit_curve.png",
        "figures/fit_curve.svg",
        "figures/residuals.png",
        "figures/residuals.svg",
        "tables/parameters.csv",
        "tables/parameters.tex",
        "tables/metrics.csv",
        "tables/metrics.tex",
        "paper/main.tex",
        "paper/main.pdf",
        "paper/report_manifest.json",
        "logs/python_stdout.log",
        "logs/execution.json",
        "logs/latexmk.log",
        "logs/xelatex.log",
        "manifest.json",
        "validation_report.json",
        "human_approval.json",
    )
    for run in (first, second):
        assert all((run / relative).is_file() and (run / relative).stat().st_size > 0 for relative in required)
        stderr_log = run / "logs/python_stderr.log"
        assert stderr_log.is_file()
        assert read_json(run / "logs/execution.json")["stderr_path"] == "logs/python_stderr.log"
        assert read_json(run / "validation_report.json")["page_count"] >= 1
        numeric_validation = read_json(run / "outputs/validation.json")
        assert abs(float(numeric_validation["diagnostics"]["residual_mean"])) <= float(
            numeric_validation["tolerance"]
        )
        assert "残差均值" in (run / "paper/main.tex").read_text(encoding="utf-8")
    manifest = read_json(second / "manifest.json")
    expected_manifest_fields = {
        "schema_version",
        "project_version",
        "run_id",
        "operating_system",
        "python_executable",
        "python_version",
        "dependencies",
        "tex_tools",
        "random_seed",
        "execution_commands",
        "inputs",
        "python_sources",
        "numeric_outputs",
        "figures",
        "tables",
        "latex_sources",
        "pdf_files",
        "reports",
        "exit_codes",
        "current_state",
        "validation",
        "failure_reason",
        "human_approval_status",
    }
    assert expected_manifest_fields <= set(manifest)
    assert manifest["current_state"] == "AWAITING_HUMAN_APPROVAL"
    assert "FINAL" not in manifest["state_history"]
    assert summary["reproducibility"]["status"] == "passed"
    assert all(summary["reproducibility"]["conditions"].values())
    assert validate_core_run(summary["workspace"])["status"] == "passed"
