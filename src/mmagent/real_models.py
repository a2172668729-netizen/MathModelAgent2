"""Strict persisted contracts for real-problem readiness artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from mmagent.models import Identifier, Scalar, Status, StrictModel, normalize_relative_path


class EvidenceItem(StrictModel):
    statement: str = Field(min_length=2)
    source_refs: list[str] = Field(min_length=1)

    _refs = field_validator("source_refs")(
        lambda value: [normalize_relative_path(item) for item in value]
    )


class ProblemAnalysis(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    subproblems: list[str] = Field(min_length=1)
    known_conditions: list[EvidenceItem] = Field(min_length=1)
    objectives: list[str] = Field(min_length=1)
    constraints: list[EvidenceItem] = Field(min_length=1)
    problem_facts: list[EvidenceItem] = Field(min_length=1)
    model_assumptions: list[str] = Field(min_length=1)
    ambiguities_and_risks: list[str] = Field(min_length=1)


class FieldAudit(StrictModel):
    name: str = Field(min_length=1)
    inferred_type: str = Field(min_length=1)
    unit: str | None = None
    missing_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    anomaly_notes: list[str]


class DatasetAudit(StrictModel):
    path: str
    fields: list[FieldAudit] = Field(min_length=1)
    cleaning_operations: list[str]
    data_risks: list[str] = Field(min_length=1)

    _path = field_validator("path")(normalize_relative_path)


class DataAudit(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    datasets: list[DatasetAudit] = Field(min_length=1)


class CandidateModel(StrictModel):
    id: Identifier
    name: str = Field(min_length=2)
    applicability: list[str] = Field(min_length=1)
    advantages: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    validation_methods: list[str] = Field(min_length=1)
    decision: Literal["adopt", "reject", "undecided"]
    decision_reason: str = Field(min_length=3)


class ModelCandidates(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    candidates: list[CandidateModel] = Field(min_length=2)
    human_selection_approved: bool = False

    @model_validator(mode="after")
    def require_one_adopted_model_for_approval(self) -> "ModelCandidates":
        adopted = [item for item in self.candidates if item.decision == "adopt"]
        if self.human_selection_approved and len(adopted) != 1:
            raise ValueError("human-approved selection requires exactly one adopted model")
        return self


class PlannedExperiment(StrictModel):
    id: Identifier
    description: str = Field(min_length=3)
    model_id: Identifier


class ExperimentPlan(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    baseline: PlannedExperiment
    experiments: list[PlannedExperiment] = Field(min_length=1)
    evaluation_metrics: list[str] = Field(min_length=1)
    random_seeds: list[int] = Field(min_length=1)
    training_validation_method: str = Field(min_length=3)
    sensitivity_or_robustness_plan: list[str] = Field(min_length=1)

    @field_validator("random_seeds")
    @classmethod
    def seeds_are_nonnegative(cls, value: list[int]) -> list[int]:
        if any(seed < 0 for seed in value):
            raise ValueError("random seeds must be nonnegative")
        return value


class SheetMetadata(StrictModel):
    name: str
    rows: int = Field(ge=0)
    columns: int = Field(ge=0)
    field_names: list[str]


class InputInventoryEntry(StrictModel):
    filename: str = Field(min_length=1)
    relative_path: str
    file_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    read_success: bool
    sheets: list[SheetMetadata] = Field(default_factory=list)
    parse_error: str | None = None

    _path = field_validator("relative_path")(normalize_relative_path)

    @model_validator(mode="after")
    def error_matches_status(self) -> "InputInventoryEntry":
        if self.read_success == (self.parse_error is not None):
            raise ValueError("parse_error must be present exactly when read_success is false")
        return self


class InputInventory(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime
    input_root: Literal["input"] = "input"
    files: list[InputInventoryEntry]


class ResultEntry(StrictModel):
    id: Identifier
    kind: Literal["scalar", "parameter", "table", "figure"]
    name: str = Field(min_length=1)
    value: Scalar | None = None
    unit: str | None = None
    artifact_path: str | None = None
    latex_macro: str | None = Field(default=None, pattern=r"^[A-Za-z]+$")
    model_name: str = Field(min_length=2)
    data_version: str = Field(min_length=1)
    experiment_id: Identifier
    source_script: str
    generated_at: datetime
    validation_status: Status

    _source = field_validator("source_script")(normalize_relative_path)

    @field_validator("artifact_path")
    @classmethod
    def artifact_is_relative(cls, value: str | None) -> str | None:
        return None if value is None else normalize_relative_path(value)

    @model_validator(mode="after")
    def kind_has_payload(self) -> "ResultEntry":
        if self.kind in {"scalar", "parameter"} and self.value is None:
            raise ValueError("scalar and parameter results require value")
        if self.kind in {"table", "figure"} and self.artifact_path is None:
            raise ValueError("table and figure results require artifact_path")
        if self.latex_macro and self.kind not in {"scalar", "parameter"}:
            raise ValueError("LaTeX macros are only supported for scalar or parameter results")
        return self


class ResultsRegistry(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    results: list[ResultEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids_and_macros(self) -> "ResultsRegistry":
        ids = [item.id for item in self.results]
        macros = [item.latex_macro for item in self.results if item.latex_macro]
        if len(ids) != len(set(ids)):
            raise ValueError("result ids must be unique")
        if len(macros) != len(set(macros)):
            raise ValueError("LaTeX macro names must be unique")
        return self


class SubjectiveBenchmarkItem(StrictModel):
    requires_human_score: Literal[True] = True
    score: float | None = Field(default=None, ge=0, le=5)
    rationale: str | None = None

    @model_validator(mode="after")
    def score_requires_rationale(self) -> "SubjectiveBenchmarkItem":
        if (self.score is None) != (self.rationale is None):
            raise ValueError("a human score and rationale must be recorded together")
        return self


class BenchmarkScorecard(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime
    subjective_scores: dict[str, SubjectiveBenchmarkItem]
    code_execution_success_rate: float | None = Field(default=None, ge=0, le=1)
    human_intervention_count: int = Field(default=0, ge=0)
    severe_error_count: int = Field(default=0, ge=0)
    total_runtime_seconds: float = Field(default=0, ge=0)

    @field_validator("subjective_scores")
    @classmethod
    def required_subjective_dimensions(
        cls, value: dict[str, SubjectiveBenchmarkItem]
    ) -> dict[str, SubjectiveBenchmarkItem]:
        required = {
            "problem_understanding_completeness",
            "data_audit_completeness",
            "model_selection_evidence",
            "validation_completeness",
            "result_traceability",
            "paper_completeness",
            "reproducibility",
        }
        missing = sorted(required - set(value))
        if missing:
            raise ValueError("missing subjective score dimensions: " + ", ".join(missing))
        return value
