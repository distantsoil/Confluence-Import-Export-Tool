"""Confluence → Obsidian Importer — interactive wizard CLI.

Usage (wizard mode):
    python -m obsidian_importer

Usage (flag mode / scripting):
    python -m obsidian_importer --export-dir ./exports/MYSPACE --vault-dir ~/vault --yes
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import click
from colorama import Fore, Style, init as colorama_init
from tqdm import tqdm

try:
    import questionary
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False

from . import __version__
from .attachment_handler import build_attachment_name_map, copy_attachments
from .converter import convert_comments_html, html_to_markdown
from .diff_merge import (
    ChangeKind,
    PageChange,
    apply_conflict_resolution,
    compute_changes,
    summarise,
)
from .frontmatter import build_frontmatter
from .hierarchy import PageNode, find_comments_file, find_html_file, load_export_hierarchy
from .link_rewriter import LinkRewriter, rewrite_attachment_refs
from .state import ImportState, PageState, load_state, save_state
from .utils import content_hash, ensure_dir, sanitize_filename

colorama_init(autoreset=True)
log = logging.getLogger(__name__)


# ── Banner ────────────────────────────────────────────────────────────────────

BANNER = f"""{Fore.CYAN}
╔══════════════════════════════════════════════════╗
║    Confluence → Obsidian Importer  v{__version__:<12}  ║
╚══════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


# ── CLI entry point ───────────────────────────────────────────────────────────

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--export-dir", "-e", type=click.Path(), default=None,
              help="Path to the Confluence export folder.")
@click.option("--vault-dir", "-v", type=click.Path(), default=None,
              help="Path to your Obsidian vault.")
@click.option("--space-path", default=None,
              help="Import sub-folder inside vault (default: Confluence/<SPACE_KEY>).")
@click.option("--mode", type=click.Choice(["changes-only", "full", "dry-run"]),
              default=None, help="Import mode (skips wizard step 3).")
@click.option("--include-comments/--no-comments", default=None,
              help="Append comments to imported pages.")
@click.option("--include-blogposts/--no-blogposts", default=True,
              help="Import blog posts into a Blog/ folder.")
@click.option("--deleted",
              type=click.Choice(["skip", "delete", "archive"]), default=None,
              help="How to handle pages removed from the export.")
@click.option("--conflict-resolution", "-c",
              type=click.Choice(["ask", "keep-local", "keep-confluence", "keep-both"]),
              default=None, help="Conflict resolution strategy.")
@click.option("--create-vault", is_flag=True, default=False,
              help="Create the vault directory if it does not exist.")
@click.option("--yes", "-y", is_flag=True, default=False,
              help="Skip all confirmation prompts.")
@click.option("--verbose", is_flag=True, default=False)
def cli(
    export_dir, vault_dir, space_path, mode, include_comments, include_blogposts,
    deleted, conflict_resolution, create_vault, yes, verbose,
):
    """Import a Confluence space export into an Obsidian vault."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    click.echo(BANNER)

    # ── Step 1: Export directory ──────────────────────────────────────────────
    _print_step(1, 5, "Export directory")
    export_path = _resolve_export_dir(export_dir, yes)

    space_key, page_count, blog_count = _probe_export(export_path)
    _ok(f"Found space {Fore.YELLOW}{space_key}{Style.RESET_ALL} — "
        f"{page_count} pages, {blog_count} blog posts")

    # ── Step 2: Vault location ────────────────────────────────────────────────
    _print_step(2, 5, "Vault location")
    vault_path = _resolve_vault_dir(vault_dir, create_vault, yes)

    default_space_path = f"Confluence/{space_key}"
    if space_path is None:
        if yes or not _HAS_QUESTIONARY:
            space_path = default_space_path
        else:
            space_path = questionary.text(
                "Import folder inside vault:",
                default=default_space_path,
            ).ask() or default_space_path

    space_dir = vault_path / Path(space_path)
    _ok(f"Target: {Fore.YELLOW}{space_dir}{Style.RESET_ALL}")

    # ── Step 3: Detect prior import ───────────────────────────────────────────
    _print_step(3, 5, "Checking for prior import")
    existing_state = load_state(space_dir)

    if existing_state:
        _info(f"Last imported: {existing_state.last_import_utc[:10]}")
        if mode is None:
            mode = _ask_mode(yes)
    else:
        _info("No prior import found — performing fresh import")
        if mode is None:
            mode = "full"

    dry_run = mode == "dry-run"

    # ── Build hierarchy ───────────────────────────────────────────────────────
    _info("Scanning export…")
    nodes = load_export_hierarchy(export_path, space_path)
    if not include_blogposts:
        nodes = {pid: n for pid, n in nodes.items() if not n.is_blog}

    # ── Step 4: Options ───────────────────────────────────────────────────────
    _print_step(4, 5, "Options")
    include_comments, deleted = _ask_options(include_comments, deleted, yes)

    # ── Compute change list ───────────────────────────────────────────────────
    state_for_diff = existing_state if mode == "changes-only" else None
    changes = compute_changes(nodes, state_for_diff, vault_path)

    summary = summarise(changes)
    if existing_state and mode == "changes-only":
        _info(
            f"  {Fore.GREEN}+{summary['NEW']} new{Style.RESET_ALL}  "
            f"  {Fore.YELLOW}~{summary['UPDATED']} updated{Style.RESET_ALL}  "
            f"  {Fore.RED}-{summary['DELETED']} removed{Style.RESET_ALL}  "
            f"  {Fore.WHITE}={summary['UNCHANGED']} unchanged{Style.RESET_ALL}"
        )

    # ── Step 5: Conflict resolution ───────────────────────────────────────────
    conflicts = [c for c in changes if c.kind == ChangeKind.CONFLICT]
    if conflicts:
        _print_step(5, 5, f"Conflict resolution ({len(conflicts)} conflicts)")
        changes = _resolve_conflicts(changes, conflict_resolution, vault_path, yes)
    else:
        _print_step(5, 5, "Conflict resolution — none found")

    # ── Pre-flight summary ────────────────────────────────────────────────────
    to_write = [
        c for c in changes
        if c.kind in (ChangeKind.NEW, ChangeKind.UPDATED)
        or (c.kind == ChangeKind.CONFLICT and c.conflict_resolution in ("keep-confluence", "keep-both"))
    ]
    to_delete = [c for c in changes if c.kind == ChangeKind.DELETED]

    click.echo(f"\n{'─'*50}")
    click.echo(f"  Ready to import:")
    click.echo(f"    {Fore.GREEN}+ {summary['NEW']} pages to add{Style.RESET_ALL}")
    click.echo(f"    {Fore.YELLOW}~ {summary['UPDATED']} pages to update{Style.RESET_ALL}")
    click.echo(f"    {Fore.WHITE}= {summary['UNCHANGED']} pages unchanged{Style.RESET_ALL}")
    if conflicts:
        click.echo(f"    {Fore.RED}! {len(conflicts)} conflicts to resolve{Style.RESET_ALL}")
    if dry_run:
        click.echo(f"\n  {Fore.CYAN}DRY RUN — no files will be written{Style.RESET_ALL}")

    if not yes and not dry_run:
        if _HAS_QUESTIONARY:
            ok = questionary.confirm("Proceed?", default=True).ask()
        else:
            ok = click.confirm("Proceed?", default=True)
        if not ok:
            click.echo("Aborted.")
            sys.exit(0)

    click.echo(f"{'─'*50}\n")

    if dry_run:
        _print_dry_run_report(changes, to_delete, deleted)
        return

    # ── Execute import ────────────────────────────────────────────────────────
    id_to_vault_path = {pid: n.vault_path for pid, n in nodes.items()}
    rewriter = LinkRewriter(id_to_vault_path)
    att_name_map = build_attachment_name_map(export_path, nodes)

    attachments_dir = space_dir / "_attachments"
    new_state = ImportState(
        space_key=space_key,
        last_import_utc=datetime.now(timezone.utc).isoformat(),
        source_export_dir=str(export_path),
        pages=dict(existing_state.pages) if existing_state else {},
    )

    report_lines: List[str] = [f"# Import Report — {space_key}\n",
                                f"Date: {new_state.last_import_utc[:10]}\n\n"]
    macro_warnings: List[str] = []

    written = skipped = updated = 0

    with tqdm(total=len(to_write), unit="page", desc="Importing pages") as pbar:
        for change in to_write:
            node = change.node
            dest_path = vault_path / node.vault_path

            md_content = _build_markdown(
                export_path, node, space_key, rewriter, att_name_map,
                include_comments, macro_warnings,
            )
            if md_content is None:
                skipped += 1
                pbar.update(1)
                continue

            # For keep-both conflicts write a secondary copy
            if change.kind == ChangeKind.CONFLICT and change.conflict_resolution == "keep-both":
                stem = dest_path.stem
                alt_path = dest_path.parent / f"{stem} (Confluence).md"
                _write_file(alt_path, md_content)
            else:
                ensure_dir(dest_path.parent)
                _write_file(dest_path, md_content)

            ver_num = _version_number(node.metadata)
            new_state.upsert_page(
                node.page_id,
                PageState(
                    vault_path=node.vault_path,
                    confluence_version=ver_num,
                    confluence_modified=_modified_date(node.metadata),
                    content_hash=content_hash(md_content),
                ),
            )

            if change.kind == ChangeKind.NEW:
                written += 1
                report_lines.append(f"- Added: {node.vault_path}\n")
            else:
                updated += 1
                report_lines.append(f"- Updated: {node.vault_path}\n")
            pbar.update(1)

    # Handle deleted pages
    _handle_deleted(to_delete, vault_path, deleted, new_state, report_lines)

    # Copy attachments
    att_copied = copy_attachments(export_path, nodes, attachments_dir)

    # Save state
    ensure_dir(space_dir)
    save_state(space_dir, new_state)

    # Write report
    if macro_warnings:
        report_lines.append("\n## Macro Warnings\n\n")
        for w in macro_warnings:
            report_lines.append(f"- {w}\n")

    report_path = space_dir / "import_report.md"
    report_path.write_text("".join(report_lines), encoding="utf-8")

    # ── Done ──────────────────────────────────────────────────────────────────
    click.echo(f"\n  {Fore.GREEN}Added:    {written} pages{Style.RESET_ALL}")
    click.echo(f"  {Fore.YELLOW}Updated:  {updated} pages{Style.RESET_ALL}")
    click.echo(f"  {Fore.WHITE}Skipped:  {skipped} pages{Style.RESET_ALL}")
    click.echo(f"  {Fore.CYAN}Attachments synced: {att_copied}{Style.RESET_ALL}")
    if macro_warnings:
        click.echo(f"  {Fore.YELLOW}Macro warnings: {len(macro_warnings)}{Style.RESET_ALL}")
    click.echo(
        f"\n{Fore.GREEN}Done.{Style.RESET_ALL} Open your vault in Obsidian to review."
    )
    click.echo(f"  Import report → {report_path}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_step(n: int, total: int, label: str) -> None:
    click.echo(f"\n{Fore.CYAN}Step {n} of {total}{Style.RESET_ALL} — {label}")


def _ok(msg: str) -> None:
    click.echo(f"  {Fore.GREEN}✔{Style.RESET_ALL} {msg}")


def _info(msg: str) -> None:
    click.echo(f"  {msg}")


def _warn(msg: str) -> None:
    click.echo(f"  {Fore.YELLOW}⚠{Style.RESET_ALL} {msg}")


def _resolve_export_dir(export_dir: Optional[str], yes: bool) -> Path:
    if export_dir:
        p = Path(export_dir)
    elif yes or not _HAS_QUESTIONARY:
        click.echo(f"  {Fore.RED}--export-dir is required in non-interactive mode.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        raw = questionary.path("Path to Confluence export folder:").ask()
        if not raw:
            sys.exit(1)
        p = Path(raw)

    if not p.exists() or not p.is_dir():
        click.echo(f"  {Fore.RED}Export directory not found: {p}{Style.RESET_ALL}")
        sys.exit(1)
    return p.resolve()


def _resolve_vault_dir(vault_dir: Optional[str], create_vault: bool, yes: bool) -> Path:
    if vault_dir:
        p = Path(vault_dir)
    elif yes or not _HAS_QUESTIONARY:
        click.echo(f"  {Fore.RED}--vault-dir is required in non-interactive mode.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        raw = questionary.path("Path to your Obsidian vault:").ask()
        if not raw:
            sys.exit(1)
        p = Path(raw)

    if not p.exists():
        if create_vault:
            ensure_dir(p)
            _ok(f"Created new vault at {p}")
        else:
            click.echo(f"  {Fore.RED}Vault directory not found: {p}{Style.RESET_ALL}")
            click.echo("  Use --create-vault to create it.")
            sys.exit(1)
    else:
        note_count = sum(1 for _ in p.rglob("*.md"))
        _ok(f"Existing vault detected ({note_count:,} notes)")
    return p.resolve()


def _probe_export(export_path: Path):
    """Return (space_key, page_count, blog_count) from the export directory."""
    space_key = "UNKNOWN"
    meta_file = export_path / "metadata" / "space_info.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as fh:
                info = json.load(fh)
            space_key = info.get("key", info.get("spaceKey", export_path.name.split("_")[0]))
        except Exception:
            space_key = export_path.name.split("_")[0]
    else:
        space_key = export_path.name.split("_")[0]

    page_count = sum(1 for _ in (export_path / "pages").glob("*_metadata.json")) \
        if (export_path / "pages").exists() else 0
    blog_count = sum(1 for _ in (export_path / "blogposts").glob("*_metadata.json")) \
        if (export_path / "blogposts").exists() else 0

    return space_key, page_count, blog_count


def _ask_mode(yes: bool) -> str:
    if yes or not _HAS_QUESTIONARY:
        return "changes-only"
    choice = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice("Import changes only (recommended)", value="changes-only"),
            questionary.Choice("Full re-import (overwrite all)", value="full"),
            questionary.Choice("Dry run — show changes without writing", value="dry-run"),
        ],
    ).ask()
    return choice or "changes-only"


def _ask_options(include_comments, deleted, yes):
    if yes or not _HAS_QUESTIONARY:
        if include_comments is None:
            include_comments = False
        if deleted is None:
            deleted = "skip"
        return include_comments, deleted

    if include_comments is None:
        include_comments = questionary.confirm("Include page comments?", default=False).ask()

    if deleted is None:
        deleted = questionary.select(
            "Pages removed from export?",
            choices=[
                questionary.Choice("Skip (leave existing notes untouched)", value="skip"),
                questionary.Choice("Move to _archive/ folder", value="archive"),
                questionary.Choice("Delete from vault", value="delete"),
            ],
        ).ask() or "skip"

    return include_comments, deleted


def _resolve_conflicts(
    changes: List[PageChange],
    conflict_resolution: Optional[str],
    vault_path: Path,
    yes: bool,
) -> List[PageChange]:
    conflicts = [c for c in changes if c.kind == ChangeKind.CONFLICT]

    if conflict_resolution and conflict_resolution != "ask":
        return apply_conflict_resolution(changes, conflict_resolution)

    if yes or not _HAS_QUESTIONARY:
        return apply_conflict_resolution(changes, "keep-confluence")

    choices = [
        questionary.Choice("Keep Confluence version (overwrite local edits)", value="keep-confluence"),
        questionary.Choice("Keep local version (skip this page)", value="keep-local"),
        questionary.Choice("Keep both (save Confluence copy alongside)", value="keep-both"),
        questionary.Choice("Apply same choice to ALL remaining conflicts", value=None),
    ]

    bulk: Optional[str] = None
    for change in conflicts:
        if bulk:
            change.conflict_resolution = bulk
            continue

        node = change.node
        old = change.old_state
        local_path = vault_path / old.vault_path if old else None
        local_mtime = ""
        if local_path and local_path.exists():
            import time
            local_mtime = time.strftime(
                "%Y-%m-%d", time.localtime(local_path.stat().st_mtime)
            )

        click.echo(f"\n  {Fore.YELLOW}Conflict:{Style.RESET_ALL} {node.title}")
        if local_mtime:
            click.echo(f"    Local change: {local_mtime}  |  "
                       f"Confluence update: {_modified_date(node.metadata)[:10]}")

        resolution = questionary.select(
            "How to resolve?",
            choices=choices,
        ).ask()

        if resolution is None:
            # User chose "apply to all"
            bulk = questionary.select(
                "Apply to all remaining conflicts:",
                choices=[c for c in choices if c.value],
            ).ask()
            change.conflict_resolution = bulk
        else:
            change.conflict_resolution = resolution

    return changes


def _build_markdown(
    export_path: Path,
    node: PageNode,
    space_key: str,
    rewriter: LinkRewriter,
    att_name_map: Dict[str, str],
    include_comments: bool,
    macro_warnings: List[str],
) -> Optional[str]:
    html_file = find_html_file(export_path, node)
    if html_file is None:
        log.warning("No HTML file for %s (%s)", node.title, node.page_id)
        return None

    html = html_file.read_text(encoding="utf-8", errors="replace")
    body_md = html_to_markdown(html, page_title=node.title)

    # Rewrite links and attachment refs
    body_md = rewriter.rewrite(body_md)
    body_md = rewrite_attachment_refs(body_md, "_attachments")

    # Fix attachment filenames using the de-duplication map
    for orig, dest in att_name_map.items():
        if orig != dest:
            body_md = body_md.replace(f"![[{orig}]]", f"![[{dest}]]")
            body_md = body_md.replace(f"[[{orig}]]", f"[[{dest}]]")

    # Detect unsupported macro residue
    if "[!warning] Unsupported macro" in body_md or "ac:structured-macro" in body_md:
        macro_warnings.append(node.title)

    fm = build_frontmatter(node.metadata, space_key=space_key)

    comments_md = ""
    if include_comments:
        cf = find_comments_file(export_path, node)
        if cf:
            comments_html = cf.read_text(encoding="utf-8", errors="replace")
            comments_md = convert_comments_html(comments_html)

    return fm + body_md + comments_md


def _write_file(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def _handle_deleted(
    deleted_changes: List[PageChange],
    vault_path: Path,
    strategy: str,
    state: ImportState,
    report_lines: List[str],
) -> None:
    if not deleted_changes:
        return

    archive_dir = vault_path / "_archive"
    if strategy == "archive":
        ensure_dir(archive_dir)

    for change in deleted_changes:
        if not change.old_state:
            continue
        local_path = vault_path / change.old_state.vault_path
        if not local_path.exists():
            state.remove_page(change.page_id)
            continue

        if strategy == "delete":
            local_path.unlink()
            state.remove_page(change.page_id)
            report_lines.append(f"- Deleted: {change.old_state.vault_path}\n")
        elif strategy == "archive":
            dest = archive_dir / local_path.name
            local_path.rename(dest)
            state.remove_page(change.page_id)
            report_lines.append(f"- Archived: {change.old_state.vault_path}\n")
        else:
            report_lines.append(f"- Skipped (removed from export): {change.old_state.vault_path}\n")


def _version_number(metadata: dict) -> int:
    v = metadata.get("version", {})
    if isinstance(v, dict):
        return int(v.get("number", 0))
    if isinstance(v, int):
        return v
    return 0


def _modified_date(metadata: dict) -> str:
    v = metadata.get("version", {})
    if isinstance(v, dict):
        when = v.get("when", "")
        if when:
            return str(when)
    return ""


def _print_dry_run_report(changes: List[PageChange], to_delete, deleted_strategy) -> None:
    click.echo(f"\n{Fore.CYAN}Dry run results:{Style.RESET_ALL}")
    for c in changes:
        if c.kind == ChangeKind.NEW:
            click.echo(f"  {Fore.GREEN}+ (new)      {c.node.vault_path}{Style.RESET_ALL}")
        elif c.kind == ChangeKind.UPDATED:
            click.echo(f"  {Fore.YELLOW}~ (update)   {c.node.vault_path}{Style.RESET_ALL}")
        elif c.kind == ChangeKind.CONFLICT:
            res = c.conflict_resolution or "?"
            click.echo(f"  {Fore.RED}! (conflict/{res}) {c.node.vault_path}{Style.RESET_ALL}")
    for c in to_delete:
        click.echo(f"  {Fore.RED}- ({deleted_strategy}) {c.old_state.vault_path}{Style.RESET_ALL}")
