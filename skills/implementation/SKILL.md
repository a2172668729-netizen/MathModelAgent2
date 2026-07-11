---
name: implementation
description: Implement a human-approved mathematical model as reproducible Python code with typed interfaces, deterministic configuration, tests, input hashes, logs, metrics, and structured experiment artifacts. Use only after `models/selected/selection.yaml` is approved and the workspace is ready to move from MODEL_SELECTED to IMPLEMENTED.
---

# Model Implementation

Translate the approved mathematics into code without changing the model silently.

## Workflow

1. Read the selected model, equations, constraints, audited data, and evaluation protocol.
2. Write problem-specific code under `code/` using `pathlib.Path` and workspace-relative data paths.
3. Separate loading, preprocessing, model logic, evaluation, and output serialization.
4. Record deterministic seeds and solver tolerances; expose unavoidable nondeterminism.
5. Add tests for equations, constraints, small known cases, and failure behavior.
6. Run the code and tests. Save stdout, stderr, parameters, environment, input hashes, metrics, and artifacts.

## Outputs

- Produce schema-valid `results/experiment.yaml` and append-only `runs/<run-id>.yaml`.
- Keep failed outputs and logs with `failed` status.
- Update state to `IMPLEMENTED` only after a fresh result validates against its schema.

## Acceptance

Accept only when the executed code matches the documented equations, tests actually pass, no absolute personal path is required, and all reported numbers come from the persisted result. Do not generate success artifacts without running the code.

