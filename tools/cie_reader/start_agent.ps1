$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root "publish\cie_reader.exe"

if (-not (Test-Path $exe)) {
    Write-Host "cie_reader.exe non trovato. Eseguo build..."
    & (Join-Path $root "build.ps1")
}

$port = 17345
if ($args.Count -gt 0 -and $args[0] -match '^\d+$') {
    $port = [int]$args[0]
}

Write-Host "Avvio CIE agent su http://127.0.0.1:$port/"
Write-Host "Lascia questa finestra aperta mentre usi LabRepair su questo PC."
Write-Host "Ctrl+C per fermare."
Write-Host ""

& $exe --serve --port $port
