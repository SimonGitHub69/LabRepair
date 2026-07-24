# Rimuove __pycache__ (utile dopo aggiornamenti zip se Django non parte).
$ErrorActionPreference = "Stop"
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Get-ChildItem -Path (Join-Path $Root "apps") -Recurse -Directory -Filter __pycache__ |
    Remove-Item -Recurse -Force
Get-ChildItem -Path (Join-Path $Root "config") -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Write-Host "Cache Python rimossa in apps/ e config/."
