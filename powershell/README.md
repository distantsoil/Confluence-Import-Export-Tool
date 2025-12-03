# Confluence Export-Import Tool (PowerShell Edition)

**Experimental Cross-Platform PowerShell Module**

This is an experimental PowerShell implementation of the Confluence Export-Import Tool, designed to provide cross-platform compatibility with both Windows PowerShell and PowerShell Core on macOS and Linux.

## 🚀 Features

### Currently Available
- ✅ **Cross-Platform Compatibility**: Works on Windows, macOS, and Linux
- ✅ **Stable PowerShell Support**: No beta versions required
- ✅ **Complete Export System**: Export entire Confluence spaces
- ✅ **Interactive Space Selection**: User-friendly space browsing
- ✅ **Configuration Management**: YAML-based configuration
- ✅ **Connection Testing**: Validate credentials and connectivity
- ✅ **Comprehensive Help System**: Built-in documentation

### Planned for Future Releases
- ⏳ **Import System**: Import exported spaces to different environments
- ⏳ **Multi-Environment Sync**: Synchronize content between instances
- ⏳ **Space Comparison**: Compare spaces across environments
- ⏳ **Attachment Support**: Full attachment download and upload

## 🔧 System Requirements

### Windows
- **PowerShell 5.1** or later (included with Windows 10/11)
- **.NET Framework 4.7.2** or later
- Internet connectivity to Confluence instance

### macOS/Linux
- **PowerShell Core 6.0** or later
- **.NET Core 2.0** or later
- Internet connectivity to Confluence instance

### Check Your PowerShell Version
```powershell
$PSVersionTable
```

## 📦 Installation

### 1. Download the Module
Clone or download this repository to your local machine.

### 2. Import the Module
```powershell
# Navigate to the PowerShell module directory
cd /path/to/Confluence-Export-Import-Tool/powershell

# Import the module
Import-Module ./ConfluenceTool/ConfluenceTool.psd1 -Verbose
```

### 3. Verify Installation
```powershell
# Check available commands
Get-Command -Module ConfluenceTool

# View help
Show-ConfluenceHelp
```

## 🚀 Quick Start

### 1. Create Configuration
```powershell
# Interactive configuration setup
New-ConfluenceConfig -Path "config.yaml"

# Or create from template
New-ConfluenceConfig -Path "config.yaml" -Template
```

### 2. Test Connection
```powershell
Test-ConfluenceConfig -ConfigFile "config.yaml" -ShowDetails
```

### 3. Export a Space
```powershell
# Interactive space selection
Export-ConfluenceSpace -ConfigFile "config.yaml" -Interactive

# Export specific space
Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey "DOCS"
```

## 📋 Available Commands

### Configuration Management
```powershell
# Create new configuration
New-ConfluenceConfig -Path "config.yaml"

# Test configuration
Test-ConfluenceConfig -ConfigFile "config.yaml"
```

### Connection and Spaces
```powershell
# Connect to Confluence
$client = Connect-ConfluenceAPI -ConfigFile "config.yaml" -TestConnection

# List all spaces
Get-ConfluenceSpaces -ConfigFile "config.yaml" -Interactive

# Get pages from a space
Get-ConfluencePages -ConfigFile "config.yaml" -SpaceKey "DOCS"
```

### Export Operations
```powershell
# Basic export
Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey "DOCS"

# Custom export location
Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey "DOCS" -OutputPath "./my-exports"

# Export without attachments
Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey "DOCS" -IncludeAttachments $false
```

### Help and Documentation
```powershell
# Main help
Show-ConfluenceHelp

# Specific topics
Show-ConfluenceHelp -Topic Setup
Show-ConfluenceHelp -Topic Export
Show-ConfluenceHelp -Topic Examples
```

## ⚙️ Configuration

Configuration is stored in YAML format:

```yaml
# config.yaml
confluence:
  base_url: "https://your-domain.atlassian.net"
  auth:
    username: "your-email@domain.com"
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

general:
  max_workers: 5
  timeout: 30
  rate_limit: 10
  logging_level: "INFO"
```

### Getting API Credentials

1. **For Atlassian Cloud** (recommended):
   - Go to: [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Click "Create API token"
   - Enter a label and copy the token

2. **For Server instances**:
   - Use your regular username and password
   - Some servers may support API tokens

## 🌍 Multi-Environment Setup

Create separate configuration files for different environments:

```powershell
# Production environment
New-ConfluenceConfig -Path "prod-config.yaml"

# Staging environment  
New-ConfluenceConfig -Path "staging-config.yaml"

# Backup environment
New-ConfluenceConfig -Path "backup-config.yaml"
```

### Cross-Environment Operations

```powershell
# Export from production
Export-ConfluenceSpace -ConfigFile "prod-config.yaml" -SpaceKey "DOCS" -OutputPath "./prod-backup"

# Basic comparison between environments
Show-BasicSpaceComparison -SourceConfig "prod-config.yaml" -TargetConfig "staging-config.yaml" -SpaceKey "DOCS"
```

> **Note**: Full import and sync capabilities are planned for future releases. Currently, you can export with PowerShell and import using the Python version of this tool.

## 📁 Export Structure

Exported spaces are organized as follows:

```
SPACENAME-YYYYMMDD-HHMMSS/
├── pages/                  # HTML files for each page
├── metadata/               # JSON metadata for each page
├── attachments/            # Downloaded attachments (if enabled)
├── README.md               # Human-readable export summary
└── export-summary.json     # Detailed export information
```

## 🔍 Examples

### Basic Workflow
```powershell
# 1. Setup
Import-Module ./ConfluenceTool/ConfluenceTool.psd1
New-ConfluenceConfig -Path "config.yaml"

# 2. Test
Test-ConfluenceConfig -ConfigFile "config.yaml" -ShowDetails

# 3. Browse spaces
Get-ConfluenceSpaces -ConfigFile "config.yaml" -Interactive

# 4. Export
Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey "DOCS"
```

### Programmatic Usage
```powershell
# Direct API client usage
$client = Connect-ConfluenceAPI -BaseUrl "https://company.atlassian.net" -Username "user@company.com" -ApiToken "token"
$spaces = $client.GetSpaces()
$pages = $client.GetPages("DOCS")
$client.Dispose()
```

### Batch Export
```powershell
# Export multiple spaces
$spaces = Get-ConfluenceSpaces -ConfigFile "config.yaml"
$spaces | Where-Object { $_.type -eq "global" } | ForEach-Object {
    Export-ConfluenceSpace -ConfigFile "config.yaml" -SpaceKey $_.key
}
```

## ❗ Troubleshooting

### Common Issues

**Authentication Errors**
```powershell
# Test your configuration
Test-ConfluenceConfig -ConfigFile "config.yaml" -ShowDetails

# Verify API token
# - Check token hasn't expired
# - Ensure email address is correct
# - Try regenerating the token
```

**PowerShell Version Issues**
```powershell
# Check your PowerShell version
$PSVersionTable

# Windows: Requires PowerShell 5.1+
# macOS/Linux: Requires PowerShell Core 6.0+
```

**Connection Issues**
```powershell
# Verify URL and connectivity
# - Test URL in browser
# - Check firewall/proxy settings
# - Verify account has API access
```

### Getting Help
```powershell
Show-ConfluenceHelp -Topic Troubleshooting
```

## 🔮 Roadmap

### Version 1.1 (Planned)
- Import functionality
- Attachment support
- Progress bars and better UI

### Version 1.2 (Planned) 
- Multi-environment synchronization
- Space comparison tools
- Advanced conflict resolution

### Version 2.0 (Future)
- Full feature parity with Python version
- Advanced filtering and selection
- Automated scheduling

## 🤝 Comparison with Python Version

| Feature | PowerShell (Current) | Python Version |
|---------|---------------------|----------------|
| Export | ✅ Available | ✅ Available |
| Import | ⏳ Planned | ✅ Available |
| Multi-env Sync | ⏳ Planned | ✅ Available |
| Space Comparison | ⏳ Planned | ✅ Available |
| Cross-platform | ✅ Yes | ✅ Yes |
| Dependencies | Minimal | Python + packages |
| Setup Complexity | Low | Medium |

## 📄 License

This project is licensed under the same terms as the main Confluence Export-Import Tool.

## 🔗 Related Resources

- [Main Python Tool](../README.md)
- [Installation Guide](../INSTALL.md)
- [Multi-Environment Guide](../MULTI_ENVIRONMENT.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)

---

**Note**: This is an experimental PowerShell implementation. For production use, consider the mature Python version which has full feature support.