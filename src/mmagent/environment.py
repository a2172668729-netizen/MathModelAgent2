"""Auditable discovery of external tools and read-only Git metadata."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class ToolDiscovery:
    name: str
    path: Path | None
    source: str | None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.path is not None


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "config").is_dir():
            return candidate
    return current


def _is_executable(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "path does not exist"
    if not path.is_file():
        return False, "path is not a file"
    if os.name == "nt":
        executable_suffixes = {
            suffix.casefold()
            for suffix in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
            if suffix
        }
        if path.suffix.casefold() not in executable_suffixes:
            return False, f"file extension {path.suffix or '<none>'} is not executable"
    elif not os.access(path, os.X_OK):
        return False, "file is not executable"
    return True, None


def _candidate_path(value: str | Path, name: str) -> Path:
    path = Path(value).expanduser()
    if path.is_dir():
        suffix = ".exe" if os.name == "nt" else ""
        return path / f"{name}{suffix}"
    return path


def _configured_candidate(value: str, name: str, project_root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return _candidate_path(path, name)


def _where_candidates(name: str) -> list[Path]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            ["where.exe", name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _read_tool_config(project_root: Path, name: str) -> str | None:
    for relative in (Path("config/environment.yaml"), Path("config/tools.yaml")):
        path = project_root / relative
        if not path.is_file():
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        tools = payload.get("tools", {})
        configured = tools.get(name) if isinstance(tools, dict) else None
        if isinstance(configured, dict):
            configured = configured.get("path")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
    report = project_root / "config/report.yaml"
    if name == "xelatex" and report.is_file():
        try:
            payload = yaml.safe_load(report.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        compiler = payload.get("compiler", {})
        if isinstance(compiler, dict):
            configured = compiler.get("path")
            if isinstance(configured, str) and configured.strip():
                return configured.strip()
    return None


def _version_key(path: Path) -> tuple[int, ...]:
    numbers = tuple(int(value) for value in re.findall(r"\d+", path.as_posix()))
    return numbers or (0,)


def _windows_tex_candidates(name: str) -> list[tuple[Path, str]]:
    if os.name != "nt":
        return []
    suffix = ".exe"
    roots: list[Path] = []
    system_drive = os.environ.get("SystemDrive", "C:").rstrip("\\/")
    for drive in (system_drive, "C:", "D:"):
        root = Path(f"{drive}/texlive")
        if root not in roots:
            roots.append(root)
    found: list[tuple[Path, str]] = []
    for root in roots:
        if not root.is_dir():
            continue
        matches = sorted(root.glob(f"*/bin/windows/{name}{suffix}"), key=_version_key, reverse=True)
        found.extend((path, f"windows_texlive_versioned:{root}") for path in matches)
    program_files = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    for value in program_files:
        if not value:
            continue
        base = Path(value)
        for relative in (
            Path(f"MiKTeX/miktex/bin/x64/{name}{suffix}"),
            Path(f"Programs/MiKTeX/miktex/bin/x64/{name}{suffix}"),
        ):
            found.append((base / relative, "windows_common_tex"))
    return found


def _windows_git_candidates() -> list[tuple[Path, str]]:
    if os.name != "nt":
        return []
    found: list[tuple[Path, str]] = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        if value := os.environ.get(variable):
            found.extend(
                (
                    (Path(value) / "Git/cmd/git.exe", "git_for_windows_common"),
                    (Path(value) / "Git/bin/git.exe", "git_for_windows_common"),
                )
            )
    if value := os.environ.get("LOCALAPPDATA"):
        found.append((Path(value) / "Programs/Git/cmd/git.exe", "git_for_windows_common"))
    runtime_root = Path.home() / ".cache/codex-runtimes"
    if runtime_root.is_dir():
        found.extend(
            (path, "codex_runtime_git")
            for path in sorted(runtime_root.glob("*/dependencies/native/git/cmd/git.exe"))
        )
    return found


def _environment_candidates(name: str) -> Iterable[tuple[str, str]]:
    specific = os.environ.get(f"MMAGENT_{name.upper()}")
    if specific:
        yield specific, f"environment:MMAGENT_{name.upper()}"
    if name in {"xelatex", "latexmk", "kpsewhich"}:
        tex_bin = os.environ.get("MMAGENT_TEX_BIN")
        if tex_bin:
            yield tex_bin, "environment:MMAGENT_TEX_BIN"


def discover_tool(name: str, *, project_root: Path | None = None) -> ToolDiscovery:
    """Discover a tool in a deterministic order and retain failed diagnostics."""
    root = find_project_root(project_root)
    diagnostics: list[str] = []
    candidates: list[tuple[Path, str]] = []

    if path_value := shutil.which(name):
        candidates.append((Path(path_value), "process_path"))
    candidates.extend((path, "where.exe") for path in _where_candidates(name))

    configured = _read_tool_config(root, name)
    if name == "git":
        candidates.extend(_windows_git_candidates())
        if configured:
            candidates.append((_configured_candidate(configured, name, root), "project_config"))
    else:
        if configured:
            candidates.append((_configured_candidate(configured, name, root), "project_config"))
        candidates.extend((_candidate_path(value, name), source) for value, source in _environment_candidates(name))
        if name in {"xelatex", "latexmk", "kpsewhich"}:
            candidates.extend(_windows_tex_candidates(name))

    seen: set[str] = set()
    for candidate, source in candidates:
        key = str(candidate).casefold()
        if key in seen:
            continue
        seen.add(key)
        valid, reason = _is_executable(candidate)
        if valid:
            return ToolDiscovery(name=name, path=candidate.resolve(), source=source, diagnostics=tuple(diagnostics))
        diagnostics.append(f"{source}: {candidate} ({reason})")
    diagnostics.append(
        f"{name} was not found; add it to PATH or configure config/environment.yaml under tools.{name}.path"
    )
    return ToolDiscovery(name=name, path=None, source=None, diagnostics=tuple(diagnostics))


def _run_git(git: Path, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(git), "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
        shell=False,
    )


def inspect_git(project_root: Path, discovery: ToolDiscovery | None = None) -> dict[str, Any]:
    root = find_project_root(project_root)
    result = discovery or discover_tool("git", project_root=root)
    if result.path is None:
        return {
            "status": "git_unavailable",
            "git_path": None,
            "source": None,
            "repository": "not_run",
            "commit": "not_run",
            "branch": "not_run",
            "worktree": "not_run",
            "diagnostics": list(result.diagnostics),
            "remedy": "Install Git for Windows, add git.exe to PATH, or configure tools.git.path in config/environment.yaml.",
        }
    try:
        repository = _run_git(result.path, root, "rev-parse", "--is-inside-work-tree")
        if repository.returncode != 0 or repository.stdout.strip().casefold() != "true":
            return {
                "status": "not_a_git_repository",
                "git_path": str(result.path),
                "source": result.source,
                "repository": "not_a_git_repository",
                "commit": "not_run",
                "branch": "not_run",
                "worktree": "not_run",
                "diagnostics": [repository.stderr.strip() or repository.stdout.strip()],
            }
        commit = _run_git(result.path, root, "rev-parse", "HEAD")
        branch = _run_git(result.path, root, "branch", "--show-current")
        worktree = _run_git(result.path, root, "status", "--porcelain")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "git_metadata_unavailable",
            "git_path": str(result.path),
            "source": result.source,
            "repository": "unknown",
            "commit": "not_run",
            "branch": "not_run",
            "worktree": "not_run",
            "diagnostics": [str(exc)],
        }
    commit_value = commit.stdout.strip()
    commit_unborn = commit.returncode != 0 and branch.returncode == 0 and worktree.returncode == 0
    if commit_unborn:
        commit_value = "unborn (repository has no commits)"
    if branch.returncode != 0 or worktree.returncode != 0 or (commit.returncode != 0 and not commit_unborn):
        return {
            "status": "git_metadata_unavailable",
            "git_path": str(result.path),
            "source": result.source,
            "repository": "git_repository",
            "commit": "not_run",
            "branch": "not_run",
            "worktree": "not_run",
            "diagnostics": [command.stderr.strip() for command in (commit, branch, worktree) if command.returncode != 0],
        }
    branch_name = branch.stdout.strip() or "detached_head"
    return {
        "status": "available",
        "git_path": str(result.path),
        "source": result.source,
        "repository": "git_repository",
        "commit": commit_value,
        "branch": branch_name,
        "worktree": "clean" if not worktree.stdout.strip() else "dirty",
        "diagnostics": list(result.diagnostics)
        + (["HEAD is unborn; the repository has no commits yet"] if commit_unborn else []),
    }
