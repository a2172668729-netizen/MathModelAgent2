"""Strict contracts for executable regression benchmark cases and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from mmagent.models import StrictModel, normalize_relative_path


class NumericExpectation(StrictModel):
    path: str
    minimum: float | None = None
    maximum: float | None = None
    absolute_tolerance: float = Field(default=1e-8, ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "NumericExpectation":
        if self.minimum is None and self.maximum is None:
            raise ValueError("numeric expectation requires minimum or maximum")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("numeric expectation minimum exceeds maximum")
        return self


class StructuralExpectations(StrictModel):
    required_files: list[str]
    minimum_figures: int = Field(ge=0)
    minimum_tables: int = Field(ge=0)
    minimum_pdf_pages: int = Field(ge=1)
    maximum_pdf_pages: int = Field(ge=1)
    required_pdf_text: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "StructuralExpectations":
        object.__setattr__(self, "required_files", [normalize_relative_path(value) for value in self.required_files])
        if self.minimum_pdf_pages > self.maximum_pdf_pages:
            raise ValueError("minimum_pdf_pages exceeds maximum_pdf_pages")
        return self


class BenchmarkCase(StrictModel):
    schema_version: Literal["1.0"]
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    title: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str]
    smoke: bool = False
    expected_outcome: Literal["passed", "failed"] = "passed"
    timeout_seconds: float = Field(gt=0, le=1800)
    random_seed: int = Field(ge=0)
    problem_file: str = "problem.md"
    data_generator: str = "generate_data.py"
    solver_profile: str
    solver_parameters: dict[str, Any] = Field(default_factory=dict)
    expected_modeling_steps: list[str] = Field(min_length=1)
    hard_checks: list[str] = Field(min_length=1)
    numeric_expectations: list[NumericExpectation] = Field(default_factory=list)
    structural_expectations: StructuralExpectations
    prohibited_errors: list[str] = Field(min_length=1)
    known_ambiguities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_paths_and_tags(self) -> "BenchmarkCase":
        object.__setattr__(self, "problem_file", normalize_relative_path(self.problem_file))
        object.__setattr__(self, "data_generator", normalize_relative_path(self.data_generator))
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("case tags must be unique")
        return self


class MetricResult(StrictModel):
    id: str
    tier: Literal["hard", "quality", "warning"]
    status: Literal["passed", "failed", "warning", "not_run", "blocked"]
    message: str
    evidence: list[str] = Field(default_factory=list)
    points_awarded: float | None = None
    points_available: float | None = None


class CaseReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    case_id: str
    title: str
    expected_outcome: Literal["passed", "failed"]
    status: Literal["passed", "failed", "expected_failure_observed", "unexpected_pass"]
    started_at: str
    finished_at: str
    duration_seconds: float
    attempts: list[str]
    metrics: list[MetricResult]
    quality_score: float = Field(ge=0, le=100)
    hard_failures: list[str]
    warnings: list[str]
    artifact_root: str
    diagnostic_report: str | None = None


class SuiteReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    mode: Literal["single", "tag", "all", "smoke", "full"]
    status: Literal["passed", "failed"]
    started_at: str
    finished_at: str
    duration_seconds: float
    configuration: dict[str, Any]
    code_version: dict[str, Any]
    environment: dict[str, Any]
    cases: list[CaseReport]
    totals: dict[str, Any]
