"""Render one document, or the library, to Word (requirement R2)."""

from __future__ import annotations

import subprocess
import tempfile
from importlib import resources
from pathlib import Path

from procgov.config import Config
from procgov.model import Document
from procgov.render.pandoc import pandoc_path
from procgov.render.postprocess import postprocess
from procgov.render.reference import build_reference


class OutputInsideLibrary(ValueError):
    """Rendered copies never land in the library (G5: no silent overwrite of source)."""


def _guard(out: Path, config: Config) -> None:
    out = out.resolve()
    library = config.library.resolve()
    if out == library or library in out.parents:
        raise OutputInsideLibrary(f"refusing to write {out}: it is inside the library {library}")


def render_document(
    doc: Document, config: Config, out: Path, reference: Path | None = None
) -> Path:
    """Render ``doc`` to ``out`` (.docx) and return the path."""
    out = Path(out)
    _guard(out, config)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="procgov-") as tmp:
        ref = reference or build_reference(config, Path(tmp) / "reference.docx")
        lua = resources.files("procgov.render") / "autowidth.lua"
        with resources.as_file(lua) as lua_path:
            shift = "0" if any(level == 1 for level, _ in doc.headings()) else "-1"
            cmd = [
                pandoc_path(),
                "-f",
                "markdown+pipe_tables+yaml_metadata_block",
                "-t",
                "docx",
                f"--shift-heading-level-by={shift}",
                "--lua-filter",
                str(lua_path),
                "--reference-doc",
                str(ref),
                "-o",
                str(out),
            ]
            if config.number_headings:
                cmd.append("--number-sections")
            subprocess.run(cmd, input=doc.path.read_bytes(), check=True, capture_output=True)
    postprocess(out, doc, config)
    return out


def render_library(docs: list[Document], config: Config, out_dir: Path) -> list[Path]:
    """Render every document in ``docs`` into ``out_dir`` as <id>.docx (one reference)."""
    out_dir = Path(out_dir)
    _guard(out_dir, config)
    with tempfile.TemporaryDirectory(prefix="procgov-") as tmp:
        ref = build_reference(config, Path(tmp) / "reference.docx")
        return [render_document(d, config, out_dir / f"{d.id}.docx", ref) for d in docs]
