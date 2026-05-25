param(
    [string]$OutputPath
)

$templatePath = Join-Path $PSScriptRoot "..\prompts\pr_body_template.md"
$body = Get-Content -Raw $templatePath

if ($OutputPath) {
    $body | Set-Content -Path $OutputPath -Encoding UTF8
    Write-Host "Wrote $OutputPath"
} else {
    Write-Output $body
}
