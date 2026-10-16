"""Enforces privacy.no_private_library_names: no private library name goes public.

The forbidden names are read from the private library on this machine, so the
list is never published:

- every Markdown file name in the library, with and without its extension;
- every ``owner`` in the library's front-matter;
- each line of the optional names file (people named only inside documents).

Usage:
    PROCGOV_PRIVATE_LIBRARY=/path/to/library \\
    PROCGOV_PRIVATE_NAMES=/path/to/names.txt \\
    python scripts/private_names.py [--range BASE..HEAD] [TEXT_FILE ...]

``--range`` checks the lines a commit range adds and its commit messages;
each TEXT_FILE (an issue or PR body before it is posted) is checked whole.
Exit 1 names each hit by the file or commit it is in, never by the name
itself, so the report is safe to paste. Without PROCGOV_PRIVATE_LIBRARY there
is nothing to check against: it says so and exits 0.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

_SEPARATORS = re.compile(r"[\s_\-]+")
_FRONT = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


def normalise(text: str) -> str:
    """Lower case, with runs of spaces, underscores and dashes as one space."""
    return _SEPARATORS.sub(" ", text.lower())


def forbidden_names(library: Path, names_file: Path | None = None) -> set[str]:
    """The normalised names that must not appear in public text."""
    names: set[str] = set()
    for path in library.rglob("*.md"):
        names.update({normalise(path.name), normalise(path.stem)})
        match = _FRONT.match(path.read_text(encoding="utf-8", errors="replace"))
        if match:
            try:
                meta = yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                meta = None
            if isinstance(meta, dict) and meta.get("owner"):
                names.add(normalise(str(meta["owner"])))
    if names_file is not None:
        for line in names_file.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                names.add(normalise(line.strip()))
    return {n.strip() for n in names if len(n.strip()) >= 3}


def hits(text: str, names: set[str]) -> int:
    """How many forbidden names occur in ``text`` as whole words."""
    haystack = f" {normalise(text)} "
    return sum(1 for n in names if re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", haystack))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def check_range(rev_range: str, names: set[str]) -> list[str]:
    """Where a commit range adds a forbidden name: '<sha>: message' or '<file>'."""
    out = []
    for sha in _git("rev-list", rev_range).split():
        if hits(_git("log", "-1", "--format=%B", sha), names):
            out.append(f"{sha[:8]}: commit message")
    current = ""
    for line in _git("diff", "--unified=0", rev_range).splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and hits(line[1:], names) and current not in out:
            out.append(current)
    for path in _git("diff", "--name-only", rev_range).split("\n"):
        if path and hits(Path(path).name, names) and path not in out:
            out.append(path)
    return out


def main(argv: list[str]) -> int:
    """Check a commit range and/or text files; exit 1 on any hit."""
    library = os.environ.get("PROCGOV_PRIVATE_LIBRARY")
    if not library:
        sys.stdout.write("private_names: PROCGOV_PRIVATE_LIBRARY not set; nothing to check\n")
        return 0
    names_file = os.environ.get("PROCGOV_PRIVATE_NAMES")
    names = forbidden_names(Path(library), Path(names_file) if names_file else None)
    found: list[str] = []
    args = list(argv)
    if "--range" in args:
        i = args.index("--range")
        found += check_range(args[i + 1], names)
        del args[i : i + 2]
    found += [path for path in args if hits(Path(path).read_text(encoding="utf-8"), names)]
    for where in found:
        sys.stdout.write(f"private_names: a private library name in {where}\n")
    if not found:
        sys.stdout.write(f"private_names: clean ({len(names)} names checked)\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
