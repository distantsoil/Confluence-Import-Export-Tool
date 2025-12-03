"""Helper utilities for the Confluence tool."""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
import platform
import html
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for cross-platform compatibility.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename safe for Windows, macOS, and Linux
    """
    # First, decode HTML entities (e.g., &amp; -> &, &lt; -> <, etc.)
    filename = html.unescape(filename)
    
    # Decode URL-encoded characters (e.g., %2C -> ,, %20 -> space)
    filename = unquote(filename)
    
    # Detect and handle URL-like filenames with query parameters
    # Pattern: filename.ext_param=value&param=value... or filename.ext?param=value
    # This handles cases where URLs were saved as filenames (e.g., from Tango.us)
    if ('&' in filename or '?' in filename) and '=' in filename:
        # Try to extract just the base filename with extension
        # Look for pattern like: uuid.ext followed by _ or ? then query params
        match = re.match(r'^([^&?]+?\.[a-zA-Z0-9]{2,10})[\?_]', filename)
        if match:
            # Extract just the filename.ext part
            filename = match.group(1)
            logger.debug(f"Extracted base filename from URL-like name: {filename}")
    
    # Remove or replace invalid characters
    # Windows invalid chars: < > : " | ? * \ /
    # Also remove control characters
    invalid_chars = r'[<>:"|?*\\/]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Replace ampersands and other problematic characters
    filename = filename.replace('&', '_')
    filename = filename.replace('=', '_')
    
    # Remove control characters (0-31) and DEL (127)
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Remove leading/trailing spaces and dots (Windows doesn't like these)
    filename = filename.strip(' .')
    
    # Handle reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
        'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
        'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in reserved_names:
        filename = f"_{filename}"
    
    # Truncate if too long (keeping extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext) - 3] + "..."
        filename = name + ext
    
    # Ensure filename is not empty
    if not filename or filename == '.':
        filename = 'untitled'
    
    return filename


def create_directory_structure(base_path: str, space_key: str) -> str:
    """Create directory structure for space export.
    
    Args:
        base_path: Base export directory
        space_key: Confluence space key
        
    Returns:
        Path to space-specific directory
    """
    space_dir = os.path.join(base_path, sanitize_filename(space_key))
    
    # Create main directories
    directories = [
        space_dir,
        os.path.join(space_dir, 'pages'),
        os.path.join(space_dir, 'attachments'),
        os.path.join(space_dir, 'metadata')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Created directory: {directory}")
    
    return space_dir


def get_safe_page_filename(title: str, page_id: str, include_id: bool = False,
                          extension: str = '.html') -> str:
    """Generate safe filename for a Confluence page.
    
    Args:
        title: Page title
        page_id: Page ID
        include_id: Whether to include page ID in filename
        extension: File extension
        
    Returns:
        Safe filename for the page
    """
    # Start with sanitized title
    safe_title = sanitize_filename(title)
    
    # Add page ID if requested
    if include_id:
        filename = f"{safe_title}_{page_id}"
    else:
        filename = safe_title
    
    # Add extension
    filename += extension
    
    return filename


def setup_logging(log_level: str = 'INFO', log_file: str = None,
                 log_format: str = None) -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        log_format: Optional log format string
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[]
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    
    # Add file handler if specified
    handlers = [console_handler]
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    # Configure root logger with handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)


def display_spaces_table(spaces: List[Dict[str, Any]]) -> None:
    """Display spaces in a formatted table.
    
    Args:
        spaces: List of space dictionaries
    """
    if not spaces:
        print("No spaces found.")
        return
    
    # Calculate column widths
    key_width = max(len("Key"), max(len(space.get('key', '')) for space in spaces))
    name_width = max(len("Name"), max(len(space.get('name', '')) for space in spaces))
    type_width = max(len("Type"), max(len(space.get('type', '')) for space in spaces))
    
    # Print header
    header = f"{'#':<3} {'Key':<{key_width}} {'Name':<{name_width}} {'Type':<{type_width}} Description"
    print(header)
    print('-' * len(header))
    
    # Print spaces
    for idx, space in enumerate(spaces, 1):
        key = space.get('key', '')
        name = space.get('name', '')
        space_type = space.get('type', '')
        description = space.get('description', {}).get('plain', {}).get('value', '') or ''
        
        # Truncate description if too long
        if len(description) > 50:
            description = description[:47] + '...'
        
        print(f"{idx:<3} {key:<{key_width}} {name:<{name_width}} {space_type:<{type_width}} {description}")


def prompt_space_selection(spaces: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prompt user to select a space from the list.
    
    Args:
        spaces: List of space dictionaries
        
    Returns:
        Selected space dictionary
    """
    if not spaces:
        raise ValueError("No spaces available for selection")
    
    if len(spaces) == 1:
        print(f"Only one space available: {spaces[0]['name']} ({spaces[0]['key']})")
        return spaces[0]
    
    while True:
        display_spaces_table(spaces)
        print(f"\nPlease select a space (1-{len(spaces)}):")
        
        try:
            choice = input("Enter your choice (number or space key): ").strip()
            
            # Try to parse as number first
            try:
                index = int(choice) - 1
                if 0 <= index < len(spaces):
                    selected_space = spaces[index]
                    print(f"Selected: {selected_space['name']} ({selected_space['key']})")
                    return selected_space
                else:
                    print(f"Please enter a number between 1 and {len(spaces)}")
                    continue
            except ValueError:
                pass
            
            # Try to find by space key
            for space in spaces:
                if space['key'].lower() == choice.lower():
                    print(f"Selected: {space['name']} ({space['key']})")
                    return space
            
            print("Invalid selection. Please try again.")
            
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            raise
        except EOFError:
            print("\nOperation cancelled.")
            raise


def get_platform_info() -> Dict[str, str]:
    """Get platform information for cross-platform compatibility.
    
    Returns:
        Dictionary with platform information
    """
    return {
        'system': platform.system(),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0]
    }


def validate_confluence_url(url: str) -> str:
    """Validate and normalize Confluence URL.
    
    Args:
        url: Confluence base URL
        
    Returns:
        Normalized URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Add https:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Basic URL validation
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ValueError("Invalid URL format")
    
    return url


def prompt_target_config_setup() -> str:
    """Interactively create a target environment configuration for import.
    
    Returns:
        Path to created configuration file
        
    Raises:
        KeyboardInterrupt: If user cancels the operation
    """
    import click
    
    print("\n" + "=" * 70)
    print("Target Environment Configuration Setup")
    print("=" * 70)
    print("\nThis import will use a DIFFERENT Confluence environment as the target.")
    print("Let's set up the target environment configuration.\n")
    
    # Get target config filename
    default_filename = "target-config.yaml"
    target_config_path = click.prompt(
        "Enter filename for target configuration",
        default=default_filename,
        type=str
    ).strip()
    
    # Add .yaml extension if not present
    if not target_config_path.endswith(('.yaml', '.yml')):
        target_config_path += '.yaml'
    
    # Check if file exists
    if os.path.exists(target_config_path):
        if not click.confirm(f"\n'{target_config_path}' already exists. Use this existing config?"):
            if not click.confirm("Overwrite it with new configuration?"):
                raise click.Abort("Configuration setup cancelled.")
    
    # If file exists and user chose to use it, return it
    if os.path.exists(target_config_path):
        print(f"\n✓ Using existing configuration: {target_config_path}")
        return target_config_path
    
    # Get target Confluence details
    print("\n--- Target Confluence Instance ---")
    
    while True:
        base_url = click.prompt("Target Confluence URL (e.g., https://target.atlassian.net)", type=str).strip()
        try:
            base_url = validate_confluence_url(base_url)
            break
        except ValueError as e:
            print(f"Error: {e}. Please try again.")
    
    username = click.prompt("Target username/email", type=str).strip()
    
    print("\n🔑 For security, we recommend using an API token.")
    print("To get an API token, visit: https://id.atlassian.com/manage-profile/security/api-tokens")
    
    use_token = click.confirm("Use API token (recommended)?", default=True)
    
    if use_token:
        print("(Type your API token - input is hidden for security)")
        api_token = click.prompt("API token", type=str, hide_input=True, confirmation_prompt=False).strip()
        password = ""
    else:
        print("(Type your password - input is hidden for security)")
        api_token = ""
        password = click.prompt("Password", type=str, hide_input=True, confirmation_prompt=False).strip()
    
    # Create configuration content
    config_content = f"""# Target Environment Configuration for Confluence Import
# Generated during import setup

confluence:
  base_url: "{base_url}"
  auth:
    username: "{username}"
    api_token: "{api_token}"
    password: "{password}"

export:
  output_directory: "./exports"
  format:
    html: true
    attachments: true
    comments: true
  naming:
    include_space_key: true
    sanitize_names: true

import:
  conflict_resolution: "skip"
  create_missing_parents: true
  preserve_page_ids: false
  import_attachments: true
  import_comments: true

general:
  verbose: false
  max_workers: 5
  timeout: 30
  rate_limit: 10
  retry:
    max_attempts: 3
    backoff_factor: 2

logging:
  level: "INFO"
  file: ""
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""
    
    # Write configuration file
    with open(target_config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"\n✓ Target configuration created: {target_config_path}")
    return target_config_path


def extract_original_space_key_from_export(export_dir: str) -> tuple:
    """Extract original space key and name from export directory.
    
    Args:
        export_dir: Path to export directory
        
    Returns:
        Tuple of (space_key, space_name) or (None, None) if not found
    """
    import json
    
    original_space_key = None
    original_space_name = None
    
    try:
        # First try export_summary.json outside the export directory
        parent_dir = os.path.dirname(export_dir)
        export_dirname = os.path.basename(export_dir)
        summary_file = os.path.join(parent_dir, f'{export_dirname}_summary.json')
        
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                original_space_key = summary.get('export_info', {}).get('space_key')
                original_space_name = summary.get('export_info', {}).get('space_name')
        
        # Fallback to space_info.json inside export directory
        if not original_space_key:
            space_info_file = os.path.join(export_dir, 'metadata', 'space_info.json')
            if os.path.exists(space_info_file):
                with open(space_info_file, 'r', encoding='utf-8') as f:
                    space_info = json.load(f)
                    original_space_key = space_info.get('key')
                    original_space_name = space_info.get('name')
    except Exception as e:
        logger.warning(f"Could not read original space info: {e}")
    
    return original_space_key, original_space_name


def prompt_space_key_remapping(original_space_key: str, target_space_key: str, 
                               export_dir: str) -> tuple:
    """Prompt user to decide on space key remapping.
    
    Args:
        original_space_key: Original space key from export
        target_space_key: Target space key for import
        export_dir: Path to export directory (for page count estimation)
        
    Returns:
        Tuple of (should_remap: bool, confirmed_old_key: str, confirmed_new_key: str)
    """
    import click
    
    print()
    print_colored("⚠️  Space Key Conflict Detected", 'YELLOW')
    print()
    print_colored(f"Original space key (from export): {original_space_key}", 'CYAN')
    print_colored(f"Target space key (for import):    {target_space_key}", 'CYAN')
    print()
    print_colored("The original space key is different from the target space key.", 'YELLOW')
    print()
    print("Options:")
    print("  1. Import WITHOUT remapping - Keep original space references as-is")
    print("     (Links to original space key will break)")
    print()
    print("  2. Import WITH remapping - Automatically rewrite all space references")
    print(f"     (All '{original_space_key}' references will be changed to '{target_space_key}')")
    print()
    
    # Try to estimate impact
    pages_dir = os.path.join(export_dir, 'pages')
    page_count = 0
    if os.path.exists(pages_dir):
        page_count = len([f for f in os.listdir(pages_dir) if f.endswith('.html')])
    
    if page_count > 0:
        print_colored(f"Impact: {page_count} pages will be processed", 'CYAN')
        estimated_minutes = max(1, int(page_count / 30))
        print_colored(f"Estimated additional time: {estimated_minutes}-{estimated_minutes * 2} minutes", 'CYAN')
        print()
    
    remap = click.confirm(
        "Do you want to enable space key remapping?",
        default=True
    )
    
    if remap:
        print()
        print_colored("✓ Space key remapping will be enabled", 'GREEN')
        print_colored(f"  All internal references from '{original_space_key}' will be rewritten to '{target_space_key}'", 'GREEN')
        return True, original_space_key, target_space_key
    else:
        print()
        print_colored("⚠️  Space key remapping disabled", 'YELLOW')
        print_colored(f"  Links referencing '{original_space_key}' may not work correctly", 'YELLOW')
        return False, None, None


def prompt_space_creation_with_key_conflict(original_space_key: str, original_space_name: str) -> tuple:
    """Prompt user for space creation when original key is taken.
    
    Args:
        original_space_key: Original space key that's already taken
        original_space_name: Original space name
        
    Returns:
        Tuple of (new_space_key, space_name, should_remap) or (None, None, False) if cancelled
    """
    import click
    
    print()
    print_colored(f"⚠️  Space Key '{original_space_key}' Already Exists", 'YELLOW')
    print()
    print_colored(f"The original space key '{original_space_key}' is already in use.", 'YELLOW')
    print()
    print("Options:")
    print(f"  1. Create a new space with a different key (e.g., {original_space_key}2, {original_space_key}_COPY)")
    print("     and enable space key remapping")
    print()
    print("  2. Cancel import and manually resolve the conflict")
    print()
    
    if not click.confirm("Do you want to create a space with a different key?", default=True):
        return None, None, False
    
    print()
    suggested_key = f"{original_space_key}2"
    new_space_key = click.prompt(
        "Enter new space key",
        default=suggested_key,
        type=str
    ).strip().upper()
    
    # Suggest a name based on the original
    suggested_name = f"{original_space_name} (Copy)" if original_space_name else "Copy"
    space_name = click.prompt(
        "Enter space name",
        default=suggested_name,
        type=str
    ).strip()
    
    print()
    print_colored("Space key remapping is required when using a different space key.", 'CYAN')
    print_colored(f"All internal references from '{original_space_key}' will be rewritten to '{new_space_key}'", 'CYAN')
    print()
    
    if click.confirm("Proceed with space creation and remapping?", default=True):
        return new_space_key, space_name, True
    else:
        return None, None, False


def print_colored(message: str, color: str = 'WHITE') -> None:
    """Print colored message if colors are available.
    
    Args:
        message: Message to print
        color: Color name (RED, GREEN, YELLOW, CYAN, WHITE)
    """
    try:
        from colorama import Fore, Style
        COLORS_AVAILABLE = True
    except ImportError:
        COLORS_AVAILABLE = False
        Fore = Style = type('MockColor', (), {'RED': '', 'GREEN': '', 'YELLOW': '', 'CYAN': '', 'WHITE': '', 'RESET_ALL': ''})()
    
    if COLORS_AVAILABLE:
        color_code = getattr(Fore, color.upper(), '')
        print(f"{color_code}{message}{Style.RESET_ALL}")
    else:
        print(message)