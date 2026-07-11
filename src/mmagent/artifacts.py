"""Portable file and provenance helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def ensure_within(root: Path, path: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path escapes allowed root {resolved_root}: {resolved}") from exc
    return resolved


def file_records(root: Path, paths: Iterable[Path]) -> list[dict[str, Any]]:
    resolved_root = root.resolve()
    records: list[dict[str, Any]] = []
    for path in sorted({item.resolve() for item in paths}):
        relative = path.relative_to(resolved_root).as_posix()
        records.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return records


def files_under(root: Path, *directories: str) -> list[Path]:
    paths: list[Path] = []
    for directory in directories:
        base = root / directory
        if base.is_dir():
            paths.extend(path for path in base.rglob("*") if path.is_file())
    return paths
