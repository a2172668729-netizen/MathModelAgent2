"""Human-explicit benchmark scorecards for historical problem runs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from mmagent.real_models import BenchmarkScorecard, SubjectiveBenchmarkItem

SUBJECTIVE_DIMENSIONS = (
    "problem_understanding_completeness",
    "data_audit_completeness",
    "model_selection_evidence",
    "validation_completeness",
    "result_traceability",
    "paper_completeness",
    "reproducibility",
)


def new_scorecard() -> BenchmarkScorecard:
    return BenchmarkScorecard(
        generated_at=datetime.now(UTC),
        subjective_scores={name: SubjectiveBenchmarkItem() for name in SUBJECTIVE_DIMENSIONS},
    )


def write_scorecard(workspace: Path, scorecard: BenchmarkScorecard | None = None) -> tuple[Path, Path]:
    root = workspace.expanduser().resolve()
    value = scorecard or new_scorecard()
    yaml_path = root / "benchmark_scorecard.yaml"
    md_path = root / "benchmark_scorecard.md"
    yaml_path.write_text(
        yaml.safe_dump(value.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    md_path.write_text(_markdown(value), encoding="utf-8")
    return yaml_path, md_path


def load_scorecard(workspace: Path) -> BenchmarkScorecard:
    path = workspace.expanduser().resolve() / "benchmark_scorecard.yaml"
    try:
        return BenchmarkScorecard.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"benchmark_scorecard.yaml: invalid scorecard: {exc}") from exc


def _markdown(scorecard: BenchmarkScorecard) -> str:
    lines = [
        "# Benchmark scorecard",
        "",
        "Subjective dimensions require a human score (0–5) and rationale. Blank is not zero and is never auto-filled.",
        "",
        "| Dimension | Human required | Score | Rationale |",
        "|---|---:|---:|---|",
    ]
    for name, item in scorecard.subjective_scores.items():
        lines.append(f"| {name} | yes | {'' if item.score is None else item.score} | {item.rationale or ''} |")
    lines.extend(
        [
            "",
            "## Objective run statistics",
            "",
            f"- Code execution success rate: {scorecard.code_execution_success_rate if scorecard.code_execution_success_rate is not None else 'not_run'}",
            f"- Human interventions: {scorecard.human_intervention_count}",
            f"- Severe errors: {scorecard.severe_error_count}",
            f"- Total runtime (seconds): {scorecard.total_runtime_seconds}",
        ]
    )
    return "\n".join(lines) + "\n"
