$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $root = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0 -and $root) {
        return $root.Trim()
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$repoRoot = Get-RepoRoot
$repoRootWithSlash = (Resolve-Path $repoRoot).Path.TrimEnd("\") + "\"
$blockedWords = @(
    "pass" + "word",
    "se" + "cret",
    "to" + "ken",
    "api" + "key",
    "api" + "_key"
)
$blockedLiterals = @(
    "Client" + "Socket",
    "10" + ".26."
)
$wordPattern = "(?i)\b($($blockedWords -join '|'))\b"
$escapedLiterals = @($blockedLiterals | ForEach-Object { [regex]::Escape($_) })
$literalPattern = "(?i)($([string]::Join('|', $escapedLiterals)))"
$blockedPattern = "$wordPattern|$literalPattern"
$excludedDirs = @(".git", "__pycache__", ".pytest_cache", "logs")
$matches = New-Object System.Collections.Generic.List[object]

Get-ChildItem -Path $repoRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $relative = $_.FullName
        if ($relative.StartsWith($repoRootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
            $relative = $relative.Substring($repoRootWithSlash.Length)
        }
        $parts = $relative -split '[\\/]'
        -not ($parts | Where-Object { $_ -in $excludedDirs })
    } |
    ForEach-Object {
        Select-String -Path $_.FullName -Pattern $blockedPattern -AllMatches -ErrorAction SilentlyContinue |
            Where-Object { $_.Line -notmatch 'secret_scan\.ps1' } |
            ForEach-Object {
                $matches.Add($_)
            }
    }

if ($matches.Count -eq 0) {
    Write-Host "No blocked text found."
    exit 0
}

foreach ($match in $matches) {
    $relative = $match.Path
    if ($relative.StartsWith($repoRootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $relative.Substring($repoRootWithSlash.Length)
    }
    Write-Host "${relative}:$($match.LineNumber): $($match.Line.Trim())"
}
exit 1
