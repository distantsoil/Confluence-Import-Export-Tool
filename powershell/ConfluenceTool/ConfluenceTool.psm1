# ConfluenceTool PowerShell Module
# Cross-platform Confluence Export-Import Tool
# Compatible with PowerShell 5.1+ on Windows and PowerShell Core 6.0+ on macOS/Linux

#Requires -Version 5.1

# Import required .NET assemblies for cross-platform HTTP requests
Add-Type -AssemblyName System.Net.Http
Add-Type -AssemblyName System.Web

# Module-level variables
$Script:ModuleVersion = '1.0.0'
$Script:UserAgent = "ConfluenceTool-PowerShell/$Script:ModuleVersion"

# Import all function files
$FunctionPath = Join-Path $PSScriptRoot 'Functions'
if (Test-Path $FunctionPath) {
    Get-ChildItem -Path $FunctionPath -Filter '*.ps1' -Recurse | ForEach-Object {
        . $_.FullName
    }
}

# Import all class files  
$ClassPath = Join-Path $PSScriptRoot 'Classes'
if (Test-Path $ClassPath) {
    Get-ChildItem -Path $ClassPath -Filter '*.ps1' -Recurse | ForEach-Object {
        . $_.FullName
    }
}

# Module initialization
Write-Verbose "ConfluenceTool module loaded. Version: $Script:ModuleVersion"
Write-Verbose "PowerShell Version: $($PSVersionTable.PSVersion)"
Write-Verbose "Platform: $($PSVersionTable.Platform -or 'Windows')"

# Export module members - functions are exported via the manifest
# Variables and aliases can be exported here if needed

# Display welcome message on import
if ($PSBoundParameters.ContainsKey('Verbose') -or $VerbosePreference -eq 'Continue') {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║            Confluence Export-Import Tool (PowerShell)       ║" -ForegroundColor Cyan  
    Write-Host "║                         Version $Script:ModuleVersion                        ║" -ForegroundColor Cyan
    Write-Host "║                    Cross-Platform Compatible                 ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Type 'Show-ConfluenceHelp' for usage information." -ForegroundColor Yellow
    Write-Host ""
}