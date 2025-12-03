# Troubleshooting Guide

This guide helps you diagnose and fix common issues with the Confluence Export-Import Tool.

## Common Gotchas

Before diving into specific issues, check these common mistakes:

### ❌ "confluence-tool: command not found"
**Problem:** After installing, running `confluence-tool` gives "command not found" error.

**This is not a bug!** It means your Python scripts directory isn't in your PATH.

**Solution:** Use the Python module method instead - it always works:

**macOS/Linux:**
```bash
python3 -m confluence_tool.main --help
python3 -m confluence_tool.main list-spaces
python3 -m confluence_tool.main export
```

**Windows:**
```bash
python -m confluence_tool.main --help
python -m confluence_tool.main list-spaces
python -m confluence_tool.main export
```

Alternatively, add Python scripts to your PATH:
- macOS/Linux: Add `export PATH="$HOME/.local/bin:$PATH"` to your shell profile
- Windows: Add `%APPDATA%\Python\Python3X\Scripts` to your system PATH

### ❌ Running quickstart.py from the wrong directory
**Problem:** Running `python quickstart.py` from anywhere other than the repository root.

**Solution:** Always navigate to the repository root first:
```bash
cd Confluence-Export-Import-Tool
python3 quickstart.py  # macOS/Linux
```

### ❌ Using `python` instead of `python3` on macOS/Linux
**Problem:** macOS and Linux systems often have Python 2 as `python` and Python 3 as `python3`.

**Solution:** Always use `python3` on macOS/Linux:
```bash
python3 quickstart.py
python3 -m pip install -e .
```

### ❌ Not activating virtual environment
**Problem:** Creating a virtual environment but forgetting to activate it.

**Solution:** Always activate after creating:
```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux - YOU MUST DO THIS!
# Now you'll see (.venv) in your prompt
```

### ❌ Installing outside virtual environment when one exists
**Problem:** Installing packages globally when you meant to use a virtual environment.

**Solution:** Check if virtual environment is active (look for `(.venv)` in prompt):
```bash
# If you see (.venv) in your prompt, you're good!
(.venv) user@mac Confluence-Export-Import-Tool %

# If not, activate it:
source .venv/bin/activate
```

## Quick Diagnosis

Before diving into specific issues, try these general diagnostic steps:

1. **Test your configuration**:
   ```bash
   confluence-tool config validate
   ```

2. **Run with verbose logging**:
   ```bash
   confluence-tool --verbose [your-command]
   ```

3. **Check the tool version**:
   ```bash
   confluence-tool --help
   ```

## Installation Issues

### Quickstart Script Issues

**Problem**: `python quickstart.py` fails or doesn't work

**Solutions**:

1. **Use the correct Python command for your system**:
   
   **macOS/Linux:**
   ```bash
   python3 quickstart.py
   ```
   
   **Windows:**
   ```cmd
   python quickstart.py
   ```

2. **Ensure you're in the repository root directory**:
   ```bash
   cd Confluence-Export-Import-Tool
   ls -la  # You should see setup.py, requirements.txt, and confluence_tool/
   python3 quickstart.py  # macOS/Linux
   ```

3. **Run in a virtual environment** (recommended):
   
   **macOS/Linux:**
   ```bash
   cd Confluence-Export-Import-Tool
   python3 -m venv .venv
   source .venv/bin/activate
   python3 quickstart.py
   ```
   
   **Windows:**
   ```cmd
   cd Confluence-Export-Import-Tool
   python -m venv .venv
   .venv\Scripts\activate
   python quickstart.py
   ```

4. **Check Python version**:
   ```bash
   python3 --version  # macOS/Linux
   python --version   # Windows
   ```
   Must be Python 3.7 or higher.

5. **Install manually if quickstart fails**:
   ```bash
   pip3 install -r requirements.txt  # macOS/Linux
   pip3 install -e .
   ```

### "Command not found" Error

**Problem**: `confluence-tool: command not found`

**Solutions**:

1. **Check if installation completed**:
   ```bash
   pip show confluence-export-import-tool
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

3. **Check PATH (if using --user install)**:
   ```bash
   # Add to your shell profile (.bashrc, .zshrc, etc.)
   export PATH="$HOME/.local/bin:$PATH"
   ```

4. **Reinstall the tool**:
   ```bash
   pip uninstall confluence-export-import-tool
   pip install -e .
   ```

### Permission Errors During Installation

**Problem**: Permission denied errors when running `pip install`

**Solutions**:

1. **Use user installation**:
   ```bash
   pip install --user -r requirements.txt
   pip install --user -e .
   ```

2. **Use virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   pip install -e .
   ```

3. **On Linux/Mac, use sudo (not recommended)**:
   ```bash
   sudo pip install -r requirements.txt
   sudo pip install -e .
   ```

### Python Version Issues

**Problem**: Tool requires Python 3.7+ but you have an older version

**Solutions**:

1. **Install Python 3.7+** from [python.org](https://python.org)

2. **Use specific Python version**:
   ```bash
   python3.9 -m pip install -e .
   python3.9 -m confluence_tool.main --help
   ```

## Configuration Issues

### Configuration File Not Found

**Problem**: `Configuration file not found`

**Solutions**:

1. **Create configuration file**:
   ```bash
   confluence-tool config create
   ```

2. **Specify config file location**:
   ```bash
   confluence-tool --config /path/to/config.yaml [command]
   ```

3. **Check expected locations**:
   - Current directory: `./config.yaml`
   - Home directory: `~/.confluence_tool_config.yaml`

### Invalid Configuration Format

**Problem**: `Invalid YAML in config file` or `Error loading config file`

**Solutions**:

1. **Validate YAML syntax** using an online YAML validator

2. **Check for common YAML errors**:
   - Incorrect indentation (use spaces, not tabs)
   - Missing quotes around special characters
   - Unescaped quotes in strings

3. **Recreate configuration**:
   ```bash
   mv config.yaml config.yaml.backup
   confluence-tool config create
   ```

### Missing Required Configuration

**Problem**: `Confluence username is required` or similar messages

**Solutions**:

1. **Check required fields in config.yaml**:
   ```yaml
   confluence:
     base_url: "https://your-domain.atlassian.net"
     auth:
       username: "your-email@example.com"
       api_token: "your-token"  # or password
   ```

2. **Ensure no empty values**:
   ```yaml
   # Bad
   username: ""
   
   # Good  
   username: "user@example.com"
   ```

## Connection Issues

### HTTP 404 Not Found Error on Confluence Cloud

**Problem**: `404 Client Error: Not Found for url: https://yourcompany.atlassian.net/rest/api/space`

**Cause**: This tool now automatically detects Confluence Cloud vs Server/Data Center instances and uses the correct API path. Confluence Cloud requires `/wiki/rest/api/` while Server/Data Center uses `/rest/api/`.

**Solutions**:

1. **The fix is automatic** - As of version 1.0.1, the tool automatically detects `.atlassian.net` domains and uses the correct path. Simply ensure you're using the latest version.

2. **Verify your URL format**:
   - ✅ Correct: `https://yourcompany.atlassian.net`
   - ❌ Wrong: `https://yourcompany.atlassian.net/wiki`
   - ❌ Wrong: `https://yourcompany.atlassian.net/`
   
   The tool will automatically add `/wiki` for Cloud instances.

3. **Test your connection**:
   
   **macOS/Linux:**
   ```bash
   confluence-tool config validate
   # Or if not installed as command:
   python3 -m confluence_tool.main config validate
   ```
   
   **Windows:**
   ```bash
   confluence-tool config validate
   # Or if not installed as command:
   python -m confluence_tool.main config validate
   ```

4. **For self-hosted Server/Data Center**, ensure your URL is:
   ```yaml
   confluence:
     base_url: "https://confluence.yourcompany.com"  # No /wiki needed
   ```

### Authentication Failed

**Problem**: `Authentication failed. Please check your credentials.`

**Solutions**:

1. **Verify API token**:
   - Check if token is expired
   - Generate new token at: https://id.atlassian.com/manage-profile/security/api-tokens
   - Copy token exactly (no extra spaces)

2. **For server instances, try password**:
   ```yaml
   auth:
     username: "your-username"
     password: "your-password"
     api_token: ""  # Leave empty
   ```

3. **Check username format**:
   - Cloud: Use email address
   - Server: May use username or email

### Connection Timeout

**Problem**: `Request timeout` or `Connection error`

**Solutions**:

1. **Increase timeout in config**:
   ```yaml
   general:
     timeout: 120  # Increase from default 30 seconds
   ```

2. **Check network connectivity**:
   ```bash
   ping your-domain.atlassian.net
   curl -I https://your-domain.atlassian.net
   ```

3. **Try with fewer concurrent workers**:
   ```yaml
   general:
     max_workers: 2  # Reduce from default 5
   ```

### Rate Limiting

**Problem**: `Rate limited` or `429 Too Many Requests`

**Solutions**:

1. **Reduce rate limit**:
   ```yaml
   general:
     rate_limit: 5  # Reduce from default 10
   ```

2. **Increase retry settings**:
   ```yaml
   general:
     retry:
       max_attempts: 5
       backoff_factor: 3
   ```

### Permission Denied

**Problem**: `Permission denied` or `403 Forbidden`

**Solutions**:

1. **Check Confluence permissions**:
   - Ensure you have read access to spaces you're exporting
   - Ensure you have write access to spaces you're importing to

2. **Verify space exists and is accessible**:
   ```bash
   confluence-tool list-spaces
   ```

3. **Check if space is restricted**:
   - Log into Confluence web interface
   - Verify you can access the space manually

## Export Issues

### Large Space Export Fails

**Problem**: Export fails or times out with large spaces

**Solutions**:

1. **Increase timeouts**:
   ```yaml
   general:
     timeout: 300  # 5 minutes
   ```

2. **Reduce concurrent operations**:
   ```yaml
   general:
     max_workers: 2
   ```

3. **Skip large components**:
   ```yaml
   export:
     format:
       attachments: false  # Skip large attachments
       versions: false     # Skip page history
   ```

4. **Export in smaller batches** (manually select smaller spaces)

### Attachment Download Fails

**Problem**: `Failed to download attachment` errors, especially 404 errors

**Root Cause**: For Confluence Cloud instances (*.atlassian.net), attachment download URLs need `/wiki` prepended to work with API token authentication. The tool now automatically handles this for Cloud instances.

**Solutions**:

1. **Verify you're using the latest code**: The fix automatically prepends `/wiki` to download URLs for Cloud instances.

2. **Check disk space**:
   ```bash
   df -h  # Linux/Mac
   dir    # Windows
   ```

3. **Increase timeout for large files**:
   ```yaml
   general:
     timeout: 600  # 10 minutes for very large attachments
   ```

4. **Verify attachment permissions**:
   - Ensure your API token has permission to access attachments
   - Check if attachments are restricted in Confluence
   - Verify the attachments exist in the Confluence UI

### Folders Not Exported or Imported

**Problem**: No folders appear in the export or import fails to recreate folders

**Root Cause**: Folders are only available in Confluence Cloud via the v2 API. They are not available in Confluence Server or Data Center instances.

**Solutions**:

1. **Verify you're using Confluence Cloud**:
   - Folders are only supported on Confluence Cloud (*.atlassian.net domains)
   - Server/Data Center instances do not have folder functionality via API
   
2. **Check the export logs**:
   - The tool will log: "Folders API not available (likely Server/DC instance or old Cloud)"
   - This is normal for Server/DC instances and older Cloud instances
   
3. **Verify folder export**:
   ```bash
   # Check if folders were exported
   ls -la exports/SPACEKEY_*/folders/
   cat exports/SPACEKEY_*/folders/folders_metadata.json
   ```

4. **For Cloud instances, ensure API v2 is available**:
   - Some older Confluence Cloud instances may not have v2 API enabled
   - The tool may return "Folders API returned server error" if the API is not fully supported
   - Contact Atlassian support if folders should be available but aren't

5. **Check import summary**:
   - After import, check the import_summary.json for folder statistics
   - Look for `folders_imported` count in the statistics section

**Note**: The absence of folder support is not an error condition. The tool will continue to export/import pages and other content normally even if folders are not available.

5. **Skip attachments temporarily** (for debugging):
   ```yaml
   export:
     format:
       attachments: false
   ```

6. **Enable debug logging** to see detailed download attempts:
   ```yaml
   logging:
     level: "DEBUG"
     file: "debug.log"
   ```

**Technical Details**: 
- For Cloud: Uses `/wiki/download/attachments/...` with API authentication
- For Server/DC: Uses `/download/attachments/...` directly
- The tool automatically detects and applies the correct format based on your Confluence URL

### Invalid File Names

**Problem**: `Invalid filename` or file creation errors

**Solutions**:

1. **Enable filename sanitization**:
   ```yaml
   export:
     naming:
       sanitize_names: true
   ```

2. **Check file path length** (Windows has 260 character limit)

3. **Use shorter output directory path**

## Import Issues

### Page Already Exists

**Problem**: Pages fail to import because they already exist

**Solutions**:

1. **Change conflict resolution**:
   ```yaml
   import:
     conflict_resolution: "overwrite"  # or "rename"
   ```

2. **Skip existing pages**:
   ```yaml
   import:
     conflict_resolution: "skip"
   ```

### Cannot Recreate Space with Same Key (Confluence Cloud)

**Problem**: Cannot create space - "Space key already exists" error even though the space was deleted.

**Cause**: Confluence Cloud retains deleted space keys indefinitely, preventing space recreation with the same key.

**Solution**: Use space key remapping to import with a different space key:
```bash
confluence-tool import /path/to/export \
  --remap-space-key OLD:NEW \
  --create-space \
  --new-space-key NEW \
  --space-name "Your Space Name"
```

This will automatically rewrite all internal space references from OLD to NEW, maintaining link integrity.

**Example:**
```bash
# Original space was "KB", but key is retained by Confluence
confluence-tool import ./exports/KB_20251002 \
  --remap-space-key KB:KB2 \
  --create-space \
  --new-space-key KB2 \
  --space-name "Knowledge Base"
```

### Broken Links After Import

**Problem**: Links between pages don't work after importing to a different space key.

**Cause**: Internal links reference the original space key, which doesn't match the target space.

**Solution**: Use space key remapping during import:
```bash
confluence-tool import /path/to/export \
  --remap-space-key ORIGINAL:TARGET \
  --space TARGET
```

The tool will automatically rewrite:
- Confluence XML links (`<ri:space-key>`)
- Wiki links (`[Title|SPACE:Page]`)
- HTML anchors (`/wiki/spaces/SPACE/...`)
- Macro space references
- Attachment references

**Note:** Space key remapping increases import time (~2-3x) as all content must be scanned and rewritten. You'll see detailed statistics after import completes.

### Pages Appear Partially Missing or Truncated

**Problem**: Some pages appear incomplete in the target environment - they show only a few lines or sections where the source page has much more content.

**Cause**: This was caused by a bug in the HTML content extraction that occurred when pages contained nested `<div>` elements (common in Confluence pages with sections, macros, tables, etc.). The bug has been fixed in recent versions.

**Solution**: 

1. **Update to the latest version** if you're experiencing this issue:
   ```bash
   cd /path/to/Confluence-Export-Import-Tool
   git pull
   pip install -e .
   ```

2. **Re-export the space** to ensure clean HTML files:
   ```bash
   confluence-tool export SPACEKEY
   ```

3. **Re-import the pages**:
   ```bash
   confluence-tool import ./exports/SPACEKEY_* --space TARGETSPACE
   ```

**Technical Details**: The fix ensures that nested HTML structures (div elements within div elements) are properly handled during content extraction. Pages with complex formatting, macros, and nested sections will now be imported completely.

### Parent Page Not Found

**Problem**: `Parent page not found` errors

**Note**: As of version 1.0.1, the tool uses a multi-pass import strategy that automatically imports pages in the correct order, handling complex parent-child relationships. This significantly reduces parent page not found errors.

**How it works**:
- Root pages (no parents) are imported first
- Child pages are imported in multiple passes
- Each pass only imports pages whose parents have been successfully imported
- The process continues until all pages are imported or no further progress can be made

**If you still encounter errors**:

1. **Verify parent creation is enabled** (default):
   ```yaml
   import:
     create_missing_parents: true
   ```

2. **Check for missing pages in export**: The parent page may not have been exported
   - Review the export summary to ensure all pages were exported
   - Re-export the space if pages are missing

3. **Import to root level** if parent relationships are broken:
   ```yaml
   import:
     create_missing_parents: false
   ```
   Then organize pages manually after import

### Attachment Upload Fails

**Problem**: Attachments fail to upload during import, especially with 400 Bad Request errors

**Common Causes**:
- Filenames with HTML-encoded characters (e.g., `&amp;`, `&lt;`, `&gt;`)
- Filenames with URL-encoded characters (e.g., `%2C`, `%20`)
- Invalid characters in attachment filenames

**Note**: The tool now automatically sanitizes filenames by decoding HTML entities and URL-encoded characters. If you're experiencing these issues, ensure you're using the latest version.

**Solutions**:

1. **Check target space permissions**:
   - Ensure you can upload attachments to the target space
   - Check space attachment size limits

2. **Disable attachment import temporarily**:
   ```yaml
   import:
     import_attachments: false
   ```

3. **Increase upload timeout**:
   ```yaml
   general:
     timeout: 300
   ```

4. **Verify filename sanitization is working**:
   - The tool automatically decodes HTML entities (`&amp;` → `&`)
   - The tool automatically decodes URL encoding (`%2C` → `,`)
   - Special characters are replaced with underscores for filesystem safety

### Import Fails Partway Through

**Problem**: Import fails after importing some pages, and you need to retry

**Solution**: Use the `clean-space` command to delete all pages before retrying

1. **First, preview what would be deleted**:
   ```bash
   confluence-tool clean-space MYSPACE --dry-run
   
   # For multi-environment setup
   confluence-tool clean-space MYSPACE --dry-run --target-config staging-config.yaml
   ```

2. **If confirmed, clean the space**:
   ```bash
   confluence-tool clean-space MYSPACE
   
   # For multi-environment setup
   confluence-tool clean-space MYSPACE --target-config staging-config.yaml
   ```
   
   The tool will:
   - Show all pages that will be deleted
   - Ask for confirmation twice
   - Require you to type "I CONFIRM" to proceed
   - Show progress with a progress bar
   - Provide a detailed summary report

3. **Retry the import**:
   ```bash
   confluence-tool import /path/to/export --space MYSPACE
   
   # For multi-environment setup
   confluence-tool import /path/to/export --space MYSPACE --target-config staging-config.yaml
   ```

**Important Notes**:
- ⚠️ The clean-space operation cannot be undone
- Make sure you have a backup if needed
- Use `--dry-run` first to preview the deletion
- The command has multiple safety confirmations to prevent accidental deletions
- Use `--target-config` to specify which environment to clean

**Alternative**: If you don't want to delete pages, you can:
- Use `--conflict-resolution skip` to skip existing pages
- Use `--conflict-resolution rename` to rename imported pages with timestamps
- Import to a different space using `--create-space --new-space-key NEWKEY`

## Performance Issues

### Slow Export/Import

**Problem**: Operations take too long

**Solutions**:

1. **Optimize concurrent operations**:
   ```yaml
   general:
     max_workers: 8  # Increase if your system can handle it
   ```

2. **Increase rate limit** (if your Confluence instance allows):
   ```yaml
   general:
     rate_limit: 15
   ```

3. **Reduce exported content**:
   ```yaml
   export:
     format:
       comments: false
       versions: false
   ```

### High Memory Usage

**Problem**: Tool uses too much memory with large spaces

**Solutions**:

1. **Reduce concurrent operations**:
   ```yaml
   general:
     max_workers: 2
   ```

2. **Process smaller batches** (export spaces individually)

3. **Close other applications** during large operations

## Platform-Specific Issues

### Windows Issues

**Problem**: Path or filename issues on Windows

**Solutions**:

1. **Use short paths**:
   ```yaml
   export:
     output_directory: "C:\\exp"  # Instead of long paths
   ```

2. **Enable filename sanitization**:
   ```yaml
   export:
     naming:
       sanitize_names: true
   ```

3. **Run as Administrator** if you get permission errors

### macOS Issues

**Problem**: SSL certificate, permission issues, or commands not working

**Solutions**:

1. **Always use `python3` and `pip3` commands**:
   ```bash
   python3 --version      # Check Python version
   pip3 install -e .      # Install tool
   python3 quickstart.py  # Run quickstart
   python3 -m confluence_tool.main --help  # Run tool directly
   ```

2. **Update certificates**:
   ```bash
   # Find your Python version first
   python3 --version
   
   # Then run the certificate installer (replace 3.x with your version)
   /Applications/Python\ 3.12/Install\ Certificates.command
   ```

3. **Use virtual environment to avoid permission issues**:
   ```bash
   cd Confluence-Export-Import-Tool
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   # Now you can run: confluence-tool --help
   ```

4. **If command still not found after installation**:
   ```bash
   # Check where pip installed the command
   which confluence-tool
   
   # If not found, run directly
   python3 -m confluence_tool.main --help
   
   # Or add to PATH in ~/.zshrc or ~/.bash_profile
   export PATH="$HOME/Library/Python/3.x/bin:$PATH"  # Replace 3.x with your version
   ```

5. **For Apple Silicon (M1/M2/M3) Macs**:
   - Make sure you have native ARM Python installed
   - Some dependencies may need Rosetta 2, but this tool should work natively
   - If issues persist, try using Homebrew Python: `brew install python@3.12`

### Linux Issues

**Problem**: Missing dependencies or permission issues

**Solutions**:

1. **Install required packages**:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3-pip python3-venv
   
   # CentOS/RHEL
   sudo yum install python3-pip
   ```

2. **Use virtual environment**:
   ```bash
   python3 -m venv confluence-env
   source confluence-env/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

## Getting More Help

### Enable Debug Logging

Add detailed logging to help diagnose issues:

```yaml
logging:
  level: "DEBUG"
  file: "debug.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
```

Then run your command and check the `debug.log` file.

### Create Support Request

When creating a support request, include:

1. **Your environment**:
   ```bash
   python --version
   pip show confluence-export-import-tool
   uname -a  # Linux/Mac
   systeminfo  # Windows
   ```

2. **The exact command** you were running

3. **The complete error message**

4. **Your configuration** (remove sensitive information):
   ```yaml
   confluence:
     base_url: "https://[REDACTED].atlassian.net"
     auth:
       username: "[REDACTED]@example.com"
       api_token: "[REDACTED]"
   ```

5. **Debug logs** (if possible)

### Common Log Messages

- **"Rate limited. Waiting X seconds"**: Normal, the tool is handling rate limits
- **"Connection error on attempt X"**: Temporary network issue, tool will retry
- **"Authentication failed"**: Check your credentials
- **"Permission denied"**: Check Confluence permissions
- **"Request timeout"**: Increase timeout in config
- **"Failed to download attachment"**: Disk space or network issue
- **"Failed to upload attachment ... 400 Client Error: Bad Request"**: Fixed in latest version - update to resolve filename encoding issues

Remember: Most issues are configuration-related. Double-check your `config.yaml` file first!