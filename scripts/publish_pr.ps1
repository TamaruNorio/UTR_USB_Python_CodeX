param(
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Title
)

$ErrorActionPreference = "Stop"
Set-Location (git rev-parse --show-toplevel)

if (-not $Title) {
    $Title = $Message
}

$branch = git branch --show-current
if ($branch -eq "main") {
    Write-Host "Refusing to publish from main."
    exit 1
}

& (Join-Path $PSScriptRoot "git_preflight.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$changedFiles = git status --short
Write-Host "== pending changes =="
$changedFiles
Write-Host "== commit message =="
Write-Host $Message
Write-Host "== PR title =="
Write-Host $Title
Write-Host "== current branch =="
Write-Host $branch

$answer = Read-Host "Type YES to git add, commit, and push"
if ($answer -ne "YES") {
    Write-Host "Canceled."
    exit 1
}

git add .
git commit -m $Message
git push -u origin $branch

$bodyPath = Join-Path (Get-Location) "pr_body.md"
& (Join-Path $PSScriptRoot "pr_body.ps1") -OutputPath $bodyPath

$bodyText = Get-Content -Raw $bodyPath
$clipboardOk = $false
try {
    Set-Clipboard -Value $bodyText
    $getClipboardCommand = Get-Command Get-Clipboard
    if ($getClipboardCommand.Parameters.ContainsKey("Raw")) {
        $clipboardText = Get-Clipboard -Raw
    } else {
        $clipboardText = (Get-Clipboard) -join [Environment]::NewLine
    }
    if ($clipboardText -eq $bodyText) {
        $clipboardOk = $true
        Write-Host "Clipboard verified."
    }
} catch {
    Write-Host "Clipboard verification failed: $($_.Exception.Message)"
}

if (-not $clipboardOk) {
    notepad $bodyPath
}

$remote = git remote get-url origin
$repoUrl = $null
if ($remote -match '^https://github.com/(.+?)(\.git)?$') {
    $repoUrl = "https://github.com/$($Matches[1] -replace '\.git$','')"
} elseif ($remote -match '^git@github.com:(.+?)(\.git)?$') {
    $repoUrl = "https://github.com/$($Matches[1] -replace '\.git$','')"
}

if ($repoUrl) {
    $createUrl = "$repoUrl/compare/main...$branch?expand=1"
    Write-Host "PR creation URL: $createUrl"
    Start-Process $createUrl
} else {
    Write-Host "Could not infer PR creation URL from origin: $remote"
}
Write-Host "PR creation, merge, and remote branch deletion remain manual."
