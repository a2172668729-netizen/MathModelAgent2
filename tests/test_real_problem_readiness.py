from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from mmagent.benchmark import load_scorecard
from mmagent.input_audit import audit_inputs
from mmagent.models import Stage
from mmagent.real_problem import (
    REAL_WORKSPACE_DIRECTORIES,
    advance_real_stage,
    create_real_workspace,
    evaluate_gate,
)
from mmagent.results_registry import generate_latex_macros
from mmagent.workspace import read_status, validate_workspace


def _yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _prepare_ingested(root: Path) -> None:
    (root / "input" / "problem.md").write_text("A historical modeling problem.", encoding="utf-8")
    pd.DataFrame({"time": [1, 2], "value": [3.0, 4.0]}).to_csv(root / "input" / "data.csv", index=False)
    audit_inputs(root)
    advance_real_stage(root, Stage.INGESTED)


def _write_stage_evidence(root: Path) -> None:
    _yaml(
        root / "problem_analysis.yaml",
        {
            "schema_version": "1.0",
            "subproblems": ["Estimate the response."],
            "known_conditions": [{"statement": "Two observations are supplied.", "source_refs": ["input/data.csv"]}],
            "objectives": ["Estimate the response."],
            "constraints": [{"statement": "Use supplied observations.", "source_refs": ["input/problem.md"]}],
            "problem_facts": [{"statement": "The statement is historical.", "source_refs": ["input/problem.md"]}],
            "model_assumptions": ["Measurement error is finite."],
            "ambiguities_and_risks": ["The sample is very small."],
        },
    )
    _yaml(
        root / "data_audit.yaml",
        {
            "schema_version": "1.0",
            "datasets": [
                {
                    "path": "input/data.csv",
                    "fields": [
                        {
                            "name": "time",
                            "inferred_type": "integer",
                            "unit": "s",
                            "missing_count": 0,
                            "duplicate_count": 0,
                            "anomaly_notes": [],
                        }
                    ],
                    "cleaning_operations": ["No cleaning applied."],
                    "data_risks": ["Only two rows are available."],
                }
            ],
        },
    )
    _yaml(
        root / "model_candidates.yaml",
        {
            "schema_version": "1.0",
            "candidates": [
                {
                    "id": "linear-model",
                    "name": "Linear model",
                    "applicability": ["Approximately linear response."],
                    "advantages": ["Interpretable baseline."],
                    "risks": ["May underfit."],
                    "validation_methods": ["Residual check."],
                    "decision": "adopt",
                    "decision_reason": "Selected as the approved baseline.",
                },
                {
                    "id": "constant-model",
                    "name": "Constant baseline",
                    "applicability": ["Response variation is negligible."],
                    "advantages": ["Simple reference."],
                    "risks": ["Likely to underfit."],
                    "validation_methods": ["Compare RMSE."],
                    "decision": "reject",
                    "decision_reason": "Rejected because observed values vary with time.",
                }
            ],
            "human_selection_approved": True,
        },
    )
    _yaml(
        root / "experiment_plan.yaml",
        {
            "schema_version": "1.0",
            "baseline": {"id": "baseline-run", "description": "Fit the baseline.", "model_id": "linear-model"},
            "experiments": [
                {"id": "robustness-run", "description": "Perturb observations.", "model_id": "linear-model"}
            ],
            "evaluation_metrics": ["RMSE"],
            "random_seeds": [42],
            "training_validation_method": "Leave-one-out validation.",
            "sensitivity_or_robustness_plan": ["Perturb each observation by one percent."],
        },
    )


def _write_executed_results(root: Path) -> None:
    (root / "code" / "solve.py").write_text("print('executed externally for test fixture')\n", encoding="utf-8")
    now = datetime.now(UTC).isoformat()
    (root / "results" / "results.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "results": [
                    {
                        "id": "rmse-result",
                        "kind": "scalar",
                        "name": "RMSE",
                        "value": 0.125,
                        "unit": "m",
                        "latex_macro": "ModelRMSE",
                        "model_name": "Linear model",
                        "data_version": "sha256:test-fixture",
                        "experiment_id": "baseline-run",
                        "source_script": "code/solve.py",
                        "generated_at": now,
                        "validation_status": "passed",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _yaml(
        root / "runs" / "baseline-run.yaml",
        {
            "schema_version": "1.0",
            "run_id": "baseline-run",
            "stage": "IMPLEMENTED",
            "status": "passed",
            "started_at": now,
            "finished_at": now,
            "command": ["python", "code/solve.py"],
            "python_version": "3.12",
            "platform": "test-platform",
            "input_hashes": {"input/data.csv": "0" * 64},
            "artifact_paths": ["results/results.json"],
        },
    )
    _yaml(
        root / "results" / "validation.yaml",
        {
            "schema_version": "1.0",
            "experiment_path": "results/results.json",
            "status": "passed",
            "checked_at": now,
            "findings": [
                {
                    "id": "consistency-check",
                    "category": "consistency",
                    "severity": "info",
                    "status": "passed",
                    "evidence_path": "results/results.json",
                    "message": "The registered value matches the persisted test result.",
                }
            ],
        },
    )


def test_new_workspace_is_valid_but_objectively_incomplete(tmp_path: Path) -> None:
    root = create_real_workspace("history-2020-a", tmp_path)

    assert all((root / relative).is_dir() for relative in REAL_WORKSPACE_DIRECTORIES)
    state, report = read_status(root)
    assert state is not None and state.current_stage is Stage.CREATED
    assert report.passed
    assert any("next gate INGESTED is blocked" in warning for warning in report.warnings)
    assert load_scorecard(root).subjective_scores
    assert all(item.score is None for item in load_scorecard(root).subjective_scores.values())


def test_input_inventory_hash_csv_xlsx_and_unsupported_diagnostic(tmp_path: Path) -> None:
    root = create_real_workspace("history-inputs", tmp_path)
    csv_path = root / "input" / "table.csv"
    xlsx_path = root / "input" / "book.xlsx"
    unknown_path = root / "input" / "archive.bin"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}).to_excel(writer, sheet_name="observations", index=False)
    unknown_path.write_bytes(b"not a supported attachment")

    before = {path: path.read_bytes() for path in (csv_path, xlsx_path, unknown_path)}
    inventory = audit_inputs(root)
    entries = {entry.filename: entry for entry in inventory.files}

    assert entries["table.csv"].sha256 == hashlib.sha256(before[csv_path]).hexdigest()
    assert entries["table.csv"].sheets[0].field_names == ["a", "b"]
    assert entries["table.csv"].sheets[0].rows == 2
    assert entries["book.xlsx"].sheets[0].name == "observations"
    assert entries["book.xlsx"].sheets[0].columns == 2
    assert not entries["archive.bin"].read_success
    assert "unsupported attachment type" in (entries["archive.bin"].parse_error or "")
    assert before == {path: path.read_bytes() for path in before}


def test_schema_missing_field_and_stage_skip_are_explicit(tmp_path: Path) -> None:
    root = create_real_workspace("history-gates", tmp_path)
    _prepare_ingested(root)
    (root / "problem_analysis.yaml").write_text("subproblems:\n  - one\n", encoding="utf-8")

    gate = evaluate_gate(root, Stage.ANALYZED)
    assert not gate.passed
    assert any("known_conditions" in error for error in gate.errors)
    with pytest.raises(ValueError, match="stage transition must be sequential"):
        advance_real_stage(root, Stage.IMPLEMENTED)


def test_complete_evidence_chain_results_macros_and_manual_final_gate(tmp_path: Path) -> None:
    root = create_real_workspace("history-chain", tmp_path)
    _prepare_ingested(root)
    _write_stage_evidence(root)

    for stage in (Stage.ANALYZED, Stage.DATA_READY, Stage.MODELS_PROPOSED, Stage.MODEL_SELECTED, Stage.IMPLEMENTED):
        advance_real_stage(root, stage)

    before = evaluate_gate(root, Stage.VALIDATED)
    assert any("results/results.json" in error for error in before.errors)
    _write_executed_results(root)
    advance_real_stage(root, Stage.VALIDATED)

    macro_path = generate_latex_macros(root)
    assert "\\newcommand{\\ModelRMSE}{0.125\\,m}" in macro_path.read_text(encoding="utf-8")
    (root / "paper" / "main.tex").write_text("\\input{generated/results_macros.tex}\n", encoding="utf-8")
    advance_real_stage(root, Stage.PAPER_DRAFTED)
    advance_real_stage(root, Stage.AWAITING_HUMAN_APPROVAL)

    reviewed = evaluate_gate(root, Stage.REVIEWED)
    assert not reviewed.passed
    assert "never an automated transition" in reviewed.errors[0]


def test_workspace_validation_rejects_optional_schema_with_missing_fields(tmp_path: Path) -> None:
    root = create_real_workspace("history-schema", tmp_path)
    (root / "experiment_plan.yaml").write_text("schema_version: '1.0'\n", encoding="utf-8")

    report = validate_workspace(root)

    assert not report.passed
    assert any("baseline" in error for error in report.errors)
