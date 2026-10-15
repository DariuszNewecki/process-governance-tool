"""R5 register, R7 package, R8 site: all read the same parsed library."""

from __future__ import annotations

import csv
import io
import json
import zipfile

from procgov.package import build_package
from procgov.register import register_csv, register_markdown, register_rows
from procgov.site import build_site


def test_register_has_one_row_per_document_in_markdown_and_csv(config, library):
    rows = register_rows(library, config)
    assert [(r["id"], r["type"], r["status"]) for r in rows] == [
        ("PR-001", "Process", "DOCUMENT"),
        ("WI-001", "Work Instruction", "DOCUMENT"),
    ]
    md = register_markdown(rows, config.organisation)
    assert md.startswith("# Document Register — Fernhill Garden Supplies")
    assert "| PR-001 | Seed Ordering | Process | DOCUMENT | Head of Purchasing |" in md
    parsed = list(csv.DictReader(io.StringIO(register_csv(rows))))
    assert [r["source"] for r in parsed] == [
        "PR-001-seed-ordering.md",
        "WI-001-receiving-deliveries.md",
    ]


def test_package_holds_active_documents_only_and_a_manifest(config, library, tmp_path):
    draft = config.library / "PR-001-v2.md"
    draft.write_text(
        (config.library / "PR-001-seed-ordering.md")
        .read_text()
        .replace("status: DOCUMENT", "status: DRAFT")
    )
    from procgov.model import load_library

    manifest = json.loads(
        build_package(load_library(config.library), config, tmp_path / "pkg").read_text()
    )
    assert [d["id"] for d in manifest["documents"]] == ["PR-001", "WI-001"]
    assert [d["source"] for d in manifest["documents"]] == [
        "PR-001-seed-ordering.md",
        "WI-001-receiving-deliveries.md",
    ]
    assert sorted(p.name for p in (tmp_path / "pkg" / "documents").iterdir()) == [
        "PR-001.docx",
        "WI-001.docx",
    ]
    assert all(len(d["output_sha256"]) == 64 for d in manifest["documents"])


def test_site_has_list_register_findings_and_a_reader_per_document(config, library, tmp_path):
    archive = build_site(library, config, tmp_path / "site")
    site = tmp_path / "site"
    assert "Seed Ordering" in (site / "index.html").read_text()
    assert "Work Instruction" in (site / "register.html").read_text()
    assert (site / "findings.html").is_file()
    reader = (site / "docs" / "PR-001-document.html").read_text()
    assert "Head of Purchasing" in reader
    assert 'href="WI-001-document.html"' in reader  # cross-reference rewritten
    assert "<script" not in reader and "http" not in reader.split("<footer>")[0]
    with zipfile.ZipFile(archive) as zf:
        assert "site/docs/WI-001-document.html" in zf.namelist()


def test_the_site_zip_is_the_same_for_the_same_source(config, library, tmp_path):
    a = build_site(library, config, tmp_path / "a" / "site").read_bytes()
    b = build_site(library, config, tmp_path / "b" / "site").read_bytes()
    assert a == b
