function Get-ConfluenceSpaces {
    <#
    .SYNOPSIS
        Retrieve all spaces from a Confluence instance.
    
    .DESCRIPTION
        Gets a list of all spaces from the connected Confluence instance.
        Returns detailed information about each space including key, name, description, and homepage.
    
    .PARAMETER Client
        The ConfluenceAPIClient object from Connect-ConfluenceAPI
    
    .PARAMETER ConfigFile
        Path to configuration file (alternative to providing Client)
    
    .PARAMETER SpaceKey
        Optional. Retrieve information for a specific space by key
    
    .PARAMETER Interactive
        Show an interactive table for space selection
    
    .EXAMPLE
        $client = Connect-ConfluenceAPI -BaseUrl "https://company.atlassian.net" -Username "user@company.com" -ApiToken "token"
        Get-ConfluenceSpaces -Client $client
        
        Gets all spaces from the Confluence instance.
    
    .EXAMPLE
        Get-ConfluenceSpaces -ConfigFile "config.yaml" -SpaceKey "MYSPACE"
        
        Gets information for a specific space using configuration file.
    
    .EXAMPLE
        Get-ConfluenceSpaces -ConfigFile "config.yaml" -Interactive
        
        Shows an interactive table for selecting spaces.
    
    .OUTPUTS
        Array of PSCustomObject containing space information
    #>
    
    [CmdletBinding(DefaultParameterSetName = 'Client')]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'Client')]
        [ConfluenceAPIClient] $Client,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Config')]
        [ValidateScript({ Test-Path $_ })]
        [string] $ConfigFile,
        
        [Parameter(Mandatory = $false)]
        [string] $SpaceKey,
        
        [Parameter(Mandatory = $false)]
        [switch] $Interactive
    )
    
    try {
        # Create client if using config file
        if ($PSCmdlet.ParameterSetName -eq 'Config') {
            $configManager = [ConfigManager]::new($ConfigFile)
            if (-not $configManager.IsValid) {
                throw "Invalid configuration file"
            }
            $Client = $configManager.CreateAPIClient()
        }
        
        if ($SpaceKey) {
            Write-Verbose "Retrieving space: $SpaceKey"
            $space = $Client.GetSpace($SpaceKey)
            return $space
        } else {
            Write-Host "Retrieving spaces..." -ForegroundColor Yellow
            $spaces = $Client.GetSpaces()
            
            if ($spaces.Count -eq 0) {
                Write-Warning "No spaces found in this Confluence instance."
                return @()
            }
            
            Write-Host "Found $($spaces.Count) spaces." -ForegroundColor Green
            
            if ($Interactive) {
                Show-SpaceSelectionTable -Spaces $spaces
            } else {
                return $spaces
            }
        }
        
    } catch {
        Write-Error "Failed to retrieve spaces: $($_.Exception.Message)"
        return @()
    } finally {
        # Clean up client if we created it
        if ($PSCmdlet.ParameterSetName -eq 'Config' -and $Client) {
            $Client.Dispose()
        }
    }
}

function Show-SpaceSelectionTable {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject[]] $Spaces
    )
    
    # Display spaces in a formatted table
    Write-Host ""
    Write-Host "Available Confluence Spaces:" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
    
    $table = @()
    for ($i = 0; $i -lt $Spaces.Count; $i++) {
        $space = $Spaces[$i]
        $description = if ($space.description -and $space.description.plain) {
            $space.description.plain.Substring(0, [Math]::Min(50, $space.description.plain.Length))
        } else {
            "No description"
        }
        
        $table += [PSCustomObject] @{
            Index = $i + 1
            Key = $space.key
            Name = $space.name
            Description = $description
            Type = $space.type
        }
    }
    
    $table | Format-Table -Property Index, Key, Name, Description, Type -AutoSize
    
    # Interactive selection
    do {
        $selection = Read-Host "Enter space number (1-$($Spaces.Count)) or 'q' to quit"
        
        if ($selection -eq 'q' -or $selection -eq 'quit') {
            return $null
        }
        
        if ($selection -match '^\d+$') {
            $index = [int]$selection - 1
            if ($index -ge 0 -and $index -lt $Spaces.Count) {
                $selectedSpace = $Spaces[$index]
                Write-Host ""
                Write-Host "Selected Space:" -ForegroundColor Green
                Write-Host "  Key: $($selectedSpace.key)" -ForegroundColor White
                Write-Host "  Name: $($selectedSpace.name)" -ForegroundColor White
                Write-Host "  Type: $($selectedSpace.type)" -ForegroundColor White
                return $selectedSpace
            }
        }
        
        Write-Warning "Invalid selection. Please enter a number between 1 and $($Spaces.Count), or 'q' to quit."
        
    } while ($true)
}