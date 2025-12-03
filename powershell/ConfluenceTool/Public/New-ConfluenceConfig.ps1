function New-ConfluenceConfig {
    <#
    .SYNOPSIS
        Create a new Confluence configuration file interactively.
    
    .DESCRIPTION
        Creates a new YAML configuration file with user-provided settings.
        Supports interactive input for all configuration options and validates
        the connection before saving.
    
    .PARAMETER Path
        Path where the configuration file should be created
    
    .PARAMETER Force
        Overwrite existing configuration file if it exists
    
    .PARAMETER Interactive
        Use interactive prompts to gather configuration (default)
    
    .PARAMETER BaseUrl
        Base URL of the Confluence instance (non-interactive)
    
    .PARAMETER Username
        Username for authentication (non-interactive)
    
    .PARAMETER ApiToken
        API token for authentication (non-interactive)
    
    .PARAMETER Template
        Create configuration template with placeholder values
    
    .EXAMPLE
        New-ConfluenceConfig -Path "prod-config.yaml"
        
        Creates a new configuration file with interactive prompts.
    
    .EXAMPLE
        New-ConfluenceConfig -Path "config.yaml" -Template
        
        Creates a template configuration file with placeholder values.
    
    .EXAMPLE
        New-ConfluenceConfig -Path "config.yaml" -BaseUrl "https://company.atlassian.net" -Username "user@company.com" -ApiToken "token123"
        
        Creates a configuration file with provided values (non-interactive).
    
    .OUTPUTS
        Boolean indicating success or failure
    #>
    
    [CmdletBinding(DefaultParameterSetName = 'Interactive')]
    param(
        [Parameter(Mandatory = $false)]
        [string] $Path = "config.yaml",
        
        [Parameter(Mandatory = $false)]
        [switch] $Force,
        
        [Parameter(Mandatory = $false, ParameterSetName = 'Interactive')]
        [switch] $Interactive = $true,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
        [ValidateNotNullOrEmpty()]
        [string] $BaseUrl,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
        [ValidateNotNullOrEmpty()]
        [string] $Username,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
        [ValidateNotNullOrEmpty()]
        [string] $ApiToken,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Template')]
        [switch] $Template
    )
    
    try {
        # Check if file already exists
        if ((Test-Path $Path) -and -not $Force) {
            $overwrite = Read-Host "Configuration file already exists at '$Path'. Overwrite? (y/N)"
            if ($overwrite -notmatch '^[Yy]') {
                Write-Host "Configuration creation cancelled." -ForegroundColor Yellow
                return $false
            }
        }
        
        # Create configuration object
        $config = @{
            confluence = @{
                base_url = ""
                auth = @{
                    username = ""
                    api_token = ""
                }
            }
            export = @{
                output_directory = "./exports"
                format = @{
                    html = $true
                    attachments = $true
                    comments = $true
                }
            }
            import = @{
                conflict_resolution = "skip"
                create_missing_parents = $true
            }
            general = @{
                max_workers = 5
                timeout = 30
                rate_limit = 10
                logging_level = "INFO"
            }
        }
        
        if ($PSCmdlet.ParameterSetName -eq 'Template') {
            # Create template with placeholder values
            $config.confluence.base_url = "https://your-domain.atlassian.net"
            $config.confluence.auth.username = "your-email@domain.com"
            $config.confluence.auth.api_token = "your-api-token-here"
            
            Write-Host "Creating configuration template..." -ForegroundColor Yellow
        }
        elseif ($PSCmdlet.ParameterSetName -eq 'Direct') {
            # Use provided values
            $config.confluence.base_url = $BaseUrl
            $config.confluence.auth.username = $Username
            $config.confluence.auth.api_token = $ApiToken
            
            Write-Host "Creating configuration with provided values..." -ForegroundColor Yellow
        }
        else {
            # Interactive mode
            Write-Host ""
            Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
            Write-Host "║              Confluence Configuration Setup                  ║" -ForegroundColor Cyan
            Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
            Write-Host ""
            
            Write-Host "Please provide your Confluence connection details:" -ForegroundColor White
            Write-Host ""
            
            # Get Confluence URL
            do {
                $baseUrl = Read-Host "Confluence Base URL (e.g., https://company.atlassian.net)"
                if ([string]::IsNullOrWhiteSpace($baseUrl)) {
                    Write-Warning "Base URL is required."
                    continue
                }
                
                # Basic URL validation
                if (-not $baseUrl.StartsWith("http")) {
                    Write-Warning "URL should start with http:// or https://"
                    continue
                }
                
                $config.confluence.base_url = $baseUrl.TrimEnd('/')
                break
                
            } while ($true)
            
            # Get username
            do {
                $username = Read-Host "Username/Email"
                if ([string]::IsNullOrWhiteSpace($username)) {
                    Write-Warning "Username is required."
                    continue
                }
                
                $config.confluence.auth.username = $username
                break
                
            } while ($true)
            
            # Get API token
            Write-Host ""
            Write-Host "For Atlassian Cloud instances, use an API token instead of your password." -ForegroundColor Yellow
            Write-Host "You can create an API token at: https://id.atlassian.com/manage-profile/security/api-tokens" -ForegroundColor Yellow
            Write-Host ""
            
            do {
                $apiToken = Read-Host "API Token" -AsSecureString
                $apiTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiToken))
                
                if ([string]::IsNullOrWhiteSpace($apiTokenPlain)) {
                    Write-Warning "API Token is required."
                    continue
                }
                
                $config.confluence.auth.api_token = $apiTokenPlain
                break
                
            } while ($true)
            
            Write-Host ""
            Write-Host "Optional: Configure additional settings" -ForegroundColor Cyan
            
            # Export directory
            $exportDir = Read-Host "Export directory [./exports]"
            if (-not [string]::IsNullOrWhiteSpace($exportDir)) {
                $config.export.output_directory = $exportDir
            }
            
            # Rate limit
            $rateLimit = Read-Host "API rate limit (requests per second) [10]"
            if ($rateLimit -match '^\d+$') {
                $config.general.rate_limit = [int]$rateLimit
            }
        }
        
        # Convert to YAML and save
        $yamlContent = ConvertTo-ConfluenceYaml -Config $config
        Set-Content -Path $Path -Value $yamlContent -Encoding UTF8
        
        Write-Host ""
        Write-Host "✓ Configuration saved to: $Path" -ForegroundColor Green
        
        # Test connection if not template mode
        if ($PSCmdlet.ParameterSetName -ne 'Template') {
            Write-Host ""
            $testConnection = Read-Host "Test connection now? (Y/n)"
            
            if ($testConnection -notmatch '^[Nn]') {
                Write-Host "Testing connection..." -ForegroundColor Yellow
                
                $configManager = [ConfigManager]::new($Path)
                if ($configManager.TestConnection()) {
                    Write-Host "✓ Connection successful!" -ForegroundColor Green
                } else {
                    Write-Warning "Connection test failed. Please verify your settings in $Path"
                    return $false
                }
            }
        }
        
        return $true
        
    } catch {
        Write-Error "Failed to create configuration: $($_.Exception.Message)"
        return $false
    }
}

function ConvertTo-ConfluenceYaml {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Config
    )
    
    $yaml = @()
    $yaml += "# Confluence Export-Import Tool Configuration"
    $yaml += "# Generated on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $yaml += ""
    
    $yaml += "confluence:"
    $yaml += "  base_url: `"$($Config.confluence.base_url)`""
    $yaml += "  auth:"
    $yaml += "    username: `"$($Config.confluence.auth.username)`""
    $yaml += "    api_token: `"$($Config.confluence.auth.api_token)`""
    $yaml += ""
    
    $yaml += "export:"
    $yaml += "  output_directory: `"$($Config.export.output_directory)`""
    $yaml += "  format:"
    $yaml += "    html: $($Config.export.format.html.ToString().ToLower())"
    $yaml += "    attachments: $($Config.export.format.attachments.ToString().ToLower())"
    $yaml += "    comments: $($Config.export.format.comments.ToString().ToLower())"
    $yaml += ""
    
    $yaml += "import:"
    $yaml += "  conflict_resolution: `"$($Config.import.conflict_resolution)`""
    $yaml += "  create_missing_parents: $($Config.import.create_missing_parents.ToString().ToLower())"
    $yaml += ""
    
    $yaml += "general:"
    $yaml += "  max_workers: $($Config.general.max_workers)"
    $yaml += "  timeout: $($Config.general.timeout)"
    $yaml += "  rate_limit: $($Config.general.rate_limit)"
    $yaml += "  logging_level: `"$($Config.general.logging_level)`""
    
    return $yaml -join "`n"
}