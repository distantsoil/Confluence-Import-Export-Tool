"""Main CLI application for Confluence Export-Import Tool."""

import os
import sys
import click
import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# Import colorama for cross-platform colored output
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    Fore = Style = type('MockColor', (), {'RED': '', 'GREEN': '', 'YELLOW': '', 'CYAN': '', 'RESET_ALL': ''})()

from .config.manager import ConfigManager
from .api.client import ConfluenceAPIClient
from .export.exporter import ConfluenceExporter
from .import_.importer import ConfluenceImporter
from .sync.synchronizer import ConfluenceSynchronizer
from .utils.helpers import (
    setup_logging, display_spaces_table, prompt_space_selection,
    get_platform_info, validate_confluence_url, prompt_target_config_setup,
    extract_original_space_key_from_export, prompt_space_key_remapping,
    prompt_space_creation_with_key_conflict
)

logger = logging.getLogger(__name__)


def print_colored(message: str, color: str = 'WHITE') -> None:
    """Print colored message if colors are available."""
    if COLORS_AVAILABLE:
        color_code = getattr(Fore, color.upper(), '')
        print(f"{color_code}{message}{Style.RESET_ALL}")
    else:
        print(message)


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                Confluence Export-Import Tool                 ║
║                         Version 1.0.0                       ║
╚══════════════════════════════════════════════════════════════╝
"""
    print_colored(banner, 'CYAN')


def print_platform_info():
    """Print platform information."""
    info = get_platform_info()
    print_colored(f"Platform: {info['system']} ({info['architecture']})", 'YELLOW')
    print_colored(f"Python: {info['python_version']}", 'YELLOW')


def init_config(ctx):
    """Initialize configuration when needed."""
    if 'config' not in ctx.obj:
        try:
            config_manager = ConfigManager(ctx.obj.get('config_path'))
            ctx.obj['config'] = config_manager
            
            # Set up logging
            log_config = config_manager.get_logging_config()
            log_level = 'DEBUG' if ctx.obj.get('verbose') else log_config.get('level', 'INFO')
            setup_logging(
                log_level=log_level,
                log_file=log_config.get('file'),
                log_format=log_config.get('format')
            )
            
            if ctx.obj.get('verbose'):
                print_platform_info()
            
        except FileNotFoundError as e:
            print_colored(f"Configuration Error: {e}", 'RED')
            print_colored("You can create a sample configuration file using:", 'YELLOW')
            print_colored("  confluence-tool config create", 'YELLOW')
            sys.exit(1)
        except Exception as e:
            print_colored(f"Configuration Error: {e}", 'RED')
            sys.exit(1)


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """Confluence Export-Import Tool - Export and import Confluence spaces via REST API."""
    print_banner()
    
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Store config path and verbose flag for later use
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose


@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command('create')
@click.argument('path', default='config.yaml')
def config_create(path):
    """Create a sample configuration file."""
    try:
        # Get the config manager to access the sample config
        from .config.manager import ConfigManager
        
        if os.path.exists(path):
            if not click.confirm(f"Configuration file {path} already exists. Overwrite?"):
                print_colored("Configuration creation cancelled.", 'YELLOW')
                return
        
        # Copy sample configuration
        package_dir = os.path.dirname(os.path.dirname(__file__))
        sample_config_path = os.path.join(package_dir, "config.yaml")
        
        if os.path.exists(sample_config_path):
            import shutil
            shutil.copy2(sample_config_path, path)
            print_colored(f"Sample configuration created at: {path}", 'GREEN')
            print_colored("Please edit this file with your Confluence details before using the tool.", 'YELLOW')
        else:
            # Create basic config if sample not found
            basic_config = """# Confluence Export-Import Tool Configuration
confluence:
  base_url: "https://your-domain.atlassian.net"
  auth:
    username: "your-email@example.com"
    api_token: "your-api-token"

export:
  output_directory: "./exports"
  format:
    html: true
    attachments: true
    comments: true

import:
  conflict_resolution: "skip"
  create_missing_parents: true
  import_attachments: true

general:
  verbose: false
  max_workers: 5
  timeout: 30

logging:
  level: "INFO"

# Multi-environment example:
# Create separate config files for different environments:
# 
# source-config.yaml:
# confluence:
#   base_url: "https://source-domain.atlassian.net"
#   auth:
#     username: "source-user@example.com"
#     api_token: "source-api-token"
#
# target-config.yaml: 
# confluence:
#   base_url: "https://target-domain.atlassian.net"
#   auth:
#     username: "target-user@example.com"
#     api_token: "target-api-token"
#
# Usage examples:
# confluence-tool export --source-config source-config.yaml --space MYSPACE
# confluence-tool import /path/to/export --target-config target-config.yaml --space NEWSPACE
# confluence-tool sync --source-config source-config.yaml --target-config target-config.yaml --source-space MYSPACE --target-space NEWSPACE
"""
            with open(path, 'w', encoding='utf-8') as f:
                f.write(basic_config)
            
            print_colored(f"Basic configuration created at: {path}", 'GREEN')
            print_colored("Please edit this file with your Confluence details.", 'YELLOW')
    
    except Exception as e:
        print_colored(f"Error creating configuration: {e}", 'RED')
        sys.exit(1)


@config.command('validate')
@click.pass_context
def config_validate(ctx):
    """Validate configuration and test Confluence connection."""
    init_config(ctx)
    
    try:
        config_manager = ctx.obj['config']
        confluence_config = config_manager.get_confluence_config()
        
        print_colored("Validating configuration...", 'YELLOW')
        
        # Validate URL
        base_url = validate_confluence_url(confluence_config['base_url'])
        print_colored(f"✓ Base URL: {base_url}", 'GREEN')
        
        # Test connection
        print_colored("Testing Confluence connection...", 'YELLOW')
        
        auth_config = confluence_config['auth']
        client = ConfluenceAPIClient(
            base_url=base_url,
            username=auth_config['username'],
            auth_token=auth_config.get('api_token'),
            password=auth_config.get('password'),
            timeout=config_manager.get('general.timeout', 30),
            max_retries=config_manager.get('general.retry.max_attempts', 3),
            rate_limit=config_manager.get('general.rate_limit', 10)
        )
        
        if client.test_connection():
            print_colored("✓ Connection successful!", 'GREEN')
            
            # Get basic info
            spaces = client.get_spaces(limit=5)
            print_colored(f"✓ Found {len(spaces)} spaces (showing first 5)", 'GREEN')
            
            # Display the spaces
            if spaces:
                for space in spaces:
                    space_name = space.get('name', 'Unknown')
                    space_key = space.get('key', 'Unknown')
                    print(f"  - {space_name} ({space_key})")
        else:
            print_colored("✗ Connection failed", 'RED')
            sys.exit(1)
    
    except Exception as e:
        print_colored(f"Validation failed: {e}", 'RED')
        sys.exit(1)


@cli.command()
@click.option('--space', '-s', help='Space key to export (if not provided, will prompt to select)')
@click.option('--output', '-o', help='Output directory (overrides config)')
@click.option('--source-config', help='Path to source environment configuration file')
@click.pass_context
def export(ctx, space, output, source_config):
    """Export a Confluence space."""
    # Use source config if provided, otherwise use the main config
    config_file_used = source_config if source_config else ctx.obj.get('config_path') or 'config.yaml'
    if source_config:
        try:
            source_config_manager = ConfigManager(source_config)
        except Exception as e:
            print_colored(f"Error loading source configuration: {e}", 'RED')
            sys.exit(1)
    else:
        init_config(ctx)
        source_config_manager = ctx.obj['config']
    
    try:
        confluence_config = source_config_manager.get_confluence_config()
        export_config = source_config_manager.get_export_config()
        general_config = source_config_manager.get_general_config()
        
        # Display configuration being used
        print()
        print_colored("=" * 60, 'CYAN')
        print_colored("Export Configuration", 'CYAN')
        print_colored("=" * 60, 'CYAN')
        print_colored(f"  Config file: {config_file_used}", 'WHITE')
        print_colored(f"  Target URL:  {confluence_config['base_url']}", 'WHITE')
        print_colored("=" * 60, 'CYAN')
        print()
        
        # Override output directory if specified
        if output:
            export_config['output_directory'] = output
        
        # Create API client
        auth_config = confluence_config['auth']
        client = ConfluenceAPIClient(
            base_url=confluence_config['base_url'],
            username=auth_config['username'],
            auth_token=auth_config.get('api_token'),
            password=auth_config.get('password'),
            timeout=general_config.get('timeout', 30),
            max_retries=general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=general_config.get('rate_limit', 10)
        )
        
        # Test connection
        print_colored("Testing connection...", 'YELLOW')
        if not client.test_connection():
            print_colored("Connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        # Select space if not provided
        if not space:
            print_colored("Fetching available spaces...", 'YELLOW')
            spaces = client.get_all_spaces()
            
            if not spaces:
                print_colored("No spaces found or no access to spaces.", 'RED')
                sys.exit(1)
            
            selected_space = prompt_space_selection(spaces)
            space_key = selected_space['key']
        else:
            space_key = space
        
        # Create exporter and export
        print_colored(f"Starting export of space: {space_key}", 'CYAN')
        
        exporter = ConfluenceExporter(client, export_config)
        export_dir = exporter.export_space(space_key)
        
        print_colored(f"Export completed successfully!", 'GREEN')
        print_colored(f"Export directory: {export_dir}", 'CYAN')
        
        # Show export summary
        summary_file = os.path.join(export_dir, 'export_summary.html')
        if os.path.exists(summary_file):
            print_colored(f"Summary report: {summary_file}", 'CYAN')
    
    except KeyboardInterrupt:
        print_colored("\nExport cancelled by user.", 'YELLOW')
        sys.exit(1)
    except Exception as e:
        print_colored(f"Export failed: {e}", 'RED')
        logger.exception("Export error details:")
        sys.exit(1)


@cli.command()
@click.argument('export_dir', type=click.Path(exists=True))
@click.option('--space', '-s', help='Target space key (if not provided, will prompt to select)')
@click.option('--space-name', help='New name for the target space (updates existing space name)')
@click.option('--create-space', is_flag=True, help='Create a new space instead of using existing one')
@click.option('--new-space-key', help='Space key for new space (required if --create-space is used)')
@click.option('--conflict-resolution', type=click.Choice(['skip', 'overwrite', 'update_newer', 'rename']),
              help='How to handle existing pages: skip (default), overwrite (replace all), update_newer (only if source is newer), or rename')
@click.option('--target-config', '-t', help='Path to target environment configuration file')
@click.option('--remap-space-key', help='Remap space key references (format: OLD_KEY:NEW_KEY). This will rewrite all internal space references in content.')
@click.pass_context
def import_(ctx, export_dir, space, space_name, create_space, new_space_key, conflict_resolution, target_config, remap_space_key):
    """Import a Confluence space from export directory."""
    # Validate create-space option
    if create_space and not new_space_key:
        print_colored("Error: --new-space-key is required when using --create-space", 'RED')
        sys.exit(1)
    
    if create_space and not space_name:
        print_colored("Error: --space-name is required when using --create-space", 'RED')
        sys.exit(1)
    
    # Parse and validate space key remapping
    old_space_key = None
    new_space_key_remap = None
    if remap_space_key:
        if ':' not in remap_space_key:
            print_colored("Error: --remap-space-key must be in format OLD_KEY:NEW_KEY", 'RED')
            sys.exit(1)
        
        parts = remap_space_key.split(':', 1)
        old_space_key = parts[0].strip()
        new_space_key_remap = parts[1].strip()
        
        if not old_space_key or not new_space_key_remap:
            print_colored("Error: Both old and new space keys must be specified in --remap-space-key", 'RED')
            sys.exit(1)
        
        logger.info(f"Space key remapping requested: {old_space_key} -> {new_space_key_remap}")
    
    # Use target config if provided, otherwise use the main config
    target_config_file_used = target_config  # Track which config file is used
    if target_config:
        try:
            target_config_manager = ConfigManager(target_config)
        except Exception as e:
            print_colored(f"Error loading target configuration: {e}", 'RED')
            sys.exit(1)
    else:
        # Prompt user if they want to use a different target environment
        print_colored("\n🌍 Multi-Environment Import", 'CYAN')
        print()
        print("You can import to:")
        print("  1. The SAME Confluence environment (using your default config.yaml)")
        print("  2. A DIFFERENT Confluence environment (using a separate target config)")
        print()
        
        use_different = click.confirm(
            "Do you want to import to a DIFFERENT Confluence environment?",
            default=False
        )
        
        if use_different:
            # Ask if they have an existing target config or want to create one
            print()
            has_config = click.confirm(
                "Do you already have a target configuration file?",
                default=False
            )
            
            if has_config:
                # Prompt for existing config file path
                target_config_path = click.prompt(
                    "Enter path to target configuration file",
                    type=click.Path(exists=True),
                    default="target-config.yaml"
                )
                target_config_file_used = target_config_path
                try:
                    target_config_manager = ConfigManager(target_config_path)
                    print_colored(f"✓ Using target configuration: {target_config_path}", 'GREEN')
                except Exception as e:
                    print_colored(f"Error loading target configuration: {e}", 'RED')
                    sys.exit(1)
            else:
                # Create new target config interactively
                try:
                    target_config_path = prompt_target_config_setup()
                    target_config_file_used = target_config_path
                    target_config_manager = ConfigManager(target_config_path)
                except KeyboardInterrupt:
                    print_colored("\nImport cancelled by user.", 'YELLOW')
                    sys.exit(0)
                except click.Abort:
                    print_colored("\nImport cancelled.", 'YELLOW')
                    sys.exit(0)
                except Exception as e:
                    print_colored(f"Error creating target configuration: {e}", 'RED')
                    sys.exit(1)
        else:
            # Use the same config as source
            init_config(ctx)
            target_config_manager = ctx.obj['config']
            target_config_file_used = ctx.obj.get('config_path') or 'config.yaml'
            print_colored("✓ Using default configuration for import", 'GREEN')
    
    try:
        confluence_config = target_config_manager.get_confluence_config()
        import_config = target_config_manager.get_import_config()
        general_config = target_config_manager.get_general_config()
        
        # Display import configuration
        print()
        print_colored("=" * 60, 'CYAN')
        print_colored("Import Configuration", 'CYAN')
        print_colored("=" * 60, 'CYAN')
        print_colored(f"  Config file: {target_config_file_used}", 'WHITE')
        print_colored(f"  Target URL:  {confluence_config['base_url']}", 'WHITE')
        print_colored("=" * 60, 'CYAN')
        print()
        
        # Set up logging from target config
        log_config = target_config_manager.get_logging_config()
        log_level = log_config.get('level', 'INFO')
        setup_logging(
            log_level=log_level,
            log_file=log_config.get('file'),
            log_format=log_config.get('format')
        )
        
        # Override conflict resolution if specified
        if conflict_resolution:
            import_config['conflict_resolution'] = conflict_resolution
        
        # Create API client
        auth_config = confluence_config['auth']
        client = ConfluenceAPIClient(
            base_url=confluence_config['base_url'],
            username=auth_config['username'],
            auth_token=auth_config.get('api_token'),
            password=auth_config.get('password'),
            timeout=general_config.get('timeout', 30),
            max_retries=general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=general_config.get('rate_limit', 10)
        )
        
        # Test connection
        print_colored("Testing connection...", 'YELLOW')
        if not client.test_connection():
            print_colored("Connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        # Handle space creation or selection
        if create_space:
            # Create new space
            print_colored(f"Creating new space: {space_name} ({new_space_key})", 'CYAN')
            try:
                new_space = client.create_space(new_space_key, space_name)
                target_space_key = new_space_key
                print_colored(f"✓ Space created successfully!", 'GREEN')
            except Exception as e:
                print_colored(f"Failed to create space: {e}", 'RED')
                sys.exit(1)
        else:
            # Select target space if not provided
            if not space:
                print_colored("Fetching available spaces...", 'YELLOW')
                spaces = client.get_all_spaces()
                
                if not spaces:
                    # No spaces available - offer to create one using the original space key
                    print_colored("No spaces found in target environment.", 'YELLOW')
                    print()
                    
                    # Extract original space info from export
                    original_space_key, original_space_name = extract_original_space_key_from_export(export_dir)
                    
                    if original_space_key:
                        print_colored(f"Original space from export: {original_space_name} ({original_space_key})", 'CYAN')
                        print()
                        print_colored("⚠️  Important: To maintain space references and links, it's recommended", 'YELLOW')
                        print_colored("   to use the same space key as the original space.", 'YELLOW')
                        print()
                        print_colored("ℹ️  Note: Confluence Free plans only allow one space. You may need a paid plan", 'CYAN')
                        print_colored("   or free trial to create additional spaces. Alternatively, you can manually", 'CYAN')
                        print_colored("   create the space in Confluence first, then run the import again.", 'CYAN')
                        print()
                        
                        if click.confirm(f"Create new space with key '{original_space_key}'?", default=True):
                            # Use original space name if available, otherwise prompt
                            if not original_space_name:
                                original_space_name = click.prompt("Enter space name", type=str)
                            
                            try:
                                print_colored(f"Creating space: {original_space_name} ({original_space_key})", 'CYAN')
                                new_space = client.create_space(original_space_key, original_space_name)
                                target_space_key = original_space_key
                                print_colored(f"✓ Space created successfully!", 'GREEN')
                            except Exception as e:
                                # Check if the error is due to space key already existing
                                error_msg = str(e).lower()
                                if 'already exists' in error_msg or 'duplicate' in error_msg or 'conflict' in error_msg:
                                    print_colored(f"Space key '{original_space_key}' is already taken.", 'YELLOW')
                                    
                                    # Prompt for alternative space key with remapping
                                    result = prompt_space_creation_with_key_conflict(original_space_key, original_space_name)
                                    if result[0]:  # User provided new space key
                                        new_space_key_for_creation, space_name_for_creation, should_enable_remapping = result
                                        try:
                                            print_colored(f"Creating space: {space_name_for_creation} ({new_space_key_for_creation})", 'CYAN')
                                            new_space = client.create_space(new_space_key_for_creation, space_name_for_creation)
                                            target_space_key = new_space_key_for_creation
                                            print_colored(f"✓ Space created successfully!", 'GREEN')
                                            
                                            # Enable remapping automatically
                                            if should_enable_remapping and not remap_space_key:
                                                old_space_key = original_space_key
                                                new_space_key_remap = new_space_key_for_creation
                                                remap_space_key = f"{old_space_key}:{new_space_key_remap}"
                                                print_colored(f"✓ Space key remapping enabled: {old_space_key} -> {new_space_key_remap}", 'GREEN')
                                        except Exception as create_error:
                                            print_colored(f"Failed to create space: {create_error}", 'RED')
                                            sys.exit(1)
                                    else:
                                        print_colored("Import cancelled.", 'YELLOW')
                                        sys.exit(1)
                                else:
                                    print_colored(f"Failed to create space: {e}", 'RED')
                                    sys.exit(1)
                        else:
                            print_colored("Import cancelled. Please create a space manually or use --create-space option.", 'YELLOW')
                            sys.exit(1)
                    else:
                        print_colored("Could not determine original space key from export.", 'YELLOW')
                        print_colored("Please create a space manually or use --create-space option.", 'YELLOW')
                        sys.exit(1)
                else:
                    selected_space = prompt_space_selection(spaces)
                    target_space_key = selected_space['key']
            else:
                target_space_key = space
            
            # Update space name if requested
            if space_name:
                print_colored(f"Updating space name to: {space_name}", 'CYAN')
                try:
                    client.update_space(target_space_key, space_name=space_name)
                    print_colored(f"✓ Space name updated successfully!", 'GREEN')
                except Exception as e:
                    print_colored(f"Warning: Failed to update space name: {e}", 'YELLOW')
                    if not click.confirm("Continue with import anyway?"):
                        print_colored("Import cancelled.", 'YELLOW')
                        return
        
        # Auto-detect space key conflicts and prompt for remapping (if not already set via CLI)
        if not remap_space_key:
            # Extract original space key from export to check for conflicts
            original_space_key_from_export, _ = extract_original_space_key_from_export(export_dir)
            
            if original_space_key_from_export and original_space_key_from_export != target_space_key:
                # Space key conflict detected - prompt user
                should_remap, detected_old_key, detected_new_key = prompt_space_key_remapping(
                    original_space_key_from_export, 
                    target_space_key,
                    export_dir
                )
                
                if should_remap:
                    # Enable remapping based on user's decision
                    old_space_key = detected_old_key
                    new_space_key_remap = detected_new_key
                    remap_space_key = f"{old_space_key}:{new_space_key_remap}"
        
        # Display space key remapping warning if enabled
        if remap_space_key:
            print()
            print_colored("⚠️  IMPORTANT: Space key remapping detected", 'YELLOW')
            print()
            print_colored(f"Original space key: {old_space_key}", 'CYAN')
            print_colored(f"New space key: {new_space_key_remap}", 'CYAN')
            print()
            print_colored("This will rewrite ALL internal links and references in the content.", 'YELLOW')
            print_colored("The import process will take longer than normal.", 'YELLOW')
            print()
            
            # Try to count pages to give estimate
            pages_dir = os.path.join(export_dir, 'pages')
            page_count = 0
            if os.path.exists(pages_dir):
                page_count = len([f for f in os.listdir(pages_dir) if f.endswith('.html')])
            
            if page_count > 0:
                print_colored(f"Pages to process: {page_count}", 'CYAN')
                # Rough estimate: 2-3x normal time
                estimated_minutes = max(1, int(page_count / 30))  # Rough estimate
                print_colored(f"Estimated additional time: {estimated_minutes}-{estimated_minutes * 2} minutes", 'CYAN')
                print()
            
            if not click.confirm("Proceed with space key remapping?", default=True):
                print_colored("Import cancelled.", 'YELLOW')
                return
        
        # Confirm import
        print_colored(f"Import directory: {export_dir}", 'CYAN')
        print_colored(f"Target space: {target_space_key}", 'CYAN')
        if conflict_resolution:
            print_colored(f"Conflict resolution: {conflict_resolution}", 'CYAN')
        
        if not click.confirm("Proceed with import?"):
            print_colored("Import cancelled.", 'YELLOW')
            return
        
        # Create importer and import
        print_colored(f"Starting import to space: {target_space_key}", 'CYAN')
        
        importer = ConfluenceImporter(client, import_config)
        
        # Enable space key remapping if requested
        if remap_space_key:
            importer.enable_space_key_remapping(old_space_key, new_space_key_remap)
            print_colored(f"Space key remapping enabled: {old_space_key} -> {new_space_key_remap}", 'CYAN')
        
        import_stats = importer.import_space(export_dir, target_space_key)
        
        print_colored(f"Import completed successfully!", 'GREEN')
        
        # Show remapping summary if enabled
        if remap_space_key:
            print()
            print_colored("✓ Import completed successfully!", 'GREEN')
            print()
            print_colored("Space Key Remapping Summary:", 'CYAN')
            print_colored(f"  Pages updated: {importer.remapping_stats['pages_with_changes']}", 'GREEN')
            print_colored(f"  Links rewritten: {importer.remapping_stats['links_rewritten']}", 'GREEN')
            print_colored(f"  Wiki links updated: {importer.remapping_stats['wiki_links_updated']}", 'GREEN')
            print_colored(f"  HTML anchors updated: {importer.remapping_stats['html_anchors_updated']}", 'GREEN')
            print_colored(f"  Macros updated: {importer.remapping_stats['macros_updated']}", 'GREEN')
            print_colored(f"  Attachments updated: {importer.remapping_stats['attachments_updated']}", 'GREEN')
            
            if len(import_stats.get('errors', [])) > 0:
                print()
                print_colored(f"  Warnings: {len(import_stats['errors'])} (see log for details)", 'YELLOW')
            
            print()
            print_colored("Note: Please review the imported content to ensure all links function correctly.", 'YELLOW')
        
        # Show import summary
        summary_file = os.path.join(export_dir, 'import_summary.html')
        if os.path.exists(summary_file):
            print_colored(f"Summary report: {summary_file}", 'CYAN')
    
    except KeyboardInterrupt:
        print_colored("\nImport cancelled by user.", 'YELLOW')
        sys.exit(1)
    except Exception as e:
        print_colored(f"Import failed: {e}", 'RED')
        logger.exception("Import error details:")
        sys.exit(1)


@cli.command()
@click.pass_context
def list_spaces(ctx):
    """List available Confluence spaces."""
    init_config(ctx)
    
    try:
        config_manager = ctx.obj['config']
        confluence_config = config_manager.get_confluence_config()
        general_config = config_manager.get_general_config()
        config_file_used = ctx.obj.get('config_path') or 'config.yaml'
        
        # Display configuration being used
        print()
        print_colored("=" * 60, 'CYAN')
        print_colored("List Spaces Configuration", 'CYAN')
        print_colored("=" * 60, 'CYAN')
        print_colored(f"  Config file: {config_file_used}", 'WHITE')
        print_colored(f"  Target URL:  {confluence_config['base_url']}", 'WHITE')
        print_colored("=" * 60, 'CYAN')
        print()
        
        # Create API client
        auth_config = confluence_config['auth']
        client = ConfluenceAPIClient(
            base_url=confluence_config['base_url'],
            username=auth_config['username'],
            auth_token=auth_config.get('api_token'),
            password=auth_config.get('password'),
            timeout=general_config.get('timeout', 30)
        )
        
        # Test connection
        print_colored("Fetching spaces...", 'YELLOW')
        if not client.test_connection():
            print_colored("Connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        spaces = client.get_all_spaces()
        
        if not spaces:
            print_colored("No spaces found or no access to spaces.", 'YELLOW')
            return
        
        print_colored(f"Found {len(spaces)} spaces:", 'GREEN')
        display_spaces_table(spaces)
    
    except Exception as e:
        print_colored(f"Failed to list spaces: {e}", 'RED')
        sys.exit(1)


@cli.command()
@click.argument('space_key')
@click.option('--dry-run', is_flag=True, help='Preview what would be deleted without actually deleting')
@click.option('--target-config', '-t', help='Path to target environment configuration file')
@click.pass_context
def clean_space(ctx, space_key, dry_run, target_config):
    """Delete all pages from a Confluence space.
    
    WARNING: This is a destructive operation. Use with extreme caution!
    
    This command is useful when an import fails partway through and you need
    to clean the space before retrying, rather than manually deleting pages.
    
    SPACE_KEY: The key of the space to clean (e.g., 'KB', 'DOCS')
    """
    try:
        # Load configuration
        config_file_used = target_config if target_config else ctx.obj.get('config_path') or 'config.yaml'
        if target_config:
            try:
                config_manager = ConfigManager(target_config)
            except Exception as e:
                print_colored(f"Error loading target configuration: {e}", 'RED')
                sys.exit(1)
        else:
            init_config(ctx)
            config_manager = ctx.obj['config']
        
        confluence_config = config_manager.get_confluence_config()
        general_config = config_manager.get_general_config()
        
        # Display configuration being used
        print()
        print_colored("=" * 60, 'CYAN')
        print_colored("Clean Space Configuration", 'CYAN')
        print_colored("=" * 60, 'CYAN')
        print_colored(f"  Config file: {config_file_used}", 'WHITE')
        print_colored(f"  Target URL:  {confluence_config['base_url']}", 'WHITE')
        print_colored(f"  Space key:   {space_key}", 'WHITE')
        print_colored("=" * 60, 'CYAN')
        print()
        
        # Create API client
        auth_config = confluence_config['auth']
        client = ConfluenceAPIClient(
            base_url=confluence_config['base_url'],
            username=auth_config['username'],
            auth_token=auth_config.get('api_token'),
            password=auth_config.get('password'),
            timeout=general_config.get('timeout', 30),
            max_retries=general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=general_config.get('rate_limit', 10)
        )
        
        # Test connection
        print_colored("Testing connection...", 'YELLOW')
        if not client.test_connection():
            print_colored("Connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        # Verify space exists
        print_colored(f"Verifying space '{space_key}' exists...", 'YELLOW')
        try:
            space_info = client.get_space(space_key)
            space_name = space_info.get('name', space_key)
        except Exception as e:
            print_colored(f"Error: Space '{space_key}' not found or not accessible.", 'RED')
            print_colored(f"Details: {e}", 'RED')
            sys.exit(1)
        
        # Fetch all pages in the space
        print_colored(f"Fetching pages from space '{space_key}' ({space_name})...", 'YELLOW')
        try:
            pages = client.get_all_space_content(space_key, content_type='page')
        except Exception as e:
            print_colored(f"Error fetching pages: {e}", 'RED')
            sys.exit(1)

        # Fetch all folders (Cloud only — silently skip if unavailable)
        print_colored(f"Fetching folders from space '{space_key}'...", 'YELLOW')
        folders = []
        try:
            space_id_v2 = client.get_space_id_v2(space_key)
            if space_id_v2:
                print_colored(f"  v2 space ID: {space_id_v2}", 'WHITE')
                folders = client.get_folders(space_id_v2)
                print_colored(f"  Folders found: {len(folders)}", 'WHITE')
            else:
                print_colored("  Warning: could not resolve v2 space ID — folder discovery skipped.", 'YELLOW')
        except Exception as e:
            print_colored(f"  Note: folder fetch raised an exception: {e}", 'YELLOW')

        if not pages and not folders:
            print_colored(f"No content found in space '{space_key}'. Nothing to delete.", 'GREEN')
            return
        
        # Display what will be deleted
        print()
        print_colored("=" * 70, 'YELLOW')
        print_colored(f"CONTENT TO BE DELETED FROM SPACE: {space_key} ({space_name})", 'YELLOW')
        print_colored("=" * 70, 'YELLOW')
        print()
        print_colored(f"Total pages found:   {len(pages)}", 'CYAN')
        print_colored(f"Total folders found: {len(folders)}", 'CYAN')
        print()

        # Show a preview of pages (first 10 and last 5 if more than 15)
        if pages:
            print_colored("Pages:", 'WHITE')
            if len(pages) <= 15:
                for page in pages:
                    print(f"  - {page.get('title', 'Unknown')} (ID: {page.get('id', 'Unknown')})")
            else:
                for page in pages[:10]:
                    print(f"  - {page.get('title', 'Unknown')} (ID: {page.get('id', 'Unknown')})")
                print(f"  ... and {len(pages) - 15} more pages ...")
                for page in pages[-5:]:
                    print(f"  - {page.get('title', 'Unknown')} (ID: {page.get('id', 'Unknown')})")

        # Show a preview of folders
        if folders:
            print_colored("Folders:", 'WHITE')
            for folder in folders[:10]:
                print(f"  - {folder.get('title', 'Unknown')} (ID: {folder.get('id', 'Unknown')})")
            if len(folders) > 10:
                print(f"  ... and {len(folders) - 10} more folders ...")
        
        print()
        
        if dry_run:
            print_colored("=" * 70, 'CYAN')
            print_colored("DRY RUN MODE - No content will be deleted", 'CYAN')
            print_colored("=" * 70, 'CYAN')
            print()
            print_colored(
                f"This was a preview. {len(pages)} pages and {len(folders)} folders would be deleted.",
                'GREEN'
            )
            print_colored("Run without --dry-run to actually delete the content.", 'YELLOW')
            return
        
        # Show strong warnings
        print()
        print_colored("⚠️  " + "=" * 66 + " ⚠️", 'RED')
        print_colored("⚠️  WARNING: THIS IS A DESTRUCTIVE OPERATION!                        ⚠️", 'RED')
        print_colored("⚠️  " + "=" * 66 + " ⚠️", 'RED')
        print()
        print_colored(f"You are about to DELETE ALL {len(pages)} pages and {len(folders)} folders from:", 'RED')
        print_colored(f"  Space: {space_key} ({space_name})", 'RED')
        print_colored(f"  URL: {confluence_config['base_url']}", 'RED')
        print()
        print_colored("This action CANNOT be undone!", 'RED')
        print_colored("Make sure you have a backup if needed.", 'RED')
        print()
        
        # First confirmation
        if not click.confirm("Do you want to proceed with deletion?", default=False):
            print_colored("Operation cancelled.", 'YELLOW')
            return
        
        # Second confirmation with exact text
        print()
        print_colored("=" * 70, 'YELLOW')
        print_colored("FINAL CONFIRMATION REQUIRED", 'YELLOW')
        print_colored("=" * 70, 'YELLOW')
        print()
        print_colored(
            f"To confirm deletion of {len(pages)} pages and {len(folders)} folders "
            f"from space '{space_key}',",
            'YELLOW'
        )
        print_colored("please type exactly: I CONFIRM", 'YELLOW')
        print()
        
        confirmation = click.prompt("Type confirmation", type=str).strip()
        
        if confirmation != "I CONFIRM":
            print_colored("Confirmation text did not match. Operation cancelled.", 'YELLOW')
            return
        
        # Proceed with deletion
        print()
        print_colored(
            f"Starting deletion of {len(pages)} pages and {len(folders)} folders...", 'CYAN'
        )
        print()
        
        # Use tqdm for progress bar
        from tqdm import tqdm
        
        deleted_count = 0
        failed_count = 0
        failed_pages = []
        
        for page in tqdm(pages, desc="Deleting pages", unit="page"):
            page_id = page.get('id')
            page_title = page.get('title', 'Unknown')
            
            try:
                client.delete_page(page_id)
                deleted_count += 1
            except Exception as e:
                failed_count += 1
                failed_pages.append({
                    'id': page_id,
                    'title': page_title,
                    'error': str(e)
                })
                logger.error(f"Failed to delete page '{page_title}' (ID: {page_id}): {e}")
        
        # Delete folders (multi-pass: 404 = already gone; retry handles nesting order)
        folder_deleted_count = 0
        folder_failed = []

        if folders:
            print()
            print_colored(f"Deleting {len(folders)} folders...", 'CYAN')
            print()
            folder_ids = [str(f.get('id')) for f in folders]
            for fid in tqdm(folder_ids, desc="Deleting folders", unit="folder"):
                try:
                    client.delete_folder(fid)
                    folder_deleted_count += 1
                except Exception as e:
                    folder_failed.append({'id': fid, 'error': str(e)})

            # Retry failed folders — sub-folders may need their parent deleted
            # first (or vice-versa), so a few passes handle arbitrary nesting.
            for _attempt in range(4):
                if not folder_failed:
                    break
                still_failed = []
                for item in folder_failed:
                    try:
                        client.delete_folder(item['id'])
                        folder_deleted_count += 1
                    except Exception as e:
                        item['error'] = str(e)
                        still_failed.append(item)
                folder_failed = still_failed

        # Show summary
        print()
        print_colored("=" * 70, 'CYAN')
        print_colored("DELETION SUMMARY", 'CYAN')
        print_colored("=" * 70, 'CYAN')
        print()
        print_colored(f"Pages processed:          {len(pages)}", 'CYAN')
        print_colored(f"  Successfully deleted:    {deleted_count}", 'GREEN')
        if failed_count > 0:
            print_colored(f"  Failed:                 {failed_count}", 'RED')
        print_colored(f"Folders processed:        {len(folders)}", 'CYAN')
        print_colored(f"  Successfully deleted:    {folder_deleted_count}", 'GREEN')
        if folder_failed:
            print_colored(f"  Failed:                 {len(folder_failed)}", 'RED')

        if failed_count > 0:
            print()
            print_colored("Failed pages:", 'RED')
            for failed_page in failed_pages[:10]:
                print(f"  - {failed_page['title']} (ID: {failed_page['id']})")
                print(f"    Error: {failed_page['error']}")
            if len(failed_pages) > 10:
                print(f"  ... and {len(failed_pages) - 10} more failures")

        if folder_failed:
            print()
            print_colored("Failed folders:", 'RED')
            for item in folder_failed[:10]:
                print(f"  - ID: {item['id']}")
                print(f"    Error: {item['error']}")
            if len(folder_failed) > 10:
                print(f"  ... and {len(folder_failed) - 10} more failures")

        if failed_count == 0 and not folder_failed:
            print_colored("All content deleted successfully!", 'GREEN')

        print()
        print_colored(f"Space '{space_key}' has been cleaned.", 'GREEN')
    
    except KeyboardInterrupt:
        print()
        print_colored("Operation cancelled by user.", 'YELLOW')
        sys.exit(1)
    except Exception as e:
        print_colored(f"Clean space operation failed: {e}", 'RED')
        logger.exception("Clean space error details:")
        sys.exit(1)


@cli.command()
def help_guide():
    """Display beginner's guide for using the tool."""
    guide = f"""
{Fore.CYAN if COLORS_AVAILABLE else ''}╔══════════════════════════════════════════════════════════════╗
║                    Beginner's Guide                          ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL if COLORS_AVAILABLE else ''}

{Fore.GREEN if COLORS_AVAILABLE else ''}🚀 Getting Started:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

1. {Fore.YELLOW if COLORS_AVAILABLE else ''}Create Configuration File:{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   confluence-tool config create

2. {Fore.YELLOW if COLORS_AVAILABLE else ''}Edit the Configuration:{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   - Open config.yaml in a text editor
   - Set your Confluence URL (e.g., https://yourcompany.atlassian.net)
   - Set your username/email
   - Set your API token (recommended) or password

{Fore.GREEN if COLORS_AVAILABLE else ''}🔑 Getting an API Token:{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   
For Atlassian Cloud:
   1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
   2. Click "Create API token"
   3. Enter a label (e.g., "Confluence Tool")
   4. Copy the generated token to your config file

{Fore.GREEN if COLORS_AVAILABLE else ''}📋 Basic Commands:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   Test your configuration:
   confluence-tool config validate

   List available spaces:
   confluence-tool list-spaces

   Export a space:
   confluence-tool export

{Fore.GREEN if COLORS_AVAILABLE else ''}📥 Complete Import Process:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Step 1: Have an exported space ready{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   First export a space using: confluence-tool export
   This creates a directory like: ./exports/SPACEKEY_20231201_143022/

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Step 2: Decide where to import{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   - Same Confluence instance: Uses your default config.yaml
   - Different Confluence instance: Create a target-config.yaml file
     (The import command will prompt you to create one if needed)

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Step 3: Run the import command{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   
   Import to SAME environment:
   confluence-tool import ./exports/SPACEKEY_20231201_143022

   Import to DIFFERENT environment:
   confluence-tool import ./exports/SPACEKEY_20231201_143022 --target-config target-config.yaml

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Step 4: Choose import options when prompted{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   - Select target space or create a new one
   - Choose conflict resolution (skip, overwrite, update_newer, rename)
   - Enable space key remapping if importing to a different space key

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Common Import Scenarios:{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   
   Import to existing space:
   confluence-tool import /path/to/export --space TARGETSPACE

   Create a new space for import:
   confluence-tool import /path/to/export --create-space --new-space-key NEWKEY --space-name "My Space"

   Import with overwrite (replace existing pages):
   confluence-tool import /path/to/export --conflict-resolution overwrite

   Import only newer pages:
   confluence-tool import /path/to/export --conflict-resolution update_newer

{Fore.GREEN if COLORS_AVAILABLE else ''}🌍 Multi-Environment Setup:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   For importing to a different Confluence instance, you need TWO config files:
   
   1. {Fore.YELLOW if COLORS_AVAILABLE else ''}config.yaml{Style.RESET_ALL if COLORS_AVAILABLE else ''} - Your source environment (where you export FROM)
   2. {Fore.YELLOW if COLORS_AVAILABLE else ''}target-config.yaml{Style.RESET_ALL if COLORS_AVAILABLE else ''} - Your target environment (where you import TO)

   Create target config manually:
   confluence-tool config create target-config.yaml
   (Then edit it with your target Confluence details)

   Or let the import command guide you:
   confluence-tool import /path/to/export
   (It will ask if you want to import to a different environment)

   Complete multi-environment workflow:
   1. confluence-tool export --space MYSPACE                    # Export from source
   2. confluence-tool import ./exports/MYSPACE_* --target-config target-config.yaml

{Fore.GREEN if COLORS_AVAILABLE else ''}🧹 Clean Space (For Failed Imports):{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   If an import fails partway through, you may need to clean the space before retrying.
   
   {Fore.YELLOW if COLORS_AVAILABLE else ''}Always preview first with --dry-run:{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   confluence-tool clean-space SPACEKEY --dry-run

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Clean same environment (using config.yaml):{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   confluence-tool clean-space SPACEKEY

   {Fore.YELLOW if COLORS_AVAILABLE else ''}Clean target environment (using target-config.yaml):{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   confluence-tool clean-space SPACEKEY --target-config target-config.yaml

   ⚠️  WARNING: This permanently deletes all pages in the space!

{Fore.GREEN if COLORS_AVAILABLE else ''}📥 Import Options Reference:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   Conflict Resolution Modes:
   - skip: Skip existing pages (default, safest)
   - overwrite: Replace all existing pages
   - update_newer: Update only if source is newer
   - rename: Rename imported pages with timestamp

   Space Key Remapping:
   Use --remap-space-key when importing to a different space key.
   This rewrites all internal links automatically.
   
   Example:
   confluence-tool import /path/to/export --remap-space-key KB:KB2 \\
     --create-space --new-space-key KB2 --space-name "Knowledge Base"

{Fore.GREEN if COLORS_AVAILABLE else ''}💡 Tips:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   - Always test your configuration first with 'config validate'
   - Exports are saved in the directory specified in your config
   - The tool will prompt you to select spaces if not specified
   - Use --verbose flag for detailed logging
   - Check the HTML summary reports after export/import

{Fore.GREEN if COLORS_AVAILABLE else ''}⚠️  Important Notes:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   - Make sure you have appropriate permissions in Confluence
   - Large spaces may take time to export/import
   - Always backup your Confluence space before importing
   - The tool preserves page hierarchy and attachments

{Fore.GREEN if COLORS_AVAILABLE else ''}🔧 Running the Tool:{Style.RESET_ALL if COLORS_AVAILABLE else ''}

   After installation with 'pip install -e .', you can use:
   - confluence-tool [command]              (if in PATH)
   - python3 -m confluence_tool.main [command]  (macOS/Linux)
   - python -m confluence_tool.main [command]   (Windows)

   If 'confluence-tool' is not found, use the python -m method.

{Fore.GREEN if COLORS_AVAILABLE else ''}📚 Need Help?{Style.RESET_ALL if COLORS_AVAILABLE else ''}
   
   Run any command with --help for detailed options:
   confluence-tool export --help
   confluence-tool import --help
   confluence-tool clean-space --help
"""
    print(guide)


@cli.command()
@click.option('--source-space', '-ss', required=True, help='Source space key')
@click.option('--target-space', '-ts', required=True, help='Target space key')
@click.option('--source-config', '-sc', help='Path to source environment configuration')
@click.option('--target-config', '-tc', help='Path to target environment configuration')
@click.option('--mode', '-m', type=click.Choice(['missing_only', 'newer_only', 'full']), 
              default='missing_only', help='Sync mode: missing_only, newer_only, or full')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without actually syncing')
@click.pass_context
def sync(ctx, source_space, target_space, source_config, target_config, mode, dry_run):
    """Synchronize content between Confluence spaces in different environments."""
    try:
        # Load configurations
        if source_config:
            try:
                source_config_manager = ConfigManager(source_config)
            except Exception as e:
                print_colored(f"Error loading source configuration: {e}", 'RED')
                sys.exit(1)
        else:
            init_config(ctx)
            source_config_manager = ctx.obj['config']
        
        if target_config:
            try:
                target_config_manager = ConfigManager(target_config)
            except Exception as e:
                print_colored(f"Error loading target configuration: {e}", 'RED')
                sys.exit(1)
        else:
            # Use same config as source if not specified
            target_config_manager = source_config_manager
        
        # Create API clients
        source_confluence_config = source_config_manager.get_confluence_config()
        source_general_config = source_config_manager.get_general_config()
        
        target_confluence_config = target_config_manager.get_confluence_config()
        target_general_config = target_config_manager.get_general_config()
        
        source_auth_config = source_confluence_config['auth']
        source_client = ConfluenceAPIClient(
            base_url=source_confluence_config['base_url'],
            username=source_auth_config['username'],
            auth_token=source_auth_config.get('api_token'),
            password=source_auth_config.get('password'),
            timeout=source_general_config.get('timeout', 30),
            max_retries=source_general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=source_general_config.get('rate_limit', 10)
        )
        
        target_auth_config = target_confluence_config['auth']
        target_client = ConfluenceAPIClient(
            base_url=target_confluence_config['base_url'],
            username=target_auth_config['username'],
            auth_token=target_auth_config.get('api_token'),
            password=target_auth_config.get('password'),
            timeout=target_general_config.get('timeout', 30),
            max_retries=target_general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=target_general_config.get('rate_limit', 10)
        )
        
        # Test connections
        print_colored("Testing source connection...", 'YELLOW')
        if not source_client.test_connection():
            print_colored("Source connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        print_colored("Testing target connection...", 'YELLOW')  
        if not target_client.test_connection():
            print_colored("Target connection failed. Please check your configuration.", 'RED')
            sys.exit(1)
        
        print_colored("Both connections successful!", 'GREEN')
        
        # Create synchronizer
        export_config = source_config_manager.get_export_config()
        import_config = target_config_manager.get_import_config()
        
        synchronizer = ConfluenceSynchronizer(
            source_client, target_client, export_config, import_config
        )
        
        if dry_run:
            # Just compare and show what would be synced
            print_colored(f"Dry run mode - analyzing spaces...", 'CYAN')
            comparison = synchronizer.compare_spaces(source_space, target_space)
            
            print_colored(f"\nComparison Results:", 'CYAN')
            print_colored(f"Source space '{source_space}': {comparison['source_page_count']} pages", 'WHITE')
            print_colored(f"Target space '{target_space}': {comparison['target_page_count']} pages", 'WHITE')
            print_colored(f"Pages only in source: {len(comparison['only_in_source'])}", 'YELLOW')
            print_colored(f"Pages newer in source: {len(comparison['newer_in_source'])}", 'YELLOW')
            
            if comparison['only_in_source']:
                print_colored("\nPages that would be copied (missing in target):", 'YELLOW')
                for title in comparison['only_in_source'][:10]:  # Show first 10
                    print(f"  - {title}")
                if len(comparison['only_in_source']) > 10:
                    print(f"  ... and {len(comparison['only_in_source']) - 10} more")
            
            if mode != 'missing_only' and comparison['newer_in_source']:
                print_colored("\nPages that would be updated (newer in source):", 'YELLOW')
                for title in comparison['newer_in_source'][:10]:
                    print(f"  - {title}")
                if len(comparison['newer_in_source']) > 10:
                    print(f"  ... and {len(comparison['newer_in_source']) - 10} more")
            
            # Save detailed report
            report_path = f"sync_analysis_{source_space}_to_{target_space}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            synchronizer.create_sync_report(comparison, report_path)
            print_colored(f"\nDetailed report saved to: {report_path}.html", 'CYAN')
            
        else:
            # Perform actual sync
            print_colored(f"Starting sync from '{source_space}' to '{target_space}' (mode: {mode})", 'CYAN')
            
            if not click.confirm("Proceed with sync? This will modify the target space."):
                print_colored("Sync cancelled.", 'YELLOW')
                return
            
            sync_stats = synchronizer.sync_space(source_space, target_space, mode)
            
            print_colored(f"Sync completed successfully!", 'GREEN')
            print_colored(f"Pages copied: {sync_stats['pages_copied']}", 'GREEN')
            print_colored(f"Pages updated: {sync_stats['pages_updated']}", 'GREEN')
            
            if sync_stats['errors']:
                print_colored(f"Errors encountered: {len(sync_stats['errors'])}", 'YELLOW')
                for error in sync_stats['errors'][:5]:  # Show first 5 errors
                    print_colored(f"  - {error}", 'RED')
    
    except KeyboardInterrupt:
        print_colored("\nSync cancelled by user.", 'YELLOW')
        sys.exit(1)
    except Exception as e:
        print_colored(f"Sync failed: {e}", 'RED')
        logger.exception("Sync error details:")
        sys.exit(1)


@cli.command()
@click.option('--source-space', '-ss', required=True, help='Source space key')
@click.option('--target-space', '-ts', required=True, help='Target space key')
@click.option('--source-config', '-sc', help='Path to source environment configuration')
@click.option('--target-config', '-tc', help='Path to target environment configuration')
@click.option('--output', '-o', help='Output path for comparison report')
@click.pass_context
def compare(ctx, source_space, target_space, source_config, target_config, output):
    """Compare content between Confluence spaces in different environments."""
    try:
        # Load configurations (same logic as sync command)
        if source_config:
            try:
                source_config_manager = ConfigManager(source_config)
            except Exception as e:
                print_colored(f"Error loading source configuration: {e}", 'RED')
                sys.exit(1)
        else:
            init_config(ctx)
            source_config_manager = ctx.obj['config']
        
        if target_config:
            try:
                target_config_manager = ConfigManager(target_config)
            except Exception as e:
                print_colored(f"Error loading target configuration: {e}", 'RED')
                sys.exit(1)
        else:
            target_config_manager = source_config_manager
        
        # Create API clients (same logic as sync command)
        source_confluence_config = source_config_manager.get_confluence_config()
        source_general_config = source_config_manager.get_general_config()
        
        target_confluence_config = target_config_manager.get_confluence_config()
        target_general_config = target_config_manager.get_general_config()
        
        source_auth_config = source_confluence_config['auth']
        source_client = ConfluenceAPIClient(
            base_url=source_confluence_config['base_url'],
            username=source_auth_config['username'],
            auth_token=source_auth_config.get('api_token'),
            password=source_auth_config.get('password'),
            timeout=source_general_config.get('timeout', 30),
            max_retries=source_general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=source_general_config.get('rate_limit', 10)
        )
        
        target_auth_config = target_confluence_config['auth']
        target_client = ConfluenceAPIClient(
            base_url=target_confluence_config['base_url'],
            username=target_auth_config['username'],
            auth_token=target_auth_config.get('api_token'),
            password=target_auth_config.get('password'),
            timeout=target_general_config.get('timeout', 30),
            max_retries=target_general_config.get('retry', {}).get('max_attempts', 3),
            rate_limit=target_general_config.get('rate_limit', 10)
        )
        
        # Test connections
        print_colored("Testing connections...", 'YELLOW')
        if not source_client.test_connection():
            print_colored("Source connection failed.", 'RED')
            sys.exit(1)
        if not target_client.test_connection():
            print_colored("Target connection failed.", 'RED')
            sys.exit(1)
        
        # Create synchronizer and compare
        export_config = source_config_manager.get_export_config()
        import_config = target_config_manager.get_import_config()
        
        synchronizer = ConfluenceSynchronizer(
            source_client, target_client, export_config, import_config
        )
        
        print_colored(f"Comparing spaces '{source_space}' and '{target_space}'...", 'CYAN')
        comparison = synchronizer.compare_spaces(source_space, target_space)
        
        # Display summary
        print_colored(f"\nComparison Results:", 'CYAN')
        print_colored(f"Source space: {comparison['source_page_count']} pages", 'WHITE')
        print_colored(f"Target space: {comparison['target_page_count']} pages", 'WHITE')
        print_colored(f"Common pages: {len(comparison['common_pages'])}", 'GREEN')
        print_colored(f"Only in source: {len(comparison['only_in_source'])}", 'YELLOW')
        print_colored(f"Only in target: {len(comparison['only_in_target'])}", 'YELLOW')
        print_colored(f"Newer in source: {len(comparison['newer_in_source'])}", 'BLUE')
        print_colored(f"Newer in target: {len(comparison['newer_in_target'])}", 'BLUE')
        
        # Save report
        if not output:
            output = f"comparison_{source_space}_vs_{target_space}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        synchronizer.create_sync_report(comparison, output)
        print_colored(f"\nDetailed report saved to: {output}.html", 'GREEN')
        
    except KeyboardInterrupt:
        print_colored("\nComparison cancelled by user.", 'YELLOW')
        sys.exit(1)
    except Exception as e:
        print_colored(f"Comparison failed: {e}", 'RED')
        logger.exception("Comparison error details:")
        sys.exit(1)


# Make import command available as import to avoid Python keyword conflict  
cli.add_command(import_, 'import')


if __name__ == '__main__':
    cli()