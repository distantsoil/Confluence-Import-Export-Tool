"""Rewrite Confluence URLs in Markdown text to Obsidian [[wiki-links]].

Handles patterns like:
  /wiki/spaces/SPACEKEY/pages/123456/Page+Title
  /wiki/spaces/SPACEKEY/pages/123456
  https://company.atlassian.net/wiki/spaces/SPACEKEY/pages/123456
"""

from __future__ import annotations

import re
from typing import Dict, Optional
from urllib.parse import unquote

# Matches both absolute and relative Confluence page URLs
# Groups: (1) optional domain, (2) space_key, (3) page_id, (4) optional slug
_CONFLUENCE_URL = re.compile(
    r'(?:https?://[^/]+)?/wiki/spaces/([A-Z0-9_\-]+)/pages/(\d+)(?:/([^)\s"\'#]*))?',
    re.IGNORECASE,
)

# Markdown link: [text](url)
_MD_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

# Plain URL in text
_PLAIN_URL = re.compile(
    r'(?<!\()(https?://[^/]+/wiki/spaces/[A-Z0-9_\-]+/pages/\d+[^)\s"\']*)',
    re.IGNORECASE,
)


class LinkRewriter:
    """Rewrite Confluence links to Obsidian wiki-links.

    *id_to_vault_path* maps page_id (str) → vault_path (str) for all pages in
    the export. When a page id is found in a URL, it is replaced with the
    corresponding vault path's stem (filename without .md extension).
    """

    def __init__(self, id_to_vault_path: Dict[str, str]):
        # Build a map of id → display title (the final path component without extension)
        self._id_to_title: Dict[str, str] = {}
        for pid, vpath in id_to_vault_path.items():
            # vault_path may be "Confluence/SPACE/Folder/Page.md" or ".../Folder/index.md"
            stem = vpath.rsplit("/", 1)[-1]
            if stem == "index.md":
                # Use parent folder name as title
                parts = vpath.rsplit("/", 2)
                stem = parts[-2] if len(parts) >= 2 else stem
            else:
                stem = stem[:-3] if stem.endswith(".md") else stem
            self._id_to_title[pid] = stem

    def rewrite(self, markdown: str) -> str:
        """Return *markdown* with all Confluence links rewritten."""
        # First handle explicit markdown links [text](confluence-url)
        result = _MD_LINK.sub(self._replace_md_link, markdown)
        # Then handle bare URLs
        result = _PLAIN_URL.sub(self._replace_plain_url, result)
        return result

    def _replace_md_link(self, m: re.Match) -> str:
        text = m.group(1)
        url = m.group(2)
        wiki = self._confluence_url_to_wikilink(url, display_text=text)
        if wiki:
            return wiki
        return m.group(0)

    def _replace_plain_url(self, m: re.Match) -> str:
        url = m.group(1)
        wiki = self._confluence_url_to_wikilink(url)
        return wiki if wiki else m.group(0)

    def _confluence_url_to_wikilink(
        self, url: str, display_text: Optional[str] = None
    ) -> Optional[str]:
        cm = _CONFLUENCE_URL.search(url)
        if not cm:
            return None

        page_id = cm.group(2)
        slug = cm.group(3) or ""
        slug = unquote(slug.replace("+", " ")).strip("/").split("/")[-1] or ""

        title = self._id_to_title.get(page_id)
        if not title:
            # Fall back to slug from URL
            title = slug or page_id

        if display_text and display_text.strip() and display_text.strip() != title:
            return f"[[{title}|{display_text.strip()}]]"
        return f"[[{title}]]"


def rewrite_attachment_refs(markdown: str, attachment_vault_prefix: str) -> str:
    """Rewrite attachment image/file references to Obsidian embed syntax.

    The export stores attachments relative to the page; we move them all to
    `_attachments/<filename>` so all references become `![[filename]]`.
    """
    # <img src="..."> already converted by markdownify to ![alt](src)
    # We just need to strip the path and emit ![[filename]]
    def _repl(m: re.Match) -> str:
        alt = m.group(1)
        src = m.group(2)
        # Already an obsidian embed
        if src.startswith("[["):
            return m.group(0)
        # Only rewrite local/relative paths
        if src.startswith("http://") or src.startswith("https://"):
            return m.group(0)
        filename = src.rsplit("/", 1)[-1].split("?")[0]
        if alt:
            return f"![[{filename}|{alt}]]"
        return f"![[{filename}]]"

    # Images: ![alt](src)
    result = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _repl, markdown)

    # Plain file links: [text](relative/path/file.ext) — non-image
    def _file_repl(m: re.Match) -> str:
        text = m.group(1)
        src = m.group(2)
        if src.startswith("http://") or src.startswith("https://"):
            return m.group(0)
        if src.startswith("[["):
            return m.group(0)
        filename = src.rsplit("/", 1)[-1].split("?")[0]
        if "." not in filename:
            return m.group(0)
        return f"[[{filename}|{text}]]" if text else f"[[{filename}]]"

    result = re.sub(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)', _file_repl, result)
    return result
