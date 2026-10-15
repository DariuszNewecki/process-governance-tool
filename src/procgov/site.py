"""The static site (R8): document list, register, findings, a reader per document.

Plain HTML and CSS, no scripts and no network: the same folder zipped is the
offline package for readers without install or network.
"""

from __future__ import annotations

import html
import re
import subprocess
import zipfile
from pathlib import Path

from procgov.checks import check_library
from procgov.classify import as_findings, classify
from procgov.config import Config
from procgov.model import Library
from procgov.register import COLUMNS, register_rows
from procgov.render.pandoc import pandoc_path
from procgov.trace import source_version

_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _css(config: Config) -> str:
    p = config.palette
    return (
        f"body{{font-family:{config.font},sans-serif;color:#{p['ink']};max-width:60rem;"
        "margin:2rem auto;padding:0 1rem}"
        f"h1,h2{{color:#{p['primary']}}}h3{{color:#{p['dark']}}}"
        f"a{{color:#{p['primary']}}}table{{border-collapse:collapse;width:100%}}"
        f"th,td{{border:1px solid #{p['line']};padding:.3rem .5rem;text-align:left}}"
        f"th{{background:#{p['light']};color:#{p['dark']}}}"
        f"header{{border-bottom:2px solid #{p['dark']};margin-bottom:1rem}}"
        f"footer{{border-top:1px solid #{p['line']};color:#{p['muted']};font-size:.8rem;"
        "margin-top:2rem}"
    )


def _page(config: Config, title: str, body: str, depth: int = 0) -> str:
    up = "../" * depth
    nav = (
        f'<a href="{up}index.html">Documents</a> · <a href="{up}register.html">Register</a>'
        f' · <a href="{up}findings.html">Findings</a>'
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)} — {html.escape(config.organisation)}</title>"
        f"<style>{_css(config)}</style></head><body>"
        f"<header><strong>{html.escape(config.header_label)}</strong> · {nav}</header>"
        f"<h1>{html.escape(title)}</h1>{body}"
        f"<footer>{html.escape(config.copyright)}</footer></body></html>\n"
    )


def _table(headers, rows) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_site(library: Library, config: Config, out_dir: Path) -> Path:
    """Write the site into ``out_dir`` and ``out_dir``.zip; return the zip."""
    out_dir = Path(out_dir)
    (out_dir / "docs").mkdir(parents=True, exist_ok=True)
    rows = register_rows(library, config)
    version = source_version(library.root)
    page_of = {
        d.rel: f"{d.id or Path(d.rel).stem}-{d.status.lower() or 'unknown'}.html"
        for d in library.documents
    }

    listing = [
        [
            f'<a href="docs/{page_of[r["source"]]}">{html.escape(r["id"])}</a>',
            html.escape(r["title"]),
            html.escape(r["type"]),
            html.escape(r["status"]),
        ]
        for r in rows
        if r["status"] == "DOCUMENT"
    ]
    _write(
        out_dir / "index.html",
        _page(config, "Documents", _table(("ID", "Title", "Type", "Status"), listing)),
    )
    _write(
        out_dir / "register.html",
        _page(
            config,
            "Document Register",
            _table(
                [c.capitalize() for c in COLUMNS],
                [[html.escape(r[c]) for c in COLUMNS] for r in rows],
            ),
        ),
    )
    findings = check_library(library, config) + as_findings(classify(library, config), config)
    _write(
        out_dir / "findings.html",
        _page(
            config,
            "Findings",
            _table(
                ("Document", "Rule", "Finding", "Reason", "Proposal"),
                [
                    [
                        html.escape(f.document),
                        html.escape(f.rule),
                        html.escape(f.message),
                        html.escape(f.reason),
                        html.escape(f.proposal),
                    ]
                    for f in findings
                ],
            ),
        ),
    )

    for doc in library.documents:
        fragment = subprocess.run(
            [pandoc_path(), "-f", "markdown+pipe_tables+yaml_metadata_block", "-t", "html"],
            input=doc.body.encode(),
            capture_output=True,
            check=True,
        ).stdout.decode()
        fragment = re.sub(
            r'href="([^"]+\.md)(#[^"]*)?"',
            lambda m, here=doc.rel: f'href="{_link(m.group(1), here, page_of)}{m.group(2) or ""}"',
            fragment,
        )
        trace = (
            f"<footer>Source {html.escape(doc.rel)} · sha256 {doc.sha256}"
            f" · commit {html.escape(str(version['commit']))}</footer>"
        )
        title = f"{doc.id} {doc.title}".strip()
        _write(out_dir / "docs" / page_of[doc.rel], _page(config, title, fragment + trace, depth=1))
    return _zip(out_dir)


def _link(target: str, here: str, page_of: dict[str, str]) -> str:
    base = Path(here).parent
    resolved = (base / target).as_posix()
    parts: list[str] = []
    for part in resolved.split("/"):
        if part == "..":
            parts and parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    return page_of.get("/".join(parts), target)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _zip(out_dir: Path) -> Path:
    archive = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in out_dir.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(path.relative_to(out_dir.parent).as_posix(), _ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return archive
