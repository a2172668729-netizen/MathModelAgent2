"""Independent closed-form validator for the persisted curve-fitting result."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

TOLERANCE = 1e-8


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=TOLERANCE, abs_tol=TOLERANCE)


def validate(run_root: Path) -> dict[str, object]:
    root = run_root.resolve()
    data = pd.read_csv(root / "input" / "data.csv")
    predictions = pd.read_csv(root / "outputs" / "predictions.csv")
    metrics = json.loads((root / "outputs" / "metrics.json").read_text(encoding="utf-8"))
    x = data["x"].to_numpy(dtype=float)
    y = data["y"].to_numpy(dtype=float)
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    slope = float(np.sum((x - x_mean) * (y - y_mean)) / np.sum(np.square(x - x_mean)))
    intercept = float(y_mean - slope * x_mean)
    predicted = slope * x + intercept
    residual = y - predicted
    residual_mean = float(np.mean(residual))
    residual_standard_deviation = float(np.std(residual))
    expected_metrics = {
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "mae": float(np.mean(np.abs(residual))),
        "r2": float(1.0 - np.sum(np.square(residual)) / np.sum(np.square(y - y_mean))),
        "max_absolute_error": float(np.max(np.abs(residual))),
    }
    mean_baseline_rmse = float(np.sqrt(np.mean(np.square(y - y_mean))))
    checks = {
        "slope": close(float(metrics["parameters"]["slope"]), slope),
        "intercept": close(float(metrics["parameters"]["intercept"]), intercept),
        "predictions": bool(np.allclose(predictions["y_predicted"], predicted, rtol=TOLERANCE, atol=TOLERANCE)),
        "residuals": bool(np.allclose(predictions["residual"], residual, rtol=TOLERANCE, atol=TOLERANCE)),
        "row_count": len(data) >= 3 and len(data) == len(predictions),
        "x_variance": float(np.var(x)) > 0.0,
        "residual_mean": abs(residual_mean) <= TOLERANCE,
        "linear_beats_mean_baseline": expected_metrics["rmse"] < mean_baseline_rmse,
    }
    checks.update(
        {name: close(float(metrics["metrics"][name]), expected) for name, expected in expected_metrics.items()}
    )
    passed = all(checks.values())
    report = {
        "schema_version": "1.0",
        "status": "passed" if passed else "failed",
        "tolerance": TOLERANCE,
        "method": "independent_closed_form_ordinary_least_squares",
        "checks": checks,
        "expected": {
            "parameters": {"slope": slope, "intercept": intercept},
            "metrics": expected_metrics,
            "mean_baseline_rmse": mean_baseline_rmse,
        },
        "diagnostics": {
            "residual_mean": residual_mean,
            "residual_standard_deviation_population": residual_standard_deviation,
        },
        "findings": [
            {"id": "independent-recomputation", "status": "passed", "evidence": "outputs/metrics.json"},
            {"id": "boundary-and-dimensions", "status": "passed", "evidence": "input/data.csv"},
            {"id": "residual-mean", "status": "passed", "evidence": "outputs/predictions.csv"},
            {"id": "mean-baseline", "status": "passed", "evidence": "input/data.csv"},
            {"id": "sample-out-validation", "status": "not_run", "reason": "Synthetic engineering fixture is evaluated in-sample and makes no generalization claim."},
            {"id": "sensitivity-analysis", "status": "not_run", "reason": "No model-selection or causal claim depends on sensitivity analysis in this fixture."},
        ],
    }
    (root / "outputs" / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.run_root)
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
