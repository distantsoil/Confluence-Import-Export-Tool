# Installation Guide

This guide will help you install and set up the Confluence Export-Import Tool on your system.

## Prerequisites

Before installing the tool, make sure you have:

1. **Python 3.7 or higher** installed on your system
2. **pip** (Python package installer) - usually comes with Python
3. **Internet connection** for downloading dependencies
4. **Confluence access** with appropriate permissions

## Check Python Installation

First, verify that Python is installed and check the version:

### Windows
```cmd
python --version
```

If Python is not recognized, try:
```cmd
py --version
```

### macOS/Linux
```bash
python3 --version
```

If you don't have Python installed, download it from [python.org](https://www.python.org/downloads/).

## Installation Methods

### Method 1: Quick Install with Quickstart Script (Recommended for Beginners)

The quickstart script automates the installation process and guides you through setup:

1. **Download the Tool**
   - Download the ZIP file from GitHub or clone the repository:
   ```bash
   git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
   cd Confluence-Export-Import-Tool
   ```

2. **Run the Quickstart Script**
   
   **macOS/Linux:**
   ```bash
   python3 quickstart.py
   ```
   
   **Windows:**
   ```cmd
   python quickstart.py
   ```
   
   The script will:
   - Check your Python version
   - Install all dependencies automatically
   - Guide you through configuration
   - Test your Confluence connection
   
   > **Important:** Always run quickstart.py from the repository root directory (Confluence-Export-Import-Tool).

### Method 2: Manual Installation

1. **Download the Tool**
   ```bash
   git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
   cd Confluence-Export-Import-Tool
   ```

2. **Install Dependencies**
   
   **macOS/Linux:**
   ```bash
   pip3 install -r requirements.txt
   pip3 install -e .
   ```
   
   **Windows:**
   ```cmd
   pip install -r requirements.txt
   pip install -e .
   ```

### Method 3: Virtual Environment (Recommended for Advanced Users)

Using a virtual environment isolates the tool's dependencies from your system Python:

1. **Create Virtual Environment**
   
   **macOS/Linux:**
   ```bash
   cd Confluence-Export-Import-Tool
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   
   **Windows:**
   ```cmd
   cd Confluence-Export-Import-Tool
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install the Tool**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Verify Installation**
   ```bash
   confluence-tool --help
   ```

4. **When you're done, deactivate the virtual environment:**
   ```bash
   deactivate
   ```
   
   > **Note:** You'll need to activate the virtual environment each time you want to use the tool:
   > - macOS/Linux: `source .venv/bin/activate`
   > - Windows: `.venv\Scripts\activate`
   >
   > **Or run the quickstart script in the virtual environment:**
   > ```bash
   > source .venv/bin/activate  # macOS/Linux
   > python3 quickstart.py
   > ```

## Verify Installation

After installation, verify that the tool is working:

```bash
confluence-tool --help
```

If `confluence-tool` is not found, use the Python module method instead:

**macOS/Linux:**
```bash
python3 -m confluence_tool.main --help
```

**Windows:**
```bash
python -m confluence_tool.main --help
```

The Python module method always works regardless of PATH configuration.

## Running the Tool

You have two options for running commands:

### Option 1: Direct Command (Recommended if in PATH)
```bash
confluence-tool list-spaces
confluence-tool export
confluence-tool import ./exports/MYSPACE_*/
```

### Option 2: Python Module (Always Works)
```bash
# macOS/Linux
python3 -m confluence_tool.main list-spaces
python3 -m confluence_tool.main export
python3 -m confluence_tool.main import ./exports/MYSPACE_*/

# Windows
python -m confluence_tool.main list-spaces
python -m confluence_tool.main export  
python -m confluence_tool.main import ./exports/MYSPACE_*/
```

**Tip:** If the `confluence-tool` command is not found, use the Python module method. It's not a bug - it means your Python scripts directory isn't in your PATH.

## Platform-Specific Notes

### macOS

- **Python Command:** Use `python3` and `pip3` instead of `python` and `pip`
- **Terminal:** Use Terminal or iTerm2
- **Quickstart Script:** Always run with `python3 quickstart.py`
- **Virtual Environment:** Recommended to avoid system Python conflicts
- **Permission Issues:** If you get permission errors, use a virtual environment or the `--user` flag: `pip3 install --user -r requirements.txt`
- **SSL Certificates:** If you get SSL errors, run:
  ```bash
  /Applications/Python\ 3.x/Install\ Certificates.command
  ```
  (Replace `3.x` with your Python version, e.g., `3.12`)

### Windows

- Use Command Prompt or PowerShell
- If you get a "command not found" error, use `python -m confluence_tool.main` instead
- Make sure Python Scripts directory is in your PATH

### Linux

- Use your distribution's terminal
- You might need to install `python3-pip` first: `sudo apt install python3-pip` (Ubuntu/Debian)
- If you get permission errors, try using `--user` flag or `sudo`

## Troubleshooting

### "Command not found" Error

If you get a "command not found" error after installation:

1. **Check if pip installed to user directory**:
   ```bash
   python -m pip show confluence-export-import-tool
   ```

2. **Try running directly with platform-appropriate Python command**:
   
   **macOS/Linux:**
   ```bash
   python3 -m confluence_tool.main --help
   ```
   
   **Windows:**
   ```bash
   python -m confluence_tool.main --help
   ```

3. **Add pip user directory to PATH** (if using --user):
   - Windows: Add `%APPDATA%\Python\Python3X\Scripts` to PATH
   - macOS/Linux: Add `~/.local/bin` to PATH

### Permission Errors

If you get permission errors during installation:

- **Windows**: Run Command Prompt as Administrator
- **macOS/Linux**: Use `--user` flag or `sudo`

### Dependency Conflicts

If you encounter dependency conflicts:

1. Use a virtual environment (see Method 2 above)
2. Update pip: `pip install --upgrade pip`
3. Try installing with `--force-reinstall` flag

## Next Steps

After successful installation:

1. **Create Configuration**: `confluence-tool config create`
2. **Edit Configuration**: Open `config.yaml` and add your Confluence details
3. **Test Connection**: `confluence-tool config validate`
4. **Read the Guide**: `confluence-tool help-guide`

## Complete Workflow Example (macOS)

Here's a complete example of getting started on macOS:

```bash
# 1. Clone the repository
git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
cd Confluence-Export-Import-Tool

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Run quickstart (recommended) or install manually
python3 quickstart.py

# OR install manually:
# pip install -r requirements.txt
# pip install -e .

# 4. The tool is now installed and ready to use
confluence-tool --help

# 5. List available spaces
confluence-tool list-spaces

# 6. Export a space
confluence-tool export
```

**Remember:** Each time you open a new terminal, you need to activate the virtual environment:
```bash
cd Confluence-Export-Import-Tool
source .venv/bin/activate
confluence-tool --help
```

## Complete Workflow Example (Windows)

Here's a complete example of getting started on Windows:

```cmd
REM 1. Clone the repository
git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
cd Confluence-Export-Import-Tool

REM 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

REM 3. Run quickstart (recommended) or install manually
python quickstart.py

REM OR install manually:
REM pip install -r requirements.txt
REM pip install -e .

REM 4. The tool is now installed and ready to use
confluence-tool --help

REM 5. List available spaces
confluence-tool list-spaces

REM 6. Export a space
confluence-tool export
```

**Remember:** Each time you open a new Command Prompt, you need to activate the virtual environment:
```cmd
cd Confluence-Export-Import-Tool
.venv\Scripts\activate
confluence-tool --help
```

## Complete Workflow Example (Linux)

Here's a complete example of getting started on Linux:

```bash
# 1. Clone the repository
git clone https://github.com/distantsoil/Confluence-Export-Import-Tool.git
cd Confluence-Export-Import-Tool

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Run quickstart (recommended) or install manually
python3 quickstart.py

# OR install manually:
# pip install -r requirements.txt
# pip install -e .

# 4. The tool is now installed and ready to use
confluence-tool --help

# 5. List available spaces
confluence-tool list-spaces

# 6. Export a space
confluence-tool export
```

**Remember:** Each time you open a new terminal, you need to activate the virtual environment:
```bash
cd Confluence-Export-Import-Tool
source .venv/bin/activate
confluence-tool --help
```

## Getting Help

If you encounter issues:

1. Check the main [README.md](README.md) for detailed usage instructions
2. Use the built-in help: `confluence-tool help-guide`
3. Enable verbose logging: `confluence-tool --verbose [command]`
4. Create an issue on GitHub with:
   - Your operating system and Python version
   - The exact error message
   - The command you were trying to run