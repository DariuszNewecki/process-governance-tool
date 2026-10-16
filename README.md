# process-governance-tool

Governed process documentation: write each process once in Markdown, get Word
documents in your organisation's own layout, a register, a delivery package and
an offline site. The tool formats, checks and proposes; only the Process Owner
decides content.

Nothing branded lives here. Your Word template, palette, labels, document types
and house spelling are inputs, read from a `procgov.yaml` next to your library.
Examples and tests use a fictional organisation, *Fernhill Garden Supplies*
(`tests/fixtures/fernhill/`).

## Install

```bash
pip install .            # pandoc comes with it (pypandoc_binary)
```

## Day to day

Each document is a Markdown file with front-matter:

```markdown
---
id: PR-001
title: Seed Ordering
type: process          # a type from procgov.yaml
status: DRAFT          # DRAFT, DOCUMENT or ARCHIVE
owner: Head of Purchasing
---

## Purpose
...
```

| Command | What it does |
| --- | --- |
| `procgov check` | Front-matter, required sections, house spelling, broken cross-references, lifecycle. Exit 1 on errors; spelling is a proposal. |
| `procgov classify` | Proposed document type and missing sections per document, and why a row is empty (a report). |
| `procgov render [ID]` | Word output in `build/docx/`, laid out from your template or configured palette. |
| `procgov register` | `register.md` and `register.csv`, one row per document. |
| `procgov package` | Active documents rendered, register and `manifest.json` (source and output hashes, commit). |
| `procgov site` | Static site (documents, register, findings, a reader per document) and its zip for offline readers. |
| `procgov promote FILE --approved-by NAME` | Shows what promoting a DRAFT changes; add `--write` to apply. |
| `procgov adopt` | Shows the front-matter an existing library is missing (id from the file name, status DRAFT, type when the classification is clear, title from the first heading); add `--write` to apply. The owner is left for the Process Owner; existing front-matter and the body are kept. |

Only `promote` and `adopt` change source, and only with `--write`.

Outputs never go into the library. The same source gives the same output.

To keep working records (status updates, invitations, drafts) beside the
governed documents without governing them, list them in `procgov.yaml`:

```yaml
library_exclude:
  - 'records/*'
  - '*_status_update_*'
```

`procgov check` names every excluded file.

## Governed by CORE

This repository is audited by [CORE](https://github.com/DariuszNewecki/CORE)
on every pull request (`.github/workflows/core-audit.yml`). Its law lives in
`.intent/`.

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
core-admin code audit --offline
```

The libraries this tool governs are private; this repository is public. No
file name or person's name from a private library goes into an issue, pull
request, commit or test data (`.intent/rules/privacy/private_library.json`).
On the machine that has the library, check a branch and any issue or PR text
before publishing it:

```bash
export PROCGOV_PRIVATE_LIBRARY=/path/to/library
export PROCGOV_PRIVATE_NAMES=/path/to/names.txt   # optional: people named inside documents
python scripts/private_names.py --range origin/main..HEAD issue-body.md
```
