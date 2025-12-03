function Show-ConfluenceHelp {
    <#
    .SYNOPSIS
        Display comprehensive help and usage information for the Confluence Tool.
    
    .DESCRIPTION
        Shows detailed help information including setup instructions, usage examples,
        and troubleshooting guidance for the PowerShell Confluence Export-Import Tool.
    
    .PARAMETER Topic
        Specific help topic to display (Setup, Export, Import, Config, Examples, MultiEnvironment)
    
    .EXAMPLE
        Show-ConfluenceHelp
        
        Shows the main help overview.
    
    .EXAMPLE
        Show-ConfluenceHelp -Topic Setup
        
        Shows detailed setup instructions.
    
    .EXAMPLE
        Show-ConfluenceHelp -Topic Examples
        
        Shows usage examples.
    #>
    
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [ValidateSet('Overview', 'Setup', 'Export', 'Import', 'Config', 'Examples', 'MultiEnvironment', 'Troubleshooting')]
        [string] $Topic = 'Overview'
    )
    
    switch ($Topic) {
        'Overview' { Show-OverviewHelp }
        'Setup' { Show-SetupHelp }
        'Export' { Show-ExportHelp }
        'Import' { Show-ImportHelp }
        'Config' { Show-ConfigHelp }
        'Examples' { Show-ExamplesHelp }
        'MultiEnvironment' { Show-MultiEnvironmentHelp }
        'Troubleshooting' { Show-TroubleshootingHelp }
    }
}

function Show-OverviewHelp {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║          Confluence Export-Import Tool (PowerShell)          ║" -ForegroundColor Cyan
    Write-Host "║                      Version 1.0.0                          ║" -ForegroundColor Cyan
    Write-Host "║                  Cross-Platform Compatible                   ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "OVERVIEW" -ForegroundColor Yellow
    Write-Host "--------" -ForegroundColor Yellow
    Write-Host "This PowerShell module provides comprehensive tools for exporting and importing"
    Write-Host "Confluence spaces using the Confluence REST API. It supports:"
    Write-Host ""
    Write-Host "✓ Cross-platform compatibility (Windows PowerShell 5.1+ & PowerShell Core 6.0+)"
    Write-Host "✓ Complete space export with pages, attachments, and metadata"
    Write-Host "✓ Multi-environment support (export from one instance, import to another)"
    Write-Host "✓ Interactive space selection and configuration"
    Write-Host "✓ Secure API token authentication"
    Write-Host "✓ Robust error handling and progress tracking"
    Write-Host ""
    
    Write-Host "AVAILABLE COMMANDS" -ForegroundColor Yellow
    Write-Host "------------------" -ForegroundColor Yellow
    Write-Host "Configuration:"
    Write-Host "  New-ConfluenceConfig      Create configuration file"
    Write-Host "  Test-ConfluenceConfig     Validate configuration and test connection"
    Write-Host ""
    Write-Host "Connection:"
    Write-Host "  Connect-ConfluenceAPI     Connect to Confluence instance"
    Write-Host ""
    Write-Host "Space Operations:"
    Write-Host "  Get-ConfluenceSpaces      List all spaces"
    Write-Host "  Export-ConfluenceSpace    Export space to local files"
    Write-Host "  Import-ConfluenceSpace    Import space from local files"
    Write-Host ""
    Write-Host "Multi-Environment:"
    Write-Host "  Sync-ConfluenceSpaces     Synchronize spaces between environments"
    Write-Host "  Compare-ConfluenceSpaces  Compare spaces across environments"
    Write-Host ""
    Write-Host "Help:"
    Write-Host "  Show-ConfluenceHelp       Show detailed help (this command)"
    Write-Host ""
    
    Write-Host "QUICK START" -ForegroundColor Yellow
    Write-Host "-----------" -ForegroundColor Yellow
    Write-Host "1. Create configuration:    New-ConfluenceConfig -Path 'config.yaml'"
    Write-Host "2. Test configuration:      Test-ConfluenceConfig -ConfigFile 'config.yaml'"
    Write-Host "3. Export a space:          Export-ConfluenceSpace -configFile 'config.yaml' -Interactive"
    Write-Host ""
    
    Write-Host "DETAILED HELP TOPICS" -ForegroundColor Yellow
    Write-Host "--------------------" -ForegroundColor Yellow
    Write-Host "For detailed information on specific topics, use:"
    Write-Host "  Show-ConfluenceHelp -Topic Setup            # Initial setup and configuration"
    Write-Host "  Show-ConfluenceHelp -Topic Export           # Exporting spaces"
    Write-Host "  Show-ConfluenceHelp -Topic Import           # Importing spaces"
    Write-Host "  Show-ConfluenceHelp -Topic Config           # Configuration options"
    Write-Host "  Show-ConfluenceHelp -Topic Examples         # Usage examples"
    Write-Host "  Show-ConfluenceHelp -Topic MultiEnvironment # Multi-environment operations"
    Write-Host "  Show-ConfluenceHelp -Topic Troubleshooting  # Common issues and solutions"
    Write-Host ""
    
    Write-Host "SYSTEM REQUIREMENTS" -ForegroundColor Yellow
    Write-Host "-------------------" -ForegroundColor Yellow
    Write-Host "• PowerShell 5.1+ (Windows) or PowerShell Core 6.0+ (macOS/Linux)"
    Write-Host "• .NET Framework 4.7.2+ (Windows) or .NET Core 2.0+ (macOS/Linux)"
    Write-Host "• Internet connectivity to reach your Confluence instance"
    Write-Host "• Valid Confluence user account with API access"
    Write-Host ""
}

function Show-SetupHelp {
    Write-Host ""
    Write-Host "SETUP GUIDE" -ForegroundColor Cyan
    Write-Host "============" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "STEP 1: INSTALL THE MODULE" -ForegroundColor Yellow
    Write-Host "---------------------------" -ForegroundColor Yellow
    Write-Host "If you haven't already imported the module:"
    Write-Host "  Import-Module ./ConfluenceTool.psd1 -Verbose"
    Write-Host ""
    
    Write-Host "STEP 2: GET API CREDENTIALS" -ForegroundColor Yellow
    Write-Host "----------------------------" -ForegroundColor Yellow
    Write-Host "For Atlassian Cloud instances (recommended):"
    Write-Host "1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens"
    Write-Host "2. Click 'Create API token'"
    Write-Host "3. Enter a label (e.g., 'Confluence Tool')"
    Write-Host "4. Copy the generated token (keep it secure!)"
    Write-Host ""
    Write-Host "For Server instances:"
    Write-Host "• You can use your regular username and password"
    Write-Host "• API tokens may also be supported depending on your server version"
    Write-Host ""
    
    Write-Host "STEP 3: CREATE CONFIGURATION" -ForegroundColor Yellow
    Write-Host "-----------------------------" -ForegroundColor Yellow
    Write-Host "Interactive setup (recommended for beginners):"
    Write-Host "  New-ConfluenceConfig -Path 'config.yaml'"
    Write-Host ""
    Write-Host "Create from template:"
    Write-Host "  New-ConfluenceConfig -Path 'config.yaml' -Template"
    Write-Host ""
    Write-Host "Direct creation:"
    Write-Host "  New-ConfluenceConfig -Path 'config.yaml' -BaseUrl 'https://company.atlassian.net' -Username 'user@company.com' -ApiToken 'your-token'"
    Write-Host ""
    
    Write-Host "STEP 4: TEST YOUR CONFIGURATION" -ForegroundColor Yellow
    Write-Host "--------------------------------" -ForegroundColor Yellow
    Write-Host "  Test-ConfluenceConfig -ConfigFile 'config.yaml' -ShowDetails"
    Write-Host ""
    Write-Host "If the test fails, check:"
    Write-Host "• URL is correct and accessible"
    Write-Host "• Username and API token are valid"
    Write-Host "• Your account has permission to access the Confluence instance"
    Write-Host ""
    
    Write-Host "STEP 5: START USING THE TOOL" -ForegroundColor Yellow
    Write-Host "-----------------------------" -ForegroundColor Yellow
    Write-Host "List available spaces:"
    Write-Host "  Get-ConfluenceSpaces -ConfigFile 'config.yaml' -Interactive"
    Write-Host ""
    Write-Host "Export a space:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -Interactive"
    Write-Host ""
}

function Show-ExportHelp {
    Write-Host ""
    Write-Host "EXPORT GUIDE" -ForegroundColor Cyan
    Write-Host "=============" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "The export function creates local copies of Confluence spaces including:"
    Write-Host "• All pages converted to HTML format"
    Write-Host "• Page metadata (version, creation date, etc.)"
    Write-Host "• Page attachments (if enabled)"
    Write-Host "• Comments (if enabled)"
    Write-Host "• Space metadata and structure"
    Write-Host ""
    
    Write-Host "BASIC EXPORT" -ForegroundColor Yellow
    Write-Host "------------" -ForegroundColor Yellow
    Write-Host "Interactive space selection:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -Interactive"
    Write-Host ""
    Write-Host "Export specific space:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS'"
    Write-Host ""
    Write-Host "Custom output location:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS' -OutputPath './my-exports'"
    Write-Host ""
    
    Write-Host "ADVANCED OPTIONS" -ForegroundColor Yellow
    Write-Host "----------------" -ForegroundColor Yellow
    Write-Host "Exclude attachments:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS' -IncludeAttachments `$false"
    Write-Host ""
    Write-Host "Exclude comments:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS' -IncludeComments `$false"
    Write-Host ""
    Write-Host "Adjust concurrency:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS' -MaxConcurrency 10"
    Write-Host ""
    
    Write-Host "EXPORT STRUCTURE" -ForegroundColor Yellow
    Write-Host "----------------" -ForegroundColor Yellow
    Write-Host "Exported files are organized as follows:"
    Write-Host "  SPACENAME-YYYYMMDD-HHMMSS/"
    Write-Host "  ├── pages/              # HTML files for each page"
    Write-Host "  ├── metadata/           # JSON metadata for each page"
    Write-Host "  ├── attachments/        # Downloaded attachments"
    Write-Host "  ├── README.md           # Human-readable export summary"
    Write-Host "  └── export-summary.json # Detailed export information"
    Write-Host ""
}

function Show-ExamplesHelp {
    Write-Host ""
    Write-Host "USAGE EXAMPLES" -ForegroundColor Cyan
    Write-Host "===============" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "BASIC WORKFLOW" -ForegroundColor Yellow
    Write-Host "--------------" -ForegroundColor Yellow
    Write-Host "# 1. Create configuration"
    Write-Host "New-ConfluenceConfig -Path 'prod-config.yaml'"
    Write-Host ""
    Write-Host "# 2. Test the configuration"
    Write-Host "Test-ConfluenceConfig -ConfigFile 'prod-config.yaml'"
    Write-Host ""
    Write-Host "# 3. List available spaces"
    Write-Host "Get-ConfluenceSpaces -ConfigFile 'prod-config.yaml'"
    Write-Host ""
    Write-Host "# 4. Export a space"
    Write-Host "Export-ConfluenceSpace -ConfigFile 'prod-config.yaml' -SpaceKey 'DOCS'"
    Write-Host ""
    
    Write-Host "MULTI-ENVIRONMENT EXAMPLE" -ForegroundColor Yellow
    Write-Host "--------------------------" -ForegroundColor Yellow
    Write-Host "# Create separate configs for different environments"
    Write-Host "New-ConfluenceConfig -Path 'prod-config.yaml'"
    Write-Host "New-ConfluenceConfig -Path 'staging-config.yaml'"
    Write-Host ""
    Write-Host "# Export from production"
    Write-Host "Export-ConfluenceSpace -ConfigFile 'prod-config.yaml' -SpaceKey 'DOCS' -OutputPath './prod-export'"
    Write-Host ""
    Write-Host "# Import to staging (when import functionality is available)"
    Write-Host "# Import-ConfluenceSpace -ConfigFile 'staging-config.yaml' -ImportPath './prod-export/DOCS-*'"
    Write-Host ""
    
    Write-Host "BATCH OPERATIONS" -ForegroundColor Yellow
    Write-Host "----------------" -ForegroundColor Yellow
    Write-Host "# Export multiple spaces"
    Write-Host "`$spaces = Get-ConfluenceSpaces -ConfigFile 'config.yaml'"
    Write-Host "`$spaces | Where-Object { `$_.type -eq 'global' } | ForEach-Object {"
    Write-Host "    Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey `$_.key"
    Write-Host "}"
    Write-Host ""
    
    Write-Host "PROGRAMMATIC USAGE" -ForegroundColor Yellow
    Write-Host "------------------" -ForegroundColor Yellow
    Write-Host "# Direct API client usage"
    Write-Host "`$client = Connect-ConfluenceAPI -BaseUrl 'https://company.atlassian.net' -Username 'user@company.com' -ApiToken 'token'"
    Write-Host "`$spaces = `$client.GetSpaces()"
    Write-Host "`$pages = `$client.GetPages('DOCS')"
    Write-Host "`$client.Dispose()"
    Write-Host ""
}

function Show-MultiEnvironmentHelp {
    Write-Host ""
    Write-Host "MULTI-ENVIRONMENT OPERATIONS" -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "The PowerShell version supports multi-environment operations by using"
    Write-Host "separate configuration files for different Confluence instances."
    Write-Host ""
    
    Write-Host "SETUP MULTIPLE ENVIRONMENTS" -ForegroundColor Yellow
    Write-Host "----------------------------" -ForegroundColor Yellow
    Write-Host "# Production environment"
    Write-Host "New-ConfluenceConfig -Path 'prod-config.yaml'"
    Write-Host ""
    Write-Host "# Staging environment"
    Write-Host "New-ConfluenceConfig -Path 'staging-config.yaml'"
    Write-Host ""
    Write-Host "# Backup environment"
    Write-Host "New-ConfluenceConfig -Path 'backup-config.yaml'"
    Write-Host ""
    
    Write-Host "CROSS-ENVIRONMENT EXPORT/IMPORT" -ForegroundColor Yellow
    Write-Host "--------------------------------" -ForegroundColor Yellow
    Write-Host "# Export from production"
    Write-Host "Export-ConfluenceSpace -ConfigFile 'prod-config.yaml' -SpaceKey 'DOCS' -OutputPath './prod-backup'"
    Write-Host ""
    Write-Host "# Import to backup environment (when import is implemented)"  
    Write-Host "# Import-ConfluenceSpace -ConfigFile 'backup-config.yaml' -ImportPath './prod-backup/DOCS-*'"
    Write-Host ""
    
    Write-Host "ENVIRONMENT COMPARISON" -ForegroundColor Yellow
    Write-Host "----------------------" -ForegroundColor Yellow
    Write-Host "# Compare spaces between environments (when implemented)"
    Write-Host "# Compare-ConfluenceSpaces -SourceConfig 'prod-config.yaml' -TargetConfig 'staging-config.yaml' -SpaceKey 'DOCS'"
    Write-Host ""
    
    Write-Host "USE CASES" -ForegroundColor Yellow
    Write-Host "---------" -ForegroundColor Yellow
    Write-Host "• Disaster Recovery: Export production → Import to backup"
    Write-Host "• Content Distribution: Export from central → Import to regional"
    Write-Host "• Environment Sync: Keep staging current with production"
    Write-Host "• Multi-site Management: Distribute content across multiple instances"
    Write-Host ""
}

function Show-TroubleshootingHelp {
    Write-Host ""
    Write-Host "TROUBLESHOOTING GUIDE" -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "COMMON ISSUES AND SOLUTIONS" -ForegroundColor Yellow
    Write-Host "---------------------------" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Authentication Errors:" -ForegroundColor Red
    Write-Host "• Error: 'Authentication failed'"
    Write-Host "  Solution: Verify username and API token are correct"
    Write-Host "  - Check token hasn't expired"
    Write-Host "  - Ensure email address is correct for username"
    Write-Host "  - Try regenerating the API token"
    Write-Host ""
    
    Write-Host "Connection Errors:" -ForegroundColor Red
    Write-Host "• Error: 'Connection test failed'"
    Write-Host "  Solution: Check network connectivity and URL"
    Write-Host "  - Verify the base URL is correct"
    Write-Host "  - Check firewall/proxy settings"
    Write-Host "  - Test URL in browser"
    Write-Host ""
    
    Write-Host "Permission Errors:" -ForegroundColor Red
    Write-Host "• Error: 'Access forbidden' or '403'"
    Write-Host "  Solution: Verify account permissions"
    Write-Host "  - Ensure account has space access"
    Write-Host "  - Check if account has API access enabled"
    Write-Host "  - Contact Confluence administrator"
    Write-Host ""
    
    Write-Host "Rate Limiting:" -ForegroundColor Red
    Write-Host "• Error: 'Rate limit exceeded' or '429'"
    Write-Host "  Solution: Adjust rate limiting in configuration"
    Write-Host "  - Reduce 'rate_limit' value in config.yaml"
    Write-Host "  - Add delays between requests"
    Write-Host "  - Consider running during off-peak hours"
    Write-Host ""
    
    Write-Host "PowerShell Version Issues:" -ForegroundColor Red
    Write-Host "• Error: Module compatibility issues"
    Write-Host "  Solution: Check PowerShell version"
    Write-Host "  - Windows: PowerShell 5.1 or later required"
    Write-Host "  - macOS/Linux: PowerShell Core 6.0 or later required"
    Write-Host "  - Run: `$PSVersionTable to check version"
    Write-Host ""
    
    Write-Host "DIAGNOSTIC COMMANDS" -ForegroundColor Yellow
    Write-Host "-------------------" -ForegroundColor Yellow
    Write-Host "Check PowerShell version:"
    Write-Host "  `$PSVersionTable"
    Write-Host ""
    Write-Host "Test configuration in detail:"
    Write-Host "  Test-ConfluenceConfig -ConfigFile 'config.yaml' -ShowDetails"
    Write-Host ""
    Write-Host "Enable verbose output:"
    Write-Host "  Export-ConfluenceSpace -ConfigFile 'config.yaml' -SpaceKey 'DOCS' -Verbose"
    Write-Host ""
    
    Write-Host "GETTING HELP" -ForegroundColor Yellow
    Write-Host "-------------" -ForegroundColor Yellow
    Write-Host "If you continue to experience issues:"
    Write-Host "1. Check the module documentation"
    Write-Host "2. Verify your Confluence version compatibility"
    Write-Host "3. Test with a simple space first"
    Write-Host "4. Enable verbose logging for detailed error information"
    Write-Host ""
}

function Show-ConfigHelp {
    Write-Host ""
    Write-Host "CONFIGURATION GUIDE" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "The configuration file uses YAML format and contains all settings"
    Write-Host "needed to connect to and interact with your Confluence instance."
    Write-Host ""
    
    Write-Host "CONFIGURATION STRUCTURE" -ForegroundColor Yellow
    Write-Host "-----------------------" -ForegroundColor Yellow
    Write-Host "confluence:"
    Write-Host "  base_url: 'https://your-domain.atlassian.net'"
    Write-Host "  auth:"
    Write-Host "    username: 'your-email@domain.com'"
    Write-Host "    api_token: 'your-api-token'"
    Write-Host ""
    Write-Host "export:"
    Write-Host "  output_directory: './exports'"
    Write-Host "  format:"
    Write-Host "    html: true"
    Write-Host "    attachments: true"
    Write-Host "    comments: true"
    Write-Host ""
    Write-Host "import:"
    Write-Host "  conflict_resolution: skip"
    Write-Host "  create_missing_parents: true"
    Write-Host ""
    Write-Host "general:"
    Write-Host "  max_workers: 5"
    Write-Host "  timeout: 30"
    Write-Host "  rate_limit: 10"
    Write-Host "  logging_level: INFO"
    Write-Host ""
    
    Write-Host "CONFIGURATION OPTIONS" -ForegroundColor Yellow
    Write-Host "---------------------" -ForegroundColor Yellow
    Write-Host "confluence.base_url:"
    Write-Host "  Your Confluence instance URL (required)"
    Write-Host "  Example: https://company.atlassian.net"
    Write-Host ""
    Write-Host "confluence.auth.username:"
    Write-Host "  Your username or email address (required)"
    Write-Host ""
    Write-Host "confluence.auth.api_token:"
    Write-Host "  API token for authentication (recommended)"
    Write-Host "  Get from: https://id.atlassian.com/manage-profile/security/api-tokens"
    Write-Host ""
    Write-Host "export.output_directory:"
    Write-Host "  Where exported files are saved (default: ./exports)"
    Write-Host ""
    Write-Host "general.rate_limit:"
    Write-Host "  Max requests per second (default: 10)"
    Write-Host "  Reduce if hitting rate limits"
    Write-Host ""
    Write-Host "general.timeout:"
    Write-Host "  Request timeout in seconds (default: 30)"
    Write-Host ""
}

function Show-ImportHelp {
    Write-Host ""
    Write-Host "IMPORT GUIDE" -ForegroundColor Cyan
    Write-Host "=============" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Import functionality is planned for future versions of this experimental"
    Write-Host "PowerShell implementation. It will support:"
    Write-Host ""
    Write-Host "PLANNED FEATURES" -ForegroundColor Yellow
    Write-Host "----------------" -ForegroundColor Yellow
    Write-Host "• Import pages from exported HTML/JSON format"
    Write-Host "• Preserve page hierarchy and relationships"
    Write-Host "• Handle conflict resolution (skip/overwrite/rename)"
    Write-Host "• Upload attachments and restore metadata"
    Write-Host "• Cross-environment import capabilities"
    Write-Host ""
    
    Write-Host "CURRENT WORKAROUND" -ForegroundColor Yellow
    Write-Host "------------------" -ForegroundColor Yellow
    Write-Host "For now, you can:"
    Write-Host "1. Use the Python version for import functionality"
    Write-Host "2. Manually recreate pages using the exported HTML content"
    Write-Host "3. Use Confluence's built-in import features with the exported data"
    Write-Host ""
    
    Write-Host "The import functionality will be added in a future update to this"
    Write-Host "experimental PowerShell version."
    Write-Host ""
}