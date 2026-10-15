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
| `procgov classify` | Proposed document type and missing sections per document (a report). |
| `procgov render [ID]` | Word output in `build/docx/`, laid out from your template or configured palette. |
| `procgov register` | `register.md` and `register.csv`, one row per document. |
| `procgov package` | Active documents rendered, register and `manifest.json` (source and output hashes, commit). |
| `procgov site` | Static site (documents, register, findings, a reader per document) and its zip for offline readers. |
| `procgov promote FILE --approved-by NAME` | Shows what promoting a DRAFT changes; add `--write` to apply. The only command that changes source. |

Outputs never go into the library. The same source gives the same output.

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
