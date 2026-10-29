"""Adopting an existing library: missing front-matter proposed, dry run by default (soak issue #1)."""

from __future__ import annotations

from dataclasses import replace

from procgov.adopt import apply_adoption, plan_adoption
from procgov.checks import check_library
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
    assert "owner: left for the Process Owner; or adopt with --owner NAME" in till.notes
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


def _versions_of_one_plan(config):
    for version in ("0.2", "0.10", "0.9"):
        (config.library / f"Quarry_Plan_v{version}.md").write_text(f"# Quarry plan {version}\n")


def test_versions_of_one_document_share_an_id_and_the_newest_is_current(config):
    _versions_of_one_plan(config)
    plan = {a.rel: a.fields for a in plan_adoption(load_library(config.library), config)}
    assert {rel: f["id"] for rel, f in plan.items()} == {
        "Quarry_Plan_v0.2.md": "quarry-plan",
        "Quarry_Plan_v0.9.md": "quarry-plan",
        "Quarry_Plan_v0.10.md": "quarry-plan",
    }
    assert plan["Quarry_Plan_v0.10.md"]["status"] == "DRAFT"
    for older in ("Quarry_Plan_v0.2.md", "Quarry_Plan_v0.9.md"):
        assert plan[older]["status"] == "ARCHIVE"
        assert plan[older]["superseded_by"] == "Quarry_Plan_v0.10.md"


def test_adopted_versions_pass_the_lifecycle_check(config):
    _versions_of_one_plan(config)
    adoptions = plan_adoption(load_library(config.library), config)
    apply_adoption(adoptions)
    findings = check_library(load_library(config.library), config)
    lifecycle = [f for f in findings if f.rule.startswith("lifecycle.")]
    assert lifecycle == []


def test_a_single_versioned_file_drops_the_version_from_its_id(config):
    (config.library / "Kiln Notes v3.md").write_text("# Kiln\n")
    [a] = plan_adoption(load_library(config.library), config)
    assert (a.fields["id"], a.fields["status"]) == ("kiln-notes", "DRAFT")


def test_a_shared_id_already_in_use_is_not_proposed(config):
    (config.library / "pr-001_v1.md").write_text("# One\n")
    (config.library / "pr-001_v2.md").write_text("# Two\n")
    plan = plan_adoption(load_library(config.library), config)
    assert all("id" not in a.fields for a in plan)
    assert all(a.notes[0].startswith("id: 'PR-001' from the file name is taken") for a in plan)


def test_an_owner_named_with_owner_is_added_where_none_is_written(config, capsys):
    _existing(config)
    (config.library / "Kept.md").write_text("---\nowner: Head of Sales\n---\n\n# Kept\n")
    assert (
        main(
            [
                "--config",
                str(config.root / "procgov.yaml"),
                "adopt",
                "--owner",
                "Head of Retail",
                "--write",
            ]
        )
        == 0
    )
    library = load_library(config.library)
    owners = {d.rel: d.owner for d in library.documents}
    assert owners["Till Opening.md"] == "Head of Retail"
    assert owners["PR-007 Returns.md"] == "Head of Retail"
    assert owners["Kept.md"] == "Head of Sales"
