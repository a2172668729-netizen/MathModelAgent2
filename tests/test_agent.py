from __future__ import annotations

from pathlib import Path

import yaml

from mmagent.agent import REQUIRED_SKILLS, validate_agent
from mmagent import cli


def test_repository_agent_configuration_passes() -> None:
    root = Path(__file__).resolve().parents[1]

    report = validate_agent(root)

    assert report.passed, report.errors
    assert len(REQUIRED_SKILLS) == 9


def test_agent_doctor_cli_passes(capsys) -> None:
    root = Path(__file__).resolve().parents[1]

    assert cli.main(["agent-doctor", str(root)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("PASS")


def test_agent_validation_rejects_enabled_parallel_agents(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in ("config", "skills"):
        source = root / relative
        target = tmp_path / relative
        if relative == "config":
            target.mkdir()
            for file in source.iterdir():
                target.joinpath(file.name).write_bytes(file.read_bytes())
        else:
            import shutil

            shutil.copytree(source, target)
    (tmp_path / "AGENTS.md").write_bytes((root / "AGENTS.md").read_bytes())
    config_path = tmp_path / "config" / "agent.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["capabilities"]["parallel_agents"] = "enabled"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    report = validate_agent(tmp_path)

    assert not report.passed
    assert "phase-three capability must remain disabled: parallel_agents" in report.errors

