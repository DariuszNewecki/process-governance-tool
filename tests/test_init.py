"""``procgov init``: a starter configuration that loads, and never one overwritten."""

from __future__ import annotations

from procgov.cli import main
from procgov.config import load_config


def test_init_writes_a_configuration_that_loads(tmp_path):
    cfg = tmp_path / "procgov.yaml"
    assert main(["--config", str(cfg), "init", "--organisation", "Fernhill: Garden"]) == 0
    config = load_config(cfg)
    assert config.organisation == "Fernhill: Garden"
    assert config.library == tmp_path / "library"
    assert set(config.document_types) == {"process", "work_instruction"}


def test_init_never_replaces_a_configuration(tmp_path, capsys):
    cfg = tmp_path / "procgov.yaml"
    cfg.write_text("mine\n")
    assert main(["--config", str(cfg), "init", "--organisation", "Fernhill"]) == 1
    assert cfg.read_text() == "mine\n"
    assert "never replaces" in capsys.readouterr().err
