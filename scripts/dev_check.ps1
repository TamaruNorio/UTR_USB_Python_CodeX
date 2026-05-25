$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $root = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0 -and $root) {
        return $root.Trim()
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Invoke-PytestCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$DisplayName,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [hashtable]$ExtraEnv = @{}
    )

    Write-Host "Trying: $DisplayName"
    $oldValues = @{}
    foreach ($key in $ExtraEnv.Keys) {
        $oldValues[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, $ExtraEnv[$key], "Process")
    }

    try {
        & $Command @Arguments | ForEach-Object { Write-Host $_ }
        $code = $LASTEXITCODE
    } finally {
        foreach ($key in $ExtraEnv.Keys) {
            [Environment]::SetEnvironmentVariable($key, $oldValues[$key], "Process")
        }
    }

    return $code
}

Set-Location (Get-RepoRoot)

Write-Host "== git status --short =="
git status --short

Write-Host ""
Write-Host "== pytest =="
$attempts = New-Object System.Collections.Generic.List[string]
$pytestRan = $false
$pytestPassed = $false
$overallPassed = $true

if (-not (Test-Path "tests")) {
    Write-Host "tests directory was not found. Pytest target remains limited to tests."
}

$pytestTemp = Join-Path $env:TEMP "utr_usb_pytest_tmp"
New-Item -ItemType Directory -Force -Path $pytestTemp | Out-Null
$pytestArguments = @("-m", "pytest", "-p", "no:cacheprovider", "--basetemp", $pytestTemp, "tests")

$candidates = @(
    @{ Name = "py $($pytestArguments -join ' ')"; Command = "py"; Arguments = $pytestArguments; Env = @{} },
    @{ Name = "python $($pytestArguments -join ' ')"; Command = "python"; Arguments = $pytestArguments; Env = @{} }
)

$codexPythonCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    (Join-Path $env:USERPROFILE ".codex\python\python.exe"),
    "C:\opt\python\python.exe"
) | Where-Object { $_ -and (Test-Path $_) }

foreach ($pythonPath in $codexPythonCandidates) {
    $candidates += @{ Name = "$pythonPath $($pytestArguments -join ' ')"; Command = $pythonPath; Arguments = $pytestArguments; Env = @{ "TMP" = $pytestTemp; "TEMP" = $pytestTemp; "PYTEST_DEBUG_TEMPROOT" = $pytestTemp } }
}

foreach ($candidate in $candidates) {
    $attempts.Add($candidate.Name)
    try {
        $code = Invoke-PytestCandidate -DisplayName $candidate.Name -Command $candidate.Command -Arguments $candidate.Arguments -ExtraEnv $candidate.Env
        $pytestRan = $true
        if ($code -eq 0) {
            $pytestPassed = $true
            break
        }
        Write-Host "Failed with exit code $code."
    } catch {
        Write-Host "Could not start: $($_.Exception.Message)"
    }
}

if (-not $pytestRan -or -not $pytestPassed) {
    Write-Host "Pytest did not complete successfully."
    Write-Host "Attempted commands:"
    foreach ($attempt in $attempts) {
        Write-Host "  - $attempt"
    }
    $overallPassed = $false
}

Write-Host ""
Write-Host "== blocked text scan =="
& (Join-Path $PSScriptRoot "secret_scan.ps1")
if ($LASTEXITCODE -ne 0) {
    $overallPassed = $false
}

Write-Host ""
Write-Host "== .gitignore check =="
$requiredIgnoreEntries = @(".pytest_cache/", "__pycache__/", "logs/", "pr_body.md")
$gitignore = Get-Content ".gitignore" -ErrorAction Stop
$missing = @($requiredIgnoreEntries | Where-Object { $_ -notin $gitignore })
if ($missing.Count -gt 0) {
    Write-Host "Missing .gitignore entries:"
    $missing | ForEach-Object { Write-Host "  - $_" }
    $overallPassed = $false
} else {
    Write-Host ".gitignore check passed."
}

if (-not $overallPassed) {
    exit 1
}
Write-Host "dev_check passed."
