"""privacy.no_private_library_names: names come from the library, never from this repo."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "private_names", Path(__file__).parents[1] / "scripts" / "private_names.py"
)
private_names = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(private_names)


@pytest.fixture
def private(tmp_path):
    """A stand-in private library with fictional names."""
    lib = tmp_path / "private"
    lib.mkdir()
    (lib / "Quarry_Plan_v0.3.md").write_text("---\nowner: Wren Halloway\n---\n\nText.\n")
    (lib / "Notes Bramble.md").write_text("# Notes\n")
    names = tmp_path / "names.txt"
    names.write_text("# people named only in documents\nOsric Pell\n")
    return lib, names


def test_file_names_owners_and_listed_people_are_forbidden(private):
    lib, names = private
    forbidden = private_names.forbidden_names(lib, names)
    for text in (
        "see Quarry_Plan_v0.3.md",
        "the quarry plan v0.3 file",
        "owned by Wren Halloway",
        "notes-bramble",
        "asked osric pell",
    ):
        assert private_names.hits(text, forbidden), text


def test_plain_descriptions_pass(private):
    lib, names = private
    forbidden = private_names.forbidden_names(lib, names)
    assert not private_names.hits("adopt on the plan, version 0.3, 2026-10-16", forbidden)
    assert not private_names.hits("Fernhill Garden Supplies, PR-001", forbidden)


def test_without_a_library_there_is_nothing_to_check(monkeypatch, capsys):
    monkeypatch.delenv("PROCGOV_PRIVATE_LIBRARY", raising=False)
    assert private_names.main([]) == 0
    assert "nothing to check" in capsys.readouterr().out


def test_a_text_with_a_name_fails_and_the_report_does_not_repeat_it(
    private, tmp_path, monkeypatch, capsys
):
    lib, names = private
    body = tmp_path / "issue.md"
    body.write_text("Found while checking Quarry_Plan_v0.3.md.\n")
    monkeypatch.setenv("PROCGOV_PRIVATE_LIBRARY", str(lib))
    monkeypatch.setenv("PROCGOV_PRIVATE_NAMES", str(names))
    assert private_names.main([str(body)]) == 1
    out = capsys.readouterr().out
    assert str(body) in out and "Quarry" not in out


def test_a_commit_range_is_checked_in_messages_lines_and_file_names(private, tmp_path, monkeypatch):
    lib, names = private
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    subprocess.run([*git, "init", "-q"], check=True)
    (repo / "a.txt").write_text("clean\n")
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-qm", "start"], check=True)
    (repo / "a.txt").write_text("clean\nasked Osric Pell\n")
    subprocess.run([*git, "commit", "-qam", "fix for Wren Halloway"], check=True)
    monkeypatch.chdir(repo)
    found = private_names.check_range("HEAD~1..HEAD", private_names.forbidden_names(lib, names))
    assert [f.split(":")[-1].strip() for f in found] == ["commit message", "a.txt"]
