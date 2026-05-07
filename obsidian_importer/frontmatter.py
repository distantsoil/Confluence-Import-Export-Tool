"""Build YAML front-matter from a Confluence page's _metadata.json."""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_frontmatter(metadata: dict, space_key: str = "") -> str:
    """Return a YAML front-matter block (including the --- delimiters)."""
    fm: Dict[str, Any] = {}

    # Title
    title = metadata.get("title", "")
    if title:
        fm["title"] = title

    # Confluence identifiers
    page_id = str(metadata.get("id", ""))
    if page_id:
        fm["confluence_id"] = page_id

    if space_key:
        fm["confluence_space"] = space_key

    # Dates
    created = _extract_date(metadata, "created", "history")
    if created:
        fm["created"] = created

    modified = _extract_date(metadata, "lastUpdated", "version")
    if modified:
        fm["updated"] = modified

    # Author
    author = _extract_author(metadata)
    if author:
        fm["author"] = author

    # Version number
    version = _extract_version(metadata)
    if version:
        fm["confluence_version"] = version

    # Labels / tags
    labels = _extract_labels(metadata)
    if labels:
        fm["tags"] = labels

    if not fm:
        return ""

    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_str(item)}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {_yaml_str(str(value))}")
    lines.append("---\n")
    return "\n".join(lines)


def _yaml_str(value: str) -> str:
    """Wrap value in quotes if it contains YAML-special characters."""
    if any(c in value for c in (':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'")):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _extract_date(meta: dict, *keys: str) -> Optional[str]:
    """Walk nested keys to find a date/datetime string."""
    obj = meta
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key, {})
        else:
            return None
    if isinstance(obj, str):
        # Return only the date portion
        return obj[:10] if len(obj) >= 10 else obj
    if isinstance(obj, dict):
        for k in ("when", "date", "lastModified"):
            if k in obj:
                val = obj[k]
                return str(val)[:10] if isinstance(val, str) and len(val) >= 10 else str(val)
    return None


def _extract_author(meta: dict) -> Optional[str]:
    for path in [
        ["history", "createdBy", "displayName"],
        ["version", "by", "displayName"],
        ["createdBy", "displayName"],
    ]:
        obj = meta
        for key in path:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                obj = None
                break
        if obj and isinstance(obj, str):
            return obj
    return None


def _extract_version(meta: dict) -> Optional[int]:
    v = meta.get("version", {})
    if isinstance(v, dict):
        num = v.get("number")
        if num is not None:
            return int(num)
    elif isinstance(v, int):
        return v
    return None


def _extract_labels(meta: dict) -> list:
    labels_data = meta.get("metadata", {}).get("labels", {})
    if isinstance(labels_data, dict):
        results = labels_data.get("results", [])
        return [r.get("name", "") for r in results if r.get("name")]
    if isinstance(labels_data, list):
        return [r.get("name", "") for r in labels_data if r.get("name")]
    return []
