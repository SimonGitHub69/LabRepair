# Crea il pacchetto auto-installante per i PC client Windows.
# Uso:
#   .\scripts\make_client_package.ps1
#   .\scripts\make_client_package.ps1 -Origin "http://192.168.200.30:8000"
#   .\scripts\make_client_package.ps1 -FrameworkDependent

param(
    [string]$OutputName = "",
    [string]$Origin = "",
    [switch]$FrameworkDependent,
    [switch]$IncludeDotNetRuntime
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
    $OutputName = "LabRepair_client_windows_$Version.zip"
}

$OutDir = Join-Path $Root "installazione"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$ZipPath = Join-Path $OutDir $OutputName
$Staging = Join-Path $env:TEMP ("LabRepair_client_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

$DefaultOrigin = "http://192.168.200.30:8000"
if (-not $Origin) { $Origin = $DefaultOrigin }
$Origin = $Origin.Trim().TrimEnd("/")
if ($Origin -notmatch "^https?://") { $Origin = "http://$Origin" }

Write-Host "Preparo pacchetto client Windows $Version"
Write-Host "Server predefinito: $Origin"

$scriptNames = @(
    "install_client_windows.ps1",
    "uninstall_client_windows.ps1",
    "install_cie_agent_client.ps1",
    "install_printer_agent_client.ps1",
    "LabRepairApp.vbs",
    "LabRepairApp.bat",
    "LabRepairApp-browser.bat",
    "LabRepairCieAgent.vbs",
    "LabRepairCieAgent.bat",
    "LabRepairPrinterAgent.vbs",
    "LabRepair.ico"
)
$stagingScripts = Join-Path $Staging "scripts"
New-Item -ItemType Directory -Path $stagingScripts -Force | Out-Null
foreach ($name in $scriptNames) {
    $src = Join-Path $Root "scripts\$name"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $stagingScripts $name) -Force
    }
}

$cieDest = Join-Path $Staging "tools\cie_reader\publish"
New-Item -ItemType Directory -Path $cieDest -Force | Out-Null
$cieProject = Join-Path $Root "tools\cie_reader\CieReader.csproj"
$publishedSelfContained = $false
if (-not $FrameworkDependent -and (Test-Path $cieProject)) {
    $dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($dotnet) {
        Write-Host "Compilo agent CIE self-contained (nessun .NET da installare sul client)..."
        try {
            & dotnet publish $cieProject `
                -c Release `
                -r win-x64 `
                --self-contained true `
                -p:DebugType=None `
                -p:DebugSymbols=false `
                -o $cieDest
            if ($LASTEXITCODE -eq 0 -and (Test-Path (Join-Path $cieDest "cie_reader.exe"))) {
                $publishedSelfContained = $true
            }
        } catch {
            Write-Host "Publish self-contained non riuscito, uso la cartella publish esistente."
        }
    }
}

if (-not $publishedSelfContained) {
    $cieSrc = Join-Path $Root "tools\cie_reader\publish"
    if (-not (Test-Path (Join-Path $cieSrc "cie_reader.exe"))) {
        throw "Manca tools\cie_reader\publish\cie_reader.exe. Esegui tools\cie_reader\build.ps1"
    }
    Write-Host "Copio agent CIE framework-dependent..."
    Copy-Item (Join-Path $cieSrc "*") $cieDest -Force
    Get-ChildItem $cieDest -Filter "*.pdb" -ErrorAction SilentlyContinue | Remove-Item -Force
}

$printerDest = Join-Path $Staging "tools\printer_agent"
New-Item -ItemType Directory -Path $printerDest -Force | Out-Null
Copy-Item (Join-Path $Root "tools\printer_agent\printer_agent.ps1") (Join-Path $printerDest "printer_agent.ps1") -Force

$wantRedist = $IncludeDotNetRuntime -or (-not $publishedSelfContained)
if ($wantRedist) {
    $redistSrc = @(
        (Join-Path $Root "redist\windowsdesktop-runtime-8.0.23-win-x64.exe"),
        (Join-Path $Root "installazione\LabRepair_files_old\windowsdesktop-runtime-8.0.23-win-x64.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($redistSrc) {
        $redistDest = Join-Path $Staging "redist"
        New-Item -ItemType Directory -Path $redistDest -Force | Out-Null
        Write-Host "Includo .NET 8 Desktop Runtime..."
        Copy-Item $redistSrc (Join-Path $redistDest (Split-Path $redistSrc -Leaf)) -Force
    } elseif (-not $publishedSelfContained) {
        Write-Host "AVVISO: runtime .NET 8 non trovato, il client lo dovra' installare a mano se manca."
    }
}

Set-Content -Path (Join-Path $Staging "origin.example.txt") -Value $Origin -Encoding ASCII
Set-Content -Path (Join-Path $Staging "origin.txt") -Value $Origin -Encoding ASCII

$installa = @"
@echo off
cd /d "%~dp0"
title LabRepair - installazione PC client
echo.
echo  LabRepair - installazione automatica PC client
echo.
if "%~1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_client_windows.ps1"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_client_windows.ps1" -Origin "%~1"
)
if errorlevel 1 (
    echo.
    echo Installazione non completata.
    pause
    exit /b 1
)
echo.
pause
exit /b 0
"@
Set-Content -Path (Join-Path $Staging "INSTALLA.bat") -Value $installa -Encoding ASCII

$disinstalla = @"
@echo off
cd /d "%~dp0"
title LabRepair - disinstallazione PC client
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\uninstall_client_windows.ps1"
if errorlevel 1 pause
"@
Set-Content -Path (Join-Path $Staging "DISINSTALLA.bat") -Value $disinstalla -Encoding ASCII

$cieNote = "incluso, senza bisogno di .NET sul PC"
if (-not $publishedSelfContained) {
    $cieNote = "incluso; se manca .NET 8 Desktop Runtime l'installer prova a installarlo"
}

$readme = @"
LabRepair - PC client Windows
=============================

Versione: $Version
Data pacchetto: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Server predefinito: $Origin

INSTALLAZIONE (un doppio clic)
------------------------------
1. Copia questa cartella sul PC cassa/banco (NON sul server).
2. Controlla origin.txt (URL del server LabRepair) e se serve modificalo.
3. Doppio clic su INSTALLA.bat
4. Usa il collegamento Desktop "LabRepair".

Installazione silenziosa:
  INSTALLA.bat http://192.168.200.30:8000

Per preimpostare il server su tanti PC: modifica origin.txt
(una riga con l'URL) e poi lancia INSTALLA.bat.

Cosa viene installato
---------------------
- App LabRepair (finestra Chrome/Edge, senza barra indirizzi)
- Agent CIE (lettore Bit4id)  [$cieNote]
- Agent stampanti (Brother e altre stampanti del PC)
- Avvio automatico degli agent all'accesso Windows
- Collegamenti Desktop e menu Start

Verifica
--------
- http://127.0.0.1:17345/health   agent CIE
- http://127.0.0.1:17346/health   agent stampanti
- Anagrafica -> Leggi CIE
- Parametri -> Stampanti -> Rileva dal sistema

Prerequisiti sul PC
-------------------
- Windows 10/11 64 bit
- Chrome oppure Edge
- Lettore Bit4id collegato (solo se usi Leggi CIE)
- Stampanti installate in Windows (solo se stampi dal PC)

Disinstallazione
----------------
Doppio clic su DISINSTALLA.bat

NOTA: questo pacchetto e' per i PC client. L'applicazione Django
resta sul server.
"@
Set-Content -Path (Join-Path $Staging "LEGGIMI.txt") -Value $readme -Encoding UTF8

Get-ChildItem -Path $cieDest -Filter "*.pdb" -ErrorAction SilentlyContinue | Remove-Item -Force

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force

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
Title="LabRepair client Windows"
BeginPrompt="Installare LabRepair su questo PC?"
RunProgram="INSTALLA.bat"
;!@InstallEnd@!
"@
    $cfgFile = Join-Path $env:TEMP ("LabRepair_sfx_" + [guid]::NewGuid().ToString("N") + ".txt")
    $inner7z = Join-Path $env:TEMP ("LabRepair_client_" + [guid]::NewGuid().ToString("N") + ".7z")
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

if (-not $madeSfx) {
    $iexStage = Join-Path $env:TEMP ("LabRepair_iex_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $iexStage -Force | Out-Null
    Copy-Item $ZipPath (Join-Path $iexStage "payload.zip") -Force
    $setupBat = @"
@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%~dp0payload.zip' -DestinationPath '%~dp0payload' -Force"
call "%~dp0payload\INSTALLA.bat"
"@
    Set-Content -Path (Join-Path $iexStage "setup.bat") -Value $setupBat -Encoding ASCII
    $sedPath = Join-Path $iexStage "setup.sed"
    $sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$sfxPath
FriendlyName=LabRepair client Windows
AppLaunched=cmd /c setup.bat
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="payload.zip"
FILE1="setup.bat"
[SourceFiles]
SourceFiles0=$iexStage\
[SourceFiles0]
%FILE0%=
%FILE1%=
"@
    Set-Content -Path $sedPath -Value $sed -Encoding ASCII
    $iexpress = Join-Path $env:SystemRoot "System32\iexpress.exe"
    if (Test-Path $iexpress) {
        try {
            if (Test-Path $sfxPath) { Remove-Item $sfxPath -Force }
            $p = Start-Process -FilePath $iexpress -ArgumentList @("/N", $sedPath) -Wait -PassThru
            if ((Test-Path $sfxPath) -and ((Get-Item $sfxPath).Length -gt 1MB) -and $p.ExitCode -eq 0) {
                $madeSfx = $true
            }
        } catch {
            $madeSfx = $false
        }
    }
    Remove-Item $iexStage -Recurse -Force -ErrorAction SilentlyContinue
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
Write-Host "CIE: $(if ($publishedSelfContained) { 'self-contained' } else { 'framework-dependent' })"
