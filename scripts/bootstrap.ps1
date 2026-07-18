[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000,

    [string[]]$Origin = @(),

    [switch]$Autostart,
    [switch]$NoHooks,
    [switch]$NoBrowser,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-ToolVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Command is required but was not found on PATH."
    }
    $output = & $Command @Arguments 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0 -or $output -notmatch '(\d+)\.(\d+)(?:\.(\d+))?') {
        throw "Could not determine the installed $Command version. Output: $($output.Trim())"
    }
    return [PSCustomObject]@{
        Text = $Matches[0]
        Major = [int]$Matches[1]
        Minor = [int]$Matches[2]
    }
}

function Assert-MinimumVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Version,

        [Parameter(Mandatory = $true)]
        [int]$Major,

        [int]$Minor = 0
    )

    if ($Version.Major -lt $Major -or ($Version.Major -eq $Major -and $Version.Minor -lt $Minor)) {
        throw "$Name $Major.$Minor or newer is required; found $($Version.Text)."
    }
}

Push-Location $RepoRoot

try {
    Write-Host "Checking Evolastra prerequisites..." -ForegroundColor Cyan
    $python = Get-ToolVersion -Command "python" -Arguments @("--version")
    $node = Get-ToolVersion -Command "node" -Arguments @("--version")
    $npm = Get-ToolVersion -Command "npm" -Arguments @("--version")
    Assert-MinimumVersion -Name "Python" -Version $python -Major 3 -Minor 12
    Assert-MinimumVersion -Name "Node.js" -Version $node -Major 20
    Assert-MinimumVersion -Name "npm" -Version $npm -Major 10
    $isWindows = $env:OS -eq "Windows_NT"

    if ($CheckOnly) {
        [PSCustomObject]@{
            ready = $isWindows
            platform = if ($isWindows) { "windows" } else { "unsupported" }
            python = $python.Text
            node = $node.Text
            npm = $npm.Text
            repository = $RepoRoot
        } | ConvertTo-Json
        return
    }

    if (-not $isWindows) {
        throw "The automated bootstrap is currently verified on Windows only. See docs/getting-started.md for platform notes."
    }

    Write-Host "Setting up locked dependencies..." -ForegroundColor Cyan
    & "$PSScriptRoot\setup.ps1"

    Write-Host "Building the static observatory..." -ForegroundColor Cyan
    npm run build

    $cli = Join-Path $RepoRoot ".venv\Scripts\evolastra.exe"
    $installArguments = @("service", "install", "--port", "$Port")
    foreach ($viewerOrigin in $Origin) {
        $installArguments += @("--origin", $viewerOrigin)
    }
    if ($Autostart) {
        $installArguments += "--autostart"
    }
    if ($NoHooks) {
        $installArguments += "--no-hooks"
    }

    Write-Host "Installing the Local Private companion..." -ForegroundColor Cyan
    & $cli @installArguments

    # Restarting makes updated ports, origins, and web builds effective immediately.
    & $cli service stop | Out-Null
    $status = & $cli service start | ConvertFrom-Json
    if (-not $status.running) {
        throw "The companion did not report a running state after startup."
    }

    $hooks = & $cli codex status | ConvertFrom-Json
    $viewerUrl = "http://127.0.0.1:$Port"

    Write-Host ""
    Write-Host "Evolastra is ready." -ForegroundColor Green
    Write-Host "  Viewer:    $viewerUrl"
    Write-Host "  Companion: running"
    Write-Host "  Hooks:     $($hooks.installed) ($($hooks.events) managed events)"
    Write-Host "  Autostart: $($status.autostart)"
    Write-Host ""
    if (-not $NoHooks) {
        Write-Host "Next: restart Codex once, open /hooks, and approve the Evolastra commands." -ForegroundColor Yellow
    }
    Write-Host "Then run '.\.venv\Scripts\evolastra.exe pair' and enter the code in the viewer."

    if (-not $NoBrowser) {
        Start-Process $viewerUrl
    }
} finally {
    Pop-Location
}
