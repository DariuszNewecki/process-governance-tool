"""The library: every governed document, parsed once. One model, one loader.

Every output (render, check, register, package, site) reads the same
``Library``, so no output can disagree with another about what a document is.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

STATUSES = ("DRAFT", "DOCUMENT", "ARCHIVE")
REQUIRED_FIELDS = ("id", "type", "status", "owner", "title")
# The front-matter block at the top of a document; group 1 is its YAML.
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Document:
    """One Markdown file with its front-matter."""

    path: Path
    rel: str
    meta: dict[str, Any]
    body: str
    sha256: str
    front_matter_error: str | None = None

    @property
    def id(self) -> str:
        """The document id from front-matter ('' when missing)."""
        return str(self.meta.get("id") or "")

    @property
    def title(self) -> str:
        """The title from front-matter ('' when missing)."""
        return str(self.meta.get("title") or "")

    @property
    def type(self) -> str:
        """The document type key from front-matter."""
        return str(self.meta.get("type") or "")

    @property
    def status(self) -> str:
        """DRAFT, DOCUMENT or ARCHIVE as written (upper-cased)."""
        return str(self.meta.get("status") or "").upper()

    @property
    def owner(self) -> str:
        """The owner from front-matter."""
        return str(self.meta.get("owner") or "")

    def headings(self) -> list[tuple[int, str]]:
        """(level, text) of every Markdown heading in the body."""
        return [(len(m.group(1)), m.group(2).strip()) for m in _HEADING.finditer(self.body)]


@dataclass(frozen=True)
class Library:
    """Every document under the library folder, sorted by path."""

    root: Path
    documents: tuple[Document, ...]
    excluded: tuple[str, ...] = ()

    def by_id(self) -> dict[str, list[Document]]:
        """Documents grouped by id (a DRAFT and a DOCUMENT may share one)."""
        out: dict[str, list[Document]] = {}
        for doc in self.documents:
            out.setdefault(doc.id, []).append(doc)
        return out

    def active(self) -> list[Document]:
        """Documents with status DOCUMENT: what is published."""
        return [d for d in self.documents if d.status == "DOCUMENT"]


def parse_document(path: Path, root: Path) -> Document:
    """Read one Markdown file; a broken front-matter is kept as an error, not raised."""
    data = path.read_bytes()
    text = data.decode("utf-8")
    meta: dict[str, Any] = {}
    error = None
    body = text
    match = FRONT_MATTER.match(text)
    if match is None:
        error = "no front-matter block (--- ... ---) at the top"
    else:
        body = text[match.end() :]
        try:
            loaded = yaml.safe_load(match.group(1))
            if isinstance(loaded, dict):
                meta = loaded
            else:
                error = "front-matter is not a mapping"
        except yaml.YAMLError as exc:
            error = f"front-matter is not valid YAML: {exc}"
    return Document(
        path=path,
        rel=path.relative_to(root).as_posix(),
        meta=meta,
        body=body,
        sha256=hashlib.sha256(data).hexdigest(),
        front_matter_error=error,
    )


def load_library(root: Path, exclude: tuple[str, ...] = ()) -> Library:
    """Parse every ``*.md`` under ``root`` (sorted, so output order is stable).

    ``exclude`` holds glob patterns, relative to ``root``, for files that are
    not governed documents (working records, drafts kept beside them). They
    are listed in ``Library.excluded``, never skipped silently.
    """
    root = Path(root).resolve()
    paths = sorted(p for p in root.rglob("*.md") if p.is_file())
    kept, excluded = [], []
    for path in paths:
        rel = PurePosixPath(path.relative_to(root).as_posix())
        (excluded if any(rel.match(g) for g in exclude) else kept).append(path)
    return Library(
        root=root,
        documents=tuple(parse_document(p, root) for p in kept),
        excluded=tuple(p.relative_to(root).as_posix() for p in excluded),
    )
