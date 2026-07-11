"""Validation and LaTeX export for traceable structured results."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from mmagent.models import RunManifest, Status
from mmagent.real_models import ResultsRegistry


def load_results_registry(workspace: Path) -> ResultsRegistry:
    root = workspace.expanduser().resolve()
    path = root / "results" / "results.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        registry = ResultsRegistry.model_validate(raw)
    except OSError as exc:
        raise ValueError(f"results/results.json: cannot read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"results/results.json: invalid JSON: {exc}") from exc
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
        )
        raise ValueError(f"results/results.json: schema error: {details}") from exc
    for item in registry.results:
        for relative in (item.source_script, item.artifact_path):
            if relative and not (root / relative).is_file():
                raise ValueError(f"result {item.id}: referenced file does not exist: {relative}")
    return registry


def validate_executed_results(workspace: Path) -> ResultsRegistry:
    root = workspace.expanduser().resolve()
    registry = load_results_registry(root)
    manifests: dict[str, RunManifest] = {}
    for item in registry.results:
        if item.experiment_id not in manifests:
            manifest_path = root / "runs" / f"{item.experiment_id}.yaml"
            try:
                manifests[item.experiment_id] = RunManifest.model_validate(
                    yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                )
            except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
                raise ValueError(
                    f"result {item.id}: missing or invalid executed-run manifest "
                    f"{manifest_path.relative_to(root).as_posix()}: {exc}"
                ) from exc
        manifest = manifests[item.experiment_id]
        if manifest.status is not Status.PASSED or manifest.finished_at is None:
            raise ValueError(f"result {item.id}: executed-run manifest must be finished with status=passed")
        if not manifest.input_hashes:
            raise ValueError(f"result {item.id}: executed-run manifest must record at least one input hash")
        if "results/results.json" not in manifest.artifact_paths:
            raise ValueError(f"result {item.id}: executed-run manifest must register results/results.json")
        if item.source_script not in " ".join(manifest.command):
            raise ValueError(f"result {item.id}: source_script must appear in the executed command")
    return registry


def generate_latex_macros(workspace: Path) -> Path:
    root = workspace.expanduser().resolve()
    registry = validate_executed_results(root)
    lines = ["% Generated from results/results.json; do not edit by hand."]
    for item in registry.results:
        if not item.latex_macro:
            continue
        if item.validation_status is not Status.PASSED:
            raise ValueError(
                f"result {item.id}: LaTeX export requires validation_status=passed, got {item.validation_status.value}"
            )
        value = str(item.value).replace("%", "\\%").replace("_", "\\_")
        if item.unit:
            value = f"{value}\\,{item.unit.replace('%', '\\%').replace('_', '\\_')}"
        lines.append(f"\\newcommand{{\\{item.latex_macro}}}{{{value}}}")
    if len(lines) == 1:
        raise ValueError("results/results.json: no validated scalar or parameter has latex_macro")
    target = root / "paper" / "generated" / "results_macros.tex"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
