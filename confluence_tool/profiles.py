"""Named connection profiles stored under ~/.confluence-tool/profiles/.

A profile is a JSON file holding a complete ConfigManager-shaped config plus
a small metadata header. Profiles let users switch between Confluence
environments without juggling repo-local YAML files.
"""

from __future__ import annotations

import copy
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROFILE_DIR_ENV = "CONFLUENCE_TOOL_HOME"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")


def state_root() -> Path:
    """Root directory for all tool state. Override with $CONFLUENCE_TOOL_HOME."""
    override = os.environ.get(PROFILE_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".confluence-tool"


def profiles_dir() -> Path:
    return state_root() / "profiles"


def _ensure_dir() -> Path:
    d = profiles_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_name(name: str) -> str:
    name = (name or "").strip()
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid profile name {name!r}. Use letters, digits, '-', '_', '.' "
            "(1-64 chars, must start with a letter or digit)."
        )
    return name


def profile_path(name: str) -> Path:
    return profiles_dir() / f"{validate_name(name)}.json"


def list_profiles() -> List[str]:
    d = profiles_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def exists(name: str) -> bool:
    return profile_path(name).exists()


def load(name: str) -> Dict[str, Any]:
    path = profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {name} (looked in {path})")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "config" not in data:
        raise ValueError(f"Profile {name!r} is malformed (missing 'config').")
    return data


def save(name: str, config: Dict[str, Any], description: str = "") -> Path:
    """Persist a profile. Returns the file path written."""
    name = validate_name(name)
    _ensure_dir()
    path = profile_path(name)
    payload = {
        "name": name,
        "description": description,
        "saved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "config": config,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path


def delete(name: str) -> bool:
    path = profile_path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def summary(name: str) -> str:
    """Short human-readable line describing a profile."""
    try:
        data = load(name)
    except Exception as exc:
        return f"{name} (unreadable: {exc})"
    cfg = data.get("config", {})
    base_url = cfg.get("confluence", {}).get("base_url", "?")
    user = cfg.get("confluence", {}).get("auth", {}).get("username", "?")
    desc = data.get("description") or ""
    tail = f" — {desc}" if desc else ""
    return f"{name}  [{user} @ {base_url}]{tail}"


def build_config(
    base_url: str,
    username: str,
    api_token: str,
    *,
    output_directory: str = "./exports",
    conflict_resolution: str = "skip",
) -> Dict[str, Any]:
    """Construct a minimal ConfigManager-shaped config from wizard inputs."""
    return {
        "confluence": {
            "base_url": base_url.rstrip("/"),
            "auth": {
                "username": username,
                "api_token": api_token,
            },
        },
        "export": {
            "output_directory": output_directory,
            "format": {
                "html": True,
                "attachments": True,
                "comments": True,
            },
        },
        "import": {
            "conflict_resolution": conflict_resolution,
            "create_missing_parents": True,
            "import_attachments": True,
        },
        "general": {
            "verbose": False,
            "max_workers": 5,
            "timeout": 30,
            "rate_limit": 10,
            "retry": {"max_attempts": 3},
        },
        "logging": {"level": "INFO"},
    }


def merged(profile_config: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep-merged copy: overrides win over profile_config."""
    out = copy.deepcopy(profile_config)

    def _merge(dst, src):
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                _merge(dst[k], v)
            else:
                dst[k] = v

    _merge(out, overrides)
    return out


def reset_tool_state() -> List[Path]:
    """Remove everything under state_root(). Returns the paths removed."""
    import shutil

    root = state_root()
    removed: List[Path] = []
    if not root.exists():
        return removed
    for child in root.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed.append(child)
    try:
        root.rmdir()
    except OSError:
        pass
    return removed
