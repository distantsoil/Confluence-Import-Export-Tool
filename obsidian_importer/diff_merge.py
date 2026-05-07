"""Compare a new Confluence export against the stored import state.

Classifies each page as:
  NEW        — in export, not in state
  UPDATED    — in export, version/mtime newer than state
  UNCHANGED  — in export, same version as state, file not edited locally
  CONFLICT   — in export, Confluence updated AND user edited local note
  DELETED    — in state, missing from export
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .hierarchy import PageNode
from .state import ImportState, PageState
from .utils import content_hash


class ChangeKind(Enum):
    NEW = auto()
    UPDATED = auto()
    UNCHANGED = auto()
    CONFLICT = auto()
    DELETED = auto()


@dataclass
class PageChange:
    page_id: str
    kind: ChangeKind
    node: Optional[PageNode] = None       # None for DELETED
    old_state: Optional[PageState] = None
    conflict_resolution: Optional[str] = None  # keep-local | keep-confluence | keep-both


def compute_changes(
    nodes: Dict[str, PageNode],
    state: Optional[ImportState],
    vault_dir: Path,
) -> List[PageChange]:
    """Return a list of PageChange objects describing what needs to happen."""
    changes: List[PageChange] = []
    seen_ids = set()

    for page_id, node in nodes.items():
        seen_ids.add(page_id)

        if state is None or page_id not in state.pages:
            changes.append(PageChange(page_id=page_id, kind=ChangeKind.NEW, node=node))
            continue

        old = state.pages[page_id]
        new_version = node.metadata.get("version", {})
        if isinstance(new_version, dict):
            new_ver_num = int(new_version.get("number", 0))
        elif isinstance(new_version, int):
            new_ver_num = new_version
        else:
            new_ver_num = 0

        confluence_updated = new_ver_num > old.confluence_version

        # Check whether the user edited the local file
        local_path = vault_dir / old.vault_path
        locally_edited = False
        if local_path.exists():
            current_hash = content_hash(local_path.read_text(encoding="utf-8", errors="replace"))
            locally_edited = current_hash != old.content_hash

        if confluence_updated and locally_edited:
            changes.append(
                PageChange(page_id=page_id, kind=ChangeKind.CONFLICT, node=node, old_state=old)
            )
        elif confluence_updated:
            changes.append(
                PageChange(page_id=page_id, kind=ChangeKind.UPDATED, node=node, old_state=old)
            )
        else:
            changes.append(
                PageChange(page_id=page_id, kind=ChangeKind.UNCHANGED, node=node, old_state=old)
            )

    # Find deleted pages (in state but not in current export)
    if state:
        for page_id, old_state in state.pages.items():
            if page_id not in seen_ids:
                changes.append(
                    PageChange(page_id=page_id, kind=ChangeKind.DELETED, old_state=old_state)
                )

    return changes


def summarise(changes: List[PageChange]) -> Dict[str, int]:
    counts: Dict[str, int] = {k.name: 0 for k in ChangeKind}
    for c in changes:
        counts[c.kind.name] += 1
    return counts


def apply_conflict_resolution(
    changes: List[PageChange], resolution: str
) -> List[PageChange]:
    """Apply a blanket conflict resolution strategy to all CONFLICT entries."""
    for c in changes:
        if c.kind == ChangeKind.CONFLICT:
            c.conflict_resolution = resolution
    return changes
