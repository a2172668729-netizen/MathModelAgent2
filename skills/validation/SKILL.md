---
name: validation
description: Independently validate persisted mathematical-model experiments through recomputation, baseline comparison, dimensional and boundary checks, residual or out-of-sample analysis, leakage review, sensitivity, robustness, and cross-artifact consistency. Use after IMPLEMENTED and before any result may be used for report writing.
---

# Model Validation

Act as an independent verifier. Do not modify solver code or reported metrics during validation.

## Workflow

1. Read the problem, selected model, run manifest, code, inputs, and structured experiment.
2. Verify input hashes and reproduce critical metrics independently.
3. Check dimensions, signs, domains, constraints, limiting cases, and small known cases.
4. Run the task-appropriate baseline, residual, sample-out, sensitivity, stability, and robustness checks.
5. Check for data leakage, overfitting, post-selection evaluation, and causal overstatement.
6. Compare numeric claims across results, tables, figures, and any existing text.

## Outputs

- Write schema-valid `results/validation.yaml` with evidence paths and per-check status.
- Keep unperformed checks as `not_run`; use `blocked` for missing evidence.
- Move to `VALIDATED` only when required critical checks pass.

## Acceptance

Never equate execution success with model correctness. A failed critical finding blocks report writing; a `not_run` check must remain visible in limitations.

