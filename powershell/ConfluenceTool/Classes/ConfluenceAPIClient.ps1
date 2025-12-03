# ConfluenceAPIClient Class
# Cross-platform HTTP client for Confluence REST API
# Compatible with PowerShell 5.1+ (Windows) and PowerShell Core 6.0+ (macOS/Linux)

class ConfluenceAPIClient {
    [string] $BaseUrl
    [string] $Username
    [string] $AuthToken
    [string] $Password
    [int] $Timeout
    [int] $MaxRetries
    [double] $RateLimit
    [datetime] $LastRequestTime
    [System.Net.Http.HttpClient] $HttpClient
    [pscredential] $Credential

    # Constructor with API token (preferred for cloud instances)
    ConfluenceAPIClient([string] $BaseUrl, [string] $Username, [string] $AuthToken) {
        $this.BaseUrl = $BaseUrl.TrimEnd('/')
        $this.Username = $Username
        $this.AuthToken = $AuthToken
        $this.Timeout = 30
        $this.MaxRetries = 3
        $this.RateLimit = 10.0
        $this.LastRequestTime = [datetime]::MinValue
        $this.InitializeHttpClient()
    }

    # Constructor with password (for server instances)
    ConfluenceAPIClient([string] $BaseUrl, [string] $Username, [string] $Password, [bool] $IsPassword) {
        $this.BaseUrl = $BaseUrl.TrimEnd('/')
        $this.Username = $Username
        $this.Password = $Password
        $this.Timeout = 30
        $this.MaxRetries = 3
        $this.RateLimit = 10.0
        $this.LastRequestTime = [datetime]::MinValue
        $this.InitializeHttpClient()
    }
    
    # Determine the API path based on whether this is Cloud or Server/Data Center
    [string] GetApiPath() {
        # Confluence Cloud instances (atlassian.net) require /wiki/rest/api/
        # Server/Data Center instances use /rest/api/
        if ($this.BaseUrl -match 'atlassian\.net') {
            return "/wiki/rest/api/"
        } else {
            return "/rest/api/"
        }
    }

    # Initialize HTTP client with proper authentication
    [void] InitializeHttpClient() {
        $this.HttpClient = New-Object System.Net.Http.HttpClient
        $this.HttpClient.Timeout = [System.TimeSpan]::FromSeconds($this.Timeout)
        
        # Set up authentication
        if ($this.AuthToken) {
            $authString = "$($this.Username):$($this.AuthToken)"
        } else {
            $authString = "$($this.Username):$($this.Password)"
        }
        
        $encodedAuth = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($authString))
        $this.HttpClient.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Basic", $encodedAuth)
        
        # Set common headers
        $this.HttpClient.DefaultRequestHeaders.Add("Accept", "application/json")
        $this.HttpClient.DefaultRequestHeaders.Add("User-Agent", $Script:UserAgent)
    }

    # Apply rate limiting
    [void] ApplyRateLimit() {
        if ($this.RateLimit -gt 0) {
            $timeSinceLastRequest = ([datetime]::UtcNow - $this.LastRequestTime).TotalSeconds
            $minInterval = 1.0 / $this.RateLimit
            
            if ($timeSinceLastRequest -lt $minInterval) {
                $sleepTime = [int](($minInterval - $timeSinceLastRequest) * 1000)
                Start-Sleep -Milliseconds $sleepTime
            }
        }
        $this.LastRequestTime = [datetime]::UtcNow
    }

    # Make HTTP request with retry logic
    [PSCustomObject] MakeRequest([string] $Method, [string] $Endpoint, [hashtable] $Parameters = @{}, [string] $Body = $null) {
        $apiPath = $this.GetApiPath()
        $url = "$($this.BaseUrl)$apiPath$($Endpoint.TrimStart('/'))"
        
        # Add query parameters
        if ($Parameters.Count -gt 0) {
            $queryString = ($Parameters.GetEnumerator() | ForEach-Object {
                "$([System.Web.HttpUtility]::UrlEncode($_.Key))=$([System.Web.HttpUtility]::UrlEncode($_.Value))"
            }) -join '&'
            $url += "?$queryString"
        }

        $attempt = 0
        $lastException = $null

        while ($attempt -lt $this.MaxRetries) {
            try {
                $this.ApplyRateLimit()
                
                $request = New-Object System.Net.Http.HttpRequestMessage
                $request.RequestUri = [System.Uri]$url
                $request.Method = [System.Net.Http.HttpMethod]::new($Method.ToUpper())
                
                if ($Body) {
                    $request.Content = New-Object System.Net.Http.StringContent($Body, [System.Text.Encoding]::UTF8, "application/json")
                }

                Write-Verbose "Making $Method request to: $url"
                $response = $this.HttpClient.SendAsync($request).GetAwaiter().GetResult()
                
                $responseContent = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                
                if ($response.IsSuccessStatusCode) {
                    if ($responseContent) {
                        return ($responseContent | ConvertFrom-Json)
                    } else {
                        return @{ success = $true }
                    }
                } else {
                    $this.HandleHttpError($response, $responseContent)
                }
            }
            catch {
                $lastException = $_
                $attempt++
                
                if ($attempt -lt $this.MaxRetries) {
                    $waitTime = [Math]::Pow(2, $attempt) * 1000
                    Write-Warning "Request failed (attempt $attempt/$($this.MaxRetries)). Retrying in $($waitTime/1000) seconds..."
                    Start-Sleep -Milliseconds $waitTime
                } else {
                    Write-Error "Request failed after $($this.MaxRetries) attempts. Last error: $($_.Exception.Message)"
                    throw $lastException
                }
            }
        }
        
        throw $lastException
    }

    # Handle HTTP errors with detailed messages
    [void] HandleHttpError([System.Net.Http.HttpResponseMessage] $Response, [string] $Content) {
        $statusCode = [int] $Response.StatusCode
        $statusDescription = $Response.ReasonPhrase
        
        $errorMessage = switch ($statusCode) {
            401 { "Authentication failed. Please check your credentials." }
            403 { "Access forbidden. You don't have permission to access this resource." }
            404 { "Resource not found. The requested page or space may not exist." }
            429 { "Rate limit exceeded. Please wait before making more requests." }
            500 { "Internal server error. The Confluence server encountered an error." }
            502 { "Bad gateway. The server received an invalid response." }
            503 { "Service unavailable. The server is temporarily unavailable." }
            default { "HTTP $statusCode - $statusDescription" }
        }
        
        if ($Content) {
            try {
                $errorObj = $Content | ConvertFrom-Json
                if ($errorObj.message) {
                    $errorMessage += " Details: $($errorObj.message)"
                }
            }
            catch {
                # Content is not JSON, append as-is
                $errorMessage += " Response: $Content"
            }
        }
        
        throw [System.Exception]::new($errorMessage)
    }

    # Get all spaces
    [PSCustomObject[]] GetSpaces() {
        $allSpaces = @()
        $start = 0
        $limit = 50
        
        do {
            $params = @{
                start = $start
                limit = $limit
                expand = "description.plain,homepage"
            }
            
            $response = $this.MakeRequest("GET", "space", $params)
            
            if ($response.results) {
                $allSpaces += $response.results
                $start += $limit
            }
        } while ($response.results.Count -eq $limit)
        
        return $allSpaces
    }

    # Get space by key
    [PSCustomObject] GetSpace([string] $SpaceKey) {
        $params = @{
            expand = "description.plain,homepage,metadata.labels"
        }
        
        return $this.MakeRequest("GET", "space/$SpaceKey", $params)
    }

    # Get pages in a space
    [PSCustomObject[]] GetPages([string] $SpaceKey, [string] $Expand = "body.storage,version,ancestors") {
        $allPages = @()
        $start = 0
        $limit = 50
        
        do {
            $params = @{
                spaceKey = $SpaceKey
                start = $start
                limit = $limit
                expand = $Expand
            }
            
            $response = $this.MakeRequest("GET", "content", $params)
            
            if ($response.results) {
                $allPages += $response.results
                $start += $limit
            }
        } while ($response.results.Count -eq $limit)
        
        return $allPages
    }

    # Get page by ID
    [PSCustomObject] GetPage([string] $PageId, [string] $Expand = "body.storage,version,ancestors,children.page") {
        $params = @{
            expand = $Expand
        }
        
        return $this.MakeRequest("GET", "content/$PageId", $params)
    }

    # Test connection
    [bool] TestConnection() {
        try {
            $this.MakeRequest("GET", "space", @{ limit = 1 })
            return $true
        }
        catch {
            Write-Warning "Connection test failed: $($_.Exception.Message)"
            return $false
        }
    }

    # Dispose of HTTP client
    [void] Dispose() {
        if ($this.HttpClient) {
            $this.HttpClient.Dispose()
        }
    }
}