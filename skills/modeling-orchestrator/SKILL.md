---
name: modeling-orchestrator
description: Coordinate an artifact-first mathematical-modeling workspace by inspecting persisted state, selecting only the next valid stage, routing work to the repository's specialist skills, enforcing human checkpoints, and resuming bounded failures. Use when starting, continuing, recovering, or auditing an end-to-end MathModelAgent workspace.
---

# Modeling Orchestrator

Coordinate stages; do not replace specialist analysis with an unsupported summary.

## Start

1. Read the repository `AGENTS.md`, workspace `state.yaml`, `decisions.md`, and latest `run_manifest.yaml`.
2. Run `mmagent validate-workspace <workspace>` before any stage write.
3. List the current stage, required inputs, existing artifacts, unresolved failures, and the next admissible stage.
4. Stop when required evidence or a human decision is missing.

## Route

- Route `CREATED`/`INGESTED` problem structuring to `$problem-analysis`.
- Route dataset readiness to `$data-audit`.
- Route candidate comparison and baseline design to `$model-design`.
- Route an approved selection to `$implementation`.
- Route persisted experiment artifacts to `$validation`.
- Route passed validation to `$report-writing`, then optionally `$academic-humanizer-zh`.
- Route final persisted artifacts to `$reviewer` in a read-only, context-isolated review.

## Control state

- Advance a state only after its acceptance checks pass and its outputs exist.
- Record every human checkpoint in `decisions.md` with time, choice, rationale, and affected artifacts.
- Preserve failed artifacts and logs. Retry only the failed stage, at most three times.
- Never launch parallel writers against `state.yaml`, `decisions.md`, or the same artifact path.
- Use `mmagent resume` only for the implemented deterministic Phase 2 contract.

## Finish

Report the current stage, artifacts written, commands actually run, checks passed, `not_run`/`blocked` checks, and the exact next human decision. Never describe the workspace as final while visual, identity, format, or reviewer gates remain incomplete.

