"""Fernhill Garden Supplies, the fictional organisation every test renders for."""

from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path

import pytest

from procgov.config import Config, load_config
from procgov.model import Library, load_library

FIXTURE = Path(__file__).parent / "fixtures" / "fernhill"


def tiny_png(path: Path, rgb=(59, 122, 59)) -> Path:
    """A 2x2 single-colour PNG, made here so no image file is committed."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(rgb) * 2 for _ in range(2))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    return path


@pytest.fixture
def fernhill(tmp_path: Path) -> Path:
    """A copy of the Fernhill library and configuration, with a wordmark."""
    root = tmp_path / "fernhill"
    shutil.copytree(FIXTURE, root)
    tiny_png(root / "wordmark.png")
    cfg = root / "procgov.yaml"
    cfg.write_text(cfg.read_text() + "wordmark: wordmark.png\n")
    return root


@pytest.fixture
def config(fernhill: Path) -> Config:
    return load_config(fernhill / "procgov.yaml")


@pytest.fixture
def library(config: Config) -> Library:
    return load_library(config.library)
