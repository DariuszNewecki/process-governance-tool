"""The delivery package (R7): active documents only, rendered, plus a manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from procgov.config import Config
from procgov.model import Library
from procgov.register import register_csv, register_markdown, register_rows
from procgov.render.docx import render_library
from procgov.trace import source_version


def build_package(library: Library, config: Config, out_dir: Path) -> Path:
    """Write ``out_dir``: documents/<id>.docx, register.md/.csv, manifest.json."""
    out_dir = Path(out_dir)
    active = library.active()
    paths = render_library(active, config, out_dir / "documents")
    rows = [r for r in register_rows(library, config) if r["status"] == "DOCUMENT"]
    (out_dir / "register.md").write_text(register_markdown(rows, config.organisation))
    (out_dir / "register.csv").write_text(register_csv(rows))
    manifest = {
        "organisation": config.organisation,
        "source": source_version(library.root),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "status": doc.status,
                "source": doc.rel,
                "source_sha256": doc.sha256,
                "output": path.relative_to(out_dir).as_posix(),
                "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for doc, path in zip(active, paths)
        ],
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path
