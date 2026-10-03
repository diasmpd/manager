"""Contract: `season rules`, `--ruleset` and `--participants` (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_INVALID, EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t

RULESETS = Path(__file__).resolve().parents[1] / "fixtures" / "rulesets"
LIGA = ["--ruleset", "test-liga-unica", "--participants",
        "alvorada,campo-florido,ferroviario,jequitiba,mineracao,pedra-branca,rio-turvo,serra-negra"]


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_rules_lists_bundled(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "season", "rules")
    assert code == EXIT_OK
    assert "mg-modulo-i-2026" in out and "test-liga-unica" in out
    assert t("rules.valid") in out


def test_rules_validate_ok(capsys: pytest.CaptureFixture[str], repo_root: Path) -> None:
    path = repo_root / "core/src/manager_core/reference/competitions/mg-modulo-i-2026.toml"
    code, out, _ = _run(capsys, "season", "rules", "--validate", str(path))
    assert code == EXIT_OK
    assert t("rules.ok", path=path) in out


def test_rules_validate_reports_every_code(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "season", "rules", "--validate",
                        str(RULESETS / "multi_three_defects.toml"))
    assert code == EXIT_INVALID
    for c in ("R004", "R008", "R013"):
        assert c in out


def test_unknown_ruleset_exits_3(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, _, err = _run(capsys, "--data", str(sample_dir), "season", "--ruleset", "nope", "groups")
    assert code == EXIT_NOT_FOUND
    assert "nope" in err


def test_other_ruleset_plays_from_the_cli(capsys: pytest.CaptureFixture[str],
                                          sample_dir: Path) -> None:
    code, out, _ = _run(capsys, "--data", str(sample_dir), "season", *LIGA, "outcomes")
    assert code == EXIT_OK
    assert "Campeão da Liga Única:" in out
    code, out, _ = _run(capsys, "--data", str(sample_dir), "season", *LIGA, "bracket")
    assert code == EXIT_OK and "Decisão" in out


def test_wrong_participant_count_exits_1(capsys: pytest.CaptureFixture[str],
                                         sample_dir: Path) -> None:
    code, _, err = _run(capsys, "--data", str(sample_dir), "season", "--ruleset",
                        "test-liga-unica", "groups")
    assert code == EXIT_INVALID
    assert "S002" in err or "12" in err


def test_unknown_participant_exits_3(capsys: pytest.CaptureFixture[str],
                                     sample_dir: Path) -> None:
    code, _, _ = _run(capsys, "--data", str(sample_dir), "season", "--ruleset",
                      "test-liga-unica", "--participants", "ghost", "groups")
    assert code == EXIT_NOT_FOUND
