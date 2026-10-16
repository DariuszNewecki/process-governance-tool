"""Organisation configuration: everything branded or house-specific is read here.

The tool holds no organisation's names, palette, labels, document types or
spelling; they come from a YAML file (``procgov.yaml``) next to the library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PALETTE = {
    "primary": "2F5D8A",
    "dark": "1F2933",
    "light": "C9D6E3",
    "ink": "222222",
    "muted": "808080",
    "line": "BFBFBF",
    "ok": "2E7D32",
}


class ConfigError(ValueError):
    """The configuration file is missing a value or has a wrong one."""


@dataclass(frozen=True)
class DocumentType:
    """A kind of governed document and the sections it must have."""

    key: str
    label: str
    required_sections: tuple[str, ...]
    indicators: tuple[str, ...] = ()


@dataclass(frozen=True)
class Config:
    """The organisation's configuration, read once and passed everywhere."""

    root: Path
    organisation: str
    header_label: str
    classification_label: str
    copyright: str
    font: str
    palette: dict[str, str]
    template: Path | None
    wordmark: Path | None
    number_headings: bool
    library: Path
    document_types: dict[str, DocumentType]
    classification_margin: int
    spelling: dict[str, str] = field(default_factory=dict)
    library_exclude: tuple[str, ...] = ()

    def doc_type(self, key: str) -> DocumentType | None:
        """The document type declared under ``key``, or None."""
        return self.document_types.get(key)


def _path(root: Path, value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else (root / path)


def load_config(path: Path) -> Config:
    """Read ``procgov.yaml``. Relative paths in it are relative to its folder."""
    path = Path(path).resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"no configuration at {path}") from exc
    root = path.parent
    org = raw.get("organisation") or {}
    name = org.get("name")
    if not name:
        raise ConfigError("organisation.name is required")
    palette = dict(DEFAULT_PALETTE)
    for key, value in (raw.get("palette") or {}).items():
        value = str(value).lstrip("#").upper()
        if len(value) != 6 or any(c not in "0123456789ABCDEF" for c in value):
            raise ConfigError(f"palette.{key} must be a hex colour like 2F5D8A, not {value!r}")
        palette[key] = value
    types: dict[str, DocumentType] = {}
    for key, spec in (raw.get("document_types") or {}).items():
        spec = spec or {}
        types[key] = DocumentType(
            key=key,
            label=str(spec.get("label") or key),
            required_sections=tuple(spec.get("required_sections") or ()),
            indicators=tuple(str(i).lower() for i in spec.get("indicators") or ()),
        )
    if not types:
        raise ConfigError("document_types must declare at least one type")
    classification = raw.get("classification") or {}
    return Config(
        root=root,
        organisation=str(name),
        header_label=str(org.get("header_label") or "Process documentation"),
        classification_label=str(org.get("classification") or "Internal"),
        copyright=str(org.get("copyright") or f"Copyright {name}"),
        font=str(raw.get("font") or "Arial"),
        palette=palette,
        template=_path(root, raw.get("template")),
        wordmark=_path(root, raw.get("wordmark")),
        number_headings=bool(raw.get("number_headings", False)),
        library=_path(root, raw.get("library") or "library") or root / "library",
        document_types=types,
        classification_margin=int(classification.get("margin", 2)),
        spelling={str(k).lower(): str(v) for k, v in (raw.get("spelling") or {}).items()},
        library_exclude=tuple(str(g) for g in raw.get("library_exclude") or ()),
    )
