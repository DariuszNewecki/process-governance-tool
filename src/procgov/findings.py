"""Findings: what the tool reports and proposes. It never decides content (G2)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

ERROR = "error"
PROPOSAL = "proposal"


@dataclass(frozen=True)
class Finding:
    """One observation about one document, with its reason and the standard it cites."""

    rule: str
    document: str
    message: str
    reason: str
    standard: str
    severity: str = ERROR
    proposal: str = ""

    def as_dict(self) -> dict[str, str]:
        """The finding as a plain dict (for JSON, CSV and the site)."""
        return asdict(self)
