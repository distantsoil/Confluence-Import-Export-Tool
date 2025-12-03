function Connect-ConfluenceAPI {
    <#
    .SYNOPSIS
        Connect to a Confluence instance using API credentials.
    
    .DESCRIPTION
        Establishes a connection to a Confluence instance using the REST API.
        Supports both API token authentication (recommended for cloud instances) 
        and password authentication (for server instances).
    
    .PARAMETER BaseUrl
        The base URL of your Confluence instance (e.g., https://company.atlassian.net)
    
    .PARAMETER Username
        Your Confluence username or email address
    
    .PARAMETER ApiToken
        API token for authentication (recommended for Atlassian Cloud)
    
    .PARAMETER Password
        Password for authentication (for server instances)
    
    .PARAMETER ConfigFile
        Path to a YAML configuration file containing connection details
    
    .PARAMETER TestConnection
        Test the connection after establishing it
    
    .EXAMPLE
        Connect-ConfluenceAPI -BaseUrl "https://company.atlassian.net" -Username "user@company.com" -ApiToken "your-api-token"
        
        Connects to Confluence using API token authentication.
    
    .EXAMPLE
        Connect-ConfluenceAPI -ConfigFile "prod-config.yaml" -TestConnection
        
        Connects using settings from a configuration file and tests the connection.
    
    .OUTPUTS
        ConfluenceAPIClient object for making API requests
    #>
    
    [CmdletBinding(DefaultParameterSetName = 'Direct')]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
        [ValidateNotNullOrEmpty()]
        [string] $BaseUrl,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
        [ValidateNotNullOrEmpty()]
        [string] $Username,
        
        [Parameter(Mandatory = $false, ParameterSetName = 'Direct')]
        [string] $ApiToken,
        
        [Parameter(Mandatory = $false, ParameterSetName = 'Direct')]
        [string] $Password,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Config')]
        [ValidateScript({ Test-Path $_ })]
        [string] $ConfigFile,
        
        [Parameter(Mandatory = $false)]
        [switch] $TestConnection
    )
    
    try {
        if ($PSCmdlet.ParameterSetName -eq 'Config') {
            Write-Verbose "Loading configuration from: $ConfigFile"
            $configManager = [ConfigManager]::new($ConfigFile)
            
            if (-not $configManager.IsValid) {
                throw "Invalid configuration file. Please check the file format and required fields."
            }
            
            $config = $configManager.GetClientConfiguration()
            
            if ($config.ApiToken) {
                $client = [ConfluenceAPIClient]::new($config.BaseUrl, $config.Username, $config.ApiToken)
            } else {
                $client = [ConfluenceAPIClient]::new($config.BaseUrl, $config.Username, $config.Password, $true)
            }
            
            # Apply settings
            if ($config.Timeout) { $client.Timeout = $config.Timeout }
            if ($config.RateLimit) { $client.RateLimit = $config.RateLimit }
        } else {
            # Validate that at least one authentication method is provided
            if (-not $ApiToken -and -not $Password) {
                throw "Either ApiToken or Password must be provided for authentication."
            }
            
            Write-Verbose "Creating direct connection to: $BaseUrl"
            
            if ($ApiToken) {
                $client = [ConfluenceAPIClient]::new($BaseUrl, $Username, $ApiToken)
            } else {
                $client = [ConfluenceAPIClient]::new($BaseUrl, $Username, $Password, $true)
            }
        }
        
        if ($TestConnection) {
            Write-Host "Testing connection..." -ForegroundColor Yellow
            if ($client.TestConnection()) {
                Write-Host "✓ Connection successful!" -ForegroundColor Green
            } else {
                throw "Connection test failed. Please verify your credentials and URL."
            }
        }
        
        Write-Verbose "Successfully connected to Confluence instance"
        return $client
        
    } catch {
        Write-Error "Failed to connect to Confluence: $($_.Exception.Message)"
        return $null
    }
}