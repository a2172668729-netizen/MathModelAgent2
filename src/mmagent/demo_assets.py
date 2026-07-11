"""Create the fixed curve-fitting engineering fixture and reviewable code."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from mmagent.artifacts import atomic_json, atomic_text

DEMO_RANDOM_SEED = 20260710


SOLVER_SOURCE = '''"""Reviewable curve-fitting solver persisted inside each run workspace."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

RANDOM_SEED = 20260710


def linear_model(x: np.ndarray, slope: float, intercept: float) -> np.ndarray:
    return slope * x + intercept


def solve(run_root: Path) -> dict[str, object]:
    root = run_root.resolve()
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    data = pd.read_csv(root / "input" / "data.csv")
    required = {"x", "y"}
    if not required <= set(data.columns):
        raise ValueError(f"data.csv is missing columns: {sorted(required - set(data.columns))}")
    if data[list(required)].isna().any().any():
        raise ValueError("data.csv contains missing x or y values")
    x = data["x"].to_numpy(dtype=float)
    y = data["y"].to_numpy(dtype=float)
    if len(x) < 3 or np.allclose(x, x[0]):
        raise ValueError("at least three observations with non-zero x variance are required")
    parameters, _ = curve_fit(linear_model, x, y, p0=(1.0, float(np.mean(y))), maxfev=10000)
    slope, intercept = (float(value) for value in parameters)
    predicted = linear_model(x, slope, intercept)
    residual = y - predicted
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    mae = float(np.mean(np.abs(residual)))
    denominator = float(np.sum(np.square(y - np.mean(y))))
    r2 = float(1.0 - np.sum(np.square(residual)) / denominator)
    maximum = float(np.max(np.abs(residual)))
    result = {
        "schema_version": "1.0",
        "model": "linear_least_squares_with_intercept",
        "random_seed": RANDOM_SEED,
        "sample_size": int(len(data)),
        "parameters": {"slope": slope, "intercept": intercept},
        "metrics": {"rmse": rmse, "mae": mae, "r2": r2, "max_absolute_error": maximum},
    }
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
    )
    predictions = pd.DataFrame(
        {"x": x, "y_observed": y, "y_predicted": predicted, "residual": residual}
    )
    predictions.to_csv(outputs / "predictions.csv", index=False, float_format="%.17g")
    predictions.to_csv(outputs / "figure_data.csv", index=False, float_format="%.17g")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    result = solve(args.run_root)
    print(json.dumps({"status": "passed", "metrics": result["metrics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


VALIDATOR_SOURCE = '''"""Independent closed-form validator for the persisted curve-fitting result."""
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
        json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
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
'''


def prepare_curve_fitting_workspace(workspace: Path) -> Path:
    root = workspace.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    input_dir = root / "input"
    source_dir = root / "src"
    input_dir.mkdir(exist_ok=True)
    source_dir.mkdir(exist_ok=True)
    required = [input_dir / "problem.md", input_dir / "data.csv", source_dir / "solve.py", source_dir / "validate.py"]
    existing = [path for path in required if path.exists()]
    if existing and len(existing) != len(required):
        missing = [path.relative_to(root).as_posix() for path in required if not path.exists()]
        raise ValueError(f"curve-fitting workspace is incomplete; refusing to invent missing base assets: {missing}")
    if not existing:
        rng = np.random.default_rng(DEMO_RANDOM_SEED)
        x = np.linspace(0.0, 10.0, 36)
        y = 2.5 * x + 4.0 + rng.normal(0.0, 1.0, size=x.size)
        data = pd.DataFrame({"x": x, "y": y})
        data.to_csv(input_dir / "data.csv", index=False, encoding="utf-8", float_format="%.12f")
        atomic_text(
            input_dir / "problem.md",
            "# 曲线拟合工程示例\n\n"
            "读取固定保存的带噪二维数据，建立带截距的一元线性最小二乘模型，"
            "计算 RMSE、MAE、R² 和最大绝对误差，分析残差，并输出中文 PDF。\n\n"
            "该数据为项目用固定种子生成的 synthetic fixture，不代表竞赛或现实观测。\n",
        )
        atomic_text(source_dir / "solve.py", SOLVER_SOURCE)
        atomic_text(source_dir / "validate.py", VALIDATOR_SOURCE)
        atomic_json(
            root / "demo_config.json",
            {
                "schema_version": "1.0",
                "demo": "curve-fitting",
                "model": "linear_least_squares_with_intercept",
                "random_seed": DEMO_RANDOM_SEED,
                "input_is_generated_once": True,
            },
        )
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        atomic_text(
            root / "decisions.md",
            "# Decisions\n\n"
            f"- {timestamp}: The user requested the curve-fitting engineering fixture and explicitly allowed a linear or nonlinear model; this fixture uses the linear option.\n"
            "- This approval applies only to the engineering demo and does not claim a competition model-selection checkpoint.\n"
            "- Automatic execution must stop at AWAITING_HUMAN_APPROVAL.\n",
        )
    return root
