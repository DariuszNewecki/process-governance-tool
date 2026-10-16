"""One check command (R3) plus lifecycle (R6). Findings only; nothing is changed (G2).

A library with nothing to inspect does not pass: the check reports that it
inspected nothing.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from procgov.config import Config
from procgov.findings import ERROR, PROPOSAL, Finding
from procgov.model import REQUIRED_FIELDS, STATUSES, Library

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+\.md)(#[^)]*)?\)")
_WORD = re.compile(r"[A-Za-z]+")


def check_library(library: Library, config: Config) -> list[Finding]:
    """Every finding for the library, in document order."""
    if not library.documents:
        return [
            Finding(
                rule="check.nothing_to_inspect",
                document="",
                message=f"no Markdown documents under {library.root}",
                reason="a check with nothing to inspect does not pass",
                standard="Qualities: a check with nothing to inspect does not pass by default",
            )
        ]
    findings: list[Finding] = []
    known = {d.rel for d in library.documents}
    for doc in library.documents:
        findings += _front_matter(doc, config)
        findings += _sections(doc, config)
        findings += _spelling(doc, config)
        findings += _links(doc, known)
    findings += _lifecycle(library)
    return findings


def _front_matter(doc, config: Config) -> list[Finding]:
    if doc.front_matter_error:
        return [
            Finding(
                "front_matter.invalid",
                doc.rel,
                doc.front_matter_error,
                "every document starts with its front-matter",
                "R1",
            )
        ]
    missing = [name for name in REQUIRED_FIELDS if not doc.meta.get(name)]
    out = []
    if missing:
        out.append(
            Finding(
                "front_matter.missing",
                doc.rel,
                "front-matter has no " + ", ".join(missing),
                "id, type, status, owner and title identify a governed document",
                "R1",
            )
        )
    if doc.type and config.doc_type(doc.type) is None:
        known = ", ".join(sorted(config.document_types))
        out.append(
            Finding(
                "front_matter.unknown_type",
                doc.rel,
                f"type '{doc.type}' is not configured (known: {known})",
                "document types are configuration",
                "R3",
            )
        )
    if doc.status and doc.status not in STATUSES:
        out.append(
            Finding(
                "lifecycle.unknown_status",
                doc.rel,
                f"status '{doc.status}' is not one of {', '.join(STATUSES)}",
                "the lifecycle has three states",
                "R6",
            )
        )
    return out


def _sections(doc, config: Config) -> list[Finding]:
    dtype = config.doc_type(doc.type)
    if dtype is None:
        return []
    present = {text.lower() for _, text in doc.headings()}
    return [
        Finding(
            "sections.missing",
            doc.rel,
            f"required section '{name}' is missing",
            f"a {dtype.label} has the sections {', '.join(dtype.required_sections)}",
            f"document type '{dtype.key}'",
        )
        for name in dtype.required_sections
        if name.lower() not in present
    ]


def _spelling(doc, config: Config) -> list[Finding]:
    out = []
    seen = set()
    for match in _WORD.finditer(doc.body):
        word = match.group(0)
        right = config.spelling.get(word.lower())
        if right and word.lower() not in seen:
            seen.add(word.lower())
            line = doc.body.count("\n", 0, match.start()) + 1
            out.append(
                Finding(
                    "spelling.house",
                    doc.rel,
                    f"'{word}' (body line {line})",
                    "house spelling",
                    "configuration: spelling",
                    severity=PROPOSAL,
                    proposal=right,
                )
            )
    return out


def _links(doc, known: set[str]) -> list[Finding]:
    base = PurePosixPath(doc.rel).parent
    out = []
    for match in _LINK.finditer(doc.body):
        target = match.group(1)
        if "://" in target:
            continue
        resolved = _normalise(base / target)
        if resolved not in known:
            out.append(
                Finding(
                    "links.broken",
                    doc.rel,
                    f"link to '{target}' finds no document",
                    "cross-references point at documents in the library",
                    "R3",
                )
            )
    return out


def _normalise(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def _lifecycle(library: Library) -> list[Finding]:
    out = []
    for doc_id, docs in sorted(library.by_id().items()):
        if not doc_id:
            continue
        drafts = [d.rel for d in docs if d.status == "DRAFT"]
        active = [d.rel for d in docs if d.status == "DOCUMENT"]
        if len(drafts) > 1:
            out.append(
                Finding(
                    "lifecycle.many_drafts",
                    doc_id,
                    f"{len(drafts)} drafts: {', '.join(drafts)}",
                    "at most one DRAFT per document",
                    "R6",
                )
            )
        if len(active) > 1:
            out.append(
                Finding(
                    "lifecycle.many_documents",
                    doc_id,
                    f"{len(active)} active versions: {', '.join(active)}",
                    "one active version per document; older ones are ARCHIVE",
                    "R6",
                )
            )
    return out


def has_errors(findings: list[Finding]) -> bool:
    """True when any finding is an error (proposals alone do not fail the check)."""
    return any(f.severity == ERROR for f in findings)
