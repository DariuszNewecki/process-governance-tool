"""Where pandoc comes from: the pypandoc_binary wheel, so no system install."""

from __future__ import annotations

import shutil


def pandoc_path() -> str:
    """The pandoc executable: the bundled one, else one on PATH."""
    try:
        import pypandoc

        return pypandoc.get_pandoc_path()
    except (ImportError, OSError):
        found = shutil.which("pandoc")
        if found is None:
            raise RuntimeError(
                "pandoc not found: install the package with its dependencies "
                "(pypandoc_binary bundles pandoc)"
            ) from None
        return found
