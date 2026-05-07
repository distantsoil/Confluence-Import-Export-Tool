"""HTML → Markdown conversion with Confluence-specific pre-processing.

Flow:
  1. BeautifulSoup: strip/replace Confluence-specific markup
  2. markdownify: convert remaining HTML to Markdown
  3. Post-process: clean up artefacts left by markdownify
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

# Confluence macro wrappers that can be safely stripped (content kept)
_TRANSPARENT_CLASSES = {
    "confluence-information-macro",
    "confluence-information-macro-information",
    "confluence-information-macro-note",
    "confluence-information-macro-warning",
    "confluence-information-macro-tip",
    "panel",
    "expand-container",
    "expand-content",
    "expand-control",
}

# Known macro names that produce an Obsidian callout instead
_MACRO_CALLOUT = {
    "info": "info",
    "note": "note",
    "warning": "warning",
    "tip": "tip",
    "expand": "abstract",
    "panel": "note",
}

_BLANK_LINES = re.compile(r'\n{3,}')
_TRAILING_WS = re.compile(r'[ \t]+\n')


def html_to_markdown(html: str, page_title: str = "") -> str:
    """Convert a Confluence-exported HTML string to Obsidian Markdown."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove the outer page wrapper div if present
    body = soup.find("div", class_="wiki-content") or soup.find("body") or soup

    _strip_confluence_macros(body)
    _convert_code_blocks(body)
    _convert_expand_macros(body)
    _convert_panels(body)
    _strip_style_spans(body)

    raw = md(str(body), heading_style="ATX", bullets="-", newline_style="backslash")

    # Clean up markdownify artefacts
    raw = _BLANK_LINES.sub("\n\n", raw)
    raw = _TRAILING_WS.sub("\n", raw)
    return raw.strip()


def convert_comments_html(html: str) -> str:
    """Convert a comments.html block to a collapsed Markdown section."""
    soup = BeautifulSoup(html, "html.parser")
    comments = soup.find_all(class_=re.compile(r"comment", re.I))
    if not comments:
        # Fallback: convert the whole thing
        text = md(html, heading_style="ATX", bullets="-")
        return f"\n---\n## Comments\n\n{text.strip()}\n"

    parts = ["\n---\n## Comments\n"]
    for c in comments:
        author = _extract_text(c, class_=re.compile(r"author|user", re.I))
        date = _extract_text(c, class_=re.compile(r"date|time", re.I))
        body_tag = c.find(class_=re.compile(r"body|content|text", re.I))
        body_md = md(str(body_tag), bullets="-").strip() if body_tag else ""
        header = " — ".join(filter(None, [author, date]))
        parts.append(f"**{header}**\n\n{body_md}\n")

    return "\n".join(parts)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _extract_text(tag: Tag, **kwargs) -> str:
    found = tag.find(**kwargs)
    return found.get_text(strip=True) if found else ""


def _strip_confluence_macros(root: Tag) -> None:
    """Remove purely structural Confluence wrapper divs/spans."""
    for cls in _TRANSPARENT_CLASSES:
        for tag in root.find_all(class_=cls):
            tag.unwrap()  # keep children, remove the wrapper tag


def _convert_code_blocks(root: Tag) -> None:
    """Replace Confluence <pre> / code-macro blocks with fenced code blocks."""
    for pre in root.find_all("pre", class_=re.compile(r"syntaxhighlighter|code", re.I)):
        lang = ""
        cls_str = " ".join(pre.get("class", []))
        lang_match = re.search(r"brush:\s*(\w+)", cls_str)
        if lang_match:
            lang = lang_match.group(1)
        code_text = pre.get_text()
        new_tag = BeautifulSoup(
            f'<pre><code class="language-{lang}">{code_text}</code></pre>', "html.parser"
        ).pre
        pre.replace_with(new_tag)


def _convert_expand_macros(root: Tag) -> None:
    """Convert <div class='expand-container'> into an Obsidian callout."""
    for div in root.find_all("div", class_="expand-container"):
        title_tag = div.find(class_="expand-control-text")
        title = title_tag.get_text(strip=True) if title_tag else "Details"
        content_div = div.find(class_="expand-content")
        content_html = str(content_div) if content_div else ""
        content_md = md(content_html, bullets="-").strip()
        callout = f'\n> [!abstract]- {title}\n'
        for line in content_md.splitlines():
            callout += f'> {line}\n'
        replacement = BeautifulSoup(f"<div>{callout}</div>", "html.parser").div
        div.replace_with(replacement)


def _convert_panels(root: Tag) -> None:
    """Convert info/note/warning/tip macro divs into Obsidian callouts."""
    macro_re = re.compile(
        r"confluence-information-macro-(information|note|warning|tip)", re.I
    )
    for div in root.find_all("div", class_=macro_re):
        cls_str = " ".join(div.get("class", []))
        m = macro_re.search(cls_str)
        kind = m.group(1).lower() if m else "note"
        callout_type = _MACRO_CALLOUT.get(kind, "note")

        title_tag = div.find(class_="confluence-information-macro-title")
        title = title_tag.get_text(strip=True) if title_tag else kind.capitalize()
        body_tag = div.find(class_="confluence-information-macro-body")
        body_html = str(body_tag) if body_tag else str(div)
        body_md = md(body_html, bullets="-").strip()

        callout = f'\n> [!{callout_type}] {title}\n'
        for line in body_md.splitlines():
            callout += f'> {line}\n'
        replacement = BeautifulSoup(f"<div>{callout}</div>", "html.parser").div
        div.replace_with(replacement)


def _strip_style_spans(root: Tag) -> None:
    """Remove <span> tags that only carry inline style/class attributes."""
    for span in root.find_all("span"):
        # Keep spans that carry semantic meaning (e.g. code)
        if span.get("class") and any("code" in c for c in span.get("class", [])):
            continue
        span.unwrap()
