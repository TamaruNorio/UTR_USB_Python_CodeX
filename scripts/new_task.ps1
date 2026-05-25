param(
    [Parameter(Mandatory = $true)][string]$Branch
)

$ErrorActionPreference = "Stop"
Set-Location (git rev-parse --show-toplevel)

$status = git status --short
if ($status) {
    Write-Host "Working tree is not clean. Commit, stash, or discard changes before starting a new task."
    git status --short
    exit 1
}

git switch main
git pull
git switch -c $Branch

Write-Host "== current branch =="
git branch --show-current
Write-Host "== git status --short =="
git status --short
