#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test script for the Confluence PowerShell module.

.DESCRIPTION
    This script tests the basic functionality of the Confluence PowerShell module
    to ensure it loads correctly and all functions are available.

.EXAMPLE
    ./Test-Module.ps1
    
    Runs all basic tests for the module.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [switch] $ShowDetails
)

# Set strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Test results
$TestResults = @{
    Passed = 0
    Failed = 0
    Total = 0
    Errors = @()
}

function Write-TestResult {
    param(
        [string] $TestName,
        [bool] $Success,
        [string] $ErrorMessage = ""
    )
    
    $TestResults.Total++
    
    if ($Success) {
        $TestResults.Passed++
        Write-Host "✓ $TestName" -ForegroundColor Green
    } else {
        $TestResults.Failed++
        $TestResults.Errors += "$TestName - $ErrorMessage"
        Write-Host "✗ $TestName" -ForegroundColor Red
        if ($ErrorMessage) {
            Write-Host "  Error: $ErrorMessage" -ForegroundColor Red
        }
    }
}

function Test-PowerShellVersion {
    $testName = "PowerShell Version Check"
    try {
        $version = $PSVersionTable.PSVersion
        $platformIsWindows = $PSVersionTable.Platform -eq 'Win32NT' -or -not $PSVersionTable.Platform
        
        if ($platformIsWindows) {
            # Windows PowerShell 5.1+ required
            $minVersion = [Version]"5.1"
        } else {
            # PowerShell Core 6.0+ required
            $minVersion = [Version]"6.0"
        }
        
        if ($version -ge $minVersion) {
            Write-TestResult $testName $true
            Write-Verbose "PowerShell version: $version (Platform: $($PSVersionTable.Platform -or 'Windows'))"
        } else {
            Write-TestResult $testName $false "PowerShell $version detected, but $minVersion+ required"
        }
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-ModuleImport {
    $testName = "Module Import"
    try {
        $modulePath = Join-Path $PSScriptRoot "ConfluenceTool/ConfluenceTool.psd1"
        
        if (-not (Test-Path $modulePath)) {
            Write-TestResult $testName $false "Module manifest not found at $modulePath"
            return
        }
        
        Import-Module $modulePath -Force -ErrorAction Stop
        Write-TestResult $testName $true
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-ModuleFunctions {
    $testName = "Module Functions Available"
    try {
        $expectedFunctions = @(
            'Connect-ConfluenceAPI',
            'Get-ConfluenceSpaces',
            'Export-ConfluenceSpace',
            'Import-ConfluenceSpace',
            'Sync-ConfluenceSpaces',
            'Compare-ConfluenceSpaces',
            'New-ConfluenceConfig',
            'Test-ConfluenceConfig',
            'Get-ConfluencePages',
            'Get-ConfluencePageContent',
            'Show-ConfluenceHelp'
        )
        
        $availableFunctions = Get-Command -Module ConfluenceTool -CommandType Function | Select-Object -ExpandProperty Name
        $missingFunctions = $expectedFunctions | Where-Object { $_ -notin $availableFunctions }
        
        if ($missingFunctions.Count -eq 0) {
            Write-TestResult $testName $true
            Write-Verbose "All $($expectedFunctions.Count) expected functions are available"
        } else {
            Write-TestResult $testName $false "Missing functions: $($missingFunctions -join ', ')"
        }
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-ClassDefinitions {
    $testName = "Class Definitions"
    try {
        # Test if classes can be instantiated (basic syntax check)
        $configManager = [ConfigManager]::new()
        
        if ($configManager) {
            Write-TestResult $testName $true
        } else {
            Write-TestResult $testName $false "ConfigManager class could not be instantiated"
        }
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-HelpSystem {
    $testName = "Help System"
    try {
        # Test main help function
        $helpOutput = Show-ConfluenceHelp -Topic Overview 2>&1
        
        if ($helpOutput -and $helpOutput.Count -gt 0) {
            Write-TestResult $testName $true
        } else {
            Write-TestResult $testName $false "Help system did not produce output"
        }
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-ConfigTemplate {
    $testName = "Configuration Template Creation"
    try {
        $tempFile = Join-Path $env:TEMP "test-config-$(Get-Random).yaml"
        
        $result = New-ConfluenceConfig -Path $tempFile -Template
        
        if ($result -and (Test-Path $tempFile)) {
            Write-TestResult $testName $true
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        } else {
            Write-TestResult $testName $false "Template configuration file was not created"
        }
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

function Test-CrossPlatformCompatibility {
    $testName = "Cross-Platform Compatibility"
    try {
        $platformIsWindows = $PSVersionTable.Platform -eq 'Win32NT' -or -not $PSVersionTable.Platform
        $platform = if ($platformIsWindows) { "Windows" } else { $PSVersionTable.Platform }
        
        # Test path operations
        $testPath = Join-Path "test" "path" "file.txt"
        
        # Test HTTP client assembly loading
        Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
        
        Write-TestResult $testName $true
        Write-Verbose "Platform: $platform - Basic compatibility checks passed"
        
    } catch {
        Write-TestResult $testName $false $_.Exception.Message
    }
}

# Main test execution
function Main {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        Confluence PowerShell Module Test Suite               ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Running compatibility and functionality tests..." -ForegroundColor Yellow
    Write-Host ""
    
    # Run all tests
    Test-PowerShellVersion
    Test-CrossPlatformCompatibility
    Test-ModuleImport
    Test-ModuleFunctions
    Test-ClassDefinitions
    Test-HelpSystem
    Test-ConfigTemplate
    
    # Display summary
    Write-Host ""
    Write-Host "TEST SUMMARY" -ForegroundColor Cyan
    Write-Host "============" -ForegroundColor Cyan
    Write-Host "Total Tests: $($TestResults.Total)" -ForegroundColor White
    Write-Host "Passed: $($TestResults.Passed)" -ForegroundColor Green
    Write-Host "Failed: $($TestResults.Failed)" -ForegroundColor Red
    
    if ($TestResults.Failed -gt 0) {
        Write-Host ""
        Write-Host "FAILURES:" -ForegroundColor Red
        $TestResults.Errors | ForEach-Object {
            Write-Host "  - $_" -ForegroundColor Red
        }
        
        Write-Host ""
        Write-Host "Some tests failed. Please check the errors above." -ForegroundColor Red
        Write-Host "The module may not function correctly in this environment." -ForegroundColor Red
    } else {
        Write-Host ""
        Write-Host "✓ All tests passed! The module should work correctly." -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "1. Create a configuration: New-ConfluenceConfig -Path 'config.yaml'" -ForegroundColor White
        Write-Host "2. Test your connection: Test-ConfluenceConfig -ConfigFile 'config.yaml'" -ForegroundColor White
        Write-Host "3. Start using the tool: Show-ConfluenceHelp" -ForegroundColor White
    }
    
    Write-Host ""
    
    # Return exit code
    if ($TestResults.Failed -gt 0) {
        exit 1
    } else {
        exit 0
    }
}

# Execute main function
Main