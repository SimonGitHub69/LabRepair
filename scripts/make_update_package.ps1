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
    ".env.example"
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

$Readme = @"
LabRepair - Aggiornamento applicazione
======================================

Data pacchetto: $(Get-Date -Format "yyyy-MM-dd HH:mm")

SUL SERVER (prima di tutto: backup database PostgreSQL)

1. Ferma il servizio LabRepair (o chiudi la finestra Waitress)
   PowerShell amministratore:
     .\scripts\uninstall_service.ps1   # solo stop, oppure
     nssm stop LabRepair

2. Copia i file dello zip SOPRA la cartella di installazione esistente
   (es. C:\LabRepair), SENZA sovrascrivere il file .env

3. PowerShell nella cartella LabRepair:
     .\scripts\clear_pycache.ps1
     .\scripts\prod_install.ps1

   prod_install esegue: pip install, migrate, collectstatic

4. Riavvia:
     .\scripts\prod_start.ps1
   oppure servizio Windows:
     .\scripts\install_service.ps1

5. Privilegi menu (obbligatorio dopo questo aggiornamento):
     .\.venv\Scripts\python.exe manage.py rebuild_labrepair_permissions --reset-groups

6. Verifica:
   - Login e selezione negozio
   - Menu Parametri > Parametri PC: per ogni postazione usa "Gap e descrizione"
   - Stampanti collegate al PC: rileva, descrizione e gap busta (mm)
   - Stampa busta: gap superiore sposta solo parte A, inferiore solo parte B
   - Menu: Documenti, Report, Comandi vocali, Sistema
   - In Admin > Gruppi: privilegi "Può accedere al menu ..."

7. Sui PC client (rilevamento stampanti locali / Brother):
     .\scripts\install_printer_agent_client.ps1
     Aprire LabRepair con LabRepairApp.vbs (avvia anche l'agente stampanti)

8. (Opzionale) Normalizza nomi anagrafiche storiche:
     .\.venv\Scripts\python.exe manage.py normalizza_nomi_anagrafiche --dry-run
     .\.venv\Scripts\python.exe manage.py normalizza_nomi_anagrafiche

9. Backup PostgreSQL schedulato (consigliato, PowerShell Amministratore):
     .\scripts\install_backup_task.ps1
     # oppure orario diverso:
     .\scripts\install_backup_task.ps1 -Time "02:30" -KeepDays 21

NOTA: non copiare .env dal pacchetto. Mantieni quello del server.
NOTA: migration core 0021/0022/0023 (stampanti per Parametri PC + FK Stampante→ConfigurazionePC).
NOTA: --reset-groups riassegna i privilegi dei gruppi Montale/Quarrata/Pistoia
      secondo il catalogo LabRepair (togli residui SECURTEK).
"@
Set-Content -Path (Join-Path $Staging "AGGIORNAMENTO.txt") -Value $Readme -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force
Remove-Item $Staging -Recurse -Force

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "Pacchetto creato: $ZipPath ($sizeMb MB)"
