# ConfigManager Class
# Cross-platform configuration management for Confluence Tool
# Supports YAML configuration files with secure credential handling

class ConfigManager {
    [string] $ConfigPath
    [PSCustomObject] $Config
    [bool] $IsValid

    # Constructor with config path
    ConfigManager([string] $ConfigPath) {
        $this.ConfigPath = $this.FindConfigPath($ConfigPath)
        $this.LoadConfig()
    }

    # Default constructor - searches for config in standard locations
    ConfigManager() {
        $this.ConfigPath = $this.FindConfigPath($null)
        $this.LoadConfig()
    }

    # Find configuration file in standard locations
    [string] FindConfigPath([string] $ProvidedPath) {
        if ($ProvidedPath -and (Test-Path $ProvidedPath)) {
            return $ProvidedPath
        }

        # Search in current directory first
        $currentDirConfig = Join-Path (Get-Location) "config.yaml"
        if (Test-Path $currentDirConfig) {
            return $currentDirConfig
        }

        # Search in user home directory
        $homeDirConfig = Join-Path $env:HOME "confluence-config.yaml"
        if (Test-Path $homeDirConfig) {
            return $homeDirConfig
        }

        # If not found, use current directory as default location
        return $currentDirConfig
    }

    # Load configuration from YAML file
    [void] LoadConfig() {
        if (-not (Test-Path $this.ConfigPath)) {
            Write-Warning "Configuration file not found: $($this.ConfigPath)"
            $this.Config = $this.GetDefaultConfig()
            $this.IsValid = $false
            return
        }

        try {
            $yamlContent = Get-Content $this.ConfigPath -Raw
            $this.Config = $this.ConvertFromYaml($yamlContent)
            $this.ValidateConfig()
        }
        catch {
            Write-Error "Failed to load configuration: $($_.Exception.Message)"
            $this.Config = $this.GetDefaultConfig()
            $this.IsValid = $false
        }
    }

    # Simple YAML parser (basic implementation for cross-platform compatibility)
    [PSCustomObject] ConvertFromYaml([string] $YamlContent) {
        $configData = @{}
        $currentSection = $null
        $lines = $YamlContent -split "`n"

        foreach ($line in $lines) {
            $line = $line.Trim()
            
            # Skip empty lines and comments
            if ([string]::IsNullOrEmpty($line) -or $line.StartsWith('#')) {
                continue
            }

            # Check for section headers (no indentation, ends with colon)
            if ($line -match '^([a-zA-Z_][a-zA-Z0-9_]*):$') {
                $currentSection = $matches[1]
                $configData[$currentSection] = @{}
                continue
            }

            # Check for key-value pairs (with indentation)
            if ($line -match '^\s+([a-zA-Z_][a-zA-Z0-9_]*):(.*)$') {
                $key = $matches[1]
                $value = $matches[2].Trim()
                
                # Remove quotes if present - using simpler approach
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Substring(1, $value.Length - 2)
                } elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
                    $value = $value.Substring(1, $value.Length - 2)
                }

                if ($currentSection) {
                    $configData[$currentSection][$key] = $value
                } else {
                    $configData[$key] = $value
                }
                continue
            }

            # Handle nested sections (auth under confluence)
            if ($line -match '^\s+([a-zA-Z_][a-zA-Z0-9_]*):$') {
                $subSection = $matches[1]
                if ($currentSection) {
                    $configData[$currentSection][$subSection] = @{}
                }
                continue
            }

            # Handle nested key-value pairs
            if ($line -match '^\s{4,}([a-zA-Z_][a-zA-Z0-9_]*):(.*)$') {
                $key = $matches[1]
                $value = $matches[2].Trim()
                
                # Remove quotes if present - using simpler approach
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Substring(1, $value.Length - 2)
                } elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
                    $value = $value.Substring(1, $value.Length - 2)
                }

                # Find the current nested section
                foreach ($section in $configData.Keys) {
                    foreach ($subSection in $configData[$section].Keys) {
                        if ($configData[$section][$subSection] -is [hashtable] -and $configData[$section][$subSection].Count -eq 0) {
                            $configData[$section][$subSection][$key] = $value
                            break
                        }
                    }
                }
            }
        }

        return [PSCustomObject] $configData
    }

    # Get default configuration structure
    [PSCustomObject] GetDefaultConfig() {
        return [PSCustomObject] @{
            confluence = @{
                base_url = "https://your-domain.atlassian.net"
                auth = @{
                    username = "your-email@domain.com"
                    api_token = "your-api-token"
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
    }

    # Validate configuration
    [void] ValidateConfig() {
        $this.IsValid = $true
        $errors = @()

        # Validate confluence section
        if (-not $this.Config.confluence) {
            $errors += "Missing 'confluence' section"
            $this.IsValid = $false
        } else {
            if (-not $this.Config.confluence.base_url) {
                $errors += "Missing 'confluence.base_url'"
                $this.IsValid = $false
            }

            if (-not $this.Config.confluence.auth) {
                $errors += "Missing 'confluence.auth' section"
                $this.IsValid = $false
            } else {
                if (-not $this.Config.confluence.auth.username) {
                    $errors += "Missing 'confluence.auth.username'"
                    $this.IsValid = $false
                }

                if (-not $this.Config.confluence.auth.api_token -and -not $this.Config.confluence.auth.password) {
                    $errors += "Missing either 'confluence.auth.api_token' or 'confluence.auth.password'"
                    $this.IsValid = $false
                }
            }
        }

        if ($errors.Count -gt 0) {
            Write-Warning "Configuration validation failed:"
            $errors | ForEach-Object { Write-Warning "  - $_" }
        }
    }

    # Save configuration to file
    [void] SaveConfig() {
        try {
            $yamlContent = $this.ConvertToYaml($this.Config)
            Set-Content -Path $this.ConfigPath -Value $yamlContent -Encoding UTF8
            Write-Verbose "Configuration saved to: $($this.ConfigPath)"
        }
        catch {
            Write-Error "Failed to save configuration: $($_.Exception.Message)"
        }
    }

    # Simple YAML serializer
    [string] ConvertToYaml([PSCustomObject] $Object) {
        $yaml = @()
        
        foreach ($property in $Object.PSObject.Properties) {
            $yaml += "$($property.Name):"
            
            if ($property.Value -is [hashtable] -or $property.Value.GetType().Name -eq 'PSCustomObject') {
                foreach ($subProperty in $property.Value.PSObject.Properties) {
                    if ($subProperty.Value -is [hashtable] -or $subProperty.Value.GetType().Name -eq 'PSCustomObject') {
                        $yaml += "  $($subProperty.Name):"
                        foreach ($subSubProperty in $subProperty.Value.PSObject.Properties) {
                            $yaml += "    $($subSubProperty.Name): `"$($subSubProperty.Value)`""
                        }
                    } else {
                        $yaml += "  $($subProperty.Name): `"$($subProperty.Value)`""
                    }
                }
            } else {
                $yaml += "  value: `"$($property.Value)`""
            }
        }
        
        return $yaml -join "`n"
    }

    # Create API client from configuration - returns configuration for client creation
    [hashtable] GetClientConfiguration() {
        if (-not $this.IsValid) {
            throw "Configuration is not valid. Please check your config file."
        }

        return @{
            BaseUrl = $this.Config.confluence.base_url
            Username = $this.Config.confluence.auth.username
            ApiToken = $this.Config.confluence.auth.api_token
            Password = $this.Config.confluence.auth.password
            Timeout = [int] $this.Config.general.timeout
            RateLimit = [double] $this.Config.general.rate_limit
        }
    }

    # Test connection using this configuration - simplified version
    [bool] TestConnection() {
        if (-not $this.IsValid) {
            Write-Warning "Configuration is not valid"
            return $false
        }
        
        # Basic validation that required fields are present
        if (-not $this.Config.confluence.base_url -or 
            -not $this.Config.confluence.auth.username -or
            (-not $this.Config.confluence.auth.api_token -and -not $this.Config.confluence.auth.password)) {
            Write-Warning "Missing required configuration fields"
            return $false
        }
        
        return $true
    }
}