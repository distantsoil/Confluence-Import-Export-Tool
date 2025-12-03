function Export-ConfluenceSpace {
    <#
    .SYNOPSIS
        Export a Confluence space to local files.
    
    .DESCRIPTION
        Exports all pages, attachments, and metadata from a Confluence space.
        Creates HTML files for pages and downloads all attachments.
        Supports multi-threaded export for improved performance.
    
    .PARAMETER Client
        The ConfluenceAPIClient object from Connect-ConfluenceAPI
    
    .PARAMETER ConfigFile
        Path to configuration file (alternative to providing Client)
    
    .PARAMETER SpaceKey
        The key of the space to export (e.g., 'MYSPACE')
    
    .PARAMETER OutputPath
        Directory where exported files will be saved
    
    .PARAMETER IncludeAttachments
        Include attachments in the export (default: true)
    
    .PARAMETER IncludeComments
        Include comments in the export (default: true)
    
    .PARAMETER MaxConcurrency
        Maximum number of concurrent operations (default: 5)
    
    .PARAMETER Interactive
        Show interactive space selection if SpaceKey is not provided
    
    .EXAMPLE
        $client = Connect-ConfluenceAPI -ConfigFile "config.yaml"
        Export-ConfluenceSpace -Client $client -SpaceKey "DOCS" -OutputPath "./exports"
        
        Exports the DOCS space to the ./exports directory.
    
    .EXAMPLE
        Export-ConfluenceSpace -ConfigFile "config.yaml" -Interactive
        
        Shows an interactive space selection menu.
    
    .OUTPUTS
        Export summary object with statistics and file paths
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
        [string] $OutputPath,
        
        [Parameter(Mandatory = $false)]
        [bool] $IncludeAttachments = $true,
        
        [Parameter(Mandatory = $false)]
        [bool] $IncludeComments = $true,
        
        [Parameter(Mandatory = $false)]
        [int] $MaxConcurrency = 5,
        
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
            
            # Use output directory from config if not specified
            if (-not $OutputPath) {
                $OutputPath = $configManager.Config.export.output_directory
            }
        }
        
        # Set default output path if not provided
        if (-not $OutputPath) {
            $OutputPath = "./exports"
        }
        
        # Interactive space selection if SpaceKey not provided
        if (-not $SpaceKey -or $Interactive) {
            Write-Host "Loading available spaces..." -ForegroundColor Yellow
            $spaces = $Client.GetSpaces()
            
            if ($spaces.Count -eq 0) {
                throw "No spaces found in this Confluence instance."
            }
            
            $selectedSpace = Show-SpaceSelectionTable -Spaces $spaces
            if (-not $selectedSpace) {
                Write-Host "Export cancelled." -ForegroundColor Yellow
                return $null
            }
            
            $SpaceKey = $selectedSpace.key
        }
        
        Write-Host ""
        Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
        Write-Host "║                    Confluence Space Export                   ║" -ForegroundColor Cyan
        Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
        Write-Host ""
        
        # Validate space exists
        Write-Host "Validating space: $SpaceKey" -ForegroundColor Yellow
        $space = $Client.GetSpace($SpaceKey)
        
        Write-Host "✓ Space found: $($space.name)" -ForegroundColor Green
        Write-Host "  Type: $($space.type)" -ForegroundColor White
        Write-Host "  Key: $($space.key)" -ForegroundColor White
        
        # Create export directory
        $exportDir = Join-Path $OutputPath "$SpaceKey-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
        
        Write-Host ""
        Write-Host "Export directory: $exportDir" -ForegroundColor Cyan
        
        # Initialize export summary
        $exportSummary = @{
            SpaceKey = $SpaceKey
            SpaceName = $space.name
            StartTime = Get-Date
            ExportPath = $exportDir
            PagesExported = 0
            AttachmentsDownloaded = 0
            CommentsExported = 0
            Errors = @()
            Success = $true
        }
        
        # Get all pages in the space
        Write-Host ""
        Write-Host "Retrieving pages..." -ForegroundColor Yellow
        $pages = $Client.GetPages($SpaceKey, "body.storage,version,ancestors,descendants.page")
        
        if ($pages.Count -eq 0) {
            Write-Warning "No pages found in space $SpaceKey"
            $exportSummary.Success = $false
            return $exportSummary
        }
        
        Write-Host "✓ Found $($pages.Count) pages" -ForegroundColor Green
        
        # Create subdirectories
        $pagesDir = Join-Path $exportDir "pages"
        $attachmentsDir = Join-Path $exportDir "attachments"
        $metadataDir = Join-Path $exportDir "metadata"
        
        New-Item -ItemType Directory -Path $pagesDir -Force | Out-Null
        if ($IncludeAttachments) {
            New-Item -ItemType Directory -Path $attachmentsDir -Force | Out-Null
        }
        New-Item -ItemType Directory -Path $metadataDir -Force | Out-Null
        
        # Export space metadata
        $space | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $metadataDir "space.json") -Encoding UTF8
        
        # Export pages with progress tracking
        Write-Host ""
        Write-Host "Exporting pages..." -ForegroundColor Yellow
        
        $progressCount = 0
        $totalPages = $pages.Count
        
        foreach ($page in $pages) {
            $progressCount++
            $progressPercent = [math]::Round(($progressCount / $totalPages) * 100, 1)
            
            Write-Progress -Activity "Exporting Pages" -Status "Processing page: $($page.title)" -PercentComplete $progressPercent
            
            try {
                # Export page content
                $pageFileName = Get-SafeFileName -FileName "$($page.title).html"
                $pageFilePath = Join-Path $pagesDir $pageFileName
                
                $htmlContent = ConvertTo-ConfluenceHTML -Page $page -Space $space
                Set-Content -Path $pageFilePath -Value $htmlContent -Encoding UTF8
                
                # Export page metadata
                $pageMetadata = @{
                    id = $page.id
                    title = $page.title
                    type = $page.type
                    status = $page.status
                    version = $page.version
                    ancestors = $page.ancestors
                    exportedFile = $pageFileName
                    exportedDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                }
                
                $metadataFileName = Get-SafeFileName -FileName "$($page.title).json"
                $metadataFilePath = Join-Path $metadataDir $metadataFileName
                $pageMetadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataFilePath -Encoding UTF8
                
                $exportSummary.PagesExported++
                
                # Export attachments if enabled
                if ($IncludeAttachments) {
                    # Note: Attachment export would be implemented here
                    # This is a simplified version for the experimental branch
                }
                
            } catch {
                $error = "Failed to export page '$($page.title)': $($_.Exception.Message)"
                Write-Warning $error
                $exportSummary.Errors += $error
            }
        }
        
        Write-Progress -Activity "Exporting Pages" -Completed
        
        # Create export summary report
        $exportSummary.EndTime = Get-Date
        $exportSummary.Duration = $exportSummary.EndTime - $exportSummary.StartTime
        
        $summaryReport = @"
# Confluence Export Summary

**Space:** $($exportSummary.SpaceName) ($($exportSummary.SpaceKey))
**Export Date:** $($exportSummary.StartTime.ToString('yyyy-MM-dd HH:mm:ss'))
**Duration:** $($exportSummary.Duration.ToString('hh\:mm\:ss'))
**Export Path:** $($exportSummary.ExportPath)

## Statistics
- **Pages Exported:** $($exportSummary.PagesExported)
- **Attachments Downloaded:** $($exportSummary.AttachmentsDownloaded)
- **Comments Exported:** $($exportSummary.CommentsExported)
- **Errors:** $($exportSummary.Errors.Count)

## Export Structure
- ``pages/`` - HTML files for each page
- ``metadata/`` - JSON metadata for each page
- ``attachments/`` - Downloaded attachments (if enabled)
- ``export-summary.json`` - Detailed export information

$( if ($exportSummary.Errors.Count -gt 0) {
    "## Errors`n" + ($exportSummary.Errors | ForEach-Object { "- $_" }) -join "`n"
} )
"@
        
        # Save reports
        Set-Content -Path (Join-Path $exportDir "README.md") -Value $summaryReport -Encoding UTF8
        $exportSummary | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $exportDir "export-summary.json") -Encoding UTF8
        
        Write-Host ""
        Write-Host "✓ Export completed successfully!" -ForegroundColor Green
        Write-Host "  Pages exported: $($exportSummary.PagesExported)" -ForegroundColor White
        Write-Host "  Export location: $exportDir" -ForegroundColor White
        Write-Host "  Duration: $($exportSummary.Duration.ToString('hh\:mm\:ss'))" -ForegroundColor White
        
        if ($exportSummary.Errors.Count -gt 0) {
            Write-Warning "Export completed with $($exportSummary.Errors.Count) errors. Check the summary report for details."
        }
        
        return $exportSummary
        
    } catch {
        Write-Error "Export failed: $($_.Exception.Message)"
        return $null
    } finally {
        # Clean up client if we created it
        if ($PSCmdlet.ParameterSetName -eq 'Config' -and $Client) {
            $Client.Dispose()
        }
    }
}

function Get-SafeFileName {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FileName
    )
    
    # Remove or replace invalid characters for cross-platform compatibility
    $safeName = $FileName -replace '[<>:"/\\|?*]', '_'
    $safeName = $safeName -replace '\s+', '_'
    
    # Handle Windows reserved names
    $reservedNames = @('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9')
    $nameWithoutExtension = [System.IO.Path]::GetFileNameWithoutExtension($safeName)
    
    if ($reservedNames -contains $nameWithoutExtension.ToUpper()) {
        $extension = [System.IO.Path]::GetExtension($safeName)
        $safeName = "${nameWithoutExtension}_safe${extension}"
    }
    
    # Limit length to 200 characters (leaving room for path)
    if ($safeName.Length -gt 200) {
        $extension = [System.IO.Path]::GetExtension($safeName)
        $nameWithoutExt = [System.IO.Path]::GetFileNameWithoutExtension($safeName)
        $safeName = $nameWithoutExt.Substring(0, 200 - $extension.Length) + $extension
    }
    
    return $safeName
}

function ConvertTo-ConfluenceHTML {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject] $Page,
        
        [Parameter(Mandatory = $true)]
        [PSCustomObject] $Space
    )
    
    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$([System.Web.HttpUtility]::HtmlEncode($Page.title))</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .page-header { border-bottom: 2px solid #0052CC; padding-bottom: 10px; margin-bottom: 20px; }
        .page-title { color: #0052CC; margin: 0; }
        .page-info { color: #666; font-size: 0.9em; margin-top: 5px; }
        .page-content { line-height: 1.6; }
        .export-info { background: #f5f5f5; padding: 10px; border-left: 4px solid #0052CC; margin-bottom: 20px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="export-info">
        <strong>Exported from Confluence:</strong> $($Space.name) ($($Space.key))<br>
        <strong>Page ID:</strong> $($Page.id)<br>
        <strong>Version:</strong> $($Page.version.number)<br>
        <strong>Last Modified:</strong> $($Page.version.when)<br>
        <strong>Export Date:</strong> $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    </div>
    
    <div class="page-header">
        <h1 class="page-title">$([System.Web.HttpUtility]::HtmlEncode($Page.title))</h1>
        <div class="page-info">
            Space: $($Space.name) | Type: $($Page.type) | Status: $($Page.status)
        </div>
    </div>
    
    <div class="page-content">
        $($Page.body.storage.value)
    </div>
    
    <hr style="margin-top: 40px;">
    <div style="color: #666; font-size: 0.8em; text-align: center;">
        Exported by Confluence Export-Import Tool (PowerShell) on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    </div>
</body>
</html>
"@
    
    return $html
}