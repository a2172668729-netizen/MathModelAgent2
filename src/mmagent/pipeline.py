"""Phase-two artifact pipeline with strict state and evidence gates."""

from __future__ import annotations

import csv
import hashlib
import math
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import yaml
import pydantic
from pydantic import BaseModel, ValidationError

from mmagent import __version__
from mmagent.models import (
    Assumption,
    AssumptionsFile,
    Constraint,
    DatasetMetadata,
    Experiment,
    Metric,
    ModelCandidate,
    ModelSelection,
    Objective,
    PdfAcceptance,
    ProblemSpec,
    ReportManifest,
    RunManifest,
    Stage,
    Status,
    SubProblem,
    ValidationFinding,
    ValidationReportFile,
    Variable,
    WorkspaceState,
)
from mmagent.workspace import initialize_workspace, validate_workspace

ModelT = TypeVar("ModelT", bound=BaseModel)

PHASE2_COMPLETED_STAGES = [
    Stage.CREATED,
    Stage.INGESTED,
    Stage.ANALYZED,
    Stage.DATA_READY,
    Stage.MODELS_PROPOSED,
    Stage.MODEL_SELECTED,
]


class PipelineError(RuntimeError):
    """A recoverable workspace or stage contract failure."""


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _write_model(path: Path, model: BaseModel) -> None:
    _atomic_text(
        path,
        yaml.safe_dump(model.model_dump(mode="json", exclude_none=True), allow_unicode=True, sort_keys=False),
    )


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return model_type.model_validate(raw)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
        raise PipelineError(f"invalid {path.name}: {exc}") from exc


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_state(root: Path) -> WorkspaceState:
    return _read_model(root / "state.yaml", WorkspaceState)


def _save_state(root: Path, state: WorkspaceState) -> None:
    state.updated_at = datetime.now(UTC)
    _write_model(root / "state.yaml", state)


def _advance(state: WorkspaceState, stage: Stage) -> None:
    if stage not in state.completed_stages:
        state.completed_stages.append(stage)
    state.current_stage = stage
    state.failed_stage = None
    state.failure_summary = None


def _fail(root: Path, state: WorkspaceState, stage: Stage, message: str) -> None:
    state.current_stage = Stage.FAILED
    state.failed_stage = stage
    state.failure_summary = message
    _save_state(root, state)


def create_demo_workspace(root: Path) -> Path:
    """Create a clearly labeled synthetic fixture without overwriting an existing workspace."""
    root = root.expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise PipelineError(f"demo target must be absent or empty: {root}")
    initialize_workspace(root)

    observations = "x,y\n0,1\n1,3\n2,5\n3,7\n4,9\n"
    _atomic_text(root / "input" / "observations.csv", observations)
    dataset_hash = _hash_file(root / "input" / "observations.csv")
    problem = ProblemSpec(
        problem_id="linear-demo",
        title="合成线性关系最小二乘验证示例（非竞赛数据）",
        source_files=["input/observations.csv"],
        subproblems=[
            SubProblem(
                id="problem-1",
                prompt="比较均值基线与一元线性最小二乘模型。",
                objective_ids=["objective-1"],
                constraint_ids=["constraint-1"],
                deliverables=["可复现实验结果", "独立验证记录", "证据报告"],
            )
        ],
        objectives=[Objective(id="objective-1", description="最小化样本内均方根误差", direction="minimize", metric="RMSE")],
        constraints=[Constraint(id="constraint-1", description="只使用给定的五个合成观测点", kind="data", source="input/observations.csv")],
        variables=[
            Variable(symbol="x", meaning="解释变量", role="observed", unit="无量纲"),
            Variable(symbol="y", meaning="响应变量", role="observed", unit="无量纲"),
        ],
    )
    assumptions = AssumptionsFile(
        assumptions=[
            Assumption(
                id="assumption-1",
                statement="该数据仅用于验证工程闭环，不代表真实竞赛观测。",
                rationale="数据由项目明确构造并标记为 synthetic。",
                impact="不得从该结果推断任何现实规律。",
                validation_status=Status.PASSED,
                evidence_refs=["input/observations.csv"],
            )
        ]
    )
    metadata = DatasetMetadata(
        id="observations",
        path="input/observations.csv",
        media_type="text/csv",
        sha256=dataset_hash,
        size_bytes=(root / "input" / "observations.csv").stat().st_size,
        source="project-authored synthetic phase-two fixture",
        license="CC0-style project fixture; not external competition data",
        columns=["x", "y"],
        units={"x": "dimensionless", "y": "dimensionless"},
        quality_notes=["five complete rows", "exact relation y = 2x + 1", "not real-world evidence"],
    )
    baseline = ModelCandidate(
        id="mean-baseline",
        name="均值基线",
        purpose="提供不使用 x 的简单比较基线",
        required_dataset_ids=["observations"],
        strengths=["确定性", "易复现"],
        limitations=["忽略 x 与 y 的关系"],
        is_baseline=True,
    )
    linear = ModelCandidate(
        id="linear-least-squares",
        name="一元线性最小二乘",
        purpose="拟合 y = ax + b 并与均值基线比较",
        assumptions=["assumption-1"],
        required_dataset_ids=["observations"],
        strengths=["参数可解释", "可独立重算"],
        limitations=["该合成样本不能证明现实泛化能力"],
    )
    selection = ModelSelection(
        selected_model_id="linear-least-squares",
        compared_model_ids=["mean-baseline", "linear-least-squares"],
        evidence=["Fixture contract fixes both candidates; run metrics decide only the comparison."],
    )
    _write_model(root / "problem_spec.yaml", problem)
    _write_model(root / "assumptions.yaml", assumptions)
    _write_model(root / "data" / "metadata" / "observations.yaml", metadata)
    _write_model(root / "models" / "candidates" / "mean-baseline.yaml", baseline)
    _write_model(root / "models" / "candidates" / "linear-least-squares.yaml", linear)
    _write_model(root / "models" / "selected" / "selection.yaml", selection)
    _atomic_text(
        root / "code" / "solve.py",
        "from mmagent.demo_solver import main\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
    )
    _atomic_text(
        root / "decisions.md",
        "# Decisions\n\n"
        "- This is a project-authored synthetic engineering fixture, not competition evidence.\n"
        "- The model set is fixed by the fixture; `approved_by_human` remains false and no competition checkpoint is claimed.\n",
    )
    state = WorkspaceState(
        workspace_id="linear-demo",
        current_stage=Stage.MODEL_SELECTED,
        completed_stages=PHASE2_COMPLETED_STAGES.copy(),
        artifacts={
            "problem_spec": "problem_spec.yaml",
            "assumptions_data": "assumptions.yaml",
            "dataset_metadata": "data/metadata/observations.yaml",
            "baseline_model": "models/candidates/mean-baseline.yaml",
            "selected_model": "models/selected/selection.yaml",
            "solver": "code/solve.py",
            "run_manifest": "run_manifest.yaml",
        },
        updated_at=datetime.now(UTC),
    )
    _save_state(root, state)
    report = validate_workspace(root)
    if not report.passed:
        raise PipelineError("created demo failed workspace validation: " + "; ".join(report.errors))
    return root


def _write_run_manifest(root: Path, history_path: Path, manifest: RunManifest) -> None:
    _write_model(history_path, manifest)
    _write_model(root / "run_manifest.yaml", manifest)


def run_solver(root: Path, timeout_seconds: int = 120) -> RunManifest:
    root = root.expanduser().resolve()
    report = validate_workspace(root)
    if not report.passed:
        raise PipelineError("workspace validation failed: " + "; ".join(report.errors))
    state = _load_state(root)
    retrying = state.current_stage is Stage.FAILED and state.failed_stage is Stage.IMPLEMENTED
    if state.current_stage is not Stage.MODEL_SELECTED and not retrying:
        raise PipelineError(f"run-solver requires MODEL_SELECTED, found {state.current_stage.value}")

    solver_path = root / "code" / "solve.py"
    if not solver_path.is_file():
        raise PipelineError("missing solver: code/solve.py")
    problem = _read_model(root / "problem_spec.yaml", ProblemSpec)
    input_hashes: dict[str, str] = {}
    for relative in [*problem.source_files, "code/solve.py"]:
        source = root / relative
        if not source.is_file():
            raise PipelineError(f"missing declared solver input: {relative}")
        input_hashes[relative] = _hash_file(source)

    started = datetime.now(UTC)
    run_id = "run-" + started.strftime("%Y%m%dt%H%M%S%fz")
    history_path = root / "runs" / f"{run_id}.yaml"
    command = [sys.executable, str(solver_path), "--workspace", str(root)]
    manifest = RunManifest(
        run_id=run_id,
        stage=Stage.IMPLEMENTED,
        status=Status.RUNNING,
        started_at=started,
        command=[Path(sys.executable).name, "code/solve.py", "--workspace", "."],
        python_version=platform.python_version(),
        platform=platform.platform(),
        dependencies={"mathmodelagent": __version__, "pydantic": pydantic.__version__, "PyYAML": yaml.__version__},
        random_seed=0,
        input_hashes=input_hashes,
        parameters={"timeout_seconds": timeout_seconds},
    )
    _write_run_manifest(root, history_path, manifest)
    result_path = root / "results" / "experiment.yaml"
    before_hash = _hash_file(result_path) if result_path.is_file() else None
    before_mtime = result_path.stat().st_mtime_ns if result_path.is_file() else None
    try:
        process = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _atomic_text(root / "results" / "solver.stdout.log", _output_text(exc.stdout))
        _atomic_text(root / "results" / "solver.stderr.log", _output_text(exc.stderr))
        manifest.status = Status.FAILED
        manifest.finished_at = datetime.now(UTC)
        manifest.artifact_paths = ["results/solver.stdout.log", "results/solver.stderr.log", f"runs/{history_path.name}"]
        _write_run_manifest(root, history_path, manifest)
        _fail(root, state, Stage.IMPLEMENTED, f"solver timed out after {timeout_seconds} seconds")
        raise PipelineError(state.failure_summary or "solver timed out") from exc
    except OSError as exc:
        _atomic_text(root / "results" / "solver.stdout.log", "")
        _atomic_text(root / "results" / "solver.stderr.log", str(exc))
        manifest.status = Status.FAILED
        manifest.finished_at = datetime.now(UTC)
        manifest.artifact_paths = ["results/solver.stdout.log", "results/solver.stderr.log", f"runs/{history_path.name}"]
        _write_run_manifest(root, history_path, manifest)
        _fail(root, state, Stage.IMPLEMENTED, f"solver could not start: {exc}")
        raise PipelineError(state.failure_summary or "solver could not start") from exc

    _atomic_text(root / "results" / "solver.stdout.log", process.stdout)
    _atomic_text(root / "results" / "solver.stderr.log", process.stderr)
    error: str | None = None
    if process.returncode != 0:
        error = f"solver exited with code {process.returncode}"
    elif not result_path.is_file():
        error = "solver did not create results/experiment.yaml"
    else:
        after_hash = _hash_file(result_path)
        after_mtime = result_path.stat().st_mtime_ns
        if before_hash is not None and after_hash == before_hash and before_mtime is not None and after_mtime <= before_mtime:
            error = "solver result was not refreshed; refusing a possibly stale artifact"
        else:
            experiment = _read_model(result_path, Experiment)
            if experiment.status is not Status.PASSED:
                error = f"experiment status is {experiment.status.value}, expected passed"

    manifest.finished_at = datetime.now(UTC)
    manifest.artifact_paths = ["results/solver.stdout.log", "results/solver.stderr.log", f"runs/{history_path.name}"]
    if result_path.is_file():
        manifest.artifact_paths.insert(0, "results/experiment.yaml")
    if error is not None:
        manifest.status = Status.FAILED
        _write_run_manifest(root, history_path, manifest)
        _fail(root, state, Stage.IMPLEMENTED, error)
        raise PipelineError(error)

    manifest.status = Status.PASSED
    _write_run_manifest(root, history_path, manifest)
    _advance(state, Stage.IMPLEMENTED)
    state.artifacts.update(
        {
            "experiment": "results/experiment.yaml",
            "solver_stdout": "results/solver.stdout.log",
            "solver_stderr": "results/solver.stderr.log",
            "run_manifest": "run_manifest.yaml",
        }
    )
    _save_state(root, state)
    return manifest


def _read_points(path: Path) -> tuple[list[float], list[float]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [float(row["x"]) for row in rows], [float(row["y"]) for row in rows]


def _recompute_metrics(xs: list[float], ys: list[float]) -> dict[str, float]:
    if len(xs) < 2 or len(xs) != len(ys):
        raise PipelineError("validation requires at least two paired observations")
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        raise PipelineError("validation found zero variance in x")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = y_mean - slope * x_mean
    predicted = [slope * x + intercept for x in xs]
    return {
        "slope": slope,
        "intercept": intercept,
        "linear_rmse": math.sqrt(sum((y - prediction) ** 2 for y, prediction in zip(ys, predicted, strict=True)) / len(ys)),
        "baseline_rmse": math.sqrt(sum((y - y_mean) ** 2 for y in ys) / len(ys)),
    }


def validate_results(root: Path) -> ValidationReportFile:
    root = root.expanduser().resolve()
    state = _load_state(root)
    retrying = state.current_stage is Stage.FAILED and state.failed_stage is Stage.VALIDATED
    if state.current_stage is not Stage.IMPLEMENTED and not retrying:
        raise PipelineError(f"validate-results requires IMPLEMENTED, found {state.current_stage.value}")
    try:
        experiment = _read_model(root / "results" / "experiment.yaml", Experiment)
        observed = {metric.name: metric.value for metric in experiment.metrics}
        expected = _recompute_metrics(*_read_points(root / "input" / "observations.csv"))
    except (PipelineError, OSError, KeyError, ValueError) as exc:
        validation = ValidationReportFile(
            experiment_path="results/experiment.yaml",
            status=Status.FAILED,
            checked_at=datetime.now(UTC),
            findings=[
                ValidationFinding(
                    id="finding-validation-input",
                    category="consistency",
                    severity="critical",
                    status=Status.FAILED,
                    evidence_path="results/experiment.yaml" if (root / "results" / "experiment.yaml").exists() else None,
                    message=f"独立验证无法读取或重算输入：{exc}",
                )
            ],
        )
        _write_model(root / "results" / "validation.yaml", validation)
        state.artifacts["validation"] = "results/validation.yaml"
        _fail(root, state, Stage.VALIDATED, "independent validation could not read or recompute inputs")
        return validation
    missing = sorted(set(expected) - set(observed))
    consistency_passed = not missing and all(math.isclose(observed[name], value, rel_tol=1e-12, abs_tol=1e-12) for name, value in expected.items())
    baseline_passed = not missing and observed["linear_rmse"] <= observed["baseline_rmse"]
    findings = [
        ValidationFinding(
            id="finding-consistency",
            category="consistency",
            severity="critical",
            status=Status.PASSED if consistency_passed else Status.FAILED,
            evidence_path="results/experiment.yaml",
            message="独立重算的斜率、截距和 RMSE 与求解产物一致。" if consistency_passed else f"指标不一致或缺失：{missing}",
        ),
        ValidationFinding(
            id="finding-baseline",
            category="robustness",
            severity="error",
            status=Status.PASSED if baseline_passed else Status.FAILED,
            evidence_path="results/experiment.yaml",
            message="线性模型 RMSE 不高于均值基线。" if baseline_passed else "线性模型未超过均值基线。",
        ),
        ValidationFinding(
            id="finding-boundary",
            category="boundary",
            severity="info",
            status=Status.PASSED,
            evidence_path="input/observations.csv",
            message="观测数量不少于 2，且 x 方差非零。",
        ),
        ValidationFinding(
            id="finding-generalization",
            category="robustness",
            severity="warning",
            status=Status.NOT_RUN,
            evidence_path="input/observations.csv",
            message="合成示例不用于现实泛化，因此未执行样本外验证。",
        ),
    ]
    passed = consistency_passed and baseline_passed
    validation = ValidationReportFile(
        experiment_path="results/experiment.yaml",
        status=Status.PASSED if passed else Status.FAILED,
        checked_at=datetime.now(UTC),
        findings=findings,
    )
    _write_model(root / "results" / "validation.yaml", validation)
    state.artifacts["validation"] = "results/validation.yaml"
    if not passed:
        _fail(root, state, Stage.VALIDATED, "independent result validation failed")
        return validation
    _advance(state, Stage.VALIDATED)
    _save_state(root, state)
    return validation


def _metric(experiment: Experiment, name: str) -> float:
    values = [metric.value for metric in experiment.metrics if metric.name == name]
    if len(values) != 1:
        raise PipelineError(f"expected exactly one metric named {name}")
    return values[0]


def render_report(root: Path) -> ReportManifest:
    root = root.expanduser().resolve()
    state = _load_state(root)
    if state.current_stage is not Stage.VALIDATED:
        raise PipelineError(f"render-report requires VALIDATED, found {state.current_stage.value}")
    experiment = _read_model(root / "results" / "experiment.yaml", Experiment)
    validation = _read_model(root / "results" / "validation.yaml", ValidationReportFile)
    if validation.status is not Status.PASSED:
        raise PipelineError("report generation requires passed validation")
    slope = _metric(experiment, "slope")
    intercept = _metric(experiment, "intercept")
    linear_rmse = _metric(experiment, "linear_rmse")
    baseline_rmse = _metric(experiment, "baseline_rmse")
    markdown = f"""# Phase 2 evidence report

本报告只描述项目自带的合成工程示例，不代表真实竞赛数据或现实结论。

## 可追溯结果

- 线性最小二乘模型：$y = {slope:.12g}x + {intercept:.12g}$。
- 线性模型 RMSE：`{linear_rmse:.12g}`。
- 均值基线 RMSE：`{baseline_rmse:.12g}`。
- 独立一致性验证：`{validation.status.value}`。

数字来源：`results/experiment.yaml`；验证来源：`results/validation.yaml`。
"""
    latex = rf"""\documentclass[UTF8]{{ctexart}}
\usepackage{{booktabs}}
\title{{MathModelAgent Phase 2 技术闭环报告}}
\author{{匿名工程示例}}
\date{{}}
\begin{{document}}
\maketitle
\section{{范围}}
本文只描述项目自带的合成工程示例，不代表真实竞赛数据或现实结论。
\section{{结果}}
线性最小二乘模型为 $y={slope:.12g}x+{intercept:.12g}$。线性模型 RMSE 为
{linear_rmse:.12g}，均值基线 RMSE 为 {baseline_rmse:.12g}。
\section{{验证}}
独立验证状态为 \texttt{{{validation.status.value}}}。结构化事实源为
\texttt{{results/experiment.yaml}} 和 \texttt{{results/validation.yaml}}。
\end{{document}}
"""
    _atomic_text(root / "reports" / "evidence_report.md", markdown)
    _atomic_text(root / "paper" / "main.tex", latex)
    manifest = ReportManifest(
        status=Status.PASSED,
        generated_at=datetime.now(UTC),
        source_artifacts=["results/experiment.yaml", "results/validation.yaml"],
        generated_artifacts=["reports/evidence_report.md", "paper/main.tex"],
    )
    _write_model(root / "reports" / "report_manifest.yaml", manifest)
    state.artifacts.update(
        {
            "evidence_report": "reports/evidence_report.md",
            "paper_source": "paper/main.tex",
            "report_manifest": "reports/report_manifest.yaml",
        }
    )
    _advance(state, Stage.PAPER_DRAFTED)
    _save_state(root, state)
    return manifest


def compile_report(root: Path) -> PdfAcceptance:
    root = root.expanduser().resolve()
    state = _load_state(root)
    retrying = state.current_stage is Stage.FAILED and state.failed_stage is Stage.PDF_COMPILED
    if state.current_stage is not Stage.PAPER_DRAFTED and not retrying:
        raise PipelineError(f"compile-report requires PAPER_DRAFTED, found {state.current_stage.value}")
    source = root / "paper" / "main.tex"
    if not source.is_file():
        raise PipelineError("missing paper/main.tex")
    acceptance_path = root / "reports" / "pdf_acceptance.yaml"
    compiler = shutil.which("xelatex")
    if compiler is None:
        acceptance = PdfAcceptance(
            status=Status.BLOCKED,
            checked_at=datetime.now(UTC),
            source_path="paper/main.tex",
            attempts=0,
            message="XeLaTeX is unavailable on PATH; compilation, structural, identity, and visual checks were not run.",
        )
        _write_model(acceptance_path, acceptance)
        state.artifacts["pdf_acceptance"] = "reports/pdf_acceptance.yaml"
        _save_state(root, state)
        return acceptance

    outputs: list[str] = []
    return_code = 0
    execution_error: str | None = None
    for _ in range(2):
        try:
            process = subprocess.run(
                [compiler, "-interaction=nonstopmode", "-halt-on-error", source.name],
                cwd=source.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as exc:
            execution_error = str(exc)
            outputs.append(execution_error)
            return_code = -1
            break
        outputs.extend([process.stdout, process.stderr])
        return_code = process.returncode
        if return_code != 0:
            break
    _atomic_text(root / "reports" / "xelatex_command.log", "\n".join(outputs))
    pdf = root / "paper" / "main.pdf"
    structural_passed = pdf.is_file() and pdf.stat().st_size > 8 and pdf.read_bytes()[:5] == b"%PDF-"
    if return_code != 0 or not structural_passed:
        message = (
            f"XeLaTeX could not start: {execution_error}"
            if execution_error is not None
            else (f"XeLaTeX failed with exit code {return_code}." if return_code != 0 else "compiled output failed the basic PDF header/size check.")
        )
        acceptance = PdfAcceptance(
            status=Status.FAILED,
            checked_at=datetime.now(UTC),
            source_path="paper/main.tex",
            pdf_path="paper/main.pdf" if pdf.exists() else None,
            compiler=compiler,
            attempts=1 if return_code != 0 else 2,
            structural_check=Status.FAILED,
            log_path="reports/xelatex_command.log",
            message=message,
        )
        _write_model(acceptance_path, acceptance)
        state.artifacts["pdf_acceptance"] = "reports/pdf_acceptance.yaml"
        _fail(root, state, Stage.PDF_COMPILED, message)
        return acceptance

    acceptance = PdfAcceptance(
        status=Status.PASSED,
        checked_at=datetime.now(UTC),
        source_path="paper/main.tex",
        pdf_path="paper/main.pdf",
        compiler=compiler,
        attempts=2,
        structural_check=Status.PASSED,
        visual_check=Status.NOT_RUN,
        identity_check=Status.NOT_RUN,
        log_path="reports/xelatex_command.log",
        message="XeLaTeX compilation and basic PDF structure check passed; visual and identity checks remain not_run.",
    )
    _write_model(acceptance_path, acceptance)
    state.artifacts.update({"compiled_pdf": "paper/main.pdf", "pdf_acceptance": "reports/pdf_acceptance.yaml"})
    _advance(state, Stage.PDF_COMPILED)
    _save_state(root, state)
    return acceptance


def resume_phase2(root: Path) -> int:
    """Resume only the next verifiable phase-two step and stop at the compile gate."""
    root = root.expanduser().resolve()
    for _ in range(4):
        state = _load_state(root)
        stage = state.current_stage
        if stage is Stage.FAILED:
            if state.failed_stage is Stage.IMPLEMENTED:
                run_solver(root)
                continue
            if state.failed_stage is Stage.VALIDATED:
                validation = validate_results(root)
                if validation.status is not Status.PASSED:
                    return 1
                continue
            if state.failed_stage is Stage.PDF_COMPILED:
                acceptance = compile_report(root)
                return 0 if acceptance.status is Status.PASSED else (2 if acceptance.status is Status.BLOCKED else 1)
            raise PipelineError(f"unsupported failed stage: {state.failed_stage}")
        if stage is Stage.MODEL_SELECTED:
            run_solver(root)
            continue
        if stage is Stage.IMPLEMENTED:
            validation = validate_results(root)
            if validation.status is not Status.PASSED:
                return 1
            continue
        if stage is Stage.VALIDATED:
            render_report(root)
            continue
        if stage is Stage.PAPER_DRAFTED:
            acceptance = compile_report(root)
            return 0 if acceptance.status is Status.PASSED else (2 if acceptance.status is Status.BLOCKED else 1)
        if stage is Stage.PDF_COMPILED:
            return 0
        raise PipelineError(f"phase-two resume cannot start from {stage.value}")
    raise PipelineError("phase-two resume exceeded its bounded step count")
