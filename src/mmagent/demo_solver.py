"""Deterministic least-squares solver used only by the phase-two demo."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import yaml

from mmagent.models import Experiment, Metric, Status


def _read_points(path: Path) -> tuple[list[float], list[float]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 2:
        raise ValueError("at least two observations are required")
    return [float(row["x"]) for row in rows], [float(row["y"]) for row in rows]


def _least_squares(xs: list[float], ys: list[float]) -> tuple[float, float]:
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        raise ValueError("x must have non-zero variance")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / denominator
    return slope, y_mean - slope * x_mean


def solve(workspace: Path) -> Experiment:
    workspace = workspace.resolve()
    xs, ys = _read_points(workspace / "input" / "observations.csv")
    slope, intercept = _least_squares(xs, ys)
    predictions = [slope * x + intercept for x in xs]
    mean_prediction = sum(ys) / len(ys)
    linear_rmse = math.sqrt(sum((actual - predicted) ** 2 for actual, predicted in zip(ys, predictions, strict=True)) / len(ys))
    baseline_rmse = math.sqrt(sum((actual - mean_prediction) ** 2 for actual in ys) / len(ys))
    return Experiment(
        id="experiment-linear-demo",
        model_id="linear-least-squares",
        status=Status.PASSED,
        command=["python", "code/solve.py", "--workspace", "."],
        random_seed=0,
        parameters={"fit_intercept": True},
        input_paths=["input/observations.csv"],
        metrics=[
            Metric(name="slope", value=slope, split="full"),
            Metric(name="intercept", value=intercept, split="full"),
            Metric(name="linear_rmse", value=linear_rmse, split="full", higher_is_better=False),
            Metric(name="baseline_rmse", value=baseline_rmse, split="full", higher_is_better=False),
        ],
        artifact_paths=["results/experiment.yaml"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    experiment = solve(args.workspace)
    output = args.workspace.resolve() / "results" / "experiment.yaml"
    temporary = output.with_suffix(".yaml.tmp")
    temporary.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json", exclude_none=True), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    temporary.replace(output)
    metrics = {metric.name: metric.value for metric in experiment.metrics}
    print(
        f"experiment={experiment.id} slope={metrics['slope']:.12g} "
        f"intercept={metrics['intercept']:.12g} linear_rmse={metrics['linear_rmse']:.12g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

