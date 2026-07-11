"""Creation, validation, and evidence gates for real-problem workspaces."""

from __future__ import annotations

import json
import platform
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from mmagent.benchmark import load_scorecard, write_scorecard
from mmagent.models import Stage, Status, ValidationReportFile, WorkspaceState
from mmagent.real_models import DataAudit, ExperimentPlan, InputInventory, ModelCandidates, ProblemAnalysis
from mmagent.results_registry import load_results_registry, validate_executed_results

REAL_WORKSPACE_DIRECTORIES = (
    "input",
    "analysis",
    "data",
    "models",
    "experiments",
    "code",
    "results",
    "figures",
    "paper",
    "review",
    "runs",
)
REAL_WORKSPACE_FILES = (
    "state.yaml",
    "decisions.md",
    "benchmark_scorecard.yaml",
    "benchmark_scorecard.md",
)
REAL_STAGE_CHAIN = (
    Stage.CREATED,
    Stage.INGESTED,
    Stage.ANALYZED,
    Stage.DATA_READY,
    Stage.MODELS_PROPOSED,
    Stage.MODEL_SELECTED,
    Stage.IMPLEMENTED,
    Stage.VALIDATED,
    Stage.PAPER_DRAFTED,
    Stage.AWAITING_HUMAN_APPROVAL,
)


@dataclass(slots=True)
class GateReport:
    target: Stage
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _identifier(value: str) -> str:
    if re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", value) is None:
        raise ValueError("problem_id must match [a-z][a-z0-9_-]{1,63}")
    return value


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(
        yaml.safe_dump(value.model_dump(mode="json"), allow_unicode=True, sort_keys=False),  # type: ignore[attr-defined]
        encoding="utf-8",
    )


def create_real_workspace(problem_id: str, parent: Path = Path("workspaces")) -> Path:
    identifier = _identifier(problem_id)
    root = (parent.expanduser().resolve() / identifier).resolve()
    if root.exists():
        raise ValueError(f"workspace already exists: {root}")
    root.mkdir(parents=True)
    for relative in REAL_WORKSPACE_DIRECTORIES:
        (root / relative).mkdir()
    now = datetime.now(UTC)
    state = WorkspaceState(
        workspace_kind="real_problem",
        workspace_id=identifier,
        current_stage=Stage.CREATED,
        completed_stages=[],
        artifacts={
            "decisions": "decisions.md",
            "benchmark_yaml": "benchmark_scorecard.yaml",
            "benchmark_markdown": "benchmark_scorecard.md",
        },
        updated_at=now,
    )
    _write_yaml(root / "state.yaml", state)
    (root / "decisions.md").write_text(
        "# Decisions\n\n"
        f"- {now.isoformat()} — Workspace `{identifier}` created by `mmagent new`; no problem interpretation, "
        "model selection, validation conclusion, or final approval has been made.\n",
        encoding="utf-8",
    )
    write_scorecard(root)
    return root


def load_real_state(workspace: Path) -> WorkspaceState:
    root = workspace.expanduser().resolve()
    try:
        state = WorkspaceState.model_validate(yaml.safe_load((root / "state.yaml").read_text(encoding="utf-8")))
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"state.yaml: cannot load real-problem state: {exc}") from exc
    if state.workspace_kind != "real_problem":
        raise ValueError("state.yaml: workspace_kind must be real_problem")
    return state


def _load_yaml(root: Path, relative: str, model_type: type) -> object:
    path = root / relative
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return model_type.model_validate(raw)
    except OSError as exc:
        raise ValueError(f"missing required file: {relative}") from exc
    except (UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"{relative}: cannot read YAML: {exc}") from exc
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}" for error in exc.errors()
        )
        raise ValueError(f"{relative}: schema error: {details}") from exc


def _load_inventory(root: Path) -> InputInventory:
    relative = "input_inventory.json"
    try:
        return InputInventory.model_validate(json.loads((root / relative).read_text(encoding="utf-8")))
    except OSError as exc:
        raise ValueError(f"missing required file: {relative}; run `mmagent audit-input {root}`") from exc
    except (UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"{relative}: invalid inventory: {exc}") from exc


def validate_real_structure(workspace: Path) -> list[str]:
    root = workspace.expanduser().resolve()
    errors: list[str] = []
    if not root.is_dir():
        return [f"workspace does not exist: {root}"]
    for relative in REAL_WORKSPACE_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"missing directory: {relative}")
    for relative in REAL_WORKSPACE_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")
    try:
        load_real_state(root)
    except ValueError as exc:
        errors.append(str(exc))
    if (root / "benchmark_scorecard.yaml").is_file():
        try:
            load_scorecard(root)
        except ValueError as exc:
            errors.append(str(exc))
    optional = (
        ("problem_analysis.yaml", ProblemAnalysis),
        ("data_audit.yaml", DataAudit),
        ("model_candidates.yaml", ModelCandidates),
        ("experiment_plan.yaml", ExperimentPlan),
        ("results/validation.yaml", ValidationReportFile),
    )
    for relative, model_type in optional:
        if (root / relative).is_file():
            try:
                _load_yaml(root, relative, model_type)
            except ValueError as exc:
                errors.append(str(exc))
    if (root / "input_inventory.json").is_file():
        try:
            _load_inventory(root)
        except ValueError as exc:
            errors.append(str(exc))
    if (root / "results" / "results.json").is_file():
        try:
            load_results_registry(root)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def evaluate_gate(workspace: Path, target: Stage) -> GateReport:
    root = workspace.expanduser().resolve()
    report = GateReport(target=target)
    try:
        state = load_real_state(root)
    except ValueError as exc:
        report.errors.append(str(exc))
        return report
    if target in {Stage.REVIEWED, Stage.FINALIZED}:
        report.errors.append(f"{target.value} is never an automated transition; isolated review or explicit human approval is required")
        return report
    try:
        current_index = REAL_STAGE_CHAIN.index(state.current_stage)
        target_index = REAL_STAGE_CHAIN.index(target)
    except ValueError:
        report.errors.append(f"unsupported real-problem stage: {target.value}")
        return report
    if target_index != current_index + 1:
        expected = REAL_STAGE_CHAIN[current_index + 1].value if current_index + 1 < len(REAL_STAGE_CHAIN) else "none"
        report.errors.append(f"stage transition must be sequential: current={state.current_stage.value}, expected={expected}, requested={target.value}")
        return report

    def require(relative: str, model_type: type) -> object | None:
        try:
            return _load_yaml(root, relative, model_type)
        except ValueError as exc:
            report.errors.append(str(exc))
            return None

    if target_index >= REAL_STAGE_CHAIN.index(Stage.INGESTED):
        try:
            inventory = _load_inventory(root)
            if not inventory.files:
                report.errors.append("input_inventory.json: files must contain at least one audited input")
            if inventory.files and not any(item.read_success for item in inventory.files):
                report.errors.append("input_inventory.json: no input file was successfully read")
            if not (root / "input_inventory.md").is_file():
                report.errors.append("missing required file: input_inventory.md")
        except ValueError as exc:
            report.errors.append(str(exc))
    if target_index >= REAL_STAGE_CHAIN.index(Stage.ANALYZED):
        require("problem_analysis.yaml", ProblemAnalysis)
    if target_index >= REAL_STAGE_CHAIN.index(Stage.DATA_READY):
        require("data_audit.yaml", DataAudit)
    candidates: ModelCandidates | None = None
    if target_index >= REAL_STAGE_CHAIN.index(Stage.MODELS_PROPOSED):
        loaded = require("model_candidates.yaml", ModelCandidates)
        candidates = loaded if isinstance(loaded, ModelCandidates) else None
    if target_index >= REAL_STAGE_CHAIN.index(Stage.MODEL_SELECTED) and candidates is not None:
        if not candidates.human_selection_approved:
            report.errors.append("model_candidates.yaml: human_selection_approved must be true before MODEL_SELECTED")
        if not any(item.decision == "adopt" for item in candidates.candidates):
            report.errors.append("model_candidates.yaml: exactly one candidate must record decision=adopt")
    if target_index >= REAL_STAGE_CHAIN.index(Stage.IMPLEMENTED):
        require("experiment_plan.yaml", ExperimentPlan)
    if target_index >= REAL_STAGE_CHAIN.index(Stage.VALIDATED):
        try:
            registry = validate_executed_results(root)
            if any(item.validation_status is not Status.PASSED for item in registry.results):
                report.errors.append("results/results.json: every key result must have validation_status=passed")
        except ValueError as exc:
            report.errors.append(str(exc))
        validation = require("results/validation.yaml", ValidationReportFile)
        if isinstance(validation, ValidationReportFile) and validation.status is not Status.PASSED:
            report.errors.append("results/validation.yaml: status must be passed")
    if target is Stage.PAPER_DRAFTED and not (root / "paper" / "main.tex").is_file():
        report.errors.append("missing required file: paper/main.tex")
    if target is Stage.AWAITING_HUMAN_APPROVAL:
        if state.current_stage is not Stage.PAPER_DRAFTED:
            report.errors.append("AWAITING_HUMAN_APPROVAL requires current stage PAPER_DRAFTED")
        if not (root / "paper" / "main.tex").is_file():
            report.errors.append("missing required file: paper/main.tex")
    return report


def advance_real_stage(workspace: Path, target: Stage) -> WorkspaceState:
    root = workspace.expanduser().resolve()
    gate = evaluate_gate(root, target)
    if not gate.passed:
        raise ValueError("; ".join(gate.errors))
    state = load_real_state(root)
    completed = [*state.completed_stages]
    if state.current_stage not in completed:
        completed.append(state.current_stage)
    state.current_stage = target
    state.completed_stages = completed
    state.updated_at = datetime.now(UTC)
    _write_yaml(root / "state.yaml", state)
    with (root / "decisions.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {state.updated_at.isoformat()} — Gate evidence accepted; advanced to `{target.value}`.\n")
    return state


def next_gate_report(workspace: Path) -> GateReport | None:
    state = load_real_state(workspace)
    try:
        index = REAL_STAGE_CHAIN.index(state.current_stage)
    except ValueError:
        return None
    if index + 1 >= len(REAL_STAGE_CHAIN):
        return None
    return evaluate_gate(workspace, REAL_STAGE_CHAIN[index + 1])
