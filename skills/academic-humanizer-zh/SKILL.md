---
name: academic-humanizer-zh
description: Refine Chinese mathematical-modeling academic prose while preserving every fact, formula, number, variable, citation, cross-reference, and experimental conclusion. Use when revising a Chinese paper draft after its technical claims have been validated and the user wants clearer, less mechanical academic expression without factual changes.
---

# Academic Humanizer Zh

Revise expression only. Treat the source artifacts as authoritative and keep technical meaning invariant.

## Required inputs

- Read the draft to revise.
- Read the structured results, figure/table manifests, and citation records referenced by the draft.
- Stop with `blocked` when a claim cannot be traced or when required evidence is missing.

## Workflow

1. Freeze protected tokens: numbers, units, formulas, variables, equation numbers, figure/table numbers, citation keys, URLs, filenames, proper nouns, and explicit conclusions.
2. Remove empty openings, inflated claims, promotional language, vague attribution, repetitive transitions, and mechanical parallelism.
3. Improve sentence order, subject clarity, terminology consistency, and the link between evidence and conclusion.
4. Preserve uncertainty and limitation language. Never strengthen correlation into causation or a provisional finding into a confirmed result.
5. Produce the revised text and a concise change log by category.
6. Compare the source and revision. Mark the result `not_run` unless protected-token and factual-consistency checks were actually performed.

## Prohibited changes

- Do not add or delete facts, assumptions, data, results, citations, or limitations.
- Do not alter formulas, symbols, numeric precision, units, signs, inequalities, rankings, or sample sizes.
- Do not renumber equations, figures, tables, sections, or references.
- Do not invent a citation, experiment, source, or validation result.
- Do not add personal voice, emotion, anecdotes, deliberate disorder, or conversational filler to imitate a human author.
- Do not claim compliance with a competition format unless the applicable official profile is verified.

## Acceptance

Accept only when every protected token is preserved, every technical claim retains the same scope and confidence, references still resolve, and the revision is clearer in context. Otherwise return the conflicting passage and required evidence instead of guessing.

