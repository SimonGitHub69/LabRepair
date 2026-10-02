# Crea il pacchetto di autoinstallazione LabRepair per il PC SERVER (Windows 10/11).
# Uso:
#   .\scripts\make_server_package.ps1
#   .\scripts\make_server_package.ps1 -OutputName LabRepair_server_windows_custom.zip
#   .\scripts\make_server_package.ps1 -Port 8000

param(
    [string]$OutputName = "",
    [int]$Port = 8000,
    [switch]$IncludeRuntimes
)

$ErrorActionPreference = "Stop"
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root

$Version = "0.0.0"
$versionFile = Join-Path $Root "VERSION"
if (Test-Path $versionFile) {
    $Version = (Get-Content $versionFile -TotalCount 1).Trim()
}

if (-not $OutputName) {
    $OutputName = "LabRepair_server_windows_$Version.zip"
}

$OutDir = Join-Path $Root "installazione"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$ZipPath = Join-Path $OutDir $OutputName
$Staging = Join-Path $env:TEMP ("LabRepair_server_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

Write-Host "Preparo pacchetto server Windows $Version"
Write-Host "Porta predefinita servizio: $Port"

$IncludeDirs = @(
    "apps",
    "config",
    "templates",
    "static",
    "scripts",
    "tools",
    "docs"
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
        if ($rel -match '(^|\\)\.env$') { return }
        if ($rel -match '(^|\\)\.venv(\\|$)') { return }
        if ($rel -match '\\__pycache__\\|\.pyc$|\.pyo$|\\\.pytest_cache\\|\\\.mypy_cache\\|\\bin\\|\\obj\\|\\\.git(\\|$)') {
            return
        }
        # Publish CIE agent non serve sul server di prima installazione.
        if ($rel -match '^tools\\cie_reader\\publish(\\|$)') {
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
    Write-Host "  + $dir"
    Copy-TreeFiltered -Source (Join-Path $Root $dir) -Destination (Join-Path $Staging $dir)
}
foreach ($file in $IncludeFiles) {
    $src = Join-Path $Root $file
    if (Test-Path $src) {
        Write-Host "  + $file"
        Copy-Item -Path $src -Destination (Join-Path $Staging $file) -Force
    }
}

# Assicura che lo script di installazione server sia presente.
$serverInstall = Join-Path $Root "scripts\install_server_windows.ps1"
if (-not (Test-Path $serverInstall)) {
    throw "Manca scripts\install_server_windows.ps1"
}
Copy-Item $serverInstall (Join-Path $Staging "scripts\install_server_windows.ps1") -Force

# Runtime offline opzionali (python + postgresql installer).
$redistSrc = Join-Path $Root "redist"
if ($IncludeRuntimes -and (Test-Path $redistSrc)) {
    Write-Host "  + redist (runtime offline)"
    Copy-TreeFiltered -Source $redistSrc -Destination (Join-Path $Staging "redist")
} elseif ($IncludeRuntimes) {
    Write-Host "  ! IncludeRuntimes richiesto ma manca cartella redist\"
}

$installa = @"
@echo off
cd /d "%~dp0"
title LabRepair - installazione server Windows
echo.
echo  LabRepair - installazione automatica SERVER
echo  ==========================================
echo  Installa anche Python e PostgreSQL se mancano
echo  Destinazione tipica: C:\LabRepair
echo  Porta servizio: $Port
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_server_windows.ps1" -Port $Port
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo Installazione terminata con errori (codice %ERR%).
) else (
  echo Operazione conclusa.
)
pause
exit /b %ERR%
"@
Set-Content -Path (Join-Path $Staging "INSTALLA.bat") -Value $installa -Encoding ASCII

$readme = @"
LabRepair - Installazione SERVER Windows 10/11
==============================================

Versione: $Version
Data pacchetto: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Porta servizio: $Port

Questo pacchetto installa LabRepair sul PC che fa da SERVER
(database PostgreSQL + Waitress come servizio Windows).

PREREQUISITI
------------
- Windows 10/11 o Windows Server 64 bit
- Connessione Internet (al primo install scarica Python e/o PostgreSQL se mancano)
- PowerShell come Amministratore (lo chiede lo script)

NON serve installare a mano Python o PostgreSQL:
l'installer li scarica e configura automaticamente se non sono presenti.

INSTALLAZIONE (un doppio clic)
------------------------------
1. Estrai lo ZIP in una cartella temporanea
   (Esplora risorse -> Estrai tutto).
   Devi vedere INSTALLA.bat, LEGGIMI.txt, manage.py, cartelle apps\, scripts\, ...
2. Doppio clic su INSTALLA.bat
3. Accetta UAC (Amministratore)
4. Conferma la cartella di installazione (default C:\LabRepair)
5. Attendi: eventuale download Python/PostgreSQL, copia file, migrate, servizio

Cosa fa l'installer
-------------------
- Se manca Python 3.12+: lo scarica e lo installa
- Se manca PostgreSQL: lo scarica, lo installa, crea utente/database labrepair
- Copia l'applicazione in C:\LabRepair (o cartella scelta)
- Crea .env (non sovrascrive .env se gia' presente)
- Crea .venv e installa requirements.txt
- Esegue migrate e collectstatic
- Installa e avvia il servizio Windows "LabRepair" (porta $Port)

Credenziali database
--------------------
Se PostgreSQL viene installato da LabRepair, trova in C:\LabRepair:
  POSTGRES_ADMIN.txt   (password superuser postgres - conserva e poi elimina)
La password dell'utente applicativo e' in .env (DATABASE_URL).

Dopo l'installazione
--------------------
1. Apri: http://127.0.0.1:$Port/
2. Crea l'utente amministratore:
     cd C:\LabRepair
     .\.venv\Scripts\python.exe manage.py createsuperuser
3. Apri la porta $Port nel Firewall Windows per i PC client
4. Sui PC client usa LabRepair_client_windows_*.zip con origin.txt:
     http://IP-DEL-SERVER:$Port

Installazione offline (senza Internet)
--------------------------------------
Metti gli installer in redist\ dentro lo zip prima di distribuirlo:
  redist\python-3.12.10-amd64.exe
  redist\postgresql-windows-x64.exe
Poi rilancia make_server_package.ps1 -IncludeRuntimes
oppure copia a mano la cartella redist nello zip.

Aggiornamenti successivi
------------------------
Usa LabRepair_update_YYYYMMDD.zip (make_update_package.ps1),
NON questo pacchetto di prima installazione.
"@
Set-Content -Path (Join-Path $Staging "LEGGIMI.txt") -Value $readme -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

# Zip con slash "/" (Explorer non lascia cartelle vuote).
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem -Path $Staging -Recurse -Force | Where-Object { -not $_.PSIsContainer } | ForEach-Object {
        $rel = $_.FullName.Substring($Staging.Length).TrimStart("\").Replace("\", "/")
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $_.FullName,
            $rel,
            [System.IO.Compression.CompressionLevel]::Optimal
        )
    }
} finally {
    $zip.Dispose()
}

$sfxPath = [System.IO.Path]::ChangeExtension($ZipPath, ".exe")
$madeSfx = $false
$sevenZip = @(
    "$env:ProgramFiles\7-Zip\7z.exe",
    "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($sevenZip) {
    $sfxModule = Join-Path (Split-Path $sevenZip) "7zS.sfx"
    if (-not (Test-Path $sfxModule)) {
        $sfxModule = Join-Path (Split-Path $sevenZip) "7z.sfx"
    }
    $config = @"
;!@Install@!UTF-8!
Title="LabRepair server Windows"
BeginPrompt="Installare LabRepair come SERVER su questo PC?"
RunProgram="INSTALLA.bat"
;!@InstallEnd@!
"@
    $cfgFile = Join-Path $env:TEMP ("LabRepair_sfx_srv_" + [guid]::NewGuid().ToString("N") + ".txt")
    $inner7z = Join-Path $env:TEMP ("LabRepair_server_" + [guid]::NewGuid().ToString("N") + ".7z")
    Set-Content -Path $cfgFile -Value $config -Encoding UTF8
    try {
        & $sevenZip a -t7z -mx=5 $inner7z (Join-Path $Staging "*") | Out-Null
        if ((Test-Path $sfxModule) -and (Test-Path $inner7z)) {
            if (Test-Path $sfxPath) { Remove-Item $sfxPath -Force }
            $out = [System.IO.File]::Create($sfxPath)
            try {
                foreach ($part in @($sfxModule, $cfgFile, $inner7z)) {
                    $bytes = [System.IO.File]::ReadAllBytes($part)
                    $out.Write($bytes, 0, $bytes.Length)
                }
            } finally {
                $out.Close()
            }
            if ((Test-Path $sfxPath) -and ((Get-Item $sfxPath).Length -gt 1MB)) {
                $madeSfx = $true
            }
        }
    } catch {
        $madeSfx = $false
    } finally {
        if (Test-Path $inner7z) { Remove-Item $inner7z -Force -ErrorAction SilentlyContinue }
        if (Test-Path $cfgFile) { Remove-Item $cfgFile -Force -ErrorAction SilentlyContinue }
    }
}

Remove-Item $Staging -Recurse -Force

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host ""
Write-Host "Pacchetto ZIP: $ZipPath ($sizeMb MB)"
if ($madeSfx) {
    $sfxMb = [math]::Round((Get-Item $sfxPath).Length / 1MB, 2)
    Write-Host "Setup EXE:     $sfxPath ($sfxMb MB)"
} else {
    Write-Host "Setup EXE:     non creato. Usa lo ZIP: estrai e doppio clic su INSTALLA.bat"
}
Write-Host ""
Write-Host "Sul PC server: estrai lo zip -> INSTALLA.bat (come Amministratore)."
