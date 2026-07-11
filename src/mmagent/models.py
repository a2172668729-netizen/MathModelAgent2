"""Strict, serializable schemas for persisted workspace artifacts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Scalar = bool | int | float | str
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")]


def normalize_relative_path(value: str) -> str:
    """Return a portable POSIX-style relative path or reject unsafe input."""
    normalized = str(value).replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be a non-empty workspace-relative path without '..'")
    if path.parts and ":" in path.parts[0]:
        raise ValueError("drive-qualified paths are not allowed")
    return path.as_posix()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Stage(StrEnum):
    CREATED = "CREATED"
    INGESTED = "INGESTED"
    ANALYZED = "ANALYZED"
    DATA_READY = "DATA_READY"
    MODELS_PROPOSED = "MODELS_PROPOSED"
    MODEL_SELECTED = "MODEL_SELECTED"
    IMPLEMENTED = "IMPLEMENTED"
    VALIDATED = "VALIDATED"
    PAPER_DRAFTED = "PAPER_DRAFTED"
    PAPER_HUMANIZED = "PAPER_HUMANIZED"
    FACT_CHECKED = "FACT_CHECKED"
    PDF_COMPILED = "PDF_COMPILED"
    FORMAT_CHECKED = "FORMAT_CHECKED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"
    FAILED = "FAILED"


class Status(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Objective(StrictModel):
    id: Identifier
    description: str = Field(min_length=3)
    direction: Literal["minimize", "maximize", "satisfy", "describe"]
    metric: str | None = None


class Constraint(StrictModel):
    id: Identifier
    description: str = Field(min_length=3)
    kind: Literal["hard", "soft", "domain", "data"]
    expression: str | None = None
    source: str = Field(min_length=1)


class Variable(StrictModel):
    symbol: str = Field(min_length=1)
    meaning: str = Field(min_length=2)
    role: Literal["decision", "state", "parameter", "observed", "derived"]
    unit: str | None = None
    domain: str | None = None


class SubProblem(StrictModel):
    id: Identifier
    prompt: str = Field(min_length=3)
    objective_ids: list[Identifier] = Field(default_factory=list)
    constraint_ids: list[Identifier] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)


class ProblemSpec(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    problem_id: Identifier
    title: str = Field(min_length=2)
    competition: str | None = None
    year: int | None = Field(default=None, ge=2000, le=2100)
    source_files: list[str] = Field(default_factory=list)
    subproblems: list[SubProblem] = Field(min_length=1)
    objectives: list[Objective] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)

    _source_paths = field_validator("source_files")(lambda value: [normalize_relative_path(item) for item in value])

    @model_validator(mode="after")
    def references_exist(self) -> "ProblemSpec":
        objective_ids = {item.id for item in self.objectives}
        constraint_ids = {item.id for item in self.constraints}
        if len(objective_ids) != len(self.objectives) or len(constraint_ids) != len(self.constraints):
            raise ValueError("objective and constraint ids must be unique")
        for subproblem in self.subproblems:
            if not set(subproblem.objective_ids) <= objective_ids:
                raise ValueError(f"{subproblem.id} references an unknown objective")
            if not set(subproblem.constraint_ids) <= constraint_ids:
                raise ValueError(f"{subproblem.id} references an unknown constraint")
        return self


class Assumption(StrictModel):
    id: Identifier
    statement: str = Field(min_length=3)
    rationale: str = Field(min_length=3)
    impact: str = Field(min_length=3)
    validation_status: Status = Status.NOT_RUN
    evidence_refs: list[str] = Field(default_factory=list)


class AssumptionsFile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    assumptions: list[Assumption] = Field(default_factory=list)


class DatasetMetadata(StrictModel):
    id: Identifier
    path: str
    media_type: str = Field(min_length=3)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    source: str = Field(min_length=1)
    license: str | None = None
    columns: list[str] = Field(default_factory=list)
    units: dict[str, str] = Field(default_factory=dict)
    quality_notes: list[str] = Field(default_factory=list)

    _path = field_validator("path")(normalize_relative_path)


class Citation(StrictModel):
    id: Identifier
    title: str = Field(min_length=2)
    authors: list[str] = Field(min_length=1)
    year: int | None = Field(default=None, ge=1000, le=2100)
    locator: str = Field(min_length=1)
    accessed_at: datetime | None = None
    verified: bool = False


class ModelCandidate(StrictModel):
    id: Identifier
    name: str = Field(min_length=2)
    purpose: str = Field(min_length=3)
    assumptions: list[Identifier] = Field(default_factory=list)
    required_dataset_ids: list[Identifier] = Field(default_factory=list)
    strengths: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    is_baseline: bool = False


class ModelSelection(StrictModel):
    selected_model_id: Identifier
    compared_model_ids: list[Identifier] = Field(min_length=2)
    evidence: list[str] = Field(min_length=1)
    approved_by_human: bool = False
    approved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> "ModelSelection":
        if self.selected_model_id not in self.compared_model_ids:
            raise ValueError("selected model must be included in compared_model_ids")
        if self.approved_by_human != (self.approved_at is not None):
            raise ValueError("approved_by_human and approved_at must be set together")
        return self


class Metric(StrictModel):
    name: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    unit: str | None = None
    split: Literal["train", "validation", "test", "full", "simulation"] = "full"
    higher_is_better: bool | None = None


class Experiment(StrictModel):
    id: Identifier
    model_id: Identifier
    status: Status
    command: list[str] = Field(min_length=1)
    random_seed: int | None = Field(default=None, ge=0)
    parameters: dict[str, Scalar] = Field(default_factory=dict)
    input_paths: list[str] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)

    _input_paths = field_validator("input_paths")(lambda value: [normalize_relative_path(item) for item in value])
    _artifact_paths = field_validator("artifact_paths")(lambda value: [normalize_relative_path(item) for item in value])


class ValidationFinding(StrictModel):
    id: Identifier
    category: Literal["dimension", "boundary", "residual", "leakage", "sensitivity", "robustness", "consistency"]
    severity: Severity
    status: Status
    evidence_path: str | None = None
    message: str = Field(min_length=3)

    @field_validator("evidence_path")
    @classmethod
    def validate_evidence_path(cls, value: str | None) -> str | None:
        return None if value is None else normalize_relative_path(value)


class ValidationReportFile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    experiment_path: str
    status: Status
    checked_at: datetime
    findings: list[ValidationFinding] = Field(min_length=1)

    _experiment_path = field_validator("experiment_path")(normalize_relative_path)

    @model_validator(mode="after")
    def findings_match_status(self) -> "ValidationReportFile":
        has_failure = any(item.status in {Status.FAILED, Status.BLOCKED} for item in self.findings)
        if self.status is Status.PASSED and has_failure:
            raise ValueError("passed validation report cannot contain failed or blocked findings")
        return self


class FigureMetadata(StrictModel):
    id: Identifier
    path: str
    caption: str = Field(min_length=3)
    source_artifacts: list[str] = Field(min_length=1)
    generated_by: list[str] = Field(min_length=1)

    _path = field_validator("path")(normalize_relative_path)
    _sources = field_validator("source_artifacts")(lambda value: [normalize_relative_path(item) for item in value])


class TableMetadata(FigureMetadata):
    columns: list[str] = Field(min_length=1)


class ReviewIssue(StrictModel):
    id: Identifier
    severity: Severity
    category: Literal["logic", "formula_code", "data", "citation", "figure", "format", "reproducibility", "identity"]
    description: str = Field(min_length=3)
    evidence_path: str
    recommended_action: str = Field(min_length=3)
    status: Literal["open", "resolved", "accepted_risk"] = "open"

    _evidence_path = field_validator("evidence_path")(normalize_relative_path)


class ReviewReportFile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Status
    reviewed_at: datetime
    reviewer_context: Literal["isolated"]
    source_artifacts: list[str] = Field(min_length=1)
    issues: list[ReviewIssue] = Field(default_factory=list)

    _source_artifacts = field_validator("source_artifacts")(
        lambda value: [normalize_relative_path(item) for item in value]
    )

    @model_validator(mode="after")
    def critical_issues_block_pass(self) -> "ReviewReportFile":
        blocking = any(
            issue.severity is Severity.CRITICAL and issue.status == "open" for issue in self.issues
        )
        if self.status is Status.PASSED and blocking:
            raise ValueError("passed review cannot contain open critical issues")
        return self


class RunManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: Identifier
    stage: Stage
    status: Status
    started_at: datetime
    finished_at: datetime | None = None
    command: list[str] = Field(min_length=1)
    python_version: str = Field(min_length=3)
    platform: str = Field(min_length=2)
    dependencies: dict[str, str] = Field(default_factory=dict)
    random_seed: int | None = Field(default=None, ge=0)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, Scalar] = Field(default_factory=dict)
    artifact_paths: list[str] = Field(default_factory=list)

    _artifacts = field_validator("artifact_paths")(lambda value: [normalize_relative_path(item) for item in value])

    @field_validator("input_hashes")
    @classmethod
    def validate_input_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        validated: dict[str, str] = {}
        for path, digest in value.items():
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError(f"input hash for {path!r} must be a lowercase SHA-256 digest")
            validated[normalize_relative_path(path)] = digest
        return validated

    @model_validator(mode="after")
    def validate_timestamps(self) -> "RunManifest":
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        return self


class ReportManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Status
    generated_at: datetime
    source_artifacts: list[str] = Field(min_length=1)
    generated_artifacts: list[str] = Field(min_length=1)

    _sources = field_validator("source_artifacts")(
        lambda value: [normalize_relative_path(item) for item in value]
    )
    _generated = field_validator("generated_artifacts")(
        lambda value: [normalize_relative_path(item) for item in value]
    )


class PdfAcceptance(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Status
    checked_at: datetime
    source_path: str
    pdf_path: str | None = None
    compiler: str | None = None
    attempts: int = Field(ge=0)
    structural_check: Status = Status.NOT_RUN
    visual_check: Status = Status.NOT_RUN
    identity_check: Status = Status.NOT_RUN
    log_path: str | None = None
    message: str = Field(min_length=3)

    _source_path = field_validator("source_path")(normalize_relative_path)

    @field_validator("pdf_path", "log_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return None if value is None else normalize_relative_path(value)


class WorkspaceState(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    workspace_kind: Literal["legacy", "real_problem"] = "legacy"
    workspace_id: Identifier
    current_stage: Stage = Stage.CREATED
    completed_stages: list[Stage] = Field(default_factory=list)
    failed_stage: Stage | None = None
    failure_summary: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime

    _artifacts = field_validator("artifacts")(lambda value: {key: normalize_relative_path(path) for key, path in value.items()})
