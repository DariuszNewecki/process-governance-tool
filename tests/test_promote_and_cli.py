"""G3 dry run by default, G4 explicit approved promotion, G5 outputs never in the source."""

from __future__ import annotations

from procgov.cli import main


def _draft(config):
    path = config.library / "WI-001-v2.md"
    path.write_text(
        (config.library / "WI-001-receiving-deliveries.md")
        .read_text()
        .replace("status: DOCUMENT", "status: DRAFT")
    )
    return path


def test_promote_is_a_dry_run_without_write(config, capsys):
    path = _draft(config)
    before = path.read_text()
    assert (
        main(
            [
                "--config",
                str(config.root / "procgov.yaml"),
                "promote",
                "WI-001-v2.md",
                "--approved-by",
                "Process Owner",
            ]
        )
        == 0
    )
    assert path.read_text() == before
    assert "dry run" in capsys.readouterr().out


def test_promote_with_write_archives_the_old_version_and_records_the_approver(config):
    path = _draft(config)
    assert (
        main(
            [
                "--config",
                str(config.root / "procgov.yaml"),
                "promote",
                "WI-001-v2.md",
                "--approved-by",
                "Process Owner",
                "--write",
            ]
        )
        == 0
    )
    assert "status: DOCUMENT\napproved_by: Process Owner" in path.read_text()
    old = (config.library / "WI-001-receiving-deliveries.md").read_text()
    assert "status: ARCHIVE" in old


def test_a_draft_that_fails_the_check_is_not_promoted(config, capsys):
    path = config.library / "WI-002.md"
    path.write_text(
        "---\nid: WI-002\ntitle: T\ntype: work_instruction\nstatus: DRAFT\n"
        "owner: me\n---\n\n## Purpose\n\nx\n"
    )
    assert (
        main(
            [
                "--config",
                str(config.root / "procgov.yaml"),
                "promote",
                "WI-002.md",
                "--approved-by",
                "Process Owner",
                "--write",
            ]
        )
        == 1
    )
    assert "status: DRAFT" in path.read_text()
    assert "does not pass the check" in capsys.readouterr().err


def test_check_exits_1_on_errors_and_0_when_clean(config):
    cfg = str(config.root / "procgov.yaml")
    assert main(["--config", cfg, "check"]) == 0
    (config.library / "bad.md").write_text("no front matter\n")
    assert main(["--config", cfg, "check"]) == 1


def test_render_into_the_library_is_refused(config, capsys):
    cfg = str(config.root / "procgov.yaml")
    assert main(["--config", cfg, "render", "PR-001", "--out", str(config.library)]) == 1
    assert "inside the library" in capsys.readouterr().err
    assert not (config.library / "PR-001.docx").exists()


def test_render_register_package_site_write_outside_the_library(config):
    cfg = str(config.root / "procgov.yaml")
    for command in ("render", "register", "package", "site"):
        assert main(["--config", cfg, command]) == 0
    build = config.root / "build"
    assert (build / "docx" / "PR-001.docx").is_file()
    assert (build / "register" / "register.csv").is_file()
    assert (build / "package" / "manifest.json").is_file()
    assert (build / "site.zip").is_file()
