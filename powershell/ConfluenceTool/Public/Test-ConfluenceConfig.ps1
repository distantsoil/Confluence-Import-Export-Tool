function Test-ConfluenceConfig {
    <#
    .SYNOPSIS
        Test and validate a Confluence configuration file.
    
    .DESCRIPTION
        Validates a Confluence configuration file and tests the connection
        to ensure all settings are correct and the API is accessible.
    
    .PARAMETER ConfigFile
        Path to the configuration file to test
    
    .PARAMETER ShowDetails
        Show detailed validation results
    
    .EXAMPLE
        Test-ConfluenceConfig -ConfigFile "config.yaml"
        
        Tests the configuration file and connection.
    
    .EXAMPLE
        Test-ConfluenceConfig -ConfigFile "prod-config.yaml" -ShowDetails
        
        Tests configuration with detailed output.
    
    .OUTPUTS
        Boolean indicating whether the configuration is valid
    #>
    
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string] $ConfigFile,
        
        [Parameter(Mandatory = $false)]
        [switch] $ShowDetails
    )
    
    try {
        Write-Host ""
        Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
        Write-Host "║                Configuration Validation                      ║" -ForegroundColor Cyan
        Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "Testing configuration file: $ConfigFile" -ForegroundColor Yellow
        
        # Load configuration
        $configManager = [ConfigManager]::new($ConfigFile)
        
        if (-not $configManager.IsValid) {
            Write-Host "✗ Configuration validation failed" -ForegroundColor Red
            if ($ShowDetails) {
                Write-Host ""
                Write-Host "Configuration Issues:" -ForegroundColor Red
                # The validation errors are already displayed by the ConfigManager
            }
            return $false
        }
        
        Write-Host "✓ Configuration file is valid" -ForegroundColor Green
        
        if ($ShowDetails) {
            Write-Host ""
            Write-Host "Configuration Details:" -ForegroundColor Cyan
            Write-Host "  Base URL: $($configManager.Config.confluence.base_url)" -ForegroundColor White
            Write-Host "  Username: $($configManager.Config.confluence.auth.username)" -ForegroundColor White
            Write-Host "  Auth Method: $(if ($configManager.Config.confluence.auth.api_token) { 'API Token' } else { 'Password' })" -ForegroundColor White
            Write-Host "  Export Directory: $($configManager.Config.export.output_directory)" -ForegroundColor White
            Write-Host "  Rate Limit: $($configManager.Config.general.rate_limit) req/sec" -ForegroundColor White
            Write-Host "  Timeout: $($configManager.Config.general.timeout) seconds" -ForegroundColor White
        }
        
        # Test API connection
        Write-Host ""
        Write-Host "Testing API connection..." -ForegroundColor Yellow
        
        $client = $configManager.CreateAPIClient()
        
        if ($client.TestConnection()) {
            Write-Host "✓ Connection successful!" -ForegroundColor Green
            
            if ($ShowDetails) {
                # Get basic info about the instance
                try {
                    $spaces = $client.GetSpaces()
                    Write-Host ""
                    Write-Host "Instance Information:" -ForegroundColor Cyan
                    Write-Host "  Total Spaces: $($spaces.Count)" -ForegroundColor White
                    
                    if ($spaces.Count -gt 0) {
                        Write-Host "  Sample Spaces:" -ForegroundColor White
                        $spaces | Select-Object -First 3 | ForEach-Object {
                            Write-Host "    - $($_.key): $($_.name)" -ForegroundColor Gray
                        }
                    }
                }
                catch {
                    Write-Warning "Could not retrieve additional instance information: $($_.Exception.Message)"
                }
            }
            
            return $true
        } else {
            Write-Host "✗ Connection failed" -ForegroundColor Red
            Write-Host "  Please verify your credentials and URL are correct." -ForegroundColor Red
            return $false
        }
        
    } catch {
        Write-Host "✗ Configuration test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        if ($client) {
            $client.Dispose()
        }
    }
}