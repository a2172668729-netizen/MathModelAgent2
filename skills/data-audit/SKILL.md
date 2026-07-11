---
name: data-audit
description: Audit authorized mathematical-modeling datasets for lineage, license, hashes, schema, units, missingness, anomalies, time semantics, leakage, and fitness for the stated objectives. Use after problem analysis and before model design whenever CSV, Excel, image-derived, or other structured data must be trusted and documented.
---

# Data Audit

Preserve raw inputs and distinguish observed, corrected, derived, and synthetic data.

## Workflow

1. Read `problem_spec.yaml` before inspecting data.
2. Inventory each dataset with relative path, media type, byte size, SHA-256, source, license, columns, units, and time grain.
3. Compute reproducible counts for rows, missing values, duplicates, invalid domains, and type failures.
4. Check join keys, sampling bias, target leakage, future leakage, encoding, unit conflicts, and unexplained transformations.
5. Keep raw files unchanged. Write transformations only under `data/processed/` with code and lineage.
6. Classify each finding as blocking, warning, or informational and link it to evidence.

## Outputs

- Write one schema-valid `DatasetMetadata` YAML under `data/metadata/` per dataset.
- Write `reports/data_audit.md` with computed evidence and unresolved risks.
- Register created artifacts in state only after files validate.

## Acceptance

Accept `DATA_READY` only when model-critical fields have known meaning and units, leakage risks are addressed, every modification is reproducible, and synthetic data is explicitly labeled. Never silently impute, delete, winsorize, or relabel data.

