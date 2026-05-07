"""Shared utilities: filename sanitisation, path helpers."""

import hashlib
import re
from pathlib import Path


# Characters illegal on Windows, macOS, or Linux filesystems
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_TRAILING = re.compile(r'[\s.]+$')
_MULTI_SPACE = re.compile(r' {2,}')

# Windows reserved names
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Return a filesystem-safe version of *name*."""
    name = _ILLEGAL_CHARS.sub("_", name)
    name = _TRAILING.sub("", name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    if name.upper() in _RESERVED:
        name = f"_{name}"
    if not name:
        name = "_unnamed"
    return name[:max_length]


def file_hash(path: Path) -> str:
    """Return a sha256 hex digest of the file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash(text: str) -> str:
    """Return a sha256 hex digest of *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
