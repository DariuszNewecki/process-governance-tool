"""The Document Register (R5): one row per document, as Markdown and CSV."""

from __future__ import annotations

import csv
import io

from procgov.config import Config
from procgov.model import Library

COLUMNS = ("id", "title", "type", "status", "owner", "source")


def register_rows(library: Library, config: Config) -> list[dict[str, str]]:
    """One row per document, sorted by id then source path."""
    rows = []
    for doc in sorted(library.documents, key=lambda d: (d.id, d.rel)):
        dtype = config.doc_type(doc.type)
        rows.append(
            {
                "id": doc.id,
                "title": doc.title,
                "type": dtype.label if dtype else doc.type,
                "status": doc.status,
                "owner": doc.owner,
                "source": doc.rel,
            }
        )
    return rows


def register_markdown(rows: list[dict[str, str]], organisation: str) -> str:
    """The register as a Markdown table."""

    def cell(value: str) -> str:
        return value.replace("|", "\\|")

    lines = [
        f"# Document Register — {organisation}",
        "",
        "| " + " | ".join(c.capitalize() for c in COLUMNS) + " |",
        "|" + " --- |" * len(COLUMNS),
    ]
    lines += ["| " + " | ".join(cell(r[c]) for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def register_csv(rows: list[dict[str, str]]) -> str:
    """The register as CSV (LF line endings, so it is the same on every system)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
