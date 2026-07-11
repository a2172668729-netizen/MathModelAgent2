"""Reusable, publication-oriented Matplotlib figures."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


PREFERRED_CJK_FONTS = (
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Arial Unicode MS",
)


def configure_publication_style() -> str | None:
    installed = {item.name for item in font_manager.fontManager.ttflist}
    selected = next((name for name in PREFERRED_CJK_FONTS if name in installed), None)
    if selected is None:
        warnings.warn("No preferred CJK font was detected; Chinese plot labels may use fallback glyphs.", stacklevel=2)
    else:
        matplotlib.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    matplotlib.rcParams.update(
        {
            "axes.unicode_minus": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "svg.hashsalt": "mathmodelagent",
        }
    )
    return selected


def _save_figure(fig: plt.Figure, output_stem: Path) -> list[Path]:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png = output_stem.with_suffix(".png")
    svg = output_stem.with_suffix(".svg")
    fig.savefig(png, dpi=300, bbox_inches="tight", metadata={"Software": "MathModelAgent"})
    fig.savefig(svg, format="svg", bbox_inches="tight", metadata={"Creator": "MathModelAgent", "Date": None})
    plt.close(fig)
    return [png, svg]


def line_chart(
    x: Sequence[float],
    y: Sequence[float],
    output_stem: Path,
    *,
    title: str = "折线图",
    xlabel: str = "x",
    ylabel: str = "y",
    label: str = "数据",
) -> list[Path]:
    configure_publication_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
    ax.plot(x, y, linewidth=1.8, label=label)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save_figure(fig, output_stem)


def scatter_chart(
    x: Sequence[float],
    y: Sequence[float],
    output_stem: Path,
    *,
    title: str = "散点图",
    xlabel: str = "x",
    ylabel: str = "y",
    label: str = "观测",
) -> list[Path]:
    configure_publication_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
    ax.scatter(x, y, s=28, alpha=0.85, label=label)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save_figure(fig, output_stem)


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    output_stem: Path,
    *,
    title: str = "柱状图",
    xlabel: str = "类别",
    ylabel: str = "数值",
) -> list[Path]:
    configure_publication_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
    ax.bar(labels, values, label="数值")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    return _save_figure(fig, output_stem)


def heatmap_chart(
    matrix: Sequence[Sequence[float]],
    output_stem: Path,
    *,
    title: str = "热力图",
    xlabel: str = "列",
    ylabel: str = "行",
) -> list[Path]:
    configure_publication_style()
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.size == 0:
        raise ValueError("heatmap matrix must be a non-empty two-dimensional array")
    fig, ax = plt.subplots(figsize=(5.6, 4.5), layout="constrained")
    image = ax.imshow(values, cmap="viridis", aspect="auto")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    fig.colorbar(image, ax=ax, label="数值")
    return _save_figure(fig, output_stem)


def generate_curve_fitting_figures(run_root: Path) -> tuple[list[Path], str | None]:
    """Generate the fitted-curve and residual figures from persisted predictions."""
    root = run_root.resolve()
    predictions = pd.read_csv(root / "outputs" / "predictions.csv")
    required = {"x", "y_observed", "y_predicted", "residual"}
    if not required <= set(predictions.columns):
        raise ValueError(f"predictions.csv is missing columns: {sorted(required - set(predictions.columns))}")
    selected_font = configure_publication_style()

    fit_fig, fit_ax = plt.subplots(figsize=(6.6, 4.4), layout="constrained")
    fit_ax.scatter(predictions["x"], predictions["y_observed"], s=28, alpha=0.82, label="原始观测")
    ordered = predictions.sort_values("x")
    fit_ax.plot(ordered["x"], ordered["y_predicted"], color="#c43c39", linewidth=2.0, label="线性拟合")
    fit_ax.set(title="原始数据与拟合曲线", xlabel="自变量 x（无量纲）", ylabel="响应 y（无量纲）")
    fit_ax.grid(True, alpha=0.3)
    fit_ax.legend()
    paths = _save_figure(fit_fig, root / "figures" / "fit_curve")

    residual_fig, residual_ax = plt.subplots(figsize=(6.6, 4.2), layout="constrained")
    residual_ax.scatter(predictions["x"], predictions["residual"], s=28, alpha=0.82, label="残差")
    residual_ax.axhline(0.0, color="#c43c39", linewidth=1.4, linestyle="--", label="零残差线")
    residual_ax.set(title="残差分析", xlabel="自变量 x（无量纲）", ylabel="残差（无量纲）")
    residual_ax.grid(True, alpha=0.3)
    residual_ax.legend()
    paths.extend(_save_figure(residual_fig, root / "figures" / "residuals"))
    return paths, selected_font
