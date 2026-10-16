"""Adopting an existing library: missing front-matter proposed, dry run by default (soak issue #1)."""

from __future__ import annotations

from dataclasses import replace

from procgov.adopt import apply_adoption, plan_adoption
from procgov.classify import classify
from procgov.cli import main
from procgov.model import load_library

_WI_BODY = "# Till opening\n\nOpen the till. Select cash. Press enter. Scan the card.\n"


def _existing(config):
    """Two documents as an existing library has them: partial or no front-matter."""
    (config.library / "Till Opening.md").write_text(
        "---\ntitle: Till opening\nsubtitle: Shop floor\n---\n\n" + _WI_BODY
    )
    (config.library / "PR-007 Returns.md").write_text("# Returns\n\nNotes on returns.\n")


def test_the_plan_proposes_id_status_type_and_title_but_never_an_owner(config):
    _existing(config)
    plan = {a.rel: a for a in plan_adoption(load_library(config.library), config)}
    assert set(plan) == {"Till Opening.md", "PR-007 Returns.md"}
    till = plan["Till Opening.md"]
    assert till.fields == {"id": "till-opening", "type": "work_instruction", "status": "DRAFT"}
    assert "owner: left for the Process Owner" in till.notes
    returns = plan["PR-007 Returns.md"]
    assert returns.fields == {"id": "PR-007", "status": "DRAFT", "title": "Returns"}
    assert (
        "type: no type declared; no type's indicators lead clearly enough for a proposal;"
        " set one by hand"
    ) in returns.notes


def test_adopt_is_a_dry_run_without_write(config, capsys):
    _existing(config)
    before = {p.name: p.read_text() for p in config.library.glob("*.md")}
    assert main(["--config", str(config.root / "procgov.yaml"), "adopt"]) == 0
    assert {p.name: p.read_text() for p in config.library.glob("*.md")} == before
    out = capsys.readouterr().out
    assert (
        "would add to Till Opening.md: id: till-opening, type: work_instruction, status: DRAFT"
        in out
    )
    assert "dry run" in out


def test_write_keeps_existing_front_matter_and_the_body_byte_for_byte(config):
    _existing(config)
    assert main(["--config", str(config.root / "procgov.yaml"), "adopt", "--write"]) == 0
    till = (config.library / "Till Opening.md").read_text()
    assert till == (
        "---\ntitle: Till opening\nsubtitle: Shop floor\n"
        "id: till-opening\ntype: work_instruction\nstatus: DRAFT\n---\n\n" + _WI_BODY
    )
    returns = (config.library / "PR-007 Returns.md").read_text()
    assert returns.endswith("---\n\n# Returns\n\nNotes on returns.\n")
    doc = next(d for d in load_library(config.library).documents if d.rel == "PR-007 Returns.md")
    assert (doc.id, doc.status, doc.title, doc.front_matter_error) == (
        "PR-007",
        "DRAFT",
        "Returns",
        None,
    )


def test_documents_with_complete_front_matter_are_left_alone(config, library):
    assert plan_adoption(library, config) == []


def test_a_taken_id_is_not_proposed_twice(config):
    (config.library / "pr-001.md").write_text("# Duplicate\n")
    [a] = plan_adoption(load_library(config.library), config)
    assert "id" not in a.fields
    assert a.notes[0] == "id: 'PR-001' from the file name is taken; set one by hand"


def test_broken_front_matter_is_refused_and_not_rewritten(config):
    path = config.library / "broken.md"
    path.write_text("---\ntitle: [unclosed\n---\n\nText.\n")
    before = path.read_text()
    adoptions = plan_adoption(load_library(config.library), config)
    [a] = [a for a in adoptions if a.rel == "broken.md"]
    assert a.refused.startswith("fix the front-matter first")
    apply_adoption(adoptions)
    assert path.read_text() == before


def test_without_indicators_adopt_gives_the_same_reason_as_classify(config):
    plain = {key: replace(dtype, indicators=()) for key, dtype in config.document_types.items()}
    config = replace(config, document_types=plain)
    _existing(config)
    library = load_library(config.library)
    notes = {r.document: r.note for r in classify(library, config)}
    for a in plan_adoption(library, config):
        assert f"type: {notes[a.rel]}; set one by hand" in a.notes
        assert "no indicators configured, so no proposal is possible" in notes[a.rel]
