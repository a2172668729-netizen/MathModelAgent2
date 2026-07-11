"""Creation and read-only validation of MathModelAgent workspaces."""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from mmagent.models import (
    AssumptionsFile,
    DatasetMetadata,
    Experiment,
    ModelCandidate,
    ModelSelection,
    PdfAcceptance,
    ProblemSpec,
    ReportManifest,
    ReviewReportFile,
    RunManifest,
    Stage,
    Status,
    ValidationReportFile,
    WorkspaceState,
)

WORKSPACE_DIRECTORIES = (
    "input",
    "research/sources",
    "data/raw",
    "data/processed",
    "data/metadata",
    "models/candidates",
    "models/selected",
    "code",
    "results",
    "figures",
    "tables",
    "reports",
    "paper",
    "review",
    "runs",
    "final",
)
WORKSPACE_FILES = (
    "problem_spec.yaml",
    "assumptions.yaml",
    "assumptions.md",
    "state.yaml",
    "run_manifest.yaml",
    "decisions.md",
)


@dataclass(slots=True)
class InitResult:
    root: Path
    created: list[Path] = field(default_factory=list)
    existing: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class ValidationReport:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _workspace_id(root: Path) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", root.name.lower()).strip("-_")
    if not slug or not slug[0].isalpha():
        slug = f"workspace-{slug or 'new'}"
    if len(slug) < 2:
        slug = f"{slug}-workspace"
    return slug[:64]


def _dump_yaml(path: Path, model: object) -> None:
    data = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def initialize_workspace(root: Path) -> InitResult:
    root = root.expanduser().resolve()
    result = InitResult(root=root)
    if root.exists() and not root.is_dir():
        raise ValueError(f"workspace path exists but is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)

    for relative in WORKSPACE_DIRECTORIES:
        target = root / relative
        if target.exists():
            if not target.is_dir():
                raise ValueError(f"required directory is occupied by a file: {relative}")
            result.existing.append(target)
        else:
            target.mkdir(parents=True)
            result.created.append(target)

    now = datetime.now(UTC)
    identifier = _workspace_id(root)
    problem = ProblemSpec(
        problem_id=identifier,
        title="待填写赛题",
        subproblems=[{"id": "problem-1", "prompt": "待根据原始赛题填写", "deliverables": ["待确认"]}],
    )
    assumptions = AssumptionsFile()
    state = WorkspaceState(
        workspace_id=identifier,
        updated_at=now,
        artifacts={
            "problem_spec": "problem_spec.yaml",
            "assumptions_data": "assumptions.yaml",
            "assumptions_notes": "assumptions.md",
            "run_manifest": "run_manifest.yaml",
        },
    )
    manifest = RunManifest(
        run_id="initialization",
        stage=Stage.CREATED,
        status=Status.PASSED,
        started_at=now,
        finished_at=now,
        command=["mmagent", "init", root.name],
        python_version=platform.python_version(),
        platform=platform.platform(),
        artifact_paths=[
            "problem_spec.yaml",
            "assumptions.yaml",
            "assumptions.md",
            "state.yaml",
            "run_manifest.yaml",
            "decisions.md",
        ],
    )
    payloads = {
        "problem_spec.yaml": problem,
        "assumptions.yaml": assumptions,
        "state.yaml": state,
        "run_manifest.yaml": manifest,
    }
    for relative, model in payloads.items():
        target = root / relative
        if target.exists():
            if not target.is_file():
                raise ValueError(f"required file path is occupied by a directory: {relative}")
            result.existing.append(target)
        else:
            _dump_yaml(target, model)
            result.created.append(target)

    decisions = root / "decisions.md"
    if decisions.exists():
        if not decisions.is_file():
            raise ValueError("required file path is occupied by a directory: decisions.md")
        result.existing.append(decisions)
    else:
        decisions.write_text("# Decisions\n\n- Workspace initialized; problem interpretation is not yet approved.\n", encoding="utf-8")
        result.created.append(decisions)
    assumption_notes = root / "assumptions.md"
    if assumption_notes.exists():
        if not assumption_notes.is_file():
            raise ValueError("required file path is occupied by a directory: assumptions.md")
        result.existing.append(assumption_notes)
    else:
        assumption_notes.write_text(
            "# Assumption notes\n\n`assumptions.yaml` is the structured source of truth. "
            "Use this file for human rationale and checkpoint discussion; do not add untracked model claims.\n",
            encoding="utf-8",
        )
        result.created.append(assumption_notes)
    return result


def _load_yaml_model(root: Path, relative: str, model_type: type) -> object:
    path = root / relative
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"{relative}: cannot read YAML: {exc}") from exc
    try:
        return model_type.model_validate(raw)
    except ValidationError as exc:
        messages = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}" for error in exc.errors()
        )
        raise ValueError(f"{relative}: schema error: {messages}") from exc


def validate_workspace(root: Path) -> ValidationReport:
    root = root.expanduser().resolve()
    report = ValidationReport(root=root)
    if not root.is_dir():
        report.errors.append(f"workspace does not exist: {root}")
        return report

    state_path = root / "state.yaml"
    if state_path.is_file():
        try:
            raw_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            raw_state = None
        if isinstance(raw_state, dict) and raw_state.get("workspace_kind") == "real_problem":
            from mmagent.real_problem import next_gate_report, validate_real_structure

            report.errors.extend(validate_real_structure(root))
            if not report.errors:
                gate = next_gate_report(root)
                if gate is not None and gate.errors:
                    report.warnings.append(
                        f"workspace is incomplete at {raw_state.get('current_stage', 'unknown')}; "
                        f"next gate {gate.target.value} is blocked"
                    )
                    report.warnings.extend(f"missing for {gate.target.value}: {error}" for error in gate.errors)
            return report

    for relative in WORKSPACE_DIRECTORIES:
        if not (root / relative).is_dir():
            report.errors.append(f"missing directory: {relative}")
    for relative in WORKSPACE_FILES:
        if not (root / relative).is_file():
            report.errors.append(f"missing file: {relative}")

    loaded: dict[str, object] = {}
    schemas = {
        "problem_spec.yaml": ProblemSpec,
        "assumptions.yaml": AssumptionsFile,
        "state.yaml": WorkspaceState,
        "run_manifest.yaml": RunManifest,
    }
    for relative, model_type in schemas.items():
        if (root / relative).is_file():
            try:
                loaded[relative] = _load_yaml_model(root, relative, model_type)
            except ValueError as exc:
                report.errors.append(str(exc))

    optional_schemas: list[tuple[str, type]] = [
        ("results/experiment.yaml", Experiment),
        ("results/validation.yaml", ValidationReportFile),
        ("reports/report_manifest.yaml", ReportManifest),
        ("reports/pdf_acceptance.yaml", PdfAcceptance),
        ("review/review_report.yaml", ReviewReportFile),
    ]
    optional_schemas.extend(
        (path.relative_to(root).as_posix(), DatasetMetadata) for path in (root / "data" / "metadata").glob("*.yaml")
    )
    optional_schemas.extend(
        (path.relative_to(root).as_posix(), ModelCandidate) for path in (root / "models" / "candidates").glob("*.yaml")
    )
    optional_schemas.extend(
        (path.relative_to(root).as_posix(), ModelSelection) for path in (root / "models" / "selected").glob("*.yaml")
    )
    optional_schemas.extend(
        (path.relative_to(root).as_posix(), RunManifest) for path in (root / "runs").glob("*.yaml")
    )
    for relative, model_type in optional_schemas:
        if (root / relative).is_file():
            try:
                _load_yaml_model(root, relative, model_type)
            except ValueError as exc:
                report.errors.append(str(exc))

    referenced_paths: set[str] = set()
    problem = loaded.get("problem_spec.yaml")
    if isinstance(problem, ProblemSpec):
        referenced_paths.update(problem.source_files)
    state = loaded.get("state.yaml")
    if isinstance(state, WorkspaceState):
        referenced_paths.update(state.artifacts.values())
    manifest = loaded.get("run_manifest.yaml")
    if isinstance(manifest, RunManifest):
        referenced_paths.update(manifest.input_hashes)
        referenced_paths.update(manifest.artifact_paths)

    for relative in sorted(referenced_paths):
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            report.errors.append(f"referenced path escapes workspace: {relative}")
            continue
        if not target.exists():
            report.errors.append(f"referenced path does not exist: {relative}")
    return report


def read_status(root: Path) -> tuple[WorkspaceState | None, ValidationReport]:
    report = validate_workspace(root)
    state_path = root.expanduser().resolve() / "state.yaml"
    if not state_path.is_file():
        return None, report
    try:
        state = _load_yaml_model(root.expanduser().resolve(), "state.yaml", WorkspaceState)
    except ValueError:
        return None, report
    return state if isinstance(state, WorkspaceState) else None, report


def cwd_is_writable(path: Path) -> bool:
    """Use the OS access check without creating a probe file."""
    return path.is_dir() and os.access(path, os.W_OK)
