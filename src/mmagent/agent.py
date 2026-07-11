"""Local validation for the repository's Codex-assisted agent configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from mmagent.models import Stage

REQUIRED_SKILLS = {
    "modeling-orchestrator",
    "problem-analysis",
    "data-audit",
    "model-design",
    "implementation",
    "validation",
    "report-writing",
    "academic-humanizer-zh",
    "reviewer",
}

EXPECTED_STAGE_CHAIN = [
    Stage.CREATED,
    Stage.INGESTED,
    Stage.ANALYZED,
    Stage.DATA_READY,
    Stage.MODELS_PROPOSED,
    Stage.MODEL_SELECTED,
    Stage.IMPLEMENTED,
    Stage.VALIDATED,
    Stage.PAPER_DRAFTED,
    Stage.PAPER_HUMANIZED,
    Stage.FACT_CHECKED,
    Stage.PDF_COMPILED,
    Stage.FORMAT_CHECKED,
    Stage.REVIEWED,
    Stage.FINALIZED,
]


@dataclass(slots=True)
class AgentValidationReport:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _yaml(path: Path, report: AgentValidationReport) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        report.errors.append(f"cannot read {path.relative_to(report.root).as_posix()}: {exc}")
        return {}
    if not isinstance(value, dict):
        report.errors.append(f"expected mapping in {path.relative_to(report.root).as_posix()}")
        return {}
    return value


def _frontmatter(path: Path, report: AgentValidationReport) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.errors.append(f"cannot read {path.relative_to(report.root).as_posix()}: {exc}")
        return {}
    if "TODO" in text:
        report.errors.append(f"unfinished TODO in {path.relative_to(report.root).as_posix()}")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        report.errors.append(f"invalid frontmatter boundary in {path.relative_to(report.root).as_posix()}")
        return {}
    try:
        value = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        report.errors.append(f"invalid frontmatter in {path.relative_to(report.root).as_posix()}: {exc}")
        return {}
    return value if isinstance(value, dict) else {}


def validate_agent(root: Path) -> AgentValidationReport:
    root = root.expanduser().resolve()
    report = AgentValidationReport(root=root)
    agent_path = root / "config" / "agent.yaml"
    model_path = root / "config" / "models.yaml"
    report_path = root / "config" / "report.yaml"
    for path in (agent_path, model_path, report_path, root / "AGENTS.md"):
        if not path.is_file():
            report.errors.append(f"missing required agent file: {path.relative_to(root).as_posix()}")
    if report.errors:
        return report

    agent_config = _yaml(agent_path, report)
    model_config = _yaml(model_path, report)
    report_config = _yaml(report_path, report)
    if agent_config.get("mode") != "assisted":
        report.errors.append("config/agent.yaml mode must be assisted")
    if agent_config.get("max_concurrent_writers") != 1:
        report.errors.append("max_concurrent_writers must remain 1")
    if agent_config.get("max_stage_retries") not in {1, 2, 3}:
        report.errors.append("max_stage_retries must be between 1 and 3")

    capabilities = agent_config.get("capabilities", {})
    for name in ("external_research", "openai_api", "rag", "web_ui", "database_service", "parallel_agents"):
        if capabilities.get(name) != "disabled":
            report.errors.append(f"phase-three capability must remain disabled: {name}")

    stages = agent_config.get("stages", [])
    actual_chain: list[str] = []
    owners: set[str] = set()
    if not isinstance(stages, list):
        report.errors.append("config/agent.yaml stages must be a list")
    else:
        for index, item in enumerate(stages):
            if not isinstance(item, dict):
                report.errors.append(f"stage entry {index} must be a mapping")
                continue
            source, target, owner = item.get("from"), item.get("to"), item.get("owner")
            if index == 0:
                actual_chain.append(str(source))
            actual_chain.append(str(target))
            owners.add(str(owner))
            if not item.get("required_outputs"):
                report.errors.append(f"stage {source}->{target} has no required_outputs")
    expected_chain = [stage.value for stage in EXPECTED_STAGE_CHAIN]
    if actual_chain != expected_chain:
        report.errors.append("configured stage chain is not the canonical continuous state chain")
    configured_checkpoints = set(agent_config.get("human_checkpoints", []))
    stage_checkpoints = {
        str(item.get("to")) for item in stages if isinstance(item, dict) and item.get("human_checkpoint") is True
    }
    if configured_checkpoints != stage_checkpoints:
        report.errors.append("human_checkpoints must match stage entries marked human_checkpoint")

    skills_root = root / "skills"
    for name in sorted(REQUIRED_SKILLS):
        skill_path = skills_root / name / "SKILL.md"
        metadata_path = skills_root / name / "agents" / "openai.yaml"
        if not skill_path.is_file():
            report.errors.append(f"missing skill: skills/{name}/SKILL.md")
            continue
        frontmatter = _frontmatter(skill_path, report)
        if frontmatter.get("name") != name:
            report.errors.append(f"skill name mismatch: {name}")
        if set(frontmatter) != {"name", "description"}:
            report.errors.append(f"skill frontmatter must contain only name and description: {name}")
        if not metadata_path.is_file():
            report.errors.append(f"missing UI metadata: skills/{name}/agents/openai.yaml")
            continue
        metadata = _yaml(metadata_path, report).get("interface", {})
        if not isinstance(metadata, dict):
            report.errors.append(f"invalid interface metadata: {name}")
            continue
        prompt = metadata.get("default_prompt", "")
        if f"${name}" not in prompt:
            report.errors.append(f"default_prompt must mention ${name}")
        description = metadata.get("short_description", "")
        if not 25 <= len(description) <= 64:
            report.errors.append(f"short_description length must be 25-64: {name}")
    if not owners <= REQUIRED_SKILLS:
        report.errors.append("stage owner references an unknown skill: " + ", ".join(sorted(owners - REQUIRED_SKILLS)))

    selection = model_config.get("selection_policy", {})
    if not all(selection.get(key) is True for key in ("baseline_required", "human_approval_required", "selection_evidence_required")):
        report.errors.append("model selection policy must require baseline, human approval, and evidence")
    gates = report_config.get("final_gates", {})
    if not gates or any(value != "required" for value in gates.values()):
        report.errors.append("every configured final gate must be required")
    return report
