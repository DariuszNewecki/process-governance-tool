"""Classification proposal per document (R4): a configurable test, reported only (G2).

Each document type lists indicator words; the type whose indicators occur most
in the body is the proposal. A proposal different from the declared type is
made only when it leads by at least ``classification.margin`` occurrences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from procgov.config import Config
from procgov.findings import PROPOSAL, Finding
from procgov.model import Library

_WORD = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Classification:
    """The proposal for one document, with the evidence and the section gaps."""

    document: str
    declared: str
    proposed: str
    scores: dict[str, int]
    missing_sections: tuple[str, ...]

    @property
    def differs(self) -> bool:
        """True when the proposal is not the declared type."""
        return self.proposed != self.declared


def classify(library: Library, config: Config) -> list[Classification]:
    """One classification per document, in library order."""
    out = []
    for doc in library.documents:
        words = _WORD.findall(doc.body.lower())
        scores = {
            key: sum(words.count(word) for word in dtype.indicators)
            for key, dtype in sorted(config.document_types.items())
        }
        best = max(scores, key=lambda k: (scores[k], k == doc.type))
        declared_score = scores.get(doc.type, 0)
        proposed = (
            best if scores[best] - declared_score >= config.classification_margin else doc.type
        )
        dtype = config.doc_type(proposed)
        present = {text.lower() for _, text in doc.headings()}
        missing = tuple(
            s for s in (dtype.required_sections if dtype else ()) if s.lower() not in present
        )
        out.append(Classification(doc.rel, doc.type, proposed, scores, missing))
    return out


def as_findings(results: list[Classification], config: Config) -> list[Finding]:
    """Reclassifications as proposals, each with its evidence (G2)."""
    out = []
    for r in results:
        if not r.differs:
            continue
        label = config.document_types[r.proposed].label
        evidence = ", ".join(f"{k} {v}" for k, v in r.scores.items())
        out.append(
            Finding(
                "classification.proposal",
                r.document,
                f"declared '{r.declared}', reads like a {label}",
                f"indicator counts: {evidence}",
                "configuration: classification",
                severity=PROPOSAL,
                proposal=r.proposed,
            )
        )
    return out
