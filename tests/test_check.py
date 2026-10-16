"""R3 checks and R6 lifecycle: findings only, and nothing to inspect does not pass."""

from __future__ import annotations

from procgov.checks import check_library, has_errors
from procgov.model import load_library


def _rules(findings):
    return sorted((f.rule, f.document) for f in findings)


def test_the_fernhill_library_is_clean(config, library):
    findings = check_library(library, config)
    assert findings == []
    assert not has_errors(findings)


def test_an_empty_library_does_not_pass(config, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    findings = check_library(load_library(empty), config)
    assert [f.rule for f in findings] == ["check.nothing_to_inspect"]
    assert has_errors(findings)


def test_front_matter_sections_spelling_and_links(config):
    bad = config.library / "PR-002-bad.md"
    bad.write_text(
        "---\nid: PR-002\ntitle: Pricing\ntype: process\nstatus: DRAFT\n---\n\n"
        "## Purpose\n\nOur organization sets prices. See [x](missing.md).\n"
    )
    findings = check_library(load_library(config.library), config)
    assert ("front_matter.missing", "PR-002-bad.md") in _rules(findings)
    missing = [f.message for f in findings if f.rule == "sections.missing"]
    assert missing == [
        "required section 'Scope' is missing",
        "required section 'Roles' is missing",
        "required section 'Steps' is missing",
    ]
    [spell] = [f for f in findings if f.rule == "spelling.house"]
    assert (spell.severity, spell.proposal) == ("proposal", "organisation")
    assert ("links.broken", "PR-002-bad.md") in _rules(findings)


def test_unknown_type_and_status_and_broken_front_matter(config):
    (config.library / "x.md").write_text("no front matter\n")
    (config.library / "y.md").write_text(
        "---\nid: Y\ntitle: Y\ntype: memo\nstatus: FINAL\nowner: me\n---\n"
    )
    rules = _rules(check_library(load_library(config.library), config))
    assert ("front_matter.invalid", "x.md") in rules
    assert ("front_matter.unknown_type", "y.md") in rules
    assert ("lifecycle.unknown_status", "y.md") in rules


def test_at_most_one_draft_and_one_active_version(config):
    src = (config.library / "WI-001-receiving-deliveries.md").read_text()
    for name in ("WI-001-v2.md", "WI-001-v3.md"):
        (config.library / name).write_text(src.replace("status: DOCUMENT", "status: DRAFT"))
    (config.library / "WI-001-copy.md").write_text(src)
    rules = _rules(check_library(load_library(config.library), config))
    assert ("lifecycle.many_drafts", "WI-001") in rules
    assert ("lifecycle.many_documents", "WI-001") in rules


def test_proposals_alone_do_not_fail_the_check(config):
    path = config.library / "WI-001-receiving-deliveries.md"
    path.write_text(path.read_text() + "\nThe color of the box does not matter.\n")
    findings = check_library(load_library(config.library), config)
    assert [f.rule for f in findings] == ["spelling.house"]
    assert not has_errors(findings)


def test_missing_front_matter_fields_are_one_finding_per_document(config):
    (config.library / "notes.md").write_text("---\ntitle: Notes\n---\n\nText.\n")
    findings = [
        f for f in check_library(load_library(config.library), config) if f.document == "notes.md"
    ]
    assert [f.message for f in findings] == ["front-matter has no id, type, status, owner"]
