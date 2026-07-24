# Avvio LabRepair in produzione (Windows)
# Uso:
#   .\scripts\prod_install.ps1
#   .\scripts\prod_start.ps1

$ErrorActionPreference = "Stop"
# Cartella progetto = padre di scripts\ (usa $PSScriptRoot; non incollare lo script nel terminale)
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root
Write-Host "Cartella progetto: $Root"

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Crea il virtualenv: python -m venv .venv"
    exit 1
}

$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Manca .env in $Root"
    Write-Host "Esegui: Copy-Item .env.example .env   poi configura DATABASE_URL e ALLOWED_HOSTS"
    exit 1
}

Write-Host "Installazione dipendenze..."
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Installazione dipendenze fallita."
    exit $LASTEXITCODE
}

$MssqlReq = Join-Path $Root "requirements-mssql.txt"
if (Test-Path $MssqlReq) {
    Write-Host "Tentativo installazione pyodbc (opzionale, sync MSSQL)..."
    & $Python -m pip install -r $MssqlReq
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "pyodbc non installato (normale su Python 3.14 senza Visual C++ Build Tools)."
        Write-Warning "LabRepair funziona comunque; sync MSSQL/Gestionale resta disabilitato."
    }
}

& $Python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Installazione OK. Avvio manuale: .\scripts\prod_start.ps1"
Write-Host "Servizio Windows (avvio automatico): apri PowerShell come Amministratore e lancia"
Write-Host "  .\scripts\install_service.ps1"
