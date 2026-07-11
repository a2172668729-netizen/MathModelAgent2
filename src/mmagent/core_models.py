"""State contracts for the executable core pipeline."""

from __future__ import annotations

from enum import StrEnum


class CoreStage(StrEnum):
    CREATED = "CREATED"
    INPUT_READY = "INPUT_READY"
    CODE_READY = "CODE_READY"
    CODE_EXECUTED = "CODE_EXECUTED"
    RESULTS_VALIDATED = "RESULTS_VALIDATED"
    FIGURES_GENERATED = "FIGURES_GENERATED"
    TABLES_GENERATED = "TABLES_GENERATED"
    PAPER_DRAFTED = "PAPER_DRAFTED"
    PDF_COMPILED = "PDF_COMPILED"
    PDF_VALIDATED = "PDF_VALIDATED"
    REPRODUCIBILITY_VALIDATED = "REPRODUCIBILITY_VALIDATED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    FINAL = "FINAL"
    FAILED = "FAILED"


AUTOMATED_STAGE_CHAIN = (
    CoreStage.CREATED,
    CoreStage.INPUT_READY,
    CoreStage.CODE_READY,
    CoreStage.CODE_EXECUTED,
    CoreStage.RESULTS_VALIDATED,
    CoreStage.FIGURES_GENERATED,
    CoreStage.TABLES_GENERATED,
    CoreStage.PAPER_DRAFTED,
    CoreStage.PDF_COMPILED,
    CoreStage.PDF_VALIDATED,
    CoreStage.REPRODUCIBILITY_VALIDATED,
    CoreStage.AWAITING_HUMAN_APPROVAL,
)


class CoreStateError(ValueError):
    """Raised when a core run attempts an invalid stage transition."""


def advance_core_stage(history: list[str], target: CoreStage) -> None:
    """Append exactly the next automated stage and reject skipped gates."""
    if not history:
        expected = CoreStage.CREATED
    else:
        current = CoreStage(history[-1])
        if current in {CoreStage.FAILED, CoreStage.FINAL}:
            raise CoreStateError(f"cannot advance from terminal stage {current.value}")
        try:
            expected = AUTOMATED_STAGE_CHAIN[AUTOMATED_STAGE_CHAIN.index(current) + 1]
        except (ValueError, IndexError) as exc:
            raise CoreStateError(f"no automated transition is defined from {current.value}") from exc
    if target is not expected:
        raise CoreStateError(f"expected next stage {expected.value}, received {target.value}")
    history.append(target.value)


def mark_core_failed(history: list[str]) -> None:
    if not history or history[-1] != CoreStage.FAILED.value:
        history.append(CoreStage.FAILED.value)


def approve_final(history: list[str], *, approved: bool) -> None:
    """Advance to FINAL only after an explicit human approval action."""
    current = CoreStage(history[-1]) if history else None
    if current is not CoreStage.AWAITING_HUMAN_APPROVAL:
        raise CoreStateError("FINAL requires AWAITING_HUMAN_APPROVAL")
    if not approved:
        raise CoreStateError("FINAL requires explicit human approval")
    history.append(CoreStage.FINAL.value)
