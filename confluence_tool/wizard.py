"""Interactive wizard for the Confluence Export-Import Tool.

Replaces flag-driven invocation with a guided flow:
  - Choose or create a connection profile (saved under ~/.confluence-tool/profiles/)
  - Pick an action (export, import, sync, etc.)
  - Collect any action-specific inputs interactively
  - Hand off to the existing command implementations

Falls back to a plain `input()`-based flow if `rich` / `questionary`
are not installed (the wizard is the *suggested* way to run, not the
*only* way; the flag-based commands still work).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import profiles as profiles_mod
from .config.manager import ConfigManager

try:
    import questionary
    from questionary import Choice
    _Q_AVAILABLE = True
except ImportError:
    questionary = None  # type: ignore
    Choice = None  # type: ignore
    _Q_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False
    Console = None  # type: ignore


_console = Console() if _RICH_AVAILABLE else None


# ---------- output helpers ----------

def _print(msg: str, style: str = "") -> None:
    if _console:
        _console.print(msg, style=style)
    else:
        print(msg)


def _panel(title: str, body: str, style: str = "cyan") -> None:
    if _console:
        _console.print(Panel(body, title=title, border_style=style))
    else:
        bar = "=" * max(len(title), 60)
        print(f"\n{bar}\n{title}\n{bar}\n{body}\n{bar}\n")


def _header(title: str, subtitle: str = "") -> None:
    if _console:
        text = Text(title, style="bold cyan")
        if subtitle:
            text.append(f"\n{subtitle}", style="dim")
        _console.print(Panel(text, border_style="cyan"))
    else:
        print(f"\n=== {title} ===")
        if subtitle:
            print(subtitle)


# ---------- prompt helpers (wrap questionary with input() fallback) ----------

def _select(message: str, choices: List[Any], default: Optional[Any] = None) -> Any:
    """Arrow-key select. `choices` may be plain strings or (label, value) tuples."""
    if _Q_AVAILABLE:
        q_choices = []
        for c in choices:
            if isinstance(c, tuple):
                label, value = c
                q_choices.append(Choice(title=label, value=value))
            else:
                q_choices.append(c)
        result = questionary.select(message, choices=q_choices, default=default).ask()
        if result is None:  # Ctrl-C / Esc
            raise KeyboardInterrupt
        return result
    # fallback
    print(f"\n{message}")
    flat: List[Tuple[str, Any]] = []
    for i, c in enumerate(choices, 1):
        if isinstance(c, tuple):
            label, value = c
        else:
            label, value = str(c), c
        flat.append((label, value))
        print(f"  {i}. {label}")
    while True:
        raw = input("Enter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(flat):
            return flat[int(raw) - 1][1]
        print("Invalid choice.")


def _text(message: str, default: str = "", validate=None) -> str:
    if _Q_AVAILABLE:
        kwargs: Dict[str, Any] = {"default": default}
        if validate is not None:
            kwargs["validate"] = validate
        result = questionary.text(message, **kwargs).ask()
        if result is None:
            raise KeyboardInterrupt
        return result
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"{message}{suffix}: ").strip()
        if not raw:
            raw = default
        if validate is not None:
            ok = validate(raw)
            if ok is not True:
                print(ok if isinstance(ok, str) else "Invalid input.")
                continue
        return raw


def _password(message: str) -> str:
    if _Q_AVAILABLE:
        result = questionary.password(message).ask()
        if result is None:
            raise KeyboardInterrupt
        return result
    import getpass
    return getpass.getpass(f"{message}: ")


def _confirm(message: str, default: bool = True) -> bool:
    if _Q_AVAILABLE:
        result = questionary.confirm(message, default=default).ask()
        if result is None:
            raise KeyboardInterrupt
        return result
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"{message} {suffix} ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


# ---------- profile selection / creation ----------

def _validate_url(value: str):
    v = (value or "").strip()
    if not v.startswith(("http://", "https://")):
        return "URL must start with http:// or https://"
    return True


def _nonempty(value: str):
    return True if value and value.strip() else "Required."


def _test_connection(config: Dict[str, Any]) -> bool:
    """Return True if the config's credentials work against Confluence."""
    from .api.client import ConfluenceAPIClient
    cc = config["confluence"]
    auth = cc["auth"]
    general = config.get("general", {})
    client = ConfluenceAPIClient(
        base_url=cc["base_url"],
        username=auth["username"],
        auth_token=auth.get("api_token"),
        password=auth.get("password"),
        timeout=general.get("timeout", 30),
        max_retries=general.get("retry", {}).get("max_attempts", 3),
        rate_limit=general.get("rate_limit", 10),
    )
    return client.test_connection()


def _create_profile_interactive(
    suggested_name: str = "",
    purpose: str = "Confluence environment",
) -> Optional[str]:
    """Walk the user through setting up a new profile. Returns the saved name, or None."""
    _header(f"New profile — {purpose}",
            "Stored at ~/.confluence-tool/profiles/<name>.json")

    name = _text(
        "Profile name (e.g. 'prod-cloud', 'dev-server'):",
        default=suggested_name,
        validate=lambda v: True if profiles_mod._NAME_RE.match((v or "").strip())
        else "1-64 chars; letters/digits/_-. only.",
    ).strip()

    if profiles_mod.exists(name):
        if not _confirm(f"Profile '{name}' already exists. Overwrite?", default=False):
            _print("Cancelled.", style="yellow")
            return None

    description = _text("Short description (optional):", default="").strip()
    base_url = _text(
        "Confluence base URL (e.g. https://example.atlassian.net):",
        validate=_validate_url,
    ).strip().rstrip("/")
    username = _text("Username / email:", validate=_nonempty).strip()
    api_token = _password("API token (input hidden):").strip()
    if not api_token:
        _print("API token is required.", style="red")
        return None

    config = profiles_mod.build_config(base_url, username, api_token)

    if _confirm("Test connection now?", default=True):
        _print("Testing connection...", style="yellow")
        try:
            ok = _test_connection(config)
        except Exception as exc:
            _print(f"Connection error: {exc}", style="red")
            ok = False
        if ok:
            _print("Connection OK.", style="green")
        else:
            _print("Connection FAILED.", style="red")
            if not _confirm("Save profile anyway?", default=False):
                return None

    path = profiles_mod.save(name, config, description=description)
    _print(f"Saved profile → {path}", style="green")
    return name


def _pick_profile(
    purpose: str = "Confluence environment",
    allow_skip: bool = False,
    skip_label: str = "(skip)",
) -> Optional[str]:
    """Let the user pick an existing profile or create one. Returns the profile name."""
    existing = profiles_mod.list_profiles()
    choices: List[Tuple[str, Any]] = []
    for name in existing:
        choices.append((profiles_mod.summary(name), ("use", name)))
    choices.append(("➕ Create new profile…", ("new", None)))
    if existing:
        choices.append(("🗑  Delete a profile…", ("delete", None)))
    if allow_skip:
        choices.append((skip_label, ("skip", None)))
    choices.append(("⬅  Back / cancel", ("cancel", None)))

    while True:
        action, value = _select(f"Select {purpose}:", choices)
        if action == "use":
            return value
        if action == "new":
            new_name = _create_profile_interactive(purpose=purpose)
            if new_name:
                return new_name
            # if cancelled, redraw the menu with refreshed choices
            return _pick_profile(purpose, allow_skip=allow_skip, skip_label=skip_label)
        if action == "delete":
            _delete_profile_interactive()
            return _pick_profile(purpose, allow_skip=allow_skip, skip_label=skip_label)
        if action == "skip":
            return None
        if action == "cancel":
            raise KeyboardInterrupt


def _delete_profile_interactive() -> None:
    existing = profiles_mod.list_profiles()
    if not existing:
        _print("No profiles to delete.", style="yellow")
        return
    name = _select(
        "Delete which profile?",
        [(profiles_mod.summary(n), n) for n in existing] + [("⬅  Back", None)],
    )
    if not name:
        return
    if _confirm(f"Really delete '{name}'?", default=False):
        if profiles_mod.delete(name):
            _print(f"Deleted '{name}'.", style="green")


# ---------- profile → live ConfigManager + shared scaffolding ----------

def _config_manager_from_profile(name: str) -> ConfigManager:
    data = profiles_mod.load(name)
    return ConfigManager.from_dict(data["config"], source=f"profile:{name}")


def _summary_table(rows: List[Tuple[str, str]], title: str = "Review") -> None:
    if _console:
        table = Table(title=title, show_header=False, border_style="cyan")
        table.add_column(style="bold")
        table.add_column()
        for k, v in rows:
            table.add_row(k, v)
        _console.print(table)
    else:
        _panel(title, "\n".join(f"{k:<22}{v}" for k, v in rows))


# ---------- action: export ----------

def _wizard_export(ctx) -> None:
    from .main import export as export_cmd  # imported lazily to avoid cycles

    name = _pick_profile("source environment (export FROM)")
    if not name:
        return
    cm = _config_manager_from_profile(name)
    ctx.obj["config"] = cm

    space = _text(
        "Space key to export (leave blank to pick from a list):",
        default="",
    ).strip() or None

    output = _text(
        "Output directory:",
        default=cm.get("export.output_directory", "./exports"),
    ).strip() or None

    _summary_table([
        ("Profile", name),
        ("Confluence URL", cm.get("confluence.base_url", "?")),
        ("Space", space or "(prompt)"),
        ("Output dir", output or cm.get("export.output_directory", "./exports")),
    ], title="Export plan")
    if not _confirm("Run export?", default=True):
        return

    ctx.invoke(export_cmd, space=space, output=output, source_config=None)


# ---------- action: import ----------

def _wizard_import(ctx) -> None:
    from .main import import_ as import_cmd

    export_dir = _text(
        "Path to the export directory to import:",
        validate=lambda v: True if v and Path(v.strip()).exists()
        else "Path does not exist.",
    ).strip()

    name = _pick_profile("target environment (import TO)")
    if not name:
        return
    cm = _config_manager_from_profile(name)
    ctx.obj["config"] = cm

    target_space = _text(
        "Target space key (leave blank to pick / create):",
        default="",
    ).strip() or None

    conflict = _select(
        "Conflict resolution for existing pages:",
        [
            ("skip — leave existing pages alone (safest)", "skip"),
            ("update_newer — overwrite only if source is newer", "update_newer"),
            ("overwrite — replace all existing pages", "overwrite"),
            ("rename — rename imported pages with a timestamp", "rename"),
        ],
        default="skip",
    )

    _summary_table([
        ("Target profile", name),
        ("Target URL", cm.get("confluence.base_url", "?")),
        ("Export dir", export_dir),
        ("Target space", target_space or "(prompt)"),
        ("Conflict mode", conflict),
    ], title="Import plan")
    if not _confirm("Run import?", default=True):
        return

    ctx.invoke(
        import_cmd,
        export_dir=export_dir,
        space=target_space,
        space_name=None,
        create_space=False,
        new_space_key=None,
        conflict_resolution=conflict,
        target_config=None,
        remap_space_key=None,
    )


# ---------- action: sync ----------

def _wizard_sync(ctx) -> None:
    from .main import sync as sync_cmd

    src = _pick_profile("SOURCE environment")
    if not src:
        return
    tgt = _pick_profile("TARGET environment")
    if not tgt:
        return
    if src == tgt:
        if not _confirm("Source and target profiles are identical. Continue?",
                        default=False):
            return

    source_space = _text("Source space key:", validate=_nonempty).strip()
    target_space = _text("Target space key:", validate=_nonempty).strip()
    mode = _select(
        "Sync mode:",
        [
            ("missing_only — copy only pages absent in target (safest)", "missing_only"),
            ("newer_only — also update target pages older than source", "newer_only"),
            ("full — copy missing + update all changed", "full"),
        ],
        default="missing_only",
    )
    dry_run = _confirm("Dry run first (preview, nothing written)?", default=True)

    src_path = _persist_profile_as_yaml(src)
    tgt_path = _persist_profile_as_yaml(tgt)

    _summary_table([
        ("Source profile", src),
        ("Target profile", tgt),
        ("Source space", source_space),
        ("Target space", target_space),
        ("Mode", mode),
        ("Dry run", "yes" if dry_run else "no"),
    ], title="Sync plan")
    if not _confirm("Run sync?", default=True):
        return

    try:
        ctx.invoke(
            sync_cmd,
            source_space=source_space,
            target_space=target_space,
            source_config=src_path,
            target_config=tgt_path,
            mode=mode,
            dry_run=dry_run,
        )
    finally:
        _cleanup_paths([src_path, tgt_path])


# ---------- action: compare ----------

def _wizard_compare(ctx) -> None:
    from .main import compare as compare_cmd

    src = _pick_profile("SOURCE environment")
    if not src:
        return
    tgt = _pick_profile("TARGET environment")
    if not tgt:
        return
    source_space = _text("Source space key:", validate=_nonempty).strip()
    target_space = _text("Target space key:", validate=_nonempty).strip()

    src_path = _persist_profile_as_yaml(src)
    tgt_path = _persist_profile_as_yaml(tgt)
    try:
        ctx.invoke(
            compare_cmd,
            source_space=source_space,
            target_space=target_space,
            source_config=src_path,
            target_config=tgt_path,
            output=None,
        )
    finally:
        _cleanup_paths([src_path, tgt_path])


# ---------- action: list spaces ----------

def _wizard_list_spaces(ctx) -> None:
    from .main import list_spaces as list_cmd

    name = _pick_profile("environment to list spaces from")
    if not name:
        return
    ctx.obj["config"] = _config_manager_from_profile(name)
    ctx.invoke(list_cmd)


# ---------- action: clean space ----------

def _wizard_clean_space(ctx) -> None:
    from .main import clean_space as clean_cmd

    _print(
        "⚠  Clean-space permanently deletes content. Always start with a dry run.",
        style="bold yellow",
    )
    name = _pick_profile("environment containing the space to clean")
    if not name:
        return
    ctx.obj["config"] = _config_manager_from_profile(name)
    space_key = _text("Space key to clean:", validate=_nonempty).strip()
    dry_run = _confirm("Dry run first (preview only)?", default=True)
    ctx.invoke(clean_cmd, space_key=space_key, dry_run=dry_run, target_config=None)


# ---------- action: manage profiles ----------

def _wizard_manage_profiles() -> None:
    while True:
        existing = profiles_mod.list_profiles()
        choices: List[Tuple[str, str]] = [
            ("➕ Create profile", "new"),
            ("👁  View profile", "view") if existing else ("(no profiles yet)", "_none"),
            ("✏  Test profile connection", "test") if existing else ("", "_none"),
            ("🗑  Delete profile", "delete") if existing else ("", "_none"),
            ("⬅  Back", "back"),
        ]
        choices = [c for c in choices if c[0] and c[1] != "_none" or c[1] == "back"
                   or c[1] == "new"]
        action = _select("Profile management:", choices)
        if action == "back":
            return
        if action == "new":
            _create_profile_interactive()
        elif action == "view":
            name = _select("View which profile?",
                           [(profiles_mod.summary(n), n) for n in existing])
            data = profiles_mod.load(name)
            cfg = data["config"]
            _summary_table([
                ("Name", data.get("name", name)),
                ("Description", data.get("description", "") or "(none)"),
                ("Saved at", data.get("saved_at", "?")),
                ("Base URL", cfg["confluence"]["base_url"]),
                ("Username", cfg["confluence"]["auth"]["username"]),
                ("Output dir", cfg.get("export", {}).get("output_directory", "?")),
            ], title=f"Profile: {name}")
        elif action == "test":
            name = _select("Test which profile?",
                           [(profiles_mod.summary(n), n) for n in existing])
            data = profiles_mod.load(name)
            _print("Testing...", style="yellow")
            try:
                ok = _test_connection(data["config"])
                _print("Connection OK." if ok else "Connection failed.",
                       style="green" if ok else "red")
            except Exception as exc:
                _print(f"Error: {exc}", style="red")
        elif action == "delete":
            _delete_profile_interactive()


# ---------- helpers used by sync/compare (need real YAML paths) ----------

def _persist_profile_as_yaml(name: str) -> str:
    """Write a profile to a temp YAML file so it can be passed via --source/target-config.
    Caller is responsible for cleanup via _cleanup_paths().
    """
    import tempfile
    import yaml

    data = profiles_mod.load(name)
    fd, path = tempfile.mkstemp(prefix=f"cf-{name}-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.safe_dump(data["config"], f, sort_keys=False)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def _cleanup_paths(paths: List[str]) -> None:
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


# ---------- top-level entry ----------

def run(ctx) -> None:
    """Main wizard loop. Called from the `wizard` click command."""
    if not _Q_AVAILABLE or not _RICH_AVAILABLE:
        _print(
            "Note: 'rich' and 'questionary' are not installed — falling back to a "
            "plain text wizard. Install them for a nicer experience:\n"
            "    pip install rich questionary",
            style="yellow",
        )

    _header(
        "Confluence Tool — Interactive Wizard",
        "Pick an action; the wizard will prompt for everything else.\n"
        "Profiles are saved at ~/.confluence-tool/profiles/.",
    )

    actions: List[Tuple[str, Any]] = [
        ("📤  Export a space", _wizard_export),
        ("📥  Import a space from an export directory", _wizard_import),
        ("🔄  Sync content between two environments", _wizard_sync),
        ("⚖   Compare two spaces (read-only)", _wizard_compare),
        ("📋  List spaces in an environment", _wizard_list_spaces),
        ("🧹  Clean (delete all content from) a space", _wizard_clean_space),
        ("⚙   Manage saved profiles", "_manage"),
        ("✖   Exit", None),
    ]

    while True:
        try:
            choice = _select("What would you like to do?", actions)
        except KeyboardInterrupt:
            _print("\nGoodbye.", style="dim")
            return

        if choice is None:
            _print("Goodbye.", style="dim")
            return

        try:
            if choice == "_manage":
                _wizard_manage_profiles()
            else:
                choice(ctx)
        except KeyboardInterrupt:
            _print("\n(Cancelled — back to main menu.)", style="yellow")
            continue
        except SystemExit:
            # underlying command called sys.exit; stay in the wizard loop
            _print("\n(Action ended.)", style="dim")
            continue
        except Exception as exc:
            _print(f"\nError: {exc}", style="red")
            continue

        if not _confirm("\nDo something else?", default=True):
            return
