# Confluence Export-Import Tool

A comprehensive Python tool for exporting and importing Confluence spaces using the Confluence REST API. This tool is designed to be robust, user-friendly, and cross-platform compatible.

> [!IMPORTANT]
> ## Upated February 21, 2026 - Now supports folders!
> - A performance update is the next major milestone to hit and will be in progress soon

> [!NOTE]
> ## :question: About this project 
> ### Why did I make this?
> Confluence allows you to import a space natively, but it doesn't allow you to alter the space key while or before you import. If you have conflcting spaces, you're stuck. It also doesn't update links quite as well as I had hoped. 
>
> ### How did you test this?
> I've been a long time lover and user of confluence, so I was able to test with my own space, and a trial space I spun up. My own space is my own personal 'second brain'. Most people now use Notion, but after being in Confluence so long I found it difficult to adapt. 
>
> ### How much AI is used?
> Less than you think. I'm not an expert with Python by any means, so I got 70-80% of the way there and used a combination of GitHub CoPilot, Claude, and ChatGPT Codex as an aid. It also made this README file, because it's better at structuring that information than I am. This wasn't vibe coded, but it was an assistive tool.
>
> ### Does your company use Confluence? and why am I pointing this out?
> Yes, the company I work for uses Confluence and so have past employers. Part of the motiviation for me writing this was a problem I saw emerging with multiple Confluence spaces that shared the same keys that might need to be consolidated. 
>
> However I did not **ever** connect to or test this tool with any of the company systems, or using company technology. This is strictly a personal initiative.
>
> You should never use this tool without **explicit** authorization from your IT team and show them this page so they understand its capabilities. 

> [!TIP]
> ## :coffee: If you like this project...
> If you found the efforts I've gone to useful, tried it and liked it, or just like what I'm doing I'd appreciate your support by [buying me a coffee](https://ko-fi.com/distantsoil)

> [!WARNING]
> ### Use of AI Disclaimer
> Portions of this project were generated, corrected, or refined with the assistance of Artificial Intelligence (AI) tools.
> AI was also used to improve presentation and documentation.
>
> While the resulting code has been reviewed and tested in a production environment, AI-assisted outputs may introduce unintended behaviors or edge cases.
> - Use **caution** in critical or sensitive environments.
> - **Independently validate and review** for security, compliance, and fitness for purpose.
> - No warranty or guarantee is provided regarding accuracy, safety, or reliability.

> [!IMPORTANT]
> ### Security & Responsible Use Disclaimer
> This tool is intended to help administrators **back up and restore Confluence spaces** (e.g., preparing a test environment or creating a migration copy).
>
> 🚫 **Not an official app:** This project is **not an Atlassian/Confluence app** and is not sanctioned, endorsed, or supported by Atlassian.
>
> ⚠️ Improper use could lead to **unauthorized data access or disclosure**, **policy/compliance violations**, or **data loss**.
> Only use with **prior approval** from your IT/Security team or relevant stakeholders, and limit actions to **authorized spaces and accounts**.

## 🚀 Features

- **Complete Space Export**: Export entire Confluence spaces including pages, attachments, comments, and metadata
- **Intelligent Import**: Import spaces with conflict resolution and hierarchy preservation
- **Space Cleanup**: Delete all pages from a space with multiple safety confirmations (useful for retry scenarios)
- **Complete Space Export**: Export entire Confluence spaces including pages, folders (Cloud only), attachments, comments, and metadata
- **Intelligent Import**: Import spaces with conflict resolution and hierarchy preservation (including folders)
- **Space Key Remapping**: Automatically rewrite all internal space references when importing to a different space key (useful for Confluence Cloud bugs, backup/restore, and migrations)
- **Multi-Environment Support**: Export from one Confluence instance and import to another with separate configurations
- **Content Synchronization**: Keep spaces synchronized between different environments with missing/newer/full sync modes
- **Space Comparison**: Compare spaces across different Confluence instances with detailed reports
- **Auto-Detection**: Automatically detects Confluence Cloud vs Server/Data Center and uses the correct API paths
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Beginner-Friendly**: Comprehensive documentation and guided setup for users new to APIs and Python
- **Robust Error Handling**: Comprehensive error handling with detailed logging and progress tracking
- **Flexible Configuration**: Central YAML configuration file with extensive customization options
- **Interactive Selection**: Easy-to-use prompts for selecting spaces
- **Progress Tracking**: Real-time progress bars and detailed summary reports

## 📋 Requirements

- Python 3.7 or higher
- Internet connection
- Valid Confluence account with appropriate permissions
- API token or password for authentication

> **Note for Confluence Cloud Free Plan Users:**  
> Confluence Free plans are limited to **one space only**. If you need to create additional spaces for imports, you'll need to:
> - Upgrade to a paid Confluence plan, or
> - Start a free trial of a paid plan, or
> - Manually create the space in Confluence first, then import to the existing space
>
> When importing to a Free plan instance with an existing space, you can still import by specifying the existing space key with `--space SPACEKEY`.

## 🔧 Installation

### Quick Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
   cd Confluence-Export-Import-Tool
   ```

2. **Run the quick start script** (recommended for beginners):
   
   **macOS/Linux:**
   ```bash
   python3 quickstart.py
   ```
   
   **Windows:**
   ```cmd
   python quickstart.py
   ```
   
   > **Note:** The quickstart script must be run from the repository root directory (Confluence-Export-Import-Tool).
   > It will automatically install dependencies and guide you through the setup process.

3. **Or install manually**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Using a Virtual Environment** (recommended for advanced users):
   
   **macOS/Linux:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```
   
   **Windows:**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

For detailed installation instructions, see the **[Installation Guide](INSTALL.md)**.

## ⚠️ Important Notes

- **Directory:** Always run `quickstart.py` from the repository root directory (`Confluence-Export-Import-Tool/`)
- **macOS/Linux:** Use `python3` command, not `python`
- **Virtual Environments:** If you create a virtual environment, remember to activate it before running commands
- **First Time Setup:** The quickstart script is the easiest way to get started

### Running Commands

After running `pip install -e .`, you have two options for running commands:

**Option 1: Direct command (if in PATH)**
```bash
confluence-tool list-spaces
```

**Option 2: Python module (always works)**
```bash
# macOS/Linux
python3 -m confluence_tool.main list-spaces

# Windows
python -m confluence_tool.main list-spaces
```

If `confluence-tool` is not found, your Python scripts directory may not be in your PATH. Use the `python3 -m confluence_tool.main` method instead - it always works regardless of PATH configuration.

## 📖 Documentation

- **[Installation Guide](INSTALL.md)** - Detailed installation instructions for all platforms
- **[Usage Examples](EXAMPLES.md)** - Real-world examples and advanced configurations
- **[Multi-Environment Guide](MULTI_ENVIRONMENT.md)** - Cross-environment export/import and synchronization
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Solutions to common problems
- **Quick Start Script** - Run `python3 quickstart.py` (macOS/Linux) or `python quickstart.py` (Windows) for interactive setup

## 🎯 Quick Start Guide

### Step 1: Create Configuration

First, create a configuration file:

```bash
confluence-tool config create
```

This creates a `config.yaml` file in your current directory.

### Step 2: Configure Your Settings

Edit the `config.yaml` file with your Confluence details:

```yaml
confluence:
  base_url: "https://yourcompany.atlassian.net"
  auth:
    username: "your-email@example.com"
    api_token: "your-api-token-here"
```

**🔑 Getting an API Token (Recommended):**

For Atlassian Cloud instances (e.g., yourcompany.atlassian.net):
1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Enter a label (e.g., "Confluence Tool")
4. Copy the generated token to your config file

**Note:** The tool automatically detects Confluence Cloud instances (*.atlassian.net) and uses the correct API endpoints. No additional configuration needed!

For self-hosted Server/Data Center instances, you may use your username and password instead of an API token.

### Step 3: Test Your Configuration

Verify your setup works:

```bash
confluence-tool config validate
```

### Step 4: Export or Import

**Export a space:**
```bash
# Interactive export (will prompt you to select a space)
confluence-tool export

# Export specific space
confluence-tool export --space MYSPACE

# Export to custom directory (useful for large spaces)
confluence-tool export --space MYSPACE --output /path/to/custom/directory
```

**Import a space:**
```bash
# Basic import to existing space (with interactive prompt for target environment)
confluence-tool import /path/to/export/directory

# Import and rename the target space
confluence-tool import /path/to/export --space MYSPACE --space-name "New Space Name"

# Import to a newly created space
confluence-tool import /path/to/export --create-space --new-space-key NEWKEY --space-name "My New Space"

# Import with conflict resolution options
confluence-tool import /path/to/export --conflict-resolution overwrite     # Replace all
confluence-tool import /path/to/export --conflict-resolution update_newer  # Update only newer
confluence-tool import /path/to/export --conflict-resolution skip          # Skip existing (default)
confluence-tool import /path/to/export --conflict-resolution rename        # Rename with timestamp

# Import with space key remapping (rewrite all internal space references)
confluence-tool import /path/to/export --remap-space-key KB:KB2 \
  --create-space --new-space-key KB2 --space-name "Knowledge Base Copy"
```

**Space Key Remapping:**

The `--remap-space-key` feature automatically rewrites all internal space references during import. This is useful for:
- **Confluence Cloud Bug**: Workaround for deleted space keys that cannot be recreated
- **Backup/Restore**: Create space copies with different keys on the same instance  
- **Migration**: Consolidate spaces from multiple instances with key conflicts
- **Testing**: Create test copies with different keys while maintaining link integrity

Example:
```bash
# Workaround for Confluence Cloud space key retention
confluence-tool import ./exports/KB_20251002 --remap-space-key KB:KB2 \
  --create-space --new-space-key KB2 --space-name "Knowledge Base"
```

The tool automatically rewrites:
- Confluence XML links (`<ri:space-key>`)
- Wiki links (`[Title|SPACE:Page]`)
- HTML anchors (`/wiki/spaces/SPACE/...`)
- Macro space parameters
- Attachment references

⚠️ Note: Remapping increases import time (~2-3x) as all content must be scanned and rewritten.

**Interactive Multi-Environment Import:**

When running import without `--target-config`, the tool will ask if you want to import to a different Confluence environment. This makes it easy to:
- Import to a different tenant (different URL, API key, user)
- Restore backups to a different instance
- Move content between development, staging, and production

The tool will guide you through creating or selecting a target configuration.

**Conflict Resolution Modes:**
- `skip` - Skip existing pages (default, safest option)
- `overwrite` - Replace all existing pages with imported versions
- `update_newer` - Update only if the imported page is newer than the existing one
- `rename` - Keep existing page and rename the imported one with timestamp

**Multi-environment operations:**
```bash
# Export from production environment
confluence-tool export --source-config prod-config.yaml --space MYSPACE

# Import to staging environment (using existing config)
confluence-tool import /path/to/export --target-config staging-config.yaml --space MYSPACE

# Import to staging environment (interactive setup)
confluence-tool import /path/to/export
# Tool will prompt to create or use target-config.yaml

# Sync content between environments
confluence-tool sync --source-config prod-config.yaml --target-config staging-config.yaml --source-space DOCS --target-space DOCS-BACKUP

# Compare spaces across environments
confluence-tool compare --source-config prod-config.yaml --target-config staging-config.yaml --source-space DOCS --target-space DOCS
```

The tool will prompt you to select spaces if not specified.

## 📖 Detailed Usage

### Configuration File

The tool uses a YAML configuration file with the following structure:

```yaml
# Confluence connection settings
confluence:
  base_url: "https://your-domain.atlassian.net"
  auth:
    username: "your-email@example.com"
    api_token: "your-api-token"  # Recommended
    password: "your-password"    # Alternative (less secure)

# Export settings
export:
  output_directory: "./exports"
  format:
    html: true          # Export as HTML files
    attachments: true   # Include attachments
    comments: true      # Include comments
    versions: false     # Include page history
  naming:
    include_space_key: true
    include_page_id: false
    sanitize_names: true

# Import settings
import:
  conflict_resolution: "skip"  # Options: skip, overwrite, rename
  create_missing_parents: true
  preserve_page_ids: false
  import_attachments: true
  import_comments: true

# General settings
general:
  verbose: false
  max_workers: 5      # Concurrent operations
  timeout: 30         # Request timeout (seconds)
  rate_limit: 10      # Requests per second

# Logging
logging:
  level: "INFO"       # DEBUG, INFO, WARNING, ERROR
  file: ""            # Optional log file path
```

### Command Reference

#### Configuration Commands

```bash
# Create sample configuration
confluence-tool config create [path]

# Validate configuration and test connection
confluence-tool config validate
```

#### Export Commands

```bash
# Export with space selection prompt
confluence-tool export

# Export specific space
confluence-tool export --space SPACEKEY

# Export to specific directory
confluence-tool export --output /path/to/exports

# Export with verbose logging
confluence-tool export --verbose
```

#### Import Commands

```bash
# Import with space selection prompt
confluence-tool import /path/to/export

# Import to specific space
confluence-tool import /path/to/export --space TARGETSPACE

# Import with verbose logging
confluence-tool import /path/to/export --verbose
```

#### Utility Commands

```bash
# List all available spaces
confluence-tool list-spaces

# Show beginner's guide
confluence-tool help-guide

# Clean a space (delete all pages) - useful for retry scenarios
# CAUTION: This is destructive! Use with extreme care
confluence-tool clean-space SPACE_KEY --dry-run              # Preview what would be deleted
confluence-tool clean-space SPACE_KEY                        # Actually delete (requires confirmation)
confluence-tool clean-space SPACE_KEY --target-config prod-config.yaml  # Use specific config

# Show help for any command
confluence-tool [command] --help
```

**Using clean-space command:**

The `clean-space` command is designed for scenarios where an import fails partway through (e.g., due to attachment errors) and you need to clean the space before retrying, rather than manually deleting hundreds of pages.

**Options:**
- `--dry-run`: Preview what would be deleted without actually deleting
- `--target-config` / `-t`: Path to target environment configuration file (useful for multi-environment setups)

**Safety Features:**
- Multiple confirmation prompts with strong warnings
- Requires typing "I CONFIRM" to proceed
- `--dry-run` flag to preview what would be deleted without actually deleting
- Progress tracking with detailed summary report
- Proper error handling for API failures

**Example workflow:**
```bash
# 1. First, preview what would be deleted
confluence-tool clean-space KB --dry-run

# 2. If you're sure, run without --dry-run
confluence-tool clean-space KB

# 3. For multi-environment, specify target config
confluence-tool clean-space KB --target-config staging-config.yaml

# The tool will:
# - Show all pages that will be deleted
# - Ask for confirmation twice
# - Require you to type "I CONFIRM"
# - Show progress bar during deletion
# - Provide a detailed summary at the end
```

⚠️ **Warning:** This operation cannot be undone! Make sure you have a backup if needed.

## 📁 Export Structure

The tool creates the following directory structure for exports:

```
exports/
└── SPACEKEY_20231201_143022/
    ├── export_summary.html          # Human-readable summary
    ├── export_summary.json          # Machine-readable summary
    ├── pages/                       # Page content
    │   ├── Page_Title.html          # Page content as HTML
    │   ├── Page_Title_metadata.json # Page metadata
    │   ├── attachments/             # Page attachments
    │   │   └── Page_Title/
    │   │       ├── file1.pdf
    │   │       └── attachments_metadata.json
    │   └── comments/                # Page comments
    │       └── Page_Title/
    │           ├── comments.html
    │           └── comments.json
    ├── blogposts/                   # Blog posts (if any)
    ├── folders/                     # Folders (Cloud only)
    │   └── folders_metadata.json    # Folder structure and metadata
    ├── databases/                   # Database stubs (Cloud only)
    │   └── databases_metadata.json  # Database structure (titles/hierarchy only — data not exported)
    └── metadata/
        └── space_info.json          # Space metadata
```

## 🔍 Troubleshooting

### Common Issues

**1. Authentication Failed**
- Verify your API token is correct and not expired
- For server instances, you may need to use password authentication
- Check if your account has permission to access the spaces

**2. Connection Timeout**
- Increase timeout in configuration: `general.timeout: 60`
- Check your network connection
- Verify the Confluence URL is correct

**3. Permission Denied**
- Ensure your account has read access to source spaces
- For imports, ensure write access to target spaces
- Check space permissions in Confluence

**4. Large Space Export/Import Takes Too Long**
- Reduce `general.max_workers` for slower connections
- Export/import in smaller batches if possible
- Use `--verbose` flag to monitor progress

**5. Pages Temporarily Appear at Space Root During Import (Cloud)**

When importing spaces that use Confluence folders (Cloud only), pages belonging to those folders may appear at the space root while the import is in progress. This is **expected behaviour**, not an error:

- Folders whose parent is a page cannot be created until that parent page has been imported.
- The tool imports all pages first, then creates the folders, then automatically moves pages into their correct folder locations.
- A notice is logged at the start of page import to confirm this will happen.
- No manual intervention is required — all pages will be in their correct locations once the import finishes.

**6. Import Runs Significantly Longer Than Expected**

For spaces with many folder-parented pages, the tool performs an additional sweep after folder creation to move each page into its correct folder (one API call per folder-parented page). This is proportional to the number of such pages and can add considerable time for large spaces.

If the slow-down is caused by API rate limiting rather than the move sweep, the tool does not yet surface HTTP 429 responses clearly — they may appear as generic warnings or timeouts in verbose output. A dedicated rate-limit notification feature is planned for a future release. In the meantime:

- Enable verbose logging (`--verbose`) and watch for repeated connection warnings or slow API responses.
- Reduce `general.max_workers` in your configuration to lower the request rate.
- Consider importing during off-peak hours.

### Error Logs

The tool provides detailed error logging. Enable verbose mode for debugging:

```bash
confluence-tool export --verbose
```

Or configure file logging in your `config.yaml`:

```yaml
logging:
  level: "DEBUG"
  file: "confluence-tool.log"
```

## 🌍 Cross-Platform Compatibility

This tool is designed to work seamlessly across different operating systems:

### Windows
- Works on Windows 10 and 11
- Supports PowerShell and Command Prompt
- Handles Windows path separators correctly
- Safe filename sanitization for NTFS

### macOS
- Compatible with macOS 10.14+
- Works with both Intel and Apple Silicon Macs
- Supports both Terminal and iTerm2

### Linux
- Tested on Ubuntu, CentOS, and Debian
- Compatible with various Python installations
- Handles different filesystem types

### Python Version Support
- Python 3.7+
- Automatically detects and adapts to the environment
- Uses cross-platform libraries for maximum compatibility

## ⚠️ Known Limitations

Due to limitations in the Confluence REST API, certain content types and features cannot be fully exported or imported by this tool.

### Content That Cannot Be Exported

| Content Type | Limitation | Notes |
|-------------|------------|-------|
| **Databases (structure)** | Partial — Cloud only | Database containers are recreated as empty stubs during import, preserving sidebar hierarchy. Pages that were children of databases are correctly moved under them using the v1 move endpoint. |
| **Databases (data)** | Not supported | Database content (rows, columns, data) cannot be exported via the REST API. Data must be re-entered manually in the Confluence UI after import. |
| **Analytics data** | Not supported | Page view statistics, user analytics, and other telemetry data are not available via the API. |
| **Space permissions** | Partial | Space permissions are not exported. Permissions must be manually configured on the target space. |
| **Page restrictions** | Metadata only | Page restrictions are captured in metadata but not automatically applied during import. |
| **Custom macros** | Varies | Custom or third-party macros may not render correctly after import if the same apps are not installed in the target instance. |

### Folder Limitations

Folders in Confluence have specific API limitations that affect export and import:

- **Cloud Only**: Folders are only available in Confluence Cloud via the v2 API. Server and Data Center instances do not support folders via API.
- **API Support**: Some Confluence Cloud instances may not have full v2 API support for folders. If folder export fails, the tool will continue exporting pages and other content.
- **Page Placement**: The Confluence v1 and v2 APIs cannot directly create pages as children of folders (the v1 `ancestors` field and v2 `parentId` both fail for folder targets). The tool works around this by creating pages at their default position and then moving them into the correct folder using the v1 move endpoint (`PUT /rest/api/content/{id}/move/append/{folderId}`). This is the confirmed community workaround (as of 2024) and correctly places pages inside folders in the sidebar.
- **Fallback**: If the move call fails (e.g. on a Server/DC instance or due to permissions), a warning is logged and the page remains at its default position rather than causing the import to fail.

### Import/Restore Behavior

When importing or restoring data, be aware of the following behaviors:

#### Orphaned Pages
If a page's parent (whether a page, folder, or database) cannot be found during import:
1. The tool attempts multiple passes to import pages in the correct hierarchy order
2. For pages under **folders**: folders are recreated and pages are moved into them using the v1 move endpoint (Cloud only)
3. For pages under **databases**: empty database stubs are recreated and pages are moved into them (Cloud only; database data must be re-entered manually)
4. If a parent still cannot be found after all passes, the tool creates a **synthetic parent page** titled `[Recovered] <Original Parent Name>`
5. The synthetic page contains a list of child pages that were grouped under it
6. You can manually reorganize these pages after import

#### Synthetic Parent Pages
Synthetic parent pages are created when:
- The original parent page was not included in the export
- The original parent was a folder or database that could not be recreated (e.g. on Server/DC instances where the v2 API is unavailable)
- The parent page failed to import due to an error

These placeholder pages can be identified by their `[Recovered]` prefix and can be safely deleted or replaced with actual content after organizing the child pages.

#### Multi-Pass Import Strategy
The import process uses a multi-pass strategy to handle complex page hierarchies:
1. **Pass 1**: Root pages (no parent) are imported first
2. **Subsequent passes**: Child pages are imported once their parents exist
3. **Final pass**: Any remaining orphaned pages are imported under synthetic parents

This ensures that parent-child relationships are preserved whenever possible.

### Confluence Cloud Space Key Retention

Confluence Cloud retains deleted space keys indefinitely. If you delete a space and try to recreate it with the same key, you will receive an error. Use the `--remap-space-key` option to import to a different space key:

```bash
confluence-tool import /path/to/export --remap-space-key OLDKEY:NEWKEY \
  --create-space --new-space-key NEWKEY --space-name "Space Name"
```

In this example, `OLDKEY` is the original space key from the export, and `NEWKEY` is the new space key to use for the import.

## 🛡️ Security Considerations

- **API Tokens**: Always use API tokens instead of passwords for cloud instances
- **Credentials**: Never commit configuration files with credentials to version control
- **Permissions**: Use accounts with minimal required permissions
- **Local Storage**: Export files may contain sensitive information; store securely

## 📝 For Developers

### Project Structure

```
confluence_tool/
├── __init__.py
├── main.py              # CLI application
├── config/
│   ├── __init__.py
│   └── manager.py       # Configuration management
├── api/
│   ├── __init__.py
│   └── client.py        # Confluence API client
├── export/
│   ├── __init__.py
│   └── exporter.py      # Export functionality
├── import/
│   ├── __init__.py
│   └── importer.py      # Import functionality
└── utils/
    ├── __init__.py
    └── helpers.py       # Utility functions
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the Apache 2.0 license - see the LICENSE and NOTICE file for details.

## 🤝 Support

> [!NOTE]  
> I am **not actively maintaining this tool** , it began as a personal project to solve a specific need.  
> If you’d like to extend or adapt it, I recommend cloning the repository and creating your own branch.  
>
> If you do encounter issues, you’re welcome to raise an issue on this repository but I make no guarantee I will be able to look at it thoroughly. Before doing so, try the built-in support options:  
>
> 1. Review the **Troubleshooting** section above.  
> 2. Run the built-in help command:  
>    ```bash
>    confluence-tool help-guide
>    ```  
> 3. Enable **verbose logging** for detailed error output.  
> 4. If issues persist, open a GitHub issue and include:  
>    - Your operating system and Python version  
>    - The exact command you were running  
>    - Any error messages (with sensitive information removed)
>    - A log file (Modify the config.yaml to change the log level to DEBUG and specify a log file)

## 🔄 Version History

- **1.1.0**: Fixed a bug where pages with folder-based parents were skipped during import when all folders in a space had page-based parents (resulting in an empty folder map at page-import time). Pages are now imported to a temporary location and automatically moved into their correct folders after the deferred folder phase completes. Verbose WARNING noise for expected folder-parent lookups during import has been suppressed. Added user-facing notice when temporary root placement will occur.
- **1.0.0**: Initial release with full export/import functionality, folder and database stub support (Cloud), space key remapping, `clean-space` command, and multi-environment import/export.

---

**Made with ❤️ for the Confluence community**
