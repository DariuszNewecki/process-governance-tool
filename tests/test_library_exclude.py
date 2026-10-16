"""library_exclude: working records beside governed documents are left out,
by the one loader, and named (soak issue #2)."""

from __future__ import annotations

from procgov.cli import main
from procgov.config import load_config
from procgov.model import load_library


def _with_records(fernhill):
    records = fernhill / "library" / "records"
    records.mkdir()
    (records / "status-update-2026-10.md").write_text("# Status\n\nNo front-matter.\n")
    (fernhill / "library" / "meeting-invite.md").write_text("# Invite\n")
    cfg = fernhill / "procgov.yaml"
    cfg.write_text(cfg.read_text() + "library_exclude:\n  - 'records/*'\n  - '*invite*'\n")
    return load_config(cfg)


def test_excluded_files_are_not_loaded_but_listed(fernhill):
    config = _with_records(fernhill)
    library = load_library(config.library, config.library_exclude)
    assert [d.id for d in library.documents] == ["PR-001", "WI-001"]
    assert library.excluded == ("meeting-invite.md", "records/status-update-2026-10.md")


def test_check_names_what_it_excluded_and_passes(fernhill, capsys):
    config = _with_records(fernhill)
    assert main(["--config", str(config.root / "procgov.yaml"), "check"]) == 0
    out = capsys.readouterr().out
    assert "excluded by library_exclude: meeting-invite.md, records/status-update-2026-10.md" in out
