"""Traceable CSV and booktabs LaTeX table generation."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from mmagent.artifacts import atomic_text, read_json


_LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: str) -> str:
    return "".join(_LATEX_REPLACEMENTS.get(character, character) for character in str(value))


def _display_value(value: Any, digits: int, missing: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return missing
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return f"{float(value):.{digits}f}"
    return str(value)


def dataframe_to_latex_table(
    frame: pd.DataFrame,
    path: Path,
    *,
    caption: str,
    label: str,
    digits: int = 6,
    missing: str = "--",
) -> Path:
    """Write a complete booktabs table while escaping user-facing text."""
    if not re.fullmatch(r"[A-Za-z0-9:._/-]+", label):
        raise ValueError("LaTeX label contains unsupported characters")
    alignments = ["r" if pd.api.types.is_numeric_dtype(frame[column]) else "l" for column in frame.columns]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{''.join(alignments)}}}",
        r"\toprule",
        " & ".join(latex_escape(str(column)) for column in frame.columns) + r" \\",
        r"\midrule",
    ]
    for row in frame.itertuples(index=False, name=None):
        displayed = [_display_value(value, digits, missing) for value in row]
        lines.append(" & ".join(latex_escape(value) for value in displayed) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    atomic_text(path, "\n".join(lines) + "\n")
    return path


def generate_result_tables(run_root: Path, *, digits: int = 6) -> list[Path]:
    root = run_root.resolve()
    result = read_json(root / "outputs" / "metrics.json")
    parameters = result.get("parameters")
    metrics = result.get("metrics")
    if not isinstance(parameters, dict) or not isinstance(metrics, dict):
        raise ValueError("metrics.json must contain parameter and metric objects")

    parameter_labels = {"slope": ("斜率", "a"), "intercept": ("截距", "b")}
    parameter_frame = pd.DataFrame(
        [
            {
                "参数": parameter_labels.get(name, (name, name))[0],
                "符号": parameter_labels.get(name, (name, name))[1],
                "原始数值": float(value),
                "展示数值": f"{float(value):.{digits}f}",
            }
            for name, value in parameters.items()
        ]
    )
    metric_labels = {
        "rmse": "RMSE",
        "mae": "MAE",
        "r2": "R²",
        "max_absolute_error": "最大绝对误差",
    }
    metric_frame = pd.DataFrame(
        [
            {
                "指标": metric_labels.get(name, name),
                "原始数值": float(value),
                "展示数值": f"{float(value):.{digits}f}",
            }
            for name, value in metrics.items()
        ]
    )
    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    parameter_csv = table_dir / "parameters.csv"
    metrics_csv = table_dir / "metrics.csv"
    parameter_frame.to_csv(parameter_csv, index=False, encoding="utf-8", float_format="%.17g", na_rep="")
    metric_frame.to_csv(metrics_csv, index=False, encoding="utf-8", float_format="%.17g", na_rep="")
    parameter_tex = dataframe_to_latex_table(
        parameter_frame,
        table_dir / "parameters.tex",
        caption="线性模型参数估计",
        label="tab:parameters",
        digits=max(digits + 4, 10),
    )
    metrics_tex = dataframe_to_latex_table(
        metric_frame,
        table_dir / "metrics.tex",
        caption="拟合误差指标",
        label="tab:metrics",
        digits=max(digits + 4, 10),
    )
    return [parameter_csv, parameter_tex, metrics_csv, metrics_tex]
