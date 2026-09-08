# Crea zip di aggiornamento LabRepair per il server cliente.
# Uso: .\scripts\make_update_package.ps1
#      .\scripts\make_update_package.ps1 -OutputName LabRepair_update_20260724.zip

param(
    [string]$OutputName = ""
)

$ErrorActionPreference = "Stop"
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root

if (-not $OutputName) {
    $OutputName = "LabRepair_update_{0:yyyyMMdd}.zip" -f (Get-Date)
}
$ZipPath = Join-Path $Root $OutputName
$Staging = Join-Path $env:TEMP ("LabRepair_update_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

$IncludeDirs = @(
    "apps",
    "config",
    "templates",
    "static",
    "scripts",
    "tools"
)
$IncludeFiles = @(
    "manage.py",
    "requirements.txt",
    "requirements-mssql.txt",
    ".env.example",
    "VERSION"
)

function Copy-TreeFiltered {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path $Source)) {
        return
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -Path $Source -Recurse -Force | ForEach-Object {
        $rel = $_.FullName.Substring($Source.Length).TrimStart("\")
        if ($rel -match '\\__pycache__\\|\.pyc$|\.pyo$|\\\.pytest_cache\\|\\\.mypy_cache\\') {
            return
        }
        $target = Join-Path $Destination $rel
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        } else {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            Copy-Item -Path $_.FullName -Destination $target -Force
        }
    }
}

foreach ($dir in $IncludeDirs) {
    Copy-TreeFiltered -Source (Join-Path $Root $dir) -Destination (Join-Path $Staging $dir)
}
foreach ($file in $IncludeFiles) {
    $src = Join-Path $Root $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $Staging $file) -Force
    }
}

$Installa = @"
@echo off
title LabRepair - aggiornamento server
cd /d "%~dp0"
echo.
echo  LabRepair - aggiornamento automatico server
echo  ==========================================
echo  1) Backup PostgreSQL PRIMA di continuare
echo  2) Conferma la cartella di installazione (es. C:\LabRepair)
echo  3) Lo script NON sovrascrive il file .env
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_update_server.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo Aggiornamento terminato con errori (codice %ERR%).
) else (
  echo Operazione conclusa.
)
pause
exit /b %ERR%
"@
Set-Content -Path (Join-Path $Staging "INSTALLA.bat") -Value $Installa -Encoding ASCII

$Readme = @"
LabRepair - Aggiornamento applicazione
======================================

Data pacchetto: $(Get-Date -Format "yyyy-MM-dd HH:mm")

INSTALLAZIONE AUTOMATICA (consigliata)
--------------------------------------
1. Backup database PostgreSQL
2. Estrai questo zip in una cartella temporanea
3. Doppio clic su INSTALLA.bat (accetta UAC amministratore)
4. Conferma la cartella di installazione (default C:\LabRepair)
5. Attendi fine script (copia file, migrate, privilegi, riavvio)

Lo installer NON sovrascrive il file .env.

INSTALLAZIONE MANUALE
---------------------
1. Ferma il servizio LabRepair (o chiudi la finestra Waitress)
   PowerShell amministratore:
     nssm stop LabRepair

2. Copia i file dello zip SOPRA la cartella di installazione esistente
   (es. C:\LabRepair), SENZA sovrascrivere il file .env

3. PowerShell nella cartella LabRepair:
     .\scripts\clear_pycache.ps1
     .\scripts\prod_install.ps1

4. Privilegi menu:
     .\.venv\Scripts\python.exe manage.py rebuild_labrepair_permissions --reset-groups

5. Riavvia:
     .\scripts\prod_start.ps1
   oppure servizio Windows:
     .\scripts\install_service.ps1

Verifica:
- Login e selezione negozio
- Menu Parametri > Parametri PC: gap e descrizione stampanti
- Stampa busta / sync casse se usati

Sui PC client (app, lettore CIE, stampanti locali):
  estrai installazione\LabRepair_client_windows_*.zip
  doppio clic su INSTALLA.bat

NOTA: non copiare .env dal pacchetto. Mantieni quello del server.
"@
Set-Content -Path (Join-Path $Staging "AGGIORNAMENTO.txt") -Value $Readme -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force
Remove-Item $Staging -Recurse -Force

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "Pacchetto creato: $ZipPath ($sizeMb MB)"
