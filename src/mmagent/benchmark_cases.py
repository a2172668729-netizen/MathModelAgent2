"""Deterministic data generators and reference implementations for benchmark fixtures.

These are executable regression fixtures.  They test the local artifact pipeline and
well-defined numerical tasks; they are not presented as autonomous problem solving.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares, linprog

from mmagent.artifacts import atomic_json
from mmagent.plotting import bar_chart, configure_publication_style, line_chart, scatter_chart
from mmagent.tables import dataframe_to_latex_table


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_case_data(root: Path, case_id: str, seed: int) -> Path:
    target = root.resolve() / "input" / "data.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    rng = _rng(seed)
    if case_id == "forecasting_seasonal":
        t = np.arange(60)
        value = 20 + 0.4 * t + 3 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 0.35, len(t))
        frame = pd.DataFrame({"time": t, "value": value})
    elif case_id == "evaluation_resilience":
        frame = pd.DataFrame(
            {
                "方案": ["甲", "乙", "丙", "丁", "戊", "己"],
                "可靠性": [92, 85, 88, 80, 90, 84],
                "成本": [65, 48, 55, 42, 72, 51],
                "响应速度": [78, 90, 82, 86, 75, 88],
                "碳排放": [31, 24, 29, 20, 35, 23],
            }
        )
    elif case_id == "optimization_production":
        frame = pd.DataFrame(
            {
                "product": ["A", "B", "C"],
                "profit": [38, 31, 44],
                "labor": [2, 1, 3],
                "material": [1, 2, 2],
                "capacity": [40, 45, 30],
            }
        )
    elif case_id == "clustering_regions":
        centers = np.array([[1.5, 2.0], [7.0, 7.5], [3.0, 8.0]])
        values = np.vstack([center + rng.normal(0, 0.35, size=(18, 2)) for center in centers])
        frame = pd.DataFrame(values, columns=["feature_x", "feature_y"])
        frame.insert(0, "sample_id", [f"S{i:03d}" for i in range(len(frame))])
    elif case_id == "ode_logistic_growth":
        t = np.linspace(0, 24, 49)
        truth = 100 / (1 + (100 / 5 - 1) * np.exp(-0.25 * t))
        frame = pd.DataFrame({"time": t, "population": truth + rng.normal(0, 0.45, len(t))})
    elif case_id == "data_quality_regression":
        x = np.arange(50, dtype=float)
        y = 5 + 3 * x + rng.normal(0, 0.8, len(x))
        y[[5, 17, 33, 41]] = np.nan
        y[[12, 28, 46]] += np.array([55, -60, 70])
        frame = pd.DataFrame({"序号": np.arange(1, 51), "自变量": x, "响应值": y})
    elif case_id == "comprehensive_city_planning":
        rows: list[dict[str, Any]] = []
        cities = ["东城", "西城", "南城", "北城", "中城"]
        for city_index, city in enumerate(cities):
            for year in range(2017, 2025):
                trend = year - 2017
                rows.append(
                    {
                        "城市": city,
                        "年份": year,
                        "经济指数": 60 + city_index * 4 + trend * (1.2 + city_index * 0.1) + rng.normal(0, 0.4),
                        "环境指数": 82 - city_index * 2 + trend * 0.5 + rng.normal(0, 0.35),
                        "交通压力": 35 + city_index * 3 + trend * 0.8 + rng.normal(0, 0.5),
                    }
                )
        frame = pd.DataFrame(rows)
    elif case_id == "intentional_failure_diagnostic":
        frame = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
    else:
        raise ValueError(f"unknown benchmark case: {case_id}")
    frame.to_csv(target, index=False, encoding="utf-8-sig")
    return target


def _metric_payload(case_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "1.0", "case_id": case_id, "metrics": metrics}


def _forecast(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    train, test = frame.iloc[:-12], frame.iloc[-12:]
    design = lambda t: np.column_stack([np.ones(len(t)), t, np.sin(2 * np.pi * t / 12), np.cos(2 * np.pi * t / 12)])
    beta, *_ = np.linalg.lstsq(design(train.time.to_numpy()), train.value.to_numpy(), rcond=None)
    predicted = design(test.time.to_numpy()) @ beta
    next_value = float((design(np.array([60])) @ beta).item())
    rmse = float(np.sqrt(np.mean((test.value.to_numpy() - predicted) ** 2)))
    detail = pd.DataFrame({"time": test.time, "actual": test.value, "predicted": predicted})
    return {"holdout_rmse": rmse, "next_period_forecast": next_value, "train_rows": len(train)}, detail


def _evaluation(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    columns = ["可靠性", "成本", "响应速度", "碳排放"]
    benefit = {"可靠性", "响应速度"}
    weights = np.array([0.35, 0.25, 0.25, 0.15])
    normalized = []
    for name in columns:
        values = frame[name].to_numpy(float)
        scaled = (values - values.min()) / (values.max() - values.min())
        normalized.append(scaled if name in benefit else 1 - scaled)
    scores = np.column_stack(normalized) @ weights
    detail = pd.DataFrame({"方案": frame["方案"], "综合得分": scores}).sort_values("综合得分", ascending=False)
    detail["排名"] = np.arange(1, len(detail) + 1)
    winner_index = int(np.argmax(scores))
    return {"top_score": float(scores[winner_index]), "winner_index": winner_index, "alternatives": len(frame)}, detail


def _optimization(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    profit = frame.profit.to_numpy(float)
    constraints = np.array([frame.labor, frame.material], dtype=float)
    result = linprog(-profit, A_ub=constraints, b_ub=np.array([80, 75]), bounds=[(0, cap) for cap in frame.capacity], method="highs")
    if not result.success:
        raise RuntimeError(f"linear program failed: {result.message}")
    detail = pd.DataFrame({"product": frame["product"], "quantity": result.x, "profit_contribution": result.x * profit})
    usage = constraints @ result.x
    return {"objective_value": float(-result.fun), "labor_used": float(usage[0]), "material_used": float(usage[1]), "solver_success": 1}, detail


def _cluster(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    values = frame[["feature_x", "feature_y"]].to_numpy(float)
    centers = [values[0]]
    for _ in range(2):
        distance = np.min(np.stack([np.sum((values - center) ** 2, axis=1) for center in centers]), axis=0)
        centers.append(values[int(np.argmax(distance))])
    centers_array = np.array(centers)
    labels = np.zeros(len(values), dtype=int)
    for _ in range(50):
        new_labels = np.argmin(np.sum((values[:, None, :] - centers_array[None, :, :]) ** 2, axis=2), axis=1)
        new_centers = np.array([values[new_labels == index].mean(axis=0) for index in range(3)])
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers_array):
            break
        labels, centers_array = new_labels, new_centers
    inertia = float(np.sum((values - centers_array[labels]) ** 2))
    detail = frame.copy()
    detail["cluster"] = labels
    return {"cluster_count": len(set(labels)), "inertia": inertia, "minimum_cluster_size": int(np.bincount(labels).min())}, detail


def _ode(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    times = frame.time.to_numpy(float)
    observed = frame.population.to_numpy(float)

    def predict(parameters: np.ndarray) -> np.ndarray:
        rate, capacity = parameters
        solution = solve_ivp(lambda _t, y: rate * y * (1 - y / capacity), (times[0], times[-1]), [observed[0]], t_eval=times, rtol=1e-9, atol=1e-10)
        return solution.y[0]

    fit = least_squares(lambda parameters: predict(parameters) - observed, x0=np.array([0.2, 95.0]), bounds=([0.01, 50], [1.0, 200]))
    predicted = predict(fit.x)
    detail = pd.DataFrame({"time": times, "observed": observed, "predicted": predicted})
    return {"growth_rate": float(fit.x[0]), "carrying_capacity": float(fit.x[1]), "fit_rmse": float(np.sqrt(np.mean((predicted - observed) ** 2)))}, detail


def _data_quality(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    missing = int(frame["响应值"].isna().sum())
    filled = frame.copy()
    filled["响应值"] = filled["响应值"].interpolate(limit_direction="both")
    preliminary = np.polyfit(filled["自变量"], filled["响应值"], 1)
    residual = filled["响应值"] - np.polyval(preliminary, filled["自变量"])
    median = float(residual.median())
    mad = float(np.median(np.abs(residual - median)))
    keep = np.abs(residual - median) <= 5 * 1.4826 * mad
    cleaned = filled.loc[keep].copy()
    slope, intercept = np.polyfit(cleaned["自变量"], cleaned["响应值"], 1)
    cleaned["predicted"] = slope * cleaned["自变量"] + intercept
    return {"missing_count": missing, "outlier_count": int((~keep).sum()), "clean_rows": len(cleaned), "slope": float(slope), "intercept": float(intercept)}, cleaned


def _comprehensive(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    latest = frame[frame["年份"] == frame["年份"].max()].copy()
    for column, beneficial in (("经济指数", True), ("环境指数", True), ("交通压力", False)):
        values = latest[column]
        scaled = (values - values.min()) / (values.max() - values.min())
        latest[column + "标准化"] = scaled if beneficial else 1 - scaled
    latest["综合得分"] = 0.4 * latest["经济指数标准化"] + 0.35 * latest["环境指数标准化"] + 0.25 * latest["交通压力标准化"]
    slopes = frame.groupby("城市").apply(lambda group: np.polyfit(group["年份"], group["经济指数"], 1)[0], include_groups=False)
    winner = latest.loc[latest["综合得分"].idxmax(), "城市"]
    return {"city_count": int(frame["城市"].nunique()), "latest_year": int(frame["年份"].max()), "top_score": float(latest["综合得分"].max()), "mean_economic_slope": float(slopes.mean()), "winner_code": int(list(sorted(frame["城市"].unique())).index(winner))}, latest


def _save_custom_figure(figure: plt.Figure, stem: Path) -> None:
    figure.tight_layout()
    figure.savefig(stem.with_suffix(".png"), dpi=180, bbox_inches="tight")
    figure.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(figure)


def _comprehensive_figures(root: Path, frame: pd.DataFrame, latest: pd.DataFrame) -> None:
    configure_publication_style()
    figures = root / "figures"
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    for city, group in frame.groupby("城市"):
        axis.plot(group["年份"], group["经济指数"], marker="o", linewidth=1.8, label=city)
    axis.set(title="五城市经济指数年度趋势", xlabel="年份", ylabel="经济指数")
    axis.legend(ncol=3, frameon=False)
    axis.grid(alpha=0.2)
    _save_custom_figure(figure, figures / "figure_01")

    ordered = latest.sort_values("综合得分", ascending=False)
    bar_chart(ordered["城市"].tolist(), ordered["综合得分"].tolist(), figures / "figure_02", title="2024 年城市综合得分", ylabel="综合得分")

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    axis.scatter(latest["交通压力"], latest["环境指数"], s=65)
    for _, row in latest.iterrows():
        axis.annotate(str(row["城市"]), (row["交通压力"], row["环境指数"]), xytext=(5, 4), textcoords="offset points")
    axis.set(title="2024 年环境指数与交通压力", xlabel="交通压力（越低越好）", ylabel="环境指数（越高越好）")
    axis.grid(alpha=0.2)
    _save_custom_figure(figure, figures / "figure_03")

    matrix = latest[["经济指数标准化", "环境指数标准化", "交通压力标准化"]].to_numpy(float)
    figure, axis = plt.subplots(figsize=(6.8, 4.8))
    image = axis.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=1)
    axis.set_xticks(range(3), labels=["经济", "环境", "交通"])
    axis.set_yticks(range(len(latest)), labels=latest["城市"].tolist())
    axis.set(title="2024 年标准化指标热图", xlabel="指标", ylabel="城市")
    figure.colorbar(image, ax=axis, label="标准化值")
    _save_custom_figure(figure, figures / "figure_04")


def _profile_figures(root: Path, profile: str, detail: pd.DataFrame) -> None:
    configure_publication_style()
    figures = root / "figures"
    if profile in {"forecasting", "ode"}:
        time_column = "time"
        observed_column = "actual" if profile == "forecasting" else "observed"
        figure, axis = plt.subplots(figsize=(7.8, 4.8))
        axis.plot(detail[time_column], detail[observed_column], marker="o", label="观测")
        axis.plot(detail[time_column], detail["predicted"], marker="s", label="模型")
        axis.set(title="样本外预测对比" if profile == "forecasting" else "Logistic 数值积分拟合", xlabel="时间", ylabel="数值")
        axis.legend(frameon=False)
        axis.grid(alpha=0.2)
        _save_custom_figure(figure, figures / "figure_01")
        residual = detail[observed_column] - detail["predicted"]
        figure, axis = plt.subplots(figsize=(7.8, 4.5))
        axis.axhline(0, color="black", linewidth=1)
        axis.bar(detail[time_column], residual, width=0.35 if profile == "ode" else 0.65)
        axis.set(title="预测残差", xlabel="时间", ylabel="观测 - 模型")
        axis.grid(axis="y", alpha=0.2)
        _save_custom_figure(figure, figures / "figure_02")
    elif profile == "data_quality":
        figure, axis = plt.subplots(figsize=(7.6, 4.8))
        axis.scatter(detail["自变量"], detail["响应值"], label="清洗后观测")
        axis.plot(detail["自变量"], detail["predicted"], color="tab:red", label="稳健基线")
        axis.set(title="清洗后数据与拟合关系", xlabel="自变量", ylabel="响应值")
        axis.legend(frameon=False)
        axis.grid(alpha=0.2)
        _save_custom_figure(figure, figures / "figure_01")
        residual = detail["响应值"] - detail["predicted"]
        scatter_chart(detail["自变量"], residual, figures / "figure_02", title="清洗后残差", xlabel="自变量", ylabel="残差")
    elif profile == "evaluation":
        bar_chart(detail["方案"].tolist(), detail["综合得分"].tolist(), figures / "figure_01", title="候选方案综合得分", ylabel="综合得分")
        bar_chart(detail["方案"].tolist(), detail["排名"].tolist(), figures / "figure_02", title="候选方案排名", ylabel="排名（越小越好）")
    elif profile == "optimization":
        bar_chart(detail["product"].tolist(), detail["quantity"].tolist(), figures / "figure_01", title="最优生产量", ylabel="生产量")
        bar_chart(detail["product"].tolist(), detail["profit_contribution"].tolist(), figures / "figure_02", title="产品利润贡献", ylabel="利润")
    elif profile == "clustering":
        figure, axis = plt.subplots(figsize=(6.8, 5.2))
        for label, group in detail.groupby("cluster"):
            axis.scatter(group["feature_x"], group["feature_y"], label=f"簇 {label}")
        axis.set(title="区域样本三簇结构", xlabel="feature_x", ylabel="feature_y")
        axis.legend(frameon=False)
        axis.grid(alpha=0.2)
        _save_custom_figure(figure, figures / "figure_01")
        counts = detail.groupby("cluster").size()
        bar_chart([str(value) for value in counts.index], counts.tolist(), figures / "figure_02", title="各簇样本数", ylabel="样本数")


def _write_artifacts(root: Path, case_id: str, title: str, metrics: dict[str, Any], detail: pd.DataFrame, minimum_figures: int, minimum_tables: int) -> None:
    outputs = root / "outputs"
    figures = root / "figures"
    tables = root / "tables"
    paper = root / "paper"
    for directory in (outputs, figures, tables, paper):
        directory.mkdir(parents=True, exist_ok=True)
    atomic_json(outputs / "metrics.json", _metric_payload(case_id, metrics))
    detail.to_csv(outputs / "details.csv", index=False, encoding="utf-8-sig")
    numeric = detail.select_dtypes(include=[np.number])
    x = np.arange(len(detail))
    if numeric.shape[1] >= 1:
        line_chart(x, numeric.iloc[:, 0].to_numpy(), figures / "figure_01", title=f"{title}：主要序列", xlabel="样本", ylabel=str(numeric.columns[0]))
    if numeric.shape[1] >= 2:
        scatter_chart(numeric.iloc[:, 0].to_numpy(), numeric.iloc[:, 1].to_numpy(), figures / "figure_02", title=f"{title}：变量关系", xlabel=str(numeric.columns[0]), ylabel=str(numeric.columns[1]))
    while len(list(figures.glob("*.png"))) < minimum_figures:
        index = len(list(figures.glob("*.png"))) + 1
        values = np.asarray(list(metrics.values()), dtype=object)
        finite = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(float(value))]
        bar_chart([str(i + 1) for i in range(len(finite))], finite, figures / f"figure_{index:02d}", title=f"{title}：指标图 {index}", ylabel="数值")
    table_frames = [pd.DataFrame([metrics]), detail.head(20)]
    if case_id == "comprehensive_city_planning":
        table_frames = [
            pd.DataFrame([metrics]),
            detail[["城市", "经济指数", "环境指数", "交通压力", "综合得分"]],
            detail[["城市", "经济指数标准化", "环境指数标准化", "交通压力标准化"]],
        ]
    if minimum_tables > 2:
        table_frames.append(detail.describe(include="all").reset_index())
    for index, table in enumerate(table_frames[:minimum_tables], start=1):
        table.to_csv(tables / f"table_{index:02d}.csv", index=False, encoding="utf-8-sig")
        dataframe_to_latex_table(table, tables / f"table_{index:02d}.tex", caption=f"{title}表 {index}", label=f"tab:{case_id}-{index}")
    claims = {
        "schema_version": "1.0",
        "claims": [
            {"metric": name, "value": value, "source": "outputs/metrics.json"}
            for name, value in metrics.items()
        ],
        "referenced_files": [
            "outputs/metrics.json",
            "outputs/details.csv",
            *[path.relative_to(root).as_posix() for path in sorted(figures.glob("*.png"))],
            *[path.relative_to(root).as_posix() for path in sorted(tables.glob("*.csv"))],
        ],
    }
    atomic_json(outputs / "claims.json", claims)
    figure_tex = "\n".join(
        rf"\begin{{figure}}[H]\centering\includegraphics[width=.72\linewidth]{{../{path.relative_to(root).as_posix()}}}\caption{{{title}图示}}\end{{figure}}"
        for path in sorted(figures.glob("*.png"))
    )
    metric_lines = []
    for name, value in metrics.items():
        escaped_name = name.replace("_", r"\_")
        displayed = f"{value:.6g}" if isinstance(value, (int, float)) else str(value)
        metric_lines.append(f"{escaped_name} & {displayed}")
    metric_rows = (r" \\" + "\n").join(metric_lines)
    extra_tables = ""
    if case_id == "comprehensive_city_planning":
        extra_tables = r"\subsection{城市明细}\input{../tables/table_02.tex}\subsection{标准化指标}\input{../tables/table_03.tex}"
    source = rf"""\documentclass[UTF8,12pt]{{ctexart}}
\usepackage{{amsmath,booktabs,graphicx,float,geometry}}
\geometry{{a4paper,margin=2.4cm}}
\title{{{title}}}\author{{匿名 Benchmark Fixture}}\date{{}}
\begin{{document}}\maketitle
\section{{任务与方法}}
本报告由可复现的本地 Python 执行生成。它用于回归测试，不代表自动完成真实竞赛建模。
\section{{关键结果}}
\begin{{table}}[H]\centering\caption{{关键数值结果}}\begin{{tabular}}{{lr}}\toprule 指标 & 数值 \\\midrule
{metric_rows} \\\bottomrule\end{{tabular}}\end{{table}}
{extra_tables}
\section{{图表证据}}
{figure_tex}
\section{{限制}}
数值仅来自本次运行的结构化产物；最终视觉定稿仍需人工逐页确认。
\end{{document}}
"""
    (paper / "main.tex").write_text(source, encoding="utf-8")


def solve_case(root: Path, case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case["id"])
    if case_id == "intentional_failure_diagnostic":
        raise RuntimeError("intentional benchmark failure: diagnostic persistence check")
    frame = pd.read_csv(root / "input" / "data.csv", encoding="utf-8-sig")
    dispatch = {
        "forecasting": _forecast,
        "evaluation": _evaluation,
        "optimization": _optimization,
        "clustering": _cluster,
        "ode": _ode,
        "data_quality": _data_quality,
        "comprehensive": _comprehensive,
    }
    profile = str(case["solver_profile"])
    if profile not in dispatch:
        raise ValueError(f"unknown solver profile: {profile}")
    metrics, detail = dispatch[profile](frame)
    structural = case["structural_expectations"]
    _write_artifacts(root, case_id, str(case["title"]), metrics, detail, int(structural["minimum_figures"]), int(structural["minimum_tables"]))
    if case_id == "comprehensive_city_planning":
        _comprehensive_figures(root, frame, detail)
    else:
        _profile_figures(root, profile, detail)
    return metrics


def read_case_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("case payload must be an object")
    return value
