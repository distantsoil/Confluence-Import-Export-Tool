function Get-ConfluencePages {
    <#
    .SYNOPSIS
        Retrieve pages from a Confluence space.
    
    .DESCRIPTION
        Gets a list of all pages from a specified Confluence space.
        Returns detailed information about each page including content, version, and metadata.
    
    .PARAMETER Client
        The ConfluenceAPIClient object from Connect-ConfluenceAPI
    
    .PARAMETER ConfigFile
        Path to configuration file (alternative to providing Client)
    
    .PARAMETER SpaceKey
        The key of the space to retrieve pages from
    
    .PARAMETER Expand
        Additional fields to expand in the response (e.g., "body.storage,version,ancestors")
    
    .PARAMETER PageId
        Retrieve a specific page by ID (optional)
    
    .EXAMPLE
        $client = Connect-ConfluenceAPI -ConfigFile "config.yaml"
        Get-ConfluencePages -Client $client -SpaceKey "DOCS"
        
        Gets all pages from the DOCS space.
    
    .EXAMPLE
        Get-ConfluencePages -ConfigFile "config.yaml" -SpaceKey "DOCS" -PageId "123456"
        
        Gets a specific page by ID from the DOCS space.
    
    .OUTPUTS
        Array of PSCustomObject containing page information
    #>
    
    [CmdletBinding(DefaultParameterSetName = 'Client')]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'Client')]
        [ConfluenceAPIClient] $Client,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'Config')]
        [ValidateScript({ Test-Path $_ })]
        [string] $ConfigFile,
        
        [Parameter(Mandatory = $true)]
        [string] $SpaceKey,
        
        [Parameter(Mandatory = $false)]
        [string] $Expand = "body.storage,version,ancestors",
        
        [Parameter(Mandatory = $false)]
        [string] $PageId
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
        
        if ($PageId) {
            Write-Verbose "Retrieving page ID: $PageId"
            $page = $Client.GetPage($PageId, $Expand)
            return $page
        } else {
            Write-Host "Retrieving pages from space: $SpaceKey" -ForegroundColor Yellow
            $pages = $Client.GetPages($SpaceKey, $Expand)
            
            if ($pages.Count -eq 0) {
                Write-Warning "No pages found in space $SpaceKey."
                return @()
            }
            
            Write-Host "Found $($pages.Count) pages." -ForegroundColor Green
            return $pages
        }
        
    } catch {
        Write-Error "Failed to retrieve pages: $($_.Exception.Message)"
        return @()
    } finally {
        # Clean up client if we created it
        if ($PSCmdlet.ParameterSetName -eq 'Config' -and $Client) {
            $Client.Dispose()
        }
    }
}

function Get-ConfluencePageContent {
    <#
    .SYNOPSIS
        Retrieve the content of a specific Confluence page.
    
    .DESCRIPTION
        Gets the full content and metadata of a specific Confluence page by ID or title.
        
    .PARAMETER Client
        The ConfluenceAPIClient object from Connect-ConfluenceAPI
    
    .PARAMETER ConfigFile
        Path to configuration file (alternative to providing Client)
    
    .PARAMETER SpaceKey
        The key of the space containing the page
    
    .PARAMETER PageId
        The ID of the page to retrieve
    
    .PARAMETER PageTitle
        The title of the page to retrieve (if PageId not provided)
    
    .PARAMETER Format
        Output format: Object (default), HTML, or Text
    
    .EXAMPLE
        Get-ConfluencePageContent -ConfigFile "config.yaml" -SpaceKey "DOCS" -PageId "123456"
        
        Gets the content of page with ID 123456.
    
    .EXAMPLE
        Get-ConfluencePageContent -ConfigFile "config.yaml" -SpaceKey "DOCS" -PageTitle "Welcome Page" -Format HTML
        
        Gets the HTML content of the "Welcome Page".
    
    .OUTPUTS
        Page content in the requested format
    #>
    
    [CmdletBinding(DefaultParameterSetName = 'ClientById')]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'ClientById')]
        [Parameter(Mandatory = $true, ParameterSetName = 'ClientByTitle')]
        [ConfluenceAPIClient] $Client,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'ConfigById')]
        [Parameter(Mandatory = $true, ParameterSetName = 'ConfigByTitle')]
        [ValidateScript({ Test-Path $_ })]
        [string] $ConfigFile,
        
        [Parameter(Mandatory = $true)]
        [string] $SpaceKey,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'ClientById')]
        [Parameter(Mandatory = $true, ParameterSetName = 'ConfigById')]
        [string] $PageId,
        
        [Parameter(Mandatory = $true, ParameterSetName = 'ClientByTitle')]
        [Parameter(Mandatory = $true, ParameterSetName = 'ConfigByTitle')]
        [string] $PageTitle,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet('Object', 'HTML', 'Text')]
        [string] $Format = 'Object'
    )
    
    try {
        # Create client if using config file
        if ($ConfigFile) {
            $configManager = [ConfigManager]::new($ConfigFile)
            if (-not $configManager.IsValid) {
                throw "Invalid configuration file"
            }
            $Client = $configManager.CreateAPIClient()
        }
        
        # Get page by ID or find by title
        if ($PageId) {
            Write-Verbose "Retrieving page by ID: $PageId"
            $page = $Client.GetPage($PageId, "body.storage,body.view,version,ancestors")
        } else {
            Write-Verbose "Finding page by title: $PageTitle"
            $pages = $Client.GetPages($SpaceKey, "body.storage,body.view,version,ancestors")
            $page = $pages | Where-Object { $_.title -eq $PageTitle } | Select-Object -First 1
            
            if (-not $page) {
                throw "Page with title '$PageTitle' not found in space $SpaceKey"
            }
        }
        
        # Return content in requested format
        switch ($Format) {
            'Object' {
                return $page
            }
            'HTML' {
                if ($page.body -and $page.body.storage) {
                    return $page.body.storage.value
                } elseif ($page.body -and $page.body.view) {
                    return $page.body.view.value
                } else {
                    return "No HTML content available"
                }
            }
            'Text' {
                if ($page.body -and $page.body.storage) {
                    # Basic HTML to text conversion (remove tags)
                    $htmlContent = $page.body.storage.value
                    $textContent = $htmlContent -replace '<[^>]+>', '' -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>'
                    return $textContent.Trim()
                } else {
                    return "No text content available"
                }
            }
        }
        
    } catch {
        Write-Error "Failed to retrieve page content: $($_.Exception.Message)"
        return $null
    } finally {
        # Clean up client if we created it
        if ($ConfigFile -and $Client) {
            $Client.Dispose()
        }
    }
}