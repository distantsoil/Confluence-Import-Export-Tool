"""Build a page tree from the Confluence export's JSON metadata.

Handles:
- v2_page_parents.json  (page → parent relationships)
- folders/folders_metadata.json  (Cloud only)
- pages/<Title>_metadata.json  (individual page metadata)

Pages with children become FolderName/index.md in the vault.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .utils import sanitize_filename

log = logging.getLogger(__name__)


@dataclass
class PageNode:
    page_id: str
    title: str
    parent_id: Optional[str]
    is_blog: bool = False
    children: List[str] = field(default_factory=list)
    # Set during vault_path computation
    vault_path: str = ""
    # Raw metadata dict loaded from _metadata.json
    metadata: dict = field(default_factory=dict)


def load_export_hierarchy(export_dir: Path, space_path: str) -> Dict[str, PageNode]:
    """Return a dict of page_id → PageNode for the entire export.

    *space_path* is the vault-relative path prefix (e.g. "Confluence/MYSPACE").
    """
    nodes: Dict[str, PageNode] = {}

    # 1. Load per-page metadata from pages/ directory
    pages_dir = export_dir / "pages"
    if pages_dir.exists():
        for meta_file in pages_dir.glob("*_metadata.json"):
            _load_page_meta(meta_file, nodes, is_blog=False)

    # 2. Load blog post metadata
    blog_dir = export_dir / "blogposts"
    if blog_dir.exists():
        for meta_file in blog_dir.glob("*_metadata.json"):
            _load_page_meta(meta_file, nodes, is_blog=True)

    # 3. Apply parent relationships from v2_page_parents.json (most reliable)
    parents_file = export_dir / "v2_page_parents.json"
    if parents_file.exists():
        try:
            with open(parents_file, "r", encoding="utf-8") as fh:
                v2_parents = json.load(fh)
            # Format: {page_id: {"parent_id": "...", ...}} or list
            if isinstance(v2_parents, dict):
                for pid, info in v2_parents.items():
                    if pid in nodes and isinstance(info, dict):
                        parent_id = info.get("parent_id") or info.get("parentId")
                        if parent_id:
                            nodes[pid].parent_id = str(parent_id)
            elif isinstance(v2_parents, list):
                for item in v2_parents:
                    pid = str(item.get("id", ""))
                    parent_id = item.get("parent_id") or item.get("parentId")
                    if pid in nodes and parent_id:
                        nodes[pid].parent_id = str(parent_id)
        except Exception as exc:
            log.warning("Could not parse v2_page_parents.json: %s", exc)

    # 4. Build children lists
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node.page_id)

    # 5. Assign vault paths
    _assign_vault_paths(nodes, space_path)

    return nodes


def _load_page_meta(meta_file: Path, nodes: Dict[str, PageNode], is_blog: bool) -> None:
    try:
        with open(meta_file, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception as exc:
        log.warning("Skipping %s: %s", meta_file, exc)
        return

    page_id = str(meta.get("id", ""))
    title = meta.get("title", meta_file.stem.replace("_metadata", ""))

    if not page_id:
        log.warning("No page id in %s — skipping", meta_file)
        return

    # Parent from metadata (may be overridden by v2_page_parents.json later)
    ancestors = meta.get("ancestors", [])
    parent_id: Optional[str] = None
    if ancestors:
        parent_id = str(ancestors[-1].get("id", "")) or None

    nodes[page_id] = PageNode(
        page_id=page_id,
        title=title,
        parent_id=parent_id,
        is_blog=is_blog,
        metadata=meta,
    )


def _assign_vault_paths(nodes: Dict[str, PageNode], space_path: str) -> None:
    """DFS from roots to assign a vault-relative path to every node."""

    def _visit(node: PageNode, parent_path: str) -> None:
        safe = sanitize_filename(node.title)
        if node.is_blog:
            # Blog posts always land in Blog/ regardless of Confluence hierarchy
            node.vault_path = f"{space_path}/Blog/{safe}.md"
            return

        if node.children:
            # This page is a parent — it becomes FolderName/index.md
            folder = f"{parent_path}/{safe}"
            node.vault_path = f"{folder}/index.md"
            for child_id in node.children:
                if child_id in nodes:
                    _visit(nodes[child_id], folder)
        else:
            node.vault_path = f"{parent_path}/{safe}.md"

    # Find root nodes (no parent, or parent not in export)
    for node in nodes.values():
        if node.is_blog:
            continue
        if not node.parent_id or node.parent_id not in nodes:
            _visit(node, space_path)

    # Blog pass (parent_path irrelevant, set in _visit)
    for node in nodes.values():
        if node.is_blog and not node.vault_path:
            _visit(node, space_path)


def find_html_file(export_dir: Path, node: PageNode) -> Optional[Path]:
    """Locate the HTML content file for *node* in the export directory."""
    subdir = "blogposts" if node.is_blog else "pages"
    safe = sanitize_filename(node.title)
    candidates = [
        export_dir / subdir / f"{safe}.html",
        export_dir / subdir / f"{node.title}.html",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Fallback: search by page id in filename
    for p in (export_dir / subdir).glob("*.html"):
        if node.page_id in p.stem:
            return p

    return None


def find_attachments_dir(export_dir: Path, node: PageNode) -> Optional[Path]:
    """Return the attachments/ sub-directory for *node*, if it exists."""
    subdir = "blogposts" if node.is_blog else "pages"
    safe = sanitize_filename(node.title)
    candidates = [
        export_dir / subdir / "attachments" / safe,
        export_dir / subdir / "attachments" / node.title,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_comments_file(export_dir: Path, node: PageNode) -> Optional[Path]:
    """Return the comments.html path for *node*, if it exists."""
    subdir = "blogposts" if node.is_blog else "pages"
    safe = sanitize_filename(node.title)
    candidates = [
        export_dir / subdir / "comments" / safe / "comments.html",
        export_dir / subdir / "comments" / node.title / "comments.html",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None
