"""Read-only inventory generation for real-problem input materials."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from PIL import Image
from pypdf import PdfReader

from mmagent.real_models import InputInventory, InputInventoryEntry, SheetMetadata


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _table_metadata(path: Path) -> list[SheetMetadata]:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame = pd.read_csv(path)
        return [
            SheetMetadata(
                name="csv",
                rows=len(frame.index),
                columns=len(frame.columns),
                field_names=[str(column) for column in frame.columns],
            )
        ]
    sheets: list[SheetMetadata] = []
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        for sheet_name in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet_name)
            sheets.append(
                SheetMetadata(
                    name=str(sheet_name),
                    rows=len(frame.index),
                    columns=len(frame.columns),
                    field_names=[str(column) for column in frame.columns],
                )
            )
    return sheets


def _probe(path: Path) -> tuple[str, list[SheetMetadata]]:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        reader = PdfReader(path)
        _ = len(reader.pages)
        return "pdf", []
    if suffix in {".txt", ".md", ".markdown"}:
        path.read_text(encoding="utf-8")
        return "text", []
    if suffix in {".csv", ".xlsx"}:
        return ("csv" if suffix == ".csv" else "xlsx"), _table_metadata(path)
    if suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
        return "json", []
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}:
        with Image.open(path) as image:
            image.verify()
        return "image", []
    raise ValueError(f"unsupported attachment type: {suffix or '<no extension>'}")


def audit_inputs(workspace: Path) -> InputInventory:
    """Scan input files without modifying them, then persist JSON and Markdown reports."""
    root = workspace.expanduser().resolve()
    input_root = root / "input"
    if not input_root.is_dir():
        raise ValueError(f"missing input directory: {input_root}")
    entries: list[InputInventoryEntry] = []
    for path in sorted((item for item in input_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        file_type = path.suffix.casefold().lstrip(".") or "unknown"
        sheets: list[SheetMetadata] = []
        error: str | None = None
        try:
            file_type, sheets = _probe(path)
        except Exception as exc:  # each file must be reported even when its parser rejects it
            error = f"{type(exc).__name__}: {exc}"
        entries.append(
            InputInventoryEntry(
                filename=path.name,
                relative_path=relative,
                file_type=file_type,
                size_bytes=path.stat().st_size,
                sha256=_sha256(path),
                read_success=error is None,
                sheets=sheets,
                parse_error=error,
            )
        )
    inventory = InputInventory(generated_at=datetime.now(UTC), files=entries)
    (root / "input_inventory.json").write_text(
        json.dumps(inventory.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "input_inventory.md").write_text(_inventory_markdown(inventory), encoding="utf-8")
    return inventory


def _inventory_markdown(inventory: InputInventory) -> str:
    lines = [
        "# Input inventory",
        "",
        f"Generated: {inventory.generated_at.isoformat()}",
        "",
        "| File | Path | Type | Bytes | SHA-256 | Read | Diagnostic |",
        "|---|---|---:|---:|---|---:|---|",
    ]
    for item in inventory.files:
        diagnostic = (item.parse_error or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item.filename} | `{item.relative_path}` | {item.file_type} | {item.size_bytes} | "
            f"`{item.sha256}` | {'yes' if item.read_success else 'no'} | {diagnostic} |"
        )
        for sheet in item.sheets:
            fields = ", ".join(sheet.field_names) or "(none)"
            lines.append(f"| ↳ sheet `{sheet.name}` |  | rows={sheet.rows} | columns={sheet.columns} |  |  | fields: {fields} |")
    if not inventory.files:
        lines.append("| (no input files) | `input/` |  |  |  | no | Add the problem PDF or attachments. |")
    return "\n".join(lines) + "\n"
