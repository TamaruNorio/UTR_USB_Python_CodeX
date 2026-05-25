param(
    [Parameter(Mandatory = $true)][string]$Branch
)

$ErrorActionPreference = "Stop"
Set-Location (git rev-parse --show-toplevel)

if ($Branch -eq "main") {
    Write-Host "Refusing to delete main."
    exit 1
}

$answer = Read-Host "Type YES to sync main and delete local branch '$Branch'"
if ($answer -ne "YES") {
    Write-Host "Canceled."
    exit 1
}

git switch main
git pull

$localBranches = git branch --format "%(refname:short)"
if ($Branch -in $localBranches) {
    git branch -d $Branch
} else {
    Write-Host "Local branch '$Branch' is already absent; skipping delete."
}

& (Join-Path $PSScriptRoot "dev_check.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "sync_after_merge passed."
