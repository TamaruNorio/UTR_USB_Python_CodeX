$ErrorActionPreference = "Stop"

Set-Location (git rev-parse --show-toplevel)

Write-Host "== current branch =="
git branch --show-current

Write-Host ""
Write-Host "== git status --short =="
git status --short

Write-Host ""
Write-Host "== git diff --stat =="
git diff --stat

Write-Host ""
Write-Host "== git log --oneline --decorate -5 =="
git log --oneline --decorate -5

Write-Host ""
Write-Host "== git diff --check =="
git diff --check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "== dev_check =="
& (Join-Path $PSScriptRoot "dev_check.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "git_preflight passed."
