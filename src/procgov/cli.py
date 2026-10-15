"""``procgov``: check, classify, register, render, package, site, promote.

Only ``promote`` changes source, and only with ``--write`` (G3). Every other
command reads the library and writes outputs outside it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from procgov.checks import check_library, has_errors
from procgov.classify import as_findings, classify
from procgov.config import ConfigError, load_config
from procgov.model import load_library
from procgov.package import build_package
from procgov.promote import PromotionRefused, apply_promotion, plan_promotion
from procgov.register import register_csv, register_markdown, register_rows
from procgov.render.docx import OutputInsideLibrary, render_document, render_library
from procgov.site import build_site


def _out(text: str = "") -> None:
    sys.stdout.write(text + "\n")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="procgov", description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--config",
        type=Path,
        default=Path("procgov.yaml"),
        help="organisation configuration (default: ./procgov.yaml)",
    )
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="check every document; exit 1 on errors")
    c.add_argument("--json", action="store_true", help="findings as JSON")
    sub.add_parser("classify", help="classification proposal and section gaps per document")
    for name, helptext in (
        ("register", "write register.md and register.csv"),
        ("package", "render active documents and write a manifest"),
        ("site", "build the static site and its zip"),
    ):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--out", type=Path, default=None)
    r = sub.add_parser("render", help="render one document (by id) or all of them")
    r.add_argument("id", nargs="?", default=None, help="document id; omit for every document")
    r.add_argument("--out", type=Path, default=None)
    pr = sub.add_parser("promote", help="promote a DRAFT (dry run unless --write)")
    pr.add_argument("draft", help="the draft's path inside the library")
    pr.add_argument("--approved-by", required=True)
    pr.add_argument("--write", action="store_true", help="apply the promotion")
    return p


def main(argv: list[str] | None = None) -> int:
    """Run one command; return its exit code."""
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        sys.stderr.write(f"procgov: {exc}\n")
        return 2
    library = load_library(config.library)
    build = config.root / "build"
    try:
        return _run(args, config, library, build)
    except (OutputInsideLibrary, PromotionRefused, FileNotFoundError) as exc:
        sys.stderr.write(f"procgov: {exc}\n")
        return 1


def _run(args, config, library, build: Path) -> int:
    if args.command == "check":
        findings = check_library(library, config)
        if args.json:
            _out(json.dumps([f.as_dict() for f in findings], indent=2))
        else:
            for f in findings:
                extra = f" -> {f.proposal}" if f.proposal else ""
                _out(f"{f.severity:8} {f.document}: {f.message}{extra}  [{f.rule}; {f.standard}]")
            _out(f"{len(library.documents)} document(s), {len(findings)} finding(s)")
        return 1 if has_errors(findings) else 0
    if args.command == "classify":
        results = classify(library, config)
        _out("| Document | Declared | Proposed | Missing sections |")
        _out("| --- | --- | --- | --- |")
        for r in results:
            _out(
                f"| {r.document} | {r.declared} | {r.proposed} | {', '.join(r.missing_sections)} |"
            )
        for f in as_findings(results, config):
            _out(f"proposal {f.document}: {f.message} ({f.reason})")
        return 0
    if args.command == "register":
        out = args.out or build / "register"
        out.mkdir(parents=True, exist_ok=True)
        rows = register_rows(library, config)
        (out / "register.md").write_text(register_markdown(rows, config.organisation))
        (out / "register.csv").write_text(register_csv(rows))
        _out(f"wrote {out / 'register.md'} and {out / 'register.csv'} ({len(rows)} rows)")
        return 0
    if args.command == "render":
        out = args.out or build / "docx"
        if args.id:
            doc = next((d for d in library.active() if d.id == args.id), None)
            doc = doc or next((d for d in library.documents if d.id == args.id), None)
            if doc is None:
                sys.stderr.write(f"procgov: no document {args.id}\n")
                return 1
            _out(f"wrote {render_document(doc, config, out / f'{doc.id}.docx')}")
        else:
            for path in render_library(list(library.documents), config, out):
                _out(f"wrote {path}")
        return 0
    if args.command == "package":
        _out(f"wrote {build_package(library, config, args.out or build / 'package')}")
        return 0
    if args.command == "site":
        _out(f"wrote {build_site(library, config, args.out or build / 'site')}")
        return 0
    if args.command == "promote":
        changes = plan_promotion(library, config, args.draft, args.approved_by)
        for c in changes:
            _out(f"{'' if args.write else 'would: '}{c.path.name}: {c.old} -> {c.new}")
        if args.write:
            apply_promotion(changes, args.approved_by)
        else:
            _out("dry run: nothing changed; add --write to promote")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
