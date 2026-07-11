"""Reviewable curve-fitting solver persisted inside each run workspace."""
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
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
