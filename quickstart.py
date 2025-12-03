#!/usr/bin/env python3
"""
Quick Start Script for Confluence Export-Import Tool

This interactive script helps beginners set up the tool step by step.
"""

import os
import sys
import subprocess
import urllib.parse
import re

def check_directory():
    """Check if script is being run from the correct directory."""
    required_files = ['setup.py', 'requirements.txt', 'confluence_tool']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ Error: This script must be run from the repository root directory.")
        print(f"   Missing: {', '.join(missing_files)}")
        print()
        print("Please navigate to the repository root directory and try again:")
        print("   cd Confluence-Export-Import-Tool")
        print(f"   {sys.executable} quickstart.py")
        return False
    return True

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║        Confluence Export-Import Tool - Quick Start          ║
║          Interactive Setup for Export and Import            ║
╚══════════════════════════════════════════════════════════════╝
""")

def print_step(step_num, title):
    print(f"\n🔸 Step {step_num}: {title}")
    print("=" * 50)

def get_input(prompt, default="", required=True):
    """Get user input with optional default and validation."""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                return default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if user_input or not required:
            return user_input
        
        print("❌ This field is required. Please try again.")

def validate_url(url):
    """Validate Confluence URL format."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            return None
        return url.rstrip('/')
    except:
        return None

def validate_email(email):
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_python():
    """Check if Python and pip are available."""
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
        python_version = result.stdout.strip()
        print(f"✅ Python found: {python_version}")
        return True
    except:
        print("❌ Python not found or not working properly")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    print("   This may take a minute...")
    try:
        # First install requirements
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Then install the tool in development mode
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-e', '.'],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're in the repository root directory")
        print("2. Try running in a virtual environment:")
        print(f"   {sys.executable} -m venv .venv")
        if sys.platform == 'win32':
            print("   .venv\\Scripts\\activate")
        else:
            print("   source .venv/bin/activate")
        print(f"   {sys.executable} quickstart.py")
        return False

def create_config():
    """Interactive configuration creation."""
    print_step(2, "Configuration Setup")
    
    print("Let's set up your Confluence connection for the SOURCE environment.")
    print("(This is where you'll export spaces from)")
    print()
    
    # Get Confluence URL
    while True:
        url = get_input("Enter your Confluence URL (e.g., https://yourcompany.atlassian.net)")
        validated_url = validate_url(url)
        if validated_url:
            break
        print("❌ Invalid URL format. Please try again.")
    
    # Get username/email
    while True:
        username = get_input("Enter your Confluence username/email")
        if validate_email(username):
            break
        print("❌ Please enter a valid email address.")
    
    # Get API token
    print("\n🔑 API Token Setup")
    print("For security, we recommend using an API token instead of your password.")
    print("To get an API token:")
    print("1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens")
    print("2. Click 'Create API token'")
    print("3. Enter a label (e.g., 'Confluence Tool')")
    print("4. Copy the generated token")
    
    use_token = get_input("Do you want to use an API token? (y/n)", "y").lower().startswith('y')
    
    if use_token:
        api_token = get_input("Enter your API token", required=True)
        password = ""
    else:
        api_token = ""
        password = get_input("Enter your password", required=True)
        print("⚠️  Note: Using passwords is less secure than API tokens")
    
    # Create configuration content
    config_content = f"""# Confluence Export-Import Tool Configuration
# Generated by quickstart.py

confluence:
  base_url: "{validated_url}"
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
    versions: false
  naming:
    include_space_key: true
    include_page_id: false
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
    with open('config.yaml', 'w') as f:
        f.write(config_content)
    
    print("\n✅ Configuration file created: config.yaml")
    return True


def prompt_target_config():
    """Prompt user to optionally set up a target environment configuration."""
    print_step(3, "Target Environment Setup (Optional)")
    
    print()
    print("You've just set up your SOURCE environment configuration.")
    print()
    print("If you plan to import content to a DIFFERENT Confluence instance,")
    print("you can set up a TARGET environment configuration now.")
    print()
    print("📝 Examples of when you need a target configuration:")
    print("   • Migrating from one Confluence tenant to another")
    print("   • Moving content from production to staging")
    print("   • Backing up to a different Confluence instance")
    print()
    
    try:
        setup_target = input("Do you want to set up a target environment now? (y/N): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n⏭️  Skipping target environment setup.")
        return True
    
    if not setup_target.startswith('y'):
        print("\n⏭️  Skipping target environment setup.")
        print("   You can always run the import command later - it will prompt you")
        print("   to create a target configuration if needed.")
        return True
    
    print("\n--- Target Confluence Instance ---")
    print("(This is where you'll IMPORT content TO)")
    print()
    
    # Get Confluence URL
    while True:
        target_url = get_input("Enter your TARGET Confluence URL (e.g., https://target.atlassian.net)")
        validated_url = validate_url(target_url)
        if validated_url:
            break
        print("❌ Invalid URL format. Please try again.")
    
    # Get username/email
    while True:
        target_username = get_input("Enter your TARGET Confluence username/email")
        if validate_email(target_username):
            break
        print("❌ Please enter a valid email address.")
    
    # Get API token
    print("\n🔑 API Token Setup for Target Environment")
    print("To get an API token:")
    print("1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens")
    print("2. Click 'Create API token'")
    print("3. Enter a label (e.g., 'Confluence Tool - Target')")
    print("4. Copy the generated token")
    
    use_token = get_input("Do you want to use an API token? (y/n)", "y").lower().startswith('y')
    
    if use_token:
        target_api_token = get_input("Enter your API token", required=True)
        target_password = ""
    else:
        target_api_token = ""
        target_password = get_input("Enter your password", required=True)
        print("⚠️  Note: Using passwords is less secure than API tokens")
    
    # Create target configuration content
    target_config_content = f"""# Target Environment Configuration for Confluence Import
# Generated by quickstart.py

confluence:
  base_url: "{validated_url}"
  auth:
    username: "{target_username}"
    api_token: "{target_api_token}"
    password: "{target_password}"

export:
  output_directory: "./exports"
  format:
    html: true
    attachments: true
    comments: true
    versions: false
  naming:
    include_space_key: true
    include_page_id: false
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
    
    # Write target configuration file
    with open('target-config.yaml', 'w') as f:
        f.write(target_config_content)
    
    print("\n✅ Target configuration file created: target-config.yaml")
    print("   Use this with: confluence-tool import /path/to/export --target-config target-config.yaml")
    return True


def test_connection():
    """Test the Confluence connection."""
    print_step(4, "Testing Connection")
    
    print("\nValidating your Confluence connection...")
    # Use platform-appropriate python command in message
    python_cmd = 'python3' if sys.platform != 'win32' else 'python'
    print(f"This runs the command: {python_cmd} -m confluence_tool.main config validate")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'confluence_tool.main', 
            'config', 'validate'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Connection test successful!")
            print(result.stdout)
            return True
        else:
            print("❌ Connection test failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

def show_next_steps(has_target_config=False):
    """Show what the user can do next."""
    print_step(5, "Next Steps and Example Commands")
    
    # Determine platform-appropriate Python command
    python_cmd = 'python3' if sys.platform != 'win32' else 'python'
    
    print("🎉 Setup complete! Here's what you can do now:")
    print()
    print("═" * 60)
    print("📌 RUNNING THE TOOL")
    print("═" * 60)
    print()
    print("After installation with 'pip install -e .', you can use:")
    print("   • confluence-tool [command]                (if in PATH)")
    print(f"   • {python_cmd} -m confluence_tool.main [command]   (always works)")
    print()
    print("If 'confluence-tool' is not found, use the python -m method.")
    print()
    print("═" * 60)
    print("📋 BASIC COMMANDS")
    print("═" * 60)
    print()
    print("List available spaces:")
    print("   confluence-tool list-spaces")
    print()
    print("Export a space:")
    print("   confluence-tool export")
    print("   confluence-tool export --space MYSPACE --output /path/to/output")
    print()
    print("═" * 60)
    print("📥 IMPORT COMMANDS")
    print("═" * 60)
    print()
    print("Import to the SAME environment (uses config.yaml):")
    print("   confluence-tool import ./exports/MYSPACE_20231201_143022/")
    print()
    
    if has_target_config:
        print("Import to the TARGET environment (uses target-config.yaml):")
        print("   confluence-tool import ./exports/MYSPACE_*/ --target-config target-config.yaml")
        print()
    else:
        print("Import to a DIFFERENT environment:")
        print("   confluence-tool import ./exports/MYSPACE_*/ --target-config target-config.yaml")
        print("   (The tool will prompt you to create target-config.yaml if needed)")
        print()
    
    print("Import with options:")
    print("   --conflict-resolution skip       # Skip existing pages (default)")
    print("   --conflict-resolution overwrite  # Replace existing pages")
    print("   --conflict-resolution update_newer  # Update only newer")
    print("   --create-space --new-space-key NEWKEY --space-name 'My Space'")
    print()
    print("═" * 60)
    print("🧹 CLEAN SPACE (For Failed Imports)")
    print("═" * 60)
    print()
    print("If an import fails, you may need to clean the space before retrying:")
    print()
    print("Preview what would be deleted (safe):")
    print("   confluence-tool clean-space SPACEKEY --dry-run")
    print()
    print("Clean same environment (uses config.yaml):")
    print("   confluence-tool clean-space SPACEKEY")
    print()
    if has_target_config:
        print("Clean TARGET environment (uses target-config.yaml):")
        print("   confluence-tool clean-space SPACEKEY --target-config target-config.yaml")
        print()
    else:
        print("Clean a specific environment:")
        print("   confluence-tool clean-space SPACEKEY --target-config target-config.yaml")
        print()
    print("⚠️  WARNING: clean-space permanently deletes all pages!")
    print()
    print("═" * 60)
    print("📖 HELP & CONFIGURATION")
    print("═" * 60)
    print()
    print("View detailed help guide:")
    print("   confluence-tool help-guide")
    print()
    print("Validate configuration:")
    print("   confluence-tool config validate")
    print()
    print("Edit configuration files:")
    print("   config.yaml        - Source environment (for exports)")
    if has_target_config:
        print("   target-config.yaml - Target environment (for imports)")
    print()

def main():
    """Main quickstart flow."""
    print_banner()
    
    # Check if we're in the right directory
    if not check_directory():
        return False
    
    print("This script will help you set up the Confluence Export-Import Tool.")
    print()
    print("ℹ️  This tool allows you to:")
    print("   • Export Confluence spaces from one environment")
    print("   • Import Confluence spaces to the same or different environment")
    print("   • Synchronize content between multiple Confluence instances")
    print()
    print("📝 We'll set up your SOURCE environment first (for exports).")
    print("   Then you can optionally set up a TARGET environment")
    print("   (for imports to a different Confluence instance).")
    print()
    print("Let's get started!")
    
    # Step 1: Check Python and install
    print_step(1, "System Check and Installation")
    
    if not check_python():
        print("Please install Python 3.7+ from https://python.org")
        return False
    
    if not install_dependencies():
        print("Please check the error messages above and try again.")
        return False
    
    # Step 2: Create source configuration
    if not create_config():
        return False
    
    # Step 3: Optionally set up target configuration
    has_target_config = False
    if prompt_target_config():
        # Check if target-config.yaml was created
        has_target_config = os.path.exists('target-config.yaml')
    
    # Step 4: Test connection
    if test_connection():
        show_next_steps(has_target_config)
        return True
    else:
        print("\n❌ Setup completed with connection issues.")
        print("Please check your configuration in config.yaml and try again.")
        print("\nTo validate your connection manually, run:")
        python_cmd = 'python3' if sys.platform != 'win32' else 'python'
        print(f"  {python_cmd} -m confluence_tool.main config validate")
        print("Or if installed:")
        print("  confluence-tool config validate")
        return False

if __name__ == '__main__':
    try:
        success = main()
        if success:
            print("\n🎉 Quick start completed successfully!")
        else:
            print("\n⚠️  Quick start completed with issues. Please review the messages above.")
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)