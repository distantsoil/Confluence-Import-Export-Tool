"""Read/write the .confluence_import_state.json file inside the vault."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


STATE_FILENAME = ".confluence_import_state.json"


class PageState:
    __slots__ = ("vault_path", "confluence_version", "confluence_modified", "content_hash")

    def __init__(
        self,
        vault_path: str,
        confluence_version: int,
        confluence_modified: str,
        content_hash: str,
    ):
        self.vault_path = vault_path
        self.confluence_version = confluence_version
        self.confluence_modified = confluence_modified
        self.content_hash = content_hash

    def to_dict(self) -> dict:
        return {
            "vault_path": self.vault_path,
            "confluence_version": self.confluence_version,
            "confluence_modified": self.confluence_modified,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PageState":
        return cls(
            vault_path=d["vault_path"],
            confluence_version=d.get("confluence_version", 0),
            confluence_modified=d.get("confluence_modified", ""),
            content_hash=d.get("content_hash", ""),
        )


class ImportState:
    def __init__(
        self,
        space_key: str,
        last_import_utc: str,
        source_export_dir: str,
        pages: Optional[Dict[str, PageState]] = None,
    ):
        self.space_key = space_key
        self.last_import_utc = last_import_utc
        self.source_export_dir = source_export_dir
        self.pages: Dict[str, PageState] = pages or {}

    def to_dict(self) -> dict:
        return {
            "space_key": self.space_key,
            "last_import_utc": self.last_import_utc,
            "source_export_dir": self.source_export_dir,
            "pages": {pid: ps.to_dict() for pid, ps in self.pages.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ImportState":
        pages = {
            pid: PageState.from_dict(ps)
            for pid, ps in d.get("pages", {}).items()
        }
        return cls(
            space_key=d["space_key"],
            last_import_utc=d.get("last_import_utc", ""),
            source_export_dir=d.get("source_export_dir", ""),
            pages=pages,
        )

    def update_timestamp(self, export_dir: str) -> None:
        self.last_import_utc = datetime.now(timezone.utc).isoformat()
        self.source_export_dir = export_dir

    def upsert_page(self, page_id: str, page_state: PageState) -> None:
        self.pages[page_id] = page_state

    def remove_page(self, page_id: str) -> None:
        self.pages.pop(page_id, None)


def state_path(space_dir: Path) -> Path:
    return space_dir / STATE_FILENAME


def load_state(space_dir: Path) -> Optional[ImportState]:
    p = state_path(space_dir)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as fh:
        return ImportState.from_dict(json.load(fh))


def save_state(space_dir: Path, state: ImportState) -> None:
    p = state_path(space_dir)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(state.to_dict(), fh, indent=2, ensure_ascii=False)
