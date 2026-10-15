"""R4: a configurable classification test, reported as proposals (G2)."""

from __future__ import annotations

from procgov.classify import as_findings, classify
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
