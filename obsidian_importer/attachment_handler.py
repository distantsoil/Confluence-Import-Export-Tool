"""Copy attachments from the export directory into the vault's _attachments folder.

All attachments for a given space are flattened into a single directory:
  <vault>/<space_path>/_attachments/<filename>

Filename collisions are resolved by prefixing the page title.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from .hierarchy import PageNode, find_attachments_dir
from .utils import ensure_dir, sanitize_filename

log = logging.getLogger(__name__)


def collect_attachments(
    export_dir: Path, nodes: Dict[str, PageNode]
) -> List[Tuple[Path, str]]:
    """Return a list of (src_path, dest_filename) for every attachment.

    Filenames are de-duplicated by prepending the page title when a clash
    is detected.
    """
    seen: Dict[str, str] = {}  # dest_filename → first page title
    pairs: List[Tuple[Path, str]] = []

    for node in nodes.values():
        att_dir = find_attachments_dir(export_dir, node)
        if att_dir is None:
            continue
        for att_file in att_dir.iterdir():
            if att_file.name == "attachments_metadata.json":
                continue
            if not att_file.is_file():
                continue

            dest_name = sanitize_filename(att_file.name)
            if dest_name in seen and seen[dest_name] != node.title:
                # Prefix with page title to avoid collision
                page_prefix = sanitize_filename(node.title)[:50]
                dest_name = f"{page_prefix}__{dest_name}"
            seen[dest_name] = node.title
            pairs.append((att_file, dest_name))

    return pairs


def copy_attachments(
    export_dir: Path,
    nodes: Dict[str, PageNode],
    attachments_dir: Path,
    overwrite: bool = True,
) -> int:
    """Copy all attachments to *attachments_dir*. Returns count copied."""
    ensure_dir(attachments_dir)
    pairs = collect_attachments(export_dir, nodes)
    copied = 0

    for src, dest_name in pairs:
        dest = attachments_dir / dest_name
        if dest.exists() and not overwrite:
            log.debug("Skipping existing attachment %s", dest_name)
            continue
        try:
            shutil.copy2(src, dest)
            copied += 1
        except OSError as exc:
            log.warning("Could not copy %s → %s: %s", src, dest, exc)

    return copied


def build_attachment_name_map(
    export_dir: Path, nodes: Dict[str, PageNode]
) -> Dict[str, str]:
    """Return {original_filename: dest_filename} for link rewriting."""
    pairs = collect_attachments(export_dir, nodes)
    return {src.name: dest for src, dest in pairs}
