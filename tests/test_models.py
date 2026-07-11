from __future__ import annotations

import pytest
from pydantic import ValidationError

from mmagent.models import ModelSelection, ProblemSpec, ReviewReportFile, RunManifest, normalize_relative_path


def test_relative_path_normalizes_windows_separator() -> None:
    assert normalize_relative_path(r"data\raw\input.csv") == "data/raw/input.csv"


@pytest.mark.parametrize("value", ["../secret.txt", "/absolute/file", r"C:\Users\name\file.csv"])
def test_relative_path_rejects_escape_or_absolute(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_relative_path(value)


def test_problem_spec_rejects_unknown_objective_reference() -> None:
    with pytest.raises(ValidationError, match="unknown objective"):
        ProblemSpec.model_validate(
            {
                "problem_id": "sample-problem",
                "title": "示例题",
                "subproblems": [
                    {"id": "problem-1", "prompt": "完成任务", "objective_ids": ["objective-missing"]}
                ],
            }
        )


def test_model_selection_requires_selected_candidate_in_comparison() -> None:
    with pytest.raises(ValidationError, match="included in compared_model_ids"):
        ModelSelection.model_validate(
            {
                "selected_model_id": "model-a",
                "compared_model_ids": ["model-b", "model-c"],
                "evidence": ["results/comparison.yaml"],
            }
        )


def test_run_manifest_rejects_invalid_input_hash() -> None:
    with pytest.raises(ValidationError, match="lowercase SHA-256"):
        RunManifest.model_validate(
            {
                "run_id": "run-1",
                "stage": "CREATED",
                "status": "passed",
                "started_at": "2026-07-10T00:00:00Z",
                "command": ["mmagent", "status", "demo"],
                "python_version": "3.12.13",
                "platform": "Windows",
                "input_hashes": {"input/problem.pdf": "not-a-hash"},
            }
        )


def test_passed_review_rejects_open_critical_issue() -> None:
    with pytest.raises(ValidationError, match="open critical"):
        ReviewReportFile.model_validate(
            {
                "status": "passed",
                "reviewed_at": "2026-07-10T00:00:00Z",
                "reviewer_context": "isolated",
                "source_artifacts": ["paper/main.tex"],
                "issues": [
                    {
                        "id": "issue-1",
                        "severity": "critical",
                        "category": "reproducibility",
                        "description": "The reported result cannot be reproduced.",
                        "evidence_path": "results/experiment.yaml",
                        "recommended_action": "Provide the missing run manifest and rerun the experiment.",
                        "status": "open",
                    }
                ],
            }
        )
