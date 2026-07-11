# MathModelAgent2 project state audit — 2026-07-11

Audit time: 2026-07-11 21:43 CST (Asia/Shanghai)  
Repository: `D:/Projects/MathModelAgent2`  
Mode: evidence-first, read-only except this report and the companion JSON report  
Audited checkout: `feature/real-problem-readiness` at `2080faa77dfa05a824b6b1ab56d012938c4c6c46`

Status vocabulary used below:

- `VERIFIED`: exercised successfully in this audit on the current working tree.
- `IMPLEMENTED_NOT_VERIFIED`: implementation exists, but this audit did not exercise it end to end.
- `PARTIAL`: only a bounded subset exists or passes.
- `DOCUMENTED_ONLY`: a contract or plan exists without corresponding exercised implementation.
- `BRANCH_ONLY`: exists only on another branch.
- `BROKEN`: a current reproducible failure was observed.
- `UNKNOWN`: evidence was insufficient.

## 1. Executive Summary

### Facts

The repository has two local branches and two commits in a strictly linear history. `feature/real-problem-readiness` contains the complete `feature/core-python-pdf-pipeline` commit and adds one further commit. There are no tags, stashes, additional worktrees, remote-tracking refs, detached HEAD, unreachable Git objects, or reflog-only commits.

The current working tree is **dirty** and contains a substantial third development batch that is not represented by any commit: 8 modified tracked files and 36 untracked files, with 0 staged files. The batch adds an executable regression benchmark system, seven normal synthetic cases, one expected-failure diagnostic case, baseline records, new runner/evaluator/process modules, CLI changes, documentation, and tests.

`origin` is reachable, but `git ls-remote --symref origin` returned exit code 0 with no refs. Therefore the remote repository is currently empty: it has no default branch, no remote branch, and no copy of either local commit. Both commits and all uncommitted work exist only on this machine.

Current engineering verification is strong for the bounded local workflow:

- `69 collected / 69 passed` in 25.83 seconds on Python 3.12.13.
- CLI help, `agent-doctor`, `validate-workspace` for both standard workspaces, and status commands passed.
- Current smoke benchmark: 2/2 cases passed from an external temporary output directory.
- Expected-failure benchmark: the non-zero failure was observed and classified correctly.
- Git, XeLaTeX, latexmk, kpsewhich, pdftoppm, scientific Python dependencies, and CJK fonts were discovered; optional `pdftotext` was missing.

This evidence does **not** establish autonomous modeling of arbitrary competition problems. The strongest proven outcome is a local, assisted, artifact-first engineering workflow with a real Python-to-PDF synthetic curve-fitting closed loop and an uncommitted synthetic regression benchmark framework. Real historical-problem forward evaluation, current official CUMCM format compliance, final human approval, external research, API, RAG, Web UI, database service, and parallel agents are not established.

### Recommendation

Use `feature/real-problem-readiness` as the canonical continuation point, but do not resume development yet. First preserve and review the uncommitted benchmark batch, create an explicit safety reference, commit the intentional batch, push it to the currently empty remote, and only then archive the fully covered core branch. No merge or cherry-pick is needed between the two existing branches because the history is already linear.

### Highest risk

**Critical — local-only loss risk.** The remote is empty, both commits are unpushed, and the newest benchmark implementation is uncommitted/untracked. Loss of this checkout or an unsafe branch/worktree operation could remove all project history and the latest development batch.

## 2. Repository Identity

| Field | Value | Evidence |
|---|---|---|
| Root | `D:/Projects/MathModelAgent2` | `git rev-parse --show-toplevel` |
| Current branch | `feature/real-problem-readiness` | `git symbolic-ref --short HEAD` |
| HEAD | `2080faa77dfa05a824b6b1ab56d012938c4c6c46` | `git rev-parse HEAD` |
| Parent | `b144c27937e7437e480f028521e7b1625ab118b8` | `git rev-parse HEAD^` |
| HEAD subject | `feat: prepare real-problem benchmark workflow` | `git show -s HEAD` |
| HEAD date | `2026-07-11T19:54:47+08:00` | `git show -s --format=%cI HEAD` |
| Initial commit | `b144c279...` — `chore: establish verified assisted pipeline baseline` | `git show -s b144c279...` |
| Detached HEAD | No | symbolic HEAD and `git worktree list --porcelain` |
| Tracked files at HEAD | 360 | `git ls-files` |
| Git worktrees | 1 | `git worktree list --porcelain` |

The repository does not have a local `main` or `master` branch. The two existing feature names are the only local branch names.

## 3. Current Working Tree

### Summary

| Category | Count | Details |
|---|---:|---|
| Staged | 0 | `git diff --cached --name-only` |
| Modified tracked | 8 | 109 insertions, 9 deletions in the unstaged diff |
| Untracked files | 36 | Benchmark cases, runtime, baseline, docs, six source modules, one test module |
| Ignored files | 20,336 | Primarily `.venv`, caches, TeX intermediates, benchmark outputs, and Python bytecode |

Modified tracked files:

1. `.gitignore`
2. `README.md`
3. `benchmarks/README.md`
4. `docs/benchmark_strategy.md`
5. `docs/decision_log.md`
6. `src/mmagent/cli.py`
7. `src/mmagent/tables.py`
8. `tests/test_plotting_tables.py`

Untracked development files:

- `benchmarks/baseline/current.json`, `benchmarks/baseline/current.md`
- Seven normal cases under `benchmarks/cases/`: clustering, comprehensive planning, data-quality regression, evaluation, seasonal forecasting, logistic ODE, and production optimization
- One negative case: `benchmarks/cases/intentional_failure_diagnostic/`
- `benchmarks/known_issues.yaml`, `benchmarks/runtime/generator_entry.py`
- `docs/benchmark_system.md`
- `src/mmagent/benchmark_cases.py`
- `src/mmagent/benchmark_evaluator.py`
- `src/mmagent/benchmark_models.py`
- `src/mmagent/benchmark_process.py`
- `src/mmagent/benchmark_runner.py`
- `src/mmagent/benchmark_worker.py`
- `tests/test_benchmark_system.py`

Important ignored local artifacts:

| Path | Files | Approx. bytes | Assessment |
|---|---:|---:|---|
| `.venv/` | 12,277 | 418,517,384 | Rebuildable dependency environment; should remain ignored |
| `artifacts/` | 2,278 | 119,923,775 | Mix of tracked acceptance evidence and ignored installers/logs/intermediates |
| `benchmark_results/` | 5,697 | 105,965,326 | Valuable local execution evidence; ignored and not remotely backed up |
| `workspaces/` | 281 | 6,404,513 | Tracked workflow evidence plus ignored TeX intermediates |
| `.pytest_cache/` | 5 | 6,936 | Rebuildable cache |

The audit test configuration disabled bytecode and pytest cache creation and used external temporary roots. A post-audit Git comparison is required before handoff and is recorded in section 20.

## 4. Remotes and Synchronization Status

Remote configuration:

```text
origin  https://github.com/a2172668729-netizen/MathModelAgent2.git (fetch)
origin  https://github.com/a2172668729-netizen/MathModelAgent2.git (push)
```

Facts:

- `git ls-remote --symref origin` completed with exit code 0 and produced no refs.
- There are no `refs/remotes/origin/*` entries and no symbolic `origin/HEAD`.
- There is no default remote branch.
- Neither local branch has an upstream.
- Ahead/behind relative to a remote cannot be calculated because the remote has no branch tips.
- Both local commits are necessarily unpushed.
- The uncommitted benchmark batch cannot be pushed until it is intentionally reviewed and committed.

Interpretation: the URL is reachable and authentication was not required for the read, but the remote repository is empty. This is not a normal “in sync” state.

## 5. Branch Inventory

### `feature/core-python-pdf-pipeline`

| Field | Result |
|---|---|
| HEAD | `b144c27937e7437e480f028521e7b1625ab118b8` |
| Parent/base | Root commit; no parent |
| Unique commits relative to readiness | None |
| Main content | 360-file assisted baseline: CLI, Pydantic schemas, state/workspace validation, deterministic Phase 2, Python/PDF core, workspaces, skills, docs, tests, TeX evidence |
| Contained by other branch | Yes, fully contained by `feature/real-problem-readiness` |
| Unique valuable work | No commit-level unique work |
| Staleness | Superseded as a continuation point, but useful as a named baseline checkpoint |
| Conflict risk | Low; it is a direct ancestor |
| Recommendation | Preserve until remote backup succeeds, then retain as a tag/record or archive/delete only with human approval |

### `feature/real-problem-readiness`

| Field | Result |
|---|---|
| HEAD | `2080faa77dfa05a824b6b1ab56d012938c4c6c46` |
| Parent/common ancestor | `b144c27937e7437e480f028521e7b1625ab118b8` |
| Unique commits relative to core | 1 (`2080faa`) |
| Committed diff | 13 files, 1,255 insertions |
| Main additions | Real-problem workspace scaffolding, input audit, result registry/macros, readiness gates, manual scorecard, CLI commands, tests and docs |
| Contains core branch | Yes, completely |
| Unique valuable work | Yes: all real-problem-readiness code and tests |
| Current extra work | The 8 modified and 36 untracked files are attached to this checkout but not to the branch commit |
| Conflict risk | Medium if another session edits the same dirty checkout; low between the two committed branches |
| Recommendation | Canonical branch candidate after preserving and committing the audited benchmark batch |

Local branch distance is `0 1` for `core...readiness`: core is zero commits ahead and one behind readiness.

## 6. Commit Graph Analysis

```text
* 2080faa (HEAD -> feature/real-problem-readiness) feat: prepare real-problem benchmark workflow
* b144c27 (feature/core-python-pdf-pipeline) chore: establish verified assisted pipeline baseline
```

There are no merge commits and no divergent branch tips. The core branch is an ancestor, not a competing implementation line. The newest benchmark system is not shown in this graph because it has not been committed.

The committed change from core to readiness adds:

- `docs/real_problem_readiness.md`
- `src/mmagent/benchmark.py`
- `src/mmagent/input_audit.py`
- `src/mmagent/real_models.py`
- `src/mmagent/real_problem.py`
- `src/mmagent/results_registry.py`
- `tests/test_real_problem_readiness.py`
- supporting changes in README, decisions, package dependencies, CLI, models and workspace validation

No merge or cherry-pick is required to combine these two commits.

## 7. Potentially Lost or Unreferenced Work

### Git object checks

- `git fsck --full --no-reflogs --unreachable`: no output; no unreachable objects found.
- `git reflog --all`: only the two known commits, branch creation, and checkout entries.
- No reflog-only important commit was identified.
- No stash exists.
- No additional worktree exists.

### Material at risk

1. **Both commits are local-only.** The remote is empty.
2. **The benchmark batch is uncommitted.** It includes source, fixtures, tests, docs, baseline summaries and an ignore rule.
3. **`benchmark_results/` is ignored and local-only.** It contains 15 historical runs, including failed diagnostic runs and later passing baselines. It is useful forensic evidence but not a Git source-of-truth artifact.
4. Several ignored environment logs/installers and TeX intermediates are local-only. They are less important than source but may matter for provenance.

Historical benchmark summaries show an evidence trail rather than uninterrupted success: early smoke/full/single runs failed, later corrected runs passed, and the current baseline is `benchmark-20260711t132624924206z`. The failed runs should not be deleted before the benchmark batch is reviewed because they document failure diagnosis and resolution.

## 8. Architecture Overview

### CLI and routing

- `src/mmagent/cli.py` builds one argparse CLI (`mmagent`) with standard workspace, Phase 2, core pipeline, real-problem, benchmark, agent and doctor commands.
- `src/mmagent/__main__.py` supports `python -m mmagent`.
- `config/agent.yaml` fixes the operating mode to `assisted`, one writer, explicit human checkpoints, and disabled external research/API/RAG/Web UI/database/parallel-agent features.
- `skills/modeling-orchestrator/SKILL.md` selects only the next valid persisted stage and stops at missing evidence or human decisions.

### Data models and state machines

- `src/mmagent/models.py` contains strict Pydantic models for stages, status, problem specifications, assumptions, datasets, experiments, validation, review, manifests, PDF acceptance and workspace state.
- `src/mmagent/core_models.py` contains the detailed Python-core run state chain ending in `AWAITING_HUMAN_APPROVAL` before `FINAL`.
- `src/mmagent/real_models.py` adds real-problem evidence, input inventory, result registry and benchmark scorecard models.
- `src/mmagent/workspace.py` creates, validates and reports standard workspace structure.
- `src/mmagent/real_problem.py` creates real-problem workspaces and enforces evidence gates.

### Execution, validation and reproducibility

- `src/mmagent/execution.py` runs Python with `shell=False`, bounded timeouts, captured logs, controlled environment and network blocking.
- `src/mmagent/pipeline.py` is the legacy deterministic Phase 2 loop with persisted failure state and independent metric recomputation.
- `src/mmagent/core_pipeline.py` provides the richer isolated Python-to-PDF run, compile, validate, reproduce and human-approval sequence.
- `src/mmagent/results_registry.py` validates executed result records and generates traceable LaTeX macros.

### Reporting and PDF

- `src/mmagent/plotting.py` generates PNG/SVG figures.
- `src/mmagent/tables.py` generates CSV/LaTeX tables and now has an uncommitted safe-label check.
- `src/mmagent/latex.py` renders the synthetic curve-fitting report.
- `src/mmagent/pdf.py` discovers TeX tools, compiles, renders page previews and performs structural/identity checks.
- The current report format is an internal `ctexart` engineering report, not a verified official 2026 CUMCM template.

### Reviewer and human gates

- `skills/reviewer/SKILL.md` defines persisted-artifact-only review and `review/` write scope.
- `workspaces/curve_fitting_demo/review/review_report.yaml` records an isolated review with technical checks passed and final human approval blocked.
- Benchmark reviewer isolation in the uncommitted system uses a separate process and copied artifact tree; it is workflow isolation, not an OS security sandbox.

### Benchmark layers

- Committed readiness layer: manual `benchmark-scorecard`, real-problem scaffolding and evidence gates.
- Uncommitted regression layer: `benchmark_models`, `benchmark_process`, `benchmark_cases`, `benchmark_worker`, `benchmark_evaluator`, `benchmark_runner`, executable fixtures, CLI integration and test coverage.
- The fixtures use repository-authored deterministic data and reference implementations. They measure engineering regressions, not autonomous reading/model selection on unknown competition problems.

## 9. Capability Matrix

| Capability | Status | Evidence and boundary |
|---|---|---|
| Core Python execution and validation pipeline | VERIFIED | `tests/test_execution.py`, `tests/test_core_integration.py`; 69/69 tests; persisted curve runs |
| Chart and table generation | VERIFIED | `src/mmagent/plotting.py`, `src/mmagent/tables.py`; plotting/table tests and persisted PNG/SVG/CSV/TeX |
| Chinese LaTeX / XeLaTeX compilation | VERIFIED | Doctor found TeX Live 2026; integration tests passed; tracked acceptance PDF and four curve PDFs |
| PDF generation and structural checks | VERIFIED | Core integration and smoke benchmark passed; `src/mmagent/pdf.py`; current external smoke output |
| Page-by-page final visual acceptance | PARTIAL | Previews exist and prior reports record inspection; no human final approval exists, and this audit did not independently inspect every page |
| Second independent reproduction | VERIFIED | `workspaces/curve_fitting_demo/reproducibility_report.json`; integration test; two persisted source/reproduction runs |
| Isolated Reviewer | VERIFIED | Persisted curve review plus benchmark workflow/process-copy tests; not an OS sandbox |
| Human approval gate enforcement | VERIFIED | State tests and latest curve status block at `AWAITING_HUMAN_APPROVAL`; the approval itself remains pending |
| Real historical-problem workspace | PARTIAL | `mmagent new` scaffolding and gates exist, but no authorized real historical problem workspace with forward result is present |
| `mmagent new` | VERIFIED | CLI help and `test_new_workspace_is_valid_but_objectively_incomplete` |
| `mmagent audit-input` | VERIFIED | CSV/XLSX and unsupported-input diagnostics exercised in `test_real_problem_readiness.py` |
| `mmagent advance` | VERIFIED | Evidence-chain and stage-skip tests passed |
| `mmagent results-macros` | VERIFIED | Traceability macro test passed |
| Real-problem benchmark/readiness workflow | PARTIAL | Committed readiness gates plus uncommitted regression benchmark; current smoke passed, arbitrary real problems unproven |
| Input file diagnostics | PARTIAL | Code probes PDF, text, CSV, XLSX, JSON and images; this audit's tests directly exercised CSV/XLSX/unsupported paths, not every format |
| PDF/CSV/XLSX/JSON/image attachment handling | PARTIAL | Read/probe/hash/metadata exists; no OCR, broad semantic extraction, or end-to-end real attachment study is proven |
| CUMCM paper typesetting | PARTIAL | Internal Chinese report pipeline works; `competition_profiles/cumcm/2026/official_spec.yaml` remains provisional |
| Academic de-AI/humanizer processing | DOCUMENTED_ONLY | Skill and strategy docs exist; no current executed before/after fact-preservation artifact was found |
| Final paper delivery workflow | PARTIAL | Compile/validate/review mechanics exist, but no workspace is `FINAL`/`FINALIZED`; explicit human gate is pending |
| CLI entry point | VERIFIED | `python -m mmagent --help` exit 0 and lists all current commands |
| Workspace validation and status | VERIFIED | Example and Phase 2 validation/status commands exit 0 |
| Agent configuration contract | VERIFIED | `mmagent agent-doctor` returns `PASS` |
| External research/API/RAG/Web UI/database/parallel agents | DOCUMENTED_ONLY / disabled | Explicitly disabled in `config/agent.yaml`; not authorized or implemented as current capabilities |

## 10. Test and Runtime Verification

| Check | Exit | Result |
|---|---:|---|
| `.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp <external>` | 0 | 69 collected, 69 passed in 25.83s |
| `python -m mmagent --help` | 0 | Current command inventory printed |
| `python -m mmagent agent-doctor` | 0 | `PASS` |
| `python -m mmagent validate-workspace workspaces/example_problem` | 0 | `PASS` |
| `python -m mmagent validate-workspace workspaces/phase2_demo` | 0 | `PASS` |
| `python -m mmagent status workspaces/phase2_demo` | 0 | `PAPER_DRAFTED`, 0 missing/invalid items |
| `python -m mmagent status workspaces/curve_fitting_demo` | 0 | `AWAITING_HUMAN_APPROVAL`, technical status passed, approval pending |
| `python -m mmagent doctor` | 0 | Python/dependencies/Git/TeX/PDF tools passed; optional `pdftotext` missing |
| `python -m mmagent benchmark list` | 0 | 7 normal cases plus 1 expected-failure case listed |
| Current source tree hash | 0 | `6666c6ec...c86eba1`, identical to persisted full baseline |
| `benchmark run --smoke --output <external>` | 0 | 2 cases, 2 passed |
| Expected failure diagnostic to external output | 0 | 1 expected failure observed, 0 unexpected failures |
| `git ls-remote --symref origin` | 0 | No refs returned; remote reachable and empty |

Not run in this audit:

- Full 7-case, two-repetition benchmark. Persisted baseline duration is 115.06 seconds and its source-tree hash matches the current tree. The audit used the lower-risk smoke and negative diagnostic instead.
- A new formal workspace build or demo run, to avoid overwriting or adding repository workspaces.
- Manual page-by-page visual inspection of all persisted PDFs.
- Any real historical competition problem.
- Any merge, checkout, commit, push, tag, stash, cleanup or branch deletion.

## 11. Documentation Consistency Review

### Consistent claims

- README and roadmap preserve the distinction between synthetic engineering evidence and real competition capability.
- `config/agent.yaml`, orchestration docs and tests agree that the mode is assisted and finalization requires humans.
- `workspaces/curve_fitting_demo` artifacts agree that technical validation passed while human final approval remains pending.
- `phase2_demo` artifacts honestly retain the historical `blocked` PDF acceptance record.

### Drift and conflicts

1. `README.md:50` and `docs/roadmap.md:17` say the complete test suite is 42/42. Current live evidence is 69/69. The 42 result remains a real historical checkpoint, but wording that presents it as current is stale.
2. `docs/core_pipeline_audit.md` contains multiple dated snapshots (27 and 42 tests). It is an audit history, not current status; readers can mistake early limitations for current capability.
3. `docs/roadmap.md:21-23` says Phase 4 benchmark regression is not implemented, while the current dirty working tree contains an executable benchmark regression system and a passing baseline. Because that implementation is uncommitted, neither statement alone is a complete repository truth.
4. Current working-tree README advertises `mmagent benchmark run/compare/list`, but no commit contains these commands. Checking out either branch tip would remove them.
5. `docs/real_problem_readiness.md:86` still documents `mmagent benchmark <workspace>` for the manual scorecard. The dirty CLI renames this to `mmagent benchmark-scorecard <workspace>` and uses `benchmark` as a subcommand group. The document is stale relative to the working tree.
6. `phase2_demo/reports/pdf_acceptance.yaml` says XeLaTeX was unavailable when that artifact was generated. Current `doctor` finds XeLaTeX. The artifact is valid historical evidence, not a current environment report.
7. `docs/architecture.md` describes a full end-to-end target flow. Several writer/humanizer/fact-check/final-package stages remain contracts rather than demonstrated real-problem delivery.

These conflicts were recorded here rather than in `docs/decision_log.md` because the audit explicitly prohibited modifying existing project files.

## 12. Generated Artifacts and Workspaces

### `workspaces/example_problem`

- Stage: `CREATED`.
- Structural validation: passed.
- Purpose: standard skeleton, not a completed problem.

### `workspaces/phase2_demo`

- Stage: `PAPER_DRAFTED`.
- Solver and independent numeric validation artifacts: passed.
- `reports/pdf_acceptance.yaml`: `blocked`, zero compile attempts, structural/visual/identity checks `not_run`.
- Reviewer: blocked by PDF, identity, human selection, validator provenance and code-trace issues.
- Current machine now has XeLaTeX, but the workspace was not rebuilt in this audit.

### `workspaces/curve_fitting_demo`

- Four persisted runs, each with a PDF and four page previews.
- Latest source run: `run-20260711t010935048946z`.
- Latest reproduction run: `run-20260711t010942206919z`.
- Reproduction report: passed; numerical tolerance `1e-10`; both PDFs valid.
- Latest state: `AWAITING_HUMAN_APPROVAL`.
- Isolated reviewer technical assessment: passed.
- Critical human final approval issue: open.
- Scope: synthetic curve fitting only.

### `benchmark_results`

- 15 ignored historical run directories.
- Includes early failed runs, corrected passing smoke/full runs, negative diagnostic runs, and the current passing full baseline.
- Current full baseline: `benchmark-20260711t132624924206z`, 7/7 cases, two attempts each, 115.064385 seconds, source-tree hash `6666c6ec...c86eba1`.
- This audit's smoke and negative outputs were written outside the repository under a temporary directory.

## 13. Known Gaps

- No remote backup or canonical default branch.
- Latest benchmark implementation not committed.
- No real historical competition workspace with authorized inputs and forward evaluation.
- No proof of autonomous problem interpretation, model recommendation or competition-grade paper production.
- No verified current official 2026 CUMCM template/rule set.
- Final human page-by-page acceptance and approval remain pending.
- Academic humanizer has no executed, fact-preservation validation artifact.
- Input handling is diagnostic/probing, not comprehensive semantic extraction or OCR.
- Optional `pdftotext` is missing.
- Full benchmark was not rerun in this audit.
- Reviewer isolation is not an OS sandbox.
- Dirty-worktree docs and CLI are internally inconsistent in at least one command name.

## 14. Risk Register

| Severity | Risk | Evidence | Consequence | Recommended handling |
|---|---|---|---|---|
| Critical | Local-only loss of all development | Empty remote; 2 unpushed commits; 8 modified + 36 untracked files | Total project/history loss | Stop edits; make reviewed safety copy/reference and push intentionally |
| Critical | Uncommitted benchmark batch lost or partially staged | Source, tests, cases, docs and baseline are untracked/modified | Latest capability disappears or becomes unreproducible | Review exact file scope, commit as one coherent batch or approved split |
| High | Canonical main line is undefined | Only two feature branches; no remote default | Sessions continue on different assumptions | Human designates/renames canonical branch after backup |
| High | Dirty checkout shared by multiple sessions | Large unstaged batch on active branch | Overwrites, mixed commits, duplicate work | Freeze development until consolidation |
| High | Real competition readiness overstated | Only synthetic/core fixtures and scaffolding | Invalid readiness or submission claims | Require authorized real-problem forward benchmark |
| High | Final approval gate bypass | Latest curve state is awaiting human approval | Unreviewed PDF treated as final | Preserve explicit manual approval and page review |
| High | Documentation advertises uncommitted CLI | README vs branch tips and stale scorecard command | Users run unavailable/wrong commands | Update docs only after benchmark commit is accepted |
| Medium | Historical status files read as current | Phase2 blocked XeLaTeX vs current doctor; 27/42/69 test snapshots | Confusing or contradictory handoff | Label dated reports and add a current status index later |
| Medium | Test coverage is fixture-heavy | 69 passing tests; synthetic cases | Generalization defects remain hidden | Add licensed real-problem forward tests after approval |
| Medium | Benchmark outputs are ignored/local | 105.9 MB under `benchmark_results/` | Forensic evidence may be lost | Preserve summarized baselines in Git and archive raw runs externally if needed |
| Medium | Windows/TeX environment portability | TeX Live under `D:/texlive/2026`; optional pdftotext absent | macOS/clean-machine failures | Keep discovery-based paths and run a clean-machine check |
| Medium | PDF heuristics mistaken for human review | Automated checks plus pending gate | Layout/anonymity issues reach submission | Require human page-by-page acceptance |
| Medium | Reviewer isolation misunderstood | Process/copy isolation, no OS sandbox | Unsafe code could exceed intended boundary | Document threat model; sandbox before untrusted code |
| Medium | Input data insufficiently audited | Probe layer supports formats but no real problem | Bad/misread inputs contaminate results | Require input inventory and human data audit before modeling |
| Medium | Evidence-chain gaps in legacy Phase 2 | Reviewer reports missing validator provenance and solver source | Claims cannot be independently reviewed | Do not promote legacy demo; use richer core contracts |
| Low | Core branch deletion too early | It is fully covered by readiness | Loss of named checkpoint, not content | Archive only after remote backup and human approval |
| Low | LF/CRLF warnings | Git warns future touches will convert LF to CRLF | Noisy diffs, possible formatting drift | Decide line-ending policy later; do not normalize during consolidation |

## 15. Canonical Branch Recommendation

Recommend `feature/real-problem-readiness` as the current canonical branch because:

1. It contains the full core branch history.
2. It adds all committed real-problem scaffolding and evidence-gate work.
3. It is the branch attached to the tested dirty benchmark batch.
4. The core branch has no unique commit.

This recommendation does not mean the current dirty working tree is ready to become `main` unchanged. The benchmark batch must first be reviewed and preserved. A later human decision may rename the canonical branch to `main`; that is a repository-governance action, not part of this audit.

## 16. Proposed Branch Consolidation Plan

No steps below were executed.

1. Freeze all development sessions using this checkout.
2. Review the 8 modified and 36 untracked files against this report. Confirm that all are intentional and that raw `benchmark_results/` remains ignored.
3. Before switching branches, make an approved external backup of the dirty diff and untracked source, or create an equivalent safe snapshot using a human-approved procedure.
4. Create a safety branch/reference at `2080faa` so the pre-benchmark committed state remains named.
5. Commit the benchmark batch on `feature/real-problem-readiness`, either as one coherent commit or an approved small sequence (framework, cases, docs/tests). Do not mix raw ignored benchmark outputs.
6. Rerun 69 tests, smoke, expected-failure diagnostic, and preferably the full benchmark after the commit; verify the committed tree hash and reports.
7. Push the canonical branch and safety reference to `origin`; verify remote refs and set upstream.
8. Establish a default remote branch (`main` or an explicitly approved alternative).
9. Keep `feature/core-python-pdf-pipeline` until the remote backup is verified. It needs no merge. Later archive/delete it only with human approval.
10. Update stale command/test-count/roadmap wording in a separate documentation commit.

Recommended merge/cherry-pick sequence: **none** for existing branches. If the benchmark batch is deliberately placed on a new branch, merge that one branch into the canonical readiness branch only after its tests and full benchmark pass; cherry-pick is unnecessary unless the batch is intentionally split and only selected commits are approved.

## 17. Recommended Next Tasks

Priority order after human review:

1. **Preserve and remotely back up current work.** This is more urgent than new feature work.
2. **Commit and revalidate the benchmark batch.** Rerun the full benchmark from the committed tree and record the new commit hash in the baseline.
3. **Resolve documentation drift.** Correct the scorecard command, distinguish historical 27/42 snapshots from current 69, and revise the Phase 4 benchmark statement.
4. **Run one authorized real historical problem as a forward readiness evaluation.** Keep human checkpoints and do not add network/API/RAG/Web UI permissions implicitly.
5. **Complete human PDF review and final approval workflow** for any candidate deliverable; do not mark the synthetic demo as a competition submission.

## 18. Human Approval Gates

Explicit approval is required before:

- Choosing which untracked/modified files belong in the benchmark commit.
- Creating a safety branch/tag or external backup procedure.
- Committing, pushing, setting upstream or choosing a remote default branch.
- Renaming a branch to `main`.
- Archiving/deleting `feature/core-python-pdf-pipeline`.
- Removing any ignored historical benchmark output.
- Selecting and importing a real historical problem or dataset and confirming its license/authorization.
- Accepting model choice, assumptions and validation conclusions.
- Accepting PDF anonymity, official-format compliance and every rendered page.
- Marking any workspace `FINAL`/`FINALIZED`.

## 19. Evidence Appendix

Primary code and configuration:

- `AGENTS.md`
- `config/agent.yaml`
- `pyproject.toml`
- `src/mmagent/cli.py`
- `src/mmagent/models.py`
- `src/mmagent/workspace.py`
- `src/mmagent/execution.py`
- `src/mmagent/pipeline.py`
- `src/mmagent/core_pipeline.py`
- `src/mmagent/pdf.py`
- `src/mmagent/input_audit.py`
- `src/mmagent/real_problem.py`
- `src/mmagent/results_registry.py`
- untracked `src/mmagent/benchmark_*.py`

Primary tests:

- `tests/test_core_integration.py`
- `tests/test_execution.py`
- `tests/test_phase2_pipeline.py`
- `tests/test_real_problem_readiness.py`
- untracked `tests/test_benchmark_system.py`

Primary persisted artifacts:

- `workspaces/phase2_demo/state.yaml`
- `workspaces/phase2_demo/results/validation.yaml`
- `workspaces/phase2_demo/reports/pdf_acceptance.yaml`
- `workspaces/phase2_demo/review/review_report.yaml`
- `workspaces/curve_fitting_demo/latest_run.json`
- `workspaces/curve_fitting_demo/reproducibility_report.json`
- `workspaces/curve_fitting_demo/review/review_report.yaml`
- untracked `benchmarks/baseline/current.json`
- ignored `benchmark_results/benchmark-20260711t132624924206z/`

Evidence distinction:

- Git commands establish repository topology and synchronization facts.
- Live commands establish current runtime results.
- Persisted artifacts establish earlier runs but are not treated as current execution unless revalidated.
- Documentation is used for stated intent and is not accepted as implementation proof by itself.

## 20. Commands Executed

All Git commands were read-only. No `fetch`, merge, rebase, cherry-pick, reset, checkout, commit, push, tag, stash or cleanup was executed.

Git evidence commands:

```text
git rev-parse --show-toplevel
git symbolic-ref --quiet --short HEAD
git rev-parse HEAD
git rev-parse HEAD^
git status --short --branch
git status --porcelain=v2 --branch --ignored
git branch -vv
git branch -a
git for-each-ref ... refs/heads refs/remotes
git remote -v
git tag --list
git stash list
git worktree list --porcelain
git log --graph --decorate --oneline --all
git show --stat --oneline HEAD
git reflog --all --date=iso-strict
git fsck --full --no-reflogs --unreachable
git merge-base <core> <readiness>
git rev-list --left-right --count <core>...<readiness>
git diff --stat / --name-status / --numstat
git ls-files --others --exclude-standard
git ls-files --others --ignored --exclude-standard
git ls-remote --symref origin
```

Runtime commands:

```text
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp <external-temp>
.venv/Scripts/python.exe -m mmagent --help
.venv/Scripts/python.exe -m mmagent agent-doctor
.venv/Scripts/python.exe -m mmagent validate-workspace workspaces/example_problem
.venv/Scripts/python.exe -m mmagent validate-workspace workspaces/phase2_demo
.venv/Scripts/python.exe -m mmagent status workspaces/phase2_demo
.venv/Scripts/python.exe -m mmagent status workspaces/curve_fitting_demo
.venv/Scripts/python.exe -m mmagent doctor
.venv/Scripts/python.exe -m mmagent benchmark list
.venv/Scripts/python.exe -m mmagent benchmark run --smoke --output <external-temp>
.venv/Scripts/python.exe -m mmagent benchmark run --case intentional_failure_diagnostic --output <external-temp>
```

Audit conclusion: continue from `feature/real-problem-readiness`, but first preserve, commit, validate and push the current benchmark batch under explicit human control.
