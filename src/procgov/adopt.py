"""Adoption: bring an existing library under the tool without editing every file.

Dry run by default (G3): without ``write`` it only says what it would add.
For each document it proposes the missing front-matter: an id from the file
name, status DRAFT, the type from the classification test when it is clear,
and a title from the first heading. The owner is never guessed; it is left
for the Process Owner. Existing front-matter lines are kept as written and
the body is never touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from procgov.classify import classify
from procgov.config import Config
from procgov.model import FRONT_MATTER, Library

_ID_PREFIX = re.compile(r"^([A-Za-z]+-\d+)")
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Adoption:
    """What adopting one document adds, or why it cannot be adopted."""

    path: Path
    rel: str
    fields: dict[str, str]
    notes: tuple[str, ...] = ()
    refused: str = ""


def _id_from_name(stem: str) -> str:
    match = _ID_PREFIX.match(stem)
    if match:
        return match.group(1).upper()
    return _SLUG.sub("-", stem.lower()).strip("-")


def plan_adoption(library: Library, config: Config) -> list[Adoption]:
    """One adoption per document that is missing front-matter, in library order."""
    proposed_types = {r.document: r.proposed for r in classify(library, config)}
    taken = {d.id for d in library.documents if d.id}
    out = []
    for doc in library.documents:
        if doc.front_matter_error and FRONT_MATTER.match(doc.path.read_text(encoding="utf-8")):
            out.append(
                Adoption(
                    doc.path,
                    doc.rel,
                    {},
                    refused=f"fix the front-matter first: {doc.front_matter_error}",
                )
            )
            continue
        fields: dict[str, str] = {}
        notes: list[str] = []
        if not doc.id:
            new_id = _id_from_name(doc.path.stem)
            if not new_id or new_id in taken:
                notes.append(f"id: '{new_id}' from the file name is taken; set one by hand")
            else:
                fields["id"] = new_id
                taken.add(new_id)
        if not doc.type:
            if proposed_types.get(doc.rel):
                fields["type"] = proposed_types[doc.rel]
            else:
                notes.append("type: the classification test gives no clear type; set one by hand")
        if not doc.status:
            fields["status"] = "DRAFT"
        if not doc.title:
            headings = [text for level, text in doc.headings() if level == 1]
            fields["title"] = headings[0] if headings else doc.path.stem
        if not doc.owner:
            notes.append("owner: left for the Process Owner")
        if fields or notes:
            out.append(Adoption(doc.path, doc.rel, fields, tuple(notes)))
    return out


def apply_adoption(adoptions: list[Adoption]) -> None:
    """Add the proposed fields at the end of each front-matter block (or a new block)."""
    for a in adoptions:
        if a.refused or not a.fields:
            continue
        lines = yaml.safe_dump(a.fields, sort_keys=False, allow_unicode=True)
        text = a.path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(text)
        if match is None:
            text = f"---\n{lines}---\n\n{text}"
        else:
            end = match.start(1) + len(match.group(1))
            text = f"{text[:end]}\n{lines.rstrip(chr(10))}{text[end:]}"
        a.path.write_text(text, encoding="utf-8")
