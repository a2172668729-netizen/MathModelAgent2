---
name: model-design
description: Design and compare baseline plus candidate mathematical models from an approved ProblemSpec and audited data, documenting assumptions, equations, data needs, interpretability, validation plans, and selection tradeoffs. Use when a workspace is DATA_READY and needs evidence-backed candidate models or a human model-selection checkpoint.
---

# Model Design

Prefer the simplest model that can answer the stated subproblem and survive validation.

## Workflow

1. Read the approved problem specification, assumptions, dataset metadata, and data-audit findings.
2. Define at least one simple baseline and two candidates when the task admits alternatives.
3. For each candidate, state equations, variables, required data, identifiability, constraints, strengths, limitations, computational cost, and failure modes.
4. Define a common evaluation protocol before seeing final results.
5. Reject candidates whose assumptions conflict with audited evidence.
6. Present a comparison table and request explicit human selection when the choice changes interpretation, cost, or risk.

## Outputs

- Write one schema-valid `ModelCandidate` YAML per candidate under `models/candidates/`.
- Write `reports/model_comparison.md` with an evidence-linked comparison.
- Write `models/selected/selection.yaml` only after an explicit human choice; record the decision in `decisions.md`.

## Acceptance

Accept `MODEL_SELECTED` only when the baseline is runnable, all compared IDs resolve, evaluation is fair, evidence supports the choice, and `approved_by_human` plus timestamp are present. Do not select a model because it is fashionable or complex.

