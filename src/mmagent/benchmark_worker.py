"""Subprocess entry points used by the benchmark runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

from mmagent.artifacts import atomic_json, read_json, sha256_file
from mmagent.benchmark_cases import generate_case_data, solve_case


def _case(root: Path) -> dict[str, Any]:
    value = json.loads((root / "case.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("case.json must contain an object")
    return value


def _nested(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def validate_numeric(root: Path, case: dict[str, Any]) -> dict[str, Any]:
    result = read_json(root / "outputs" / "metrics.json")
    checks: list[dict[str, Any]] = []
    for expectation in case["numeric_expectations"]:
        path = str(expectation["path"])
        try:
            actual = float(_nested(result, path))
            lower = expectation.get("minimum")
            upper = expectation.get("maximum")
            tolerance = float(expectation.get("absolute_tolerance", 0))
            passed = (lower is None or actual >= float(lower) - tolerance) and (
                upper is None or actual <= float(upper) + tolerance
            )
            message = f"actual={actual}; expected=[{lower}, {upper}]"
        except (KeyError, TypeError, ValueError) as exc:
            actual = None
            passed = False
            message = f"could not read numeric result: {exc}"
        checks.append({"path": path, "actual": actual, "passed": passed, "message": message})
    report = {
        "schema_version": "1.0",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "checks": checks,
        "metrics_sha256": sha256_file(root / "outputs" / "metrics.json"),
        "input_sha256": sha256_file(root / "input" / "data.csv"),
    }
    atomic_json(root / "oracle_validation.json", report)
    return report


def review_snapshot(root: Path, case: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    claims_path = root / "outputs" / "claims.json"
    references: list[str] = []
    if claims_path.is_file():
        references = [str(value) for value in read_json(claims_path).get("referenced_files", [])]
    else:
        findings.append({"id": "claims-missing", "severity": "critical", "message": "outputs/claims.json is missing"})
    for relative in references:
        path = root / Path(relative)
        if not path.is_file():
            findings.append({"id": "reference-missing", "severity": "critical", "message": relative})
    for image_path in sorted((root / "figures").glob("*.png")) if (root / "figures").is_dir() else []:
        try:
            with Image.open(image_path) as image:
                image.verify()
            if image_path.stat().st_size < 1024:
                raise ValueError("image is unexpectedly small")
        except Exception as exc:
            findings.append({"id": "image-invalid", "severity": "critical", "message": f"{image_path.name}: {exc}"})
    execution = root / "logs" / "solver_execution.json"
    if not execution.is_file() or read_json(execution).get("exit_code") != 0:
        findings.append({"id": "execution-evidence", "severity": "critical", "message": "solver exit evidence is absent or non-zero"})
    validation = root / "oracle_validation.json"
    if not validation.is_file() or read_json(validation).get("status") != "passed":
        findings.append({"id": "oracle-validation", "severity": "critical", "message": "independent range validation did not pass"})
    report = {
        "schema_version": "1.0",
        "status": "passed" if not findings else "failed",
        "reviewer_context": "isolated_snapshot_process",
        "write_scope": "review",
        "source_case": case["id"],
        "source_artifacts": references,
        "findings": findings,
    }
    target = root / "review" / "review_report.json"
    atomic_json(target, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "solve", "validate", "review"))
    parser.add_argument("--run-root", type=Path, default=Path("."))
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    root = args.run_root.resolve()
    case = _case(root)
    if args.action == "generate":
        generate_case_data(root, str(case["id"]), int(case["random_seed"] if args.seed is None else args.seed))
    elif args.action == "solve":
        solve_case(root, case)
    elif args.action == "validate":
        report = validate_numeric(root, case)
        return 0 if report["status"] == "passed" else 1
    else:
        report = review_snapshot(root, case)
        return 0 if report["status"] == "passed" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
