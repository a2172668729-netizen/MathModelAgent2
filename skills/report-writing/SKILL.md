---
name: report-writing
description: Draft Chinese mathematical-modeling reports and LaTeX sources strictly from approved problem specifications, verified citations, passed validation findings, structured metrics, and provenance manifests. Use after VALIDATED when a technical report or paper draft must be generated without inventing numbers, sources, experiments, or format compliance.
---

# Evidence Report Writing

Treat persisted artifacts as the only factual source.

## Workflow

1. Read `problem_spec.yaml`, decisions, selected model, run manifests, experiment, validation, figure/table metadata, and verified citations.
2. Build a claim-to-evidence map before drafting.
3. Write the problem restatement, assumptions, symbols, model, solution, results, validation, limitations, and references.
4. Copy numeric precision and units from structured results; never recompute silently in prose.
5. Label provisional competition-format rules and internal templates accurately.
6. Generate Markdown and LaTeX source, then a report manifest listing every source artifact.

## Outputs

- Write drafts under `reports/` and `paper/`; never write directly to `final/`.
- Record unresolved claims as blockers or explicit limitations.
- Route expression-only revision to `$academic-humanizer-zh`, then rerun factual consistency checks.

## Acceptance

Accept `PAPER_DRAFTED` only when every quantitative claim resolves to a persisted result, every citation supports its nearby statement, and validation limitations remain visible. Do not claim official format compliance or award quality.

