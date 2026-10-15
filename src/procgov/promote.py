"""Promotion (G4): a DRAFT becomes the DOCUMENT only by an explicit, approved step.

Dry run by default (G3): without ``write`` it only says what it would change.
The previous DOCUMENT of the same id becomes ARCHIVE; the draft becomes
DOCUMENT and records who approved it. Only the status lines change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from procgov.checks import check_library
from procgov.config import Config
from procgov.findings import ERROR
from procgov.model import Library

_STATUS = re.compile(r"^status:\s*\S+\s*$", re.MULTILINE)


class PromotionRefused(ValueError):
    """The draft cannot be promoted; nothing was changed."""


@dataclass(frozen=True)
class Change:
    """One source file and its new status."""

    path: Path
    old: str
    new: str


def plan_promotion(
    library: Library, config: Config, draft_rel: str, approved_by: str
) -> list[Change]:
    """What promoting ``draft_rel`` changes; refuses when it is not ready."""
    if not approved_by.strip():
        raise PromotionRefused("a promotion needs the approver's name (--approved-by)")
    draft = next((d for d in library.documents if d.rel == draft_rel), None)
    if draft is None:
        raise PromotionRefused(f"no document {draft_rel} in the library")
    if draft.status != "DRAFT":
        raise PromotionRefused(f"{draft_rel} is {draft.status or 'without status'}, not DRAFT")
    errors = [
        f
        for f in check_library(library, config)
        if f.severity == ERROR and f.document in (draft.rel, draft.id)
    ]
    if errors:
        raise PromotionRefused(
            f"{draft_rel} does not pass the check: " + "; ".join(f.message for f in errors)
        )
    changes = [
        Change(d.path, "DOCUMENT", "ARCHIVE")
        for d in library.documents
        if d.id == draft.id and d.status == "DOCUMENT"
    ]
    changes.append(Change(draft.path, "DRAFT", "DOCUMENT"))
    return changes


def apply_promotion(changes: list[Change], approved_by: str) -> None:
    """Rewrite the status lines (and record the approver on the promoted draft)."""
    for change in changes:
        text = change.path.read_text(encoding="utf-8")
        text = re.sub(r"^approved_by:.*\n", "", text, flags=re.MULTILINE)
        text = _STATUS.sub(f"status: {change.new}", text, count=1)
        if change.new == "DOCUMENT":
            text = text.replace(
                f"status: {change.new}", f"status: {change.new}\napproved_by: {approved_by}", 1
            )
        change.path.write_text(text, encoding="utf-8")
