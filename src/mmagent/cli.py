"""Command-line interface for workspace foundations and the phase-two closed loop."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import sys
from pathlib import Path

from mmagent.agent import validate_agent
from mmagent.core_pipeline import (
    CorePipelineError,
    core_status,
    execute_curve_fitting_run,
    reproduce_curve_fitting,
    recompile_core_run,
    run_curve_fitting_demo,
    validate_core_run,
)
from mmagent.environment import discover_tool, inspect_git
from mmagent.benchmark import load_scorecard, write_scorecard
from mmagent.artifacts import atomic_json, atomic_text
from mmagent.benchmark_runner import compare_suite_reports, load_cases, run_suite, select_cases
from mmagent.input_audit import audit_inputs
from mmagent.models import Status
from mmagent.pdf import PdfPipelineError
from mmagent.pipeline import (
    PipelineError,
    compile_report,
    create_demo_workspace,
    render_report,
    resume_phase2,
    run_solver,
    validate_results,
)
from mmagent.workspace import cwd_is_writable, initialize_workspace, read_status, validate_workspace
from mmagent.models import Stage
from mmagent.real_problem import advance_real_stage, create_real_workspace
from mmagent.results_registry import generate_latex_macros


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mmagent", description="Artifact-first mathematical modeling workspace and assisted agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "validate-workspace", "validate-results", "render-report", "compile-report", "resume"):
        command = subparsers.add_parser(name)
        command.add_argument("workspace", type=Path)
    new_command = subparsers.add_parser("new")
    new_command.add_argument("problem_id")
    new_command.add_argument("--root", type=Path, default=Path("workspaces"))
    audit_input = subparsers.add_parser("audit-input")
    audit_input.add_argument("workspace", type=Path)
    advance = subparsers.add_parser("advance")
    advance.add_argument("workspace", type=Path)
    advance.add_argument("stage", choices=[stage.value for stage in Stage])
    result_macros = subparsers.add_parser("results-macros")
    result_macros.add_argument("workspace", type=Path)
    scorecard = subparsers.add_parser("benchmark-scorecard")
    scorecard.add_argument("workspace", type=Path)
    benchmark = subparsers.add_parser("benchmark")
    benchmark_actions = benchmark.add_subparsers(dest="benchmark_action", required=True)
    benchmark_run = benchmark_actions.add_parser("run")
    selection = benchmark_run.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case")
    selection.add_argument("--tag")
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--smoke", action="store_true")
    selection.add_argument("--full", action="store_true")
    benchmark_run.add_argument("--repeat", type=int)
    benchmark_run.add_argument("--output", type=Path, default=Path("benchmark_results"))
    benchmark_run.add_argument("--cases-root", type=Path, default=Path("benchmarks/cases"))
    benchmark_compare = benchmark_actions.add_parser("compare")
    benchmark_compare.add_argument("first", type=Path)
    benchmark_compare.add_argument("second", type=Path)
    benchmark_compare.add_argument("--output", type=Path)
    benchmark_actions.add_parser("list")
    demo = subparsers.add_parser("demo")
    demo.add_argument("target", help="'curve-fitting' or a legacy Phase 2 workspace path")
    demo.add_argument("--workspace", type=Path, help="output workspace for the curve-fitting demo")
    demo.add_argument("--timeout", type=float, default=120)
    run_command = subparsers.add_parser("run-solver")
    run_command.add_argument("workspace", type=Path)
    run_command.add_argument("--timeout", type=int, default=120)
    core_run = subparsers.add_parser("run")
    core_run.add_argument("workspace", type=Path)
    core_run.add_argument("--timeout", type=float, default=120)
    core_compile = subparsers.add_parser("compile")
    core_compile.add_argument("workspace", type=Path)
    core_compile.add_argument("--run-id")
    core_validate = subparsers.add_parser("validate")
    core_validate.add_argument("workspace", type=Path)
    core_validate.add_argument("--run-id")
    core_reproduce = subparsers.add_parser("reproduce")
    core_reproduce.add_argument("workspace", type=Path)
    core_reproduce.add_argument("--run-id")
    core_reproduce.add_argument("--timeout", type=float, default=120)
    agent_doctor = subparsers.add_parser("agent-doctor")
    agent_doctor.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    subparsers.add_parser("doctor")
    return parser


def _print_report(errors: list[str], warnings: list[str]) -> None:
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")


def _doctor() -> int:
    required = {
        "Python >= 3.11": sys.version_info >= (3, 11),
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "PyYAML": importlib.util.find_spec("yaml") is not None,
        "numpy": importlib.util.find_spec("numpy") is not None,
        "pandas": importlib.util.find_spec("pandas") is not None,
        "openpyxl": importlib.util.find_spec("openpyxl") is not None,
        "Pillow": importlib.util.find_spec("PIL") is not None,
        "scipy": importlib.util.find_spec("scipy") is not None,
        "matplotlib": importlib.util.find_spec("matplotlib") is not None,
        "pypdf": importlib.util.find_spec("pypdf") is not None,
        "PyMuPDF": importlib.util.find_spec("fitz") is not None,
        "current directory writable (OS check only)": cwd_is_writable(Path.cwd()),
    }
    root = Path.cwd()
    optional = {
        "XeLaTeX": discover_tool("xelatex", project_root=root),
        "latexmk": discover_tool("latexmk", project_root=root),
        "kpsewhich": discover_tool("kpsewhich", project_root=root),
        "pdftotext": discover_tool("pdftotext", project_root=root),
        "pdftoppm": discover_tool("pdftoppm", project_root=root),
    }
    git = inspect_git(root)
    print(f"Platform: {platform.platform()}")
    print(f"Python: {platform.python_version()}")
    for name, available in required.items():
        print(f"{'PASS' if available else 'FAIL'}: {name}")
    if git["git_path"]:
        print(f"FOUND: Git -> {git['git_path']} [source={git['source']}]")
        print(f"Git status: {git['status']}")
        print(f"Git repository: {git['repository']}")
        print(f"Git commit: {git['commit']}")
        print(f"Git branch: {git['branch']}")
        print(f"Git worktree: {git['worktree']}")
        for diagnostic in git["diagnostics"]:
            if diagnostic:
                print(f"Git diagnostic: {diagnostic}")
    else:
        print("MISSING (optional): Git")
        print(f"Git status: {git['status']}")
        print(f"Git repository: {git['repository']}")
        print(f"Git worktree: {git['worktree']}")
        print(f"Git remedy: {git.get('remedy', 'inspect Git diagnostics')}")
        for diagnostic in git["diagnostics"]:
            if diagnostic:
                print(f"Git diagnostic: {diagnostic}")
    for name, discovery in optional.items():
        detail = f" -> {discovery.path} [source={discovery.source}]" if discovery.path else ""
        print(f"{'FOUND' if discovery.found else 'MISSING (optional)'}: {name}{detail}")
        if not discovery.found:
            for diagnostic in discovery.diagnostics:
                print(f"  diagnostic: {diagnostic}")
    font_roots = [Path.home() / "AppData/Local/Microsoft/Windows/Fonts", Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    if windows_root := os.environ.get("WINDIR"):
        font_roots.append(Path(windows_root) / "Fonts")
    recommended_stems = {"simsun", "simhei", "msyh", "songti sc", "heiti sc", "stfangsong"}
    found_fonts = sorted(
        {
            item.stem
            for root in font_roots
            if root.is_dir()
            for item in root.iterdir()
            if item.is_file() and item.stem.casefold() in recommended_stems
        }
    )
    detail = f" -> {', '.join(found_fonts)}" if found_fonts else ""
    print(f"{'FOUND' if found_fonts else 'NOT CONFIRMED (optional)'}: recommended CJK fonts{detail}")
    return 0 if all(required.values()) else 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "new":
        try:
            root = create_real_workspace(args.problem_id, args.root)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"Workspace: {root}")
        print("Current stage: CREATED")
        print("NEXT: place the problem PDF and attachments in input/, then run audit-input")
        return 0
    if args.command == "audit-input":
        try:
            inventory = audit_inputs(args.workspace)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"Audited files: {len(inventory.files)}")
        print(f"Readable files: {sum(item.read_success for item in inventory.files)}")
        print("Reports: input_inventory.json, input_inventory.md")
        return 0
    if args.command == "advance":
        try:
            state = advance_real_stage(args.workspace, Stage(args.stage))
        except (OSError, ValueError) as exc:
            print(f"BLOCKED: {exc}")
            return 2
        print(f"PASS: advanced to {state.current_stage.value}")
        return 0
    if args.command == "results-macros":
        try:
            target = generate_latex_macros(args.workspace)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {target}")
        return 0
    if args.command == "benchmark-scorecard":
        try:
            scorecard = load_scorecard(args.workspace)
            _, target = write_scorecard(args.workspace, scorecard)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {target}")
        print("Subjective scores remain human-only; blank scores were not filled.")
        return 0
    if args.command == "benchmark":
        repo_root = Path.cwd().resolve()
        if args.benchmark_action == "list":
            try:
                cases = load_cases(repo_root / "benchmarks" / "cases")
            except (OSError, ValueError) as exc:
                print(f"ERROR: {exc}")
                return 1
            for case, _ in cases.values():
                print(f"{case.id}\t{case.difficulty}\t{','.join(case.tags)}\t{'smoke' if case.smoke else 'full'}\t{case.expected_outcome}")
            return 0
        if args.benchmark_action == "compare":
            try:
                comparison = compare_suite_reports(args.first, args.second)
            except (OSError, ValueError) as exc:
                print(f"ERROR: {exc}")
                return 1
            output = args.output or args.second.parent / f"comparison-{args.first.parent.name}-to-{args.second.parent.name}.json"
            atomic_json(output, comparison)
            atomic_text(output.with_suffix(".md"), "# Benchmark comparison\n\n" + f"Status: **{comparison['status']}**\n\n" + "\n".join(f"- {item}" for item in comparison["regressions"]) + "\n")
            print(f"Comparison: {output}")
            print(f"Status: {comparison['status']}")
            return 1 if comparison["status"] == "regression" else 0
        try:
            cases = load_cases(args.cases_root)
            mode, selected = select_cases(
                cases,
                case_id=args.case,
                tag=args.tag,
                all_cases=args.all,
                smoke=args.smoke,
                full=args.full,
            )
            repetitions = args.repeat if args.repeat is not None else (2 if args.full else 1)
            if repetitions < 1:
                raise ValueError("--repeat must be at least 1")
            report, result_root = run_suite(repo_root, selected, mode=mode, output_root=args.output, repetitions=repetitions)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"Benchmark: {result_root}")
        print(f"Status: {report.status}")
        print(f"Cases: {report.totals}")
        return 0 if report.status == "passed" else 1
    if args.command == "init":
        try:
            result = initialize_workspace(args.workspace)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"Workspace: {result.root}")
        for path in result.created:
            print(f"CREATED: {path.relative_to(result.root).as_posix() if path != result.root else '.'}")
        for path in result.existing:
            print(f"PRESERVED: {path.relative_to(result.root).as_posix()}")
        return 0
    if args.command == "status":
        if (args.workspace.expanduser().resolve() / "latest_run.json").is_file():
            try:
                status = core_status(args.workspace)
            except (OSError, ValueError, CorePipelineError) as exc:
                print(f"ERROR: {exc}")
                return 1
            print(f"Workspace: {status['workspace']}")
            print(f"Latest run: {status['latest']['run_id']}")
            print(f"Current state: {status['manifest']['current_state']}")
            print(f"Status: {status['manifest']['status']}")
            print(f"Human approval: {status['manifest']['human_approval_status']}")
            return 0
        state, report = read_status(args.workspace)
        if state is not None:
            print(f"Workspace: {state.workspace_id}")
            print(f"Current stage: {state.current_stage.value}")
            completed = ", ".join(stage.value for stage in state.completed_stages) or "none"
            print(f"Completed stages: {completed}")
        _print_report(report.errors, report.warnings)
        print(f"Missing or invalid items: {len(report.errors)}")
        return 0 if state is not None else 1
    if args.command == "validate-workspace":
        report = validate_workspace(args.workspace)
        _print_report(report.errors, report.warnings)
        print("PASS" if report.passed else "FAIL")
        return 0 if report.passed else 1
    if args.command == "demo":
        if args.target == "curve-fitting":
            workspace = args.workspace or Path("workspaces") / "curve_fitting_demo"
            try:
                summary = run_curve_fitting_demo(workspace, timeout_seconds=args.timeout)
            except (OSError, ValueError, CorePipelineError, PdfPipelineError) as exc:
                print(f"ERROR: {exc}")
                return 1
            print(f"Workspace: {summary['workspace']}")
            print(f"First run: {summary['first_run']}")
            print(f"Reproduction run: {summary['reproduction_run']}")
            print(f"Reproducibility: {summary['reproducibility']['status']}")
            print(f"Current state: {summary['state']}")
            return 0
        if args.workspace is not None:
            print("ERROR: --workspace is only valid with 'demo curve-fitting'")
            return 1
        try:
            root = create_demo_workspace(Path(args.target))
            print(f"Demo workspace: {root}")
            result = resume_phase2(root)
            if result == 2:
                print("BLOCKED: report source and acceptance record were created, but XeLaTeX is unavailable.")
            return result
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
    if args.command == "run":
        try:
            run = execute_curve_fitting_run(args.workspace, timeout_seconds=args.timeout)
        except (OSError, ValueError, CorePipelineError, PdfPipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {run}")
        print("Current state: PDF_VALIDATED")
        return 0
    if args.command == "compile":
        try:
            run, execution, validation = recompile_core_run(args.workspace, args.run_id)
        except (OSError, ValueError, CorePipelineError, PdfPipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {run / 'paper' / 'main.pdf'}")
        print(f"Pages: {validation['page_count']}; bytes: {validation['size_bytes']}; exit: {execution['exit_code']}")
        return 0
    if args.command == "validate":
        try:
            validation = validate_core_run(args.workspace, args.run_id)
        except (OSError, ValueError, CorePipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(validation["status"].upper())
        print(f"Run: {validation['run_id']}")
        print(f"Current state: {validation['current_state']}")
        return 0 if validation["status"] == "passed" else 1
    if args.command == "reproduce":
        try:
            run, report = reproduce_curve_fitting(
                args.workspace,
                source_run_id=args.run_id,
                timeout_seconds=args.timeout,
            )
        except (OSError, ValueError, CorePipelineError, PdfPipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {run}")
        print(f"Reproducibility: {report['classification']}")
        print("Current state: AWAITING_HUMAN_APPROVAL")
        return 0
    if args.command == "run-solver":
        try:
            manifest = run_solver(args.workspace, timeout_seconds=args.timeout)
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {manifest.run_id}")
        return 0
    if args.command == "validate-results":
        try:
            validation = validate_results(args.workspace)
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(validation.status.value.upper())
        return 0 if validation.status is Status.PASSED else 1
    if args.command == "render-report":
        try:
            manifest = render_report(args.workspace)
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"PASS: {', '.join(manifest.generated_artifacts)}")
        return 0
    if args.command == "compile-report":
        try:
            acceptance = compile_report(args.workspace)
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"{acceptance.status.value.upper()}: {acceptance.message}")
        return 0 if acceptance.status is Status.PASSED else (2 if acceptance.status is Status.BLOCKED else 1)
    if args.command == "resume":
        try:
            result = resume_phase2(args.workspace)
        except (OSError, ValueError, PipelineError) as exc:
            print(f"ERROR: {exc}")
            return 1
        if result == 2:
            print("BLOCKED: XeLaTeX is unavailable; inspect reports/pdf_acceptance.yaml.")
        return result
    if args.command == "doctor":
        return _doctor()
    if args.command == "agent-doctor":
        report = validate_agent(args.root)
        _print_report(report.errors, report.warnings)
        print("PASS" if report.passed else "FAIL")
        return 0 if report.passed else 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
