"""Adoption: bring an existing library under the tool without editing every file.

Dry run by default (G3): without ``write`` it only says what it would add.
For each document it proposes the missing front-matter: an id from the file
name (without a version suffix), status DRAFT, the type from the
classification test when it is clear, and a title from the first heading.
The owner is never guessed: it is left for the Process Owner, unless the
person adopting names one with ``owner`` (``--owner``). Files whose
names differ only by a version suffix are versions of one document: they
share one id, the newest is the DRAFT and the older ones are ARCHIVE,
superseded by it. Existing front-matter lines are kept as written and the
body is never touched.
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
# A version at the end of a file name: "_v0.3", " v2", "-V1.10".
_VERSION = re.compile(r"[ _.\-]+v(\d+(?:\.\d+)*)$", re.IGNORECASE)


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


def _version(stem: str) -> tuple[str, tuple[int, ...]]:
    """The name without its version suffix, and the version (() when none)."""
    match = _VERSION.search(stem)
    if match is None:
        return stem, ()
    return stem[: match.start()], tuple(int(p) for p in match.group(1).split("."))


def _versions(library: Library) -> dict[str, tuple[str, str]]:
    """For files that are versions of one document: rel -> (shared id, newest rel).

    Files without an id whose names differ only by a version suffix are one
    document (governor 2026-10-16, issue #10): the newest is the current one,
    the older ones are superseded.
    """
    groups: dict[str, list[tuple[tuple[int, ...], str]]] = {}
    for doc in library.documents:
        base, version = _version(doc.path.stem)
        if version and not doc.id:
            key = str(doc.path.parent / base)
            groups.setdefault(key, []).append((version, doc.rel))
    out = {}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        newest = max(members)[1]
        shared = _id_from_name(Path(key).name)
        out.update({rel: (shared, newest) for _, rel in members})
    return out


def plan_adoption(library: Library, config: Config, owner: str = "") -> list[Adoption]:
    """One adoption per document that is missing front-matter, in library order."""
    classified = {r.document: r for r in classify(library, config)}
    versions = _versions(library)
    existing = {d.id for d in library.documents if d.id}
    # A shared id belongs to its versions from the start, so no other file takes it.
    taken = existing | {shared for shared, _ in versions.values()}
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
        shared, newest = versions.get(doc.rel, ("", ""))
        if not doc.id:
            # A version suffix is never part of the id: versions share one.
            new_id = shared or _id_from_name(_version(doc.path.stem)[0])
            if not new_id or (new_id in existing if shared else new_id in taken):
                notes.append(f"id: '{new_id}' from the file name is taken; set one by hand")
            else:
                fields["id"] = new_id
                taken.add(new_id)
        if not doc.type:
            result = classified[doc.rel]
            if result.proposed:
                fields["type"] = result.proposed
            else:
                # The same reason `classify` prints for this row.
                notes.append(f"type: {result.note}; set one by hand")
        if not doc.status:
            if shared and doc.rel != newest:
                fields["status"] = "ARCHIVE"
                fields["superseded_by"] = newest
            else:
                fields["status"] = "DRAFT"
        if not doc.title:
            headings = [text for level, text in doc.headings() if level == 1]
            fields["title"] = headings[0] if headings else doc.path.stem
        if not doc.owner:
            if owner:
                fields["owner"] = owner
            else:
                notes.append("owner: left for the Process Owner; or adopt with --owner NAME")
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
