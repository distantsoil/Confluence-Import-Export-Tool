# Confluence → Obsidian Importer

Import a [Confluence Import-Export Tool](https://github.com/distantsoil/Confluence-Import-Export-Tool) export into an [Obsidian](https://obsidian.md) vault.

## Prerequisites

- Python 3.9+
- A Confluence export directory produced by the Confluence Import-Export Tool
- An existing Obsidian vault (or use `--create-vault` to create one)

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Interactive wizard (recommended)

```bash
python -m obsidian_importer
```

The wizard walks through five steps:

1. **Export directory** — point to the export folder (e.g. `./exports/MYSPACE_20240115`)
2. **Vault location** — path to your Obsidian vault
3. **Prior import check** — if a previous import is detected, choose changes-only / full / dry-run
4. **Options** — comments, blog posts, deleted-page handling
5. **Conflict resolution** — per-conflict or bulk strategy when a note was edited locally AND Confluence was updated

### Flag-based / scripting

```bash
python -m obsidian_importer \
  --export-dir ./exports/MYSPACE_20240115 \
  --vault-dir  /path/to/vault \
  --space-path "Confluence/MYSPACE" \
  --mode       changes-only \
  --deleted    archive \
  --conflict-resolution keep-confluence \
  --yes
```

| Flag | Values | Default |
|------|--------|---------|
| `--export-dir` | path | (prompted) |
| `--vault-dir` | path | (prompted) |
| `--space-path` | folder path inside vault | `Confluence/<SPACE_KEY>` |
| `--mode` | `changes-only` `full` `dry-run` | (prompted) |
| `--include-comments` / `--no-comments` | | no |
| `--include-blogposts` / `--no-blogposts` | | yes |
| `--deleted` | `skip` `delete` `archive` | (prompted) |
| `--conflict-resolution` | `ask` `keep-local` `keep-confluence` `keep-both` | (prompted) |
| `--create-vault` | flag | off |
| `--yes` / `-y` | flag | off — skip all prompts |
| `--verbose` | flag | off |

## Vault structure

All content lands in a scoped sub-folder so your existing notes are never touched:

```
<vault>/
└── Confluence/
    └── MYSPACE/
        ├── .confluence_import_state.json   ← tracks import state
        ├── import_report.md                ← summary of last import
        ├── _attachments/                   ← all downloaded files
        ├── Blog/                           ← blog posts
        └── … (page hierarchy as folders)
```

Pages that have child pages become `FolderName/index.md`.

## Re-import / diff-merge

Run the same command again with a newer export directory. The tool reads the
state file and only writes what changed:

| Condition | Action |
|-----------|--------|
| New page | Added |
| Confluence version increased | Updated |
| Same version, note unedited | Skipped |
| Confluence updated AND note edited locally | **Conflict** — prompted |
| Page missing from new export | Controlled by `--deleted` |

## Known limitations

| Limitation | Detail |
|------------|--------|
| **Confluence macros** | Jira queries, roadmaps, status badges, expand blocks, custom plugins are replaced with an Obsidian `[!warning]` callout |
| **Database content** | Not exported by the source tool — nothing to import |
| **Inline comments** | Not included in the HTML export |
| **Page version history** | Only the latest version is exported |
| **Complex tables** | Column spans may lose formatting (data is preserved) |
| **Multi-column layouts** | Collapse to single column |
| **Custom CSS / colours** | Stripped |
| **Folder hierarchy** | Cloud-only; Server/Data Center exports use page-parent relationships only |
| **Blog post semantics** | Blog posts become regular notes in `Blog/` |
