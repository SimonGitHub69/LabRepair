# Avvia LabRepair con Waitress (produzione)
# Esempio: .\scripts\prod_start.ps1
#          .\scripts\prod_start.ps1 -ListenHost 0.0.0.0 -Port 8000

param(
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8000,
    [int]$Threads = 6
)

$ErrorActionPreference = "Stop"
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root
Write-Host "Cartella progetto: $Root"

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Virtualenv non trovato: $Python"
}

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Write-Error "Manca .env in $Root - esegui: Copy-Item .env.example .env"
}

$env:DJANGO_SETTINGS_MODULE = "config.settings"
$Listen = "{0}:{1}" -f $ListenHost, $Port
$Url = "http://" + $Listen + "/"

Write-Host ("LabRepair in ascolto su " + $Url)
& $Python -m waitress --listen=$Listen --threads=$Threads config.wsgi:application
