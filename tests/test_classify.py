"""R4: a configurable classification test, reported as proposals (G2)."""

from __future__ import annotations

from dataclasses import replace

from procgov.classify import as_findings, classify
from procgov.cli import main
from procgov.model import load_library


def test_declared_types_that_read_right_get_no_proposal(config, library):
    results = classify(library, config)
    assert [(r.document, r.proposed) for r in results] == [
        ("PR-001-seed-ordering.md", "process"),
        ("WI-001-receiving-deliveries.md", "work_instruction"),
    ]
    assert as_findings(results, config) == []


def test_a_process_that_reads_like_a_work_instruction_is_proposed(config):
    (config.library / "PR-009.md").write_text(
        "---\nid: PR-009\ntitle: Till\ntype: process\nstatus: DRAFT\nowner: me\n---\n\n"
        "## Purpose\n\nOpen the till. Select cash. Press enter. Scan the card. Click done.\n"
    )
    results = classify(load_library(config.library), config)
    [r] = [r for r in results if r.document == "PR-009.md"]
    assert (r.declared, r.proposed, r.missing_sections) == (
        "process",
        "work_instruction",
        ("Steps",),
    )
    [f] = as_findings(results, config)
    assert f.severity == "proposal" and f.proposal == "work_instruction"
    assert "indicator counts" in f.reason


def test_rows_that_read_right_carry_no_note(config, library):
    assert [r.note for r in classify(library, config)] == ["", ""]


def test_a_document_without_a_type_says_why_its_row_is_empty(config):
    (config.library / "notes.md").write_text("---\ntitle: Notes\n---\n\nPlain text.\n")
    [r] = [r for r in classify(load_library(config.library), config) if r.document == "notes.md"]
    assert (r.declared, r.proposed, r.missing_sections) == ("", "", ())
    assert r.note == "no type declared; no type's indicators lead clearly enough for a proposal"


def test_without_indicators_no_proposal_is_possible_and_the_row_says_so(config):
    plain = {key: replace(dtype, indicators=()) for key, dtype in config.document_types.items()}
    (config.library / "notes.md").write_text("---\ntitle: Notes\n---\n\nPlain text.\n")
    results = classify(load_library(config.library), replace(config, document_types=plain))
    assert {r.document: r.note for r in results}["notes.md"] == (
        "no type declared; no indicators configured, so no proposal is possible"
    )
    assert all("no indicators configured" in r.note for r in results)


def test_classify_prints_the_note(config, capsys):
    (config.library / "notes.md").write_text("---\ntitle: Notes\n---\n\nPlain text.\n")
    assert main(["--config", str(config.root / "procgov.yaml"), "classify"]) == 0
    out = capsys.readouterr().out
    assert "| Document | Declared | Proposed | Missing sections | Note |" in out
    assert "| notes.md |  |  |  | no type declared;" in out
