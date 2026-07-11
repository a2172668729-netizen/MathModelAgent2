---
name: problem-analysis
description: Convert mathematical-modeling problem statements and authorized attachments into a traceable ProblemSpec containing subproblems, objectives, constraints, variables, deliverables, ambiguities, and evidence locators. Use when a workspace is CREATED or INGESTED and its problem specification must be created or corrected before data or model work begins.
---

# Problem Analysis

Structure the problem without solving it.

## Inputs

- Read every authorized file under `input/` and record its SHA-256 or existing metadata.
- Read existing `problem_spec.yaml`, `assumptions.yaml`, and user decisions.
- Treat unreadable files, missing pages, and ambiguous statements as explicit blockers.

## Workflow

1. Separate literal requirements from interpretation.
2. Enumerate every subproblem and its deliverables.
3. Define objectives, hard/soft/data constraints, variables, units, domains, and dependencies.
4. Record each proposed assumption with rationale, impact, evidence, and `not_run` validation status.
5. Cite the source file and page, sheet, table, or paragraph for every nontrivial extracted condition.
6. Ask for a human checkpoint when alternative interpretations would change the model family or feasible region.

## Outputs

- Write schema-valid `problem_spec.yaml`.
- Write schema-valid `assumptions.yaml` and explanatory `assumptions.md`.
- Append confirmed interpretation decisions to `decisions.md`.

## Acceptance

Accept only when every requested deliverable maps to a subproblem, every referenced objective/constraint ID resolves, units and unknowns are explicit, and unresolved ambiguity is visible. Do not propose algorithms, invent missing conditions, or advance beyond `ANALYZED`.

