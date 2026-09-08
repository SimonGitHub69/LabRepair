# Installa LabRepair sul PC client Windows (cassa / banco).
# Non richiede privilegi di amministratore (salvo eventuale .NET 8).
#
# Uso:
#   .\scripts\install_client_windows.ps1
#   .\scripts\install_client_windows.ps1 -Origin "http://192.168.200.30:8000"
#   .\scripts\install_client_windows.ps1 -Silent
# Dal pacchetto: doppio clic su INSTALLA.bat

param(
    [string]$Origin = "",
    [switch]$Silent,
    [switch]$SkipLaunch,
    [switch]$SkipDotNet
)

$ErrorActionPreference = "Stop"

if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}

function Normalize-Origin([string]$value) {
    $value = $value.Trim().TrimEnd("/")
    if ($value -notmatch "^https?://") {
        $value = "http://$value"
    }
    return $value
}

function Test-DotNet8 {
    try {
        $runtimes = & dotnet --list-runtimes 2>$null
        if ($runtimes -match "Microsoft\.WindowsDesktop\.App 8\.") { return $true }
        if ($runtimes -match "Microsoft\.NETCore\.App 8\.") { return $true }
    } catch {
        return $false
    }
    return $false
}

function Find-Browser {
    $candidates = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    return $null
}

function New-Shortcut($path, $target, $arguments, $workDir, $icon, $description) {
    $folder = Split-Path -Parent $path
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
    }
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $target
    if ($arguments) { $lnk.Arguments = $arguments }
    if ($workDir) { $lnk.WorkingDirectory = $workDir }
    if ($icon -and (Test-Path $icon)) {
        $lnk.IconLocation = "$icon,0"
    }
    $lnk.Description = $description
    $lnk.Save()
}

function Read-OriginFile([string]$path) {
    if (-not (Test-Path $path)) { return "" }
    $line = (Get-Content -Path $path -TotalCount 1 -ErrorAction SilentlyContinue)
    if ($null -eq $line) { return "" }
    return $line.ToString().Trim()
}

$DefaultOrigin = "http://192.168.200.30:8000"
$resolved = $Origin
if (-not $resolved) {
    $resolved = Read-OriginFile (Join-Path $Root "origin.txt")
}
if (-not $resolved) {
    $resolved = Read-OriginFile (Join-Path $PSScriptRoot "origin.txt")
}
if (-not $resolved) {
    if ($Silent) {
        $resolved = $DefaultOrigin
    } else {
        Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
        $typed = [Microsoft.VisualBasic.Interaction]::InputBox(
            "Indirizzo del server LabRepair (senza slash finale).",
            "Installazione LabRepair",
            $DefaultOrigin
        )
        if ([string]::IsNullOrWhiteSpace($typed)) {
            Write-Host "Installazione annullata."
            exit 1
        }
        $resolved = $typed
    }
}
$Origin = Normalize-Origin $resolved

$ScriptsDir = Join-Path $Root "scripts"
$CieSource = Join-Path $Root "tools\cie_reader\publish"
$PrinterSource = Join-Path $Root "tools\printer_agent\printer_agent.ps1"
$AppDir = Join-Path $env:LOCALAPPDATA "LabRepair"
$CieDir = Join-Path $env:LOCALAPPDATA "LabRepairCieAgent"
$PrinterDir = Join-Path $env:LOCALAPPDATA "LabRepairPrinterAgent"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Startup = [Environment]::GetFolderPath("Startup")
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\LabRepair"

Write-Host "LabRepair - installazione PC client"
Write-Host "Server: $Origin"
Write-Host "Cartella: $AppDir"
Write-Host ""

New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
New-Item -ItemType Directory -Force -Path $CieDir | Out-Null
New-Item -ItemType Directory -Force -Path $PrinterDir | Out-Null
New-Item -ItemType Directory -Force -Path $StartMenu | Out-Null

$launcherFiles = @(
    "LabRepairApp.vbs",
    "LabRepairApp.bat",
    "LabRepairApp-browser.bat",
    "LabRepairCieAgent.vbs",
    "LabRepairCieAgent.bat",
    "LabRepairPrinterAgent.vbs",
    "LabRepair.ico"
)
foreach ($name in $launcherFiles) {
    $src = Join-Path $ScriptsDir $name
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $AppDir $name) -Force
    }
}

Set-Content -Path (Join-Path $AppDir "origin.txt") -Value $Origin -Encoding ASCII

$cieExe = Join-Path $CieSource "cie_reader.exe"
if (Test-Path $cieExe) {
    Write-Host "Copio agent CIE..."
    Copy-Item (Join-Path $CieSource "*") $CieDir -Recurse -Force
} else {
    Write-Host "ATTENZIONE: manca cie_reader.exe in $CieSource"
    Write-Host "  Sul PC di sviluppo: tools\cie_reader\build.ps1"
}

if (Test-Path $PrinterSource) {
    Write-Host "Copio agent stampanti..."
    Copy-Item $PrinterSource (Join-Path $PrinterDir "printer_agent.ps1") -Force
} else {
    Write-Host "ATTENZIONE: manca $PrinterSource"
}

$appVbs = Join-Path $AppDir "LabRepairApp.vbs"
$cieVbs = Join-Path $AppDir "LabRepairCieAgent.vbs"
$printerVbs = Join-Path $AppDir "LabRepairPrinterAgent.vbs"
$icon = Join-Path $AppDir "LabRepair.ico"

New-Shortcut `
    (Join-Path $Desktop "LabRepair.lnk") `
    "wscript.exe" `
    "//nologo `"$appVbs`"" `
    $AppDir `
    $icon `
    "LabRepair"
New-Shortcut `
    (Join-Path $StartMenu "LabRepair.lnk") `
    "wscript.exe" `
    "//nologo `"$appVbs`"" `
    $AppDir `
    $icon `
    "LabRepair"

if (Test-Path $cieVbs) {
    New-Shortcut `
        (Join-Path $Startup "LabRepair CIE Agent.lnk") `
        "wscript.exe" `
        "//nologo `"$cieVbs`"" `
        $AppDir `
        $null `
        "Agent lettore CIE LabRepair"
    if (Test-Path (Join-Path $CieDir "cie_reader.exe")) {
        New-Shortcut `
            (Join-Path $Desktop "LabRepair CIE Agent.lnk") `
            (Join-Path $CieDir "cie_reader.exe") `
            "--serve" `
            $CieDir `
            $null `
            "Agent lettore CIE per LabRepair"
    }
}

if (Test-Path $printerVbs) {
    New-Shortcut `
        (Join-Path $Startup "LabRepair Printer Agent.lnk") `
        "wscript.exe" `
        "//nologo `"$printerVbs`"" `
        $AppDir `
        $null `
        "Agent stampanti LabRepair"
}

$dotnetOk = Test-DotNet8
$needsDotNet = (Test-Path (Join-Path $CieDir "cie_reader.exe")) -and -not (Test-Path (Join-Path $CieDir "coreclr.dll"))
if ($needsDotNet -and -not $dotnetOk -and -not $SkipDotNet) {
    $redist = $null
    foreach ($dir in @(
        (Join-Path $Root "redist"),
        (Join-Path $Root "installazione\LabRepair_files_old")
    )) {
        if (-not (Test-Path $dir)) { continue }
        $redist = Get-ChildItem -Path $dir -Filter "windowsdesktop-runtime-*.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($redist) { break }
    }
    if ($redist) {
        Write-Host "Installo .NET 8 Desktop Runtime (richiede conferma UAC)..."
        try {
            Start-Process -FilePath $redist.FullName -ArgumentList "/install /quiet /norestart" -Wait -Verb RunAs
        } catch {
            Write-Host "Installazione .NET 8 saltata o annullata."
        }
        $dotnetOk = Test-DotNet8
    }
    if (-not $dotnetOk) {
        Write-Host "ATTENZIONE: .NET 8 non risulta installato."
        Write-Host "  Se l'agent CIE non parte: https://dotnet.microsoft.com/download/dotnet/8.0"
        Write-Host "  Scegli Desktop Runtime x64."
    }
}

$browser = Find-Browser
if (-not $browser) {
    Write-Host "ATTENZIONE: Chrome o Edge non trovati. Installali prima di aprire LabRepair."
}

function Test-HttpOk([string]$url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

if (Test-Path $cieVbs) {
    Start-Process "wscript.exe" -ArgumentList "//nologo `"$cieVbs`"" -WindowStyle Hidden
}
if (Test-Path $printerVbs) {
    Start-Process "wscript.exe" -ArgumentList "//nologo `"$printerVbs`"" -WindowStyle Hidden
}
Start-Sleep -Seconds 2

if (Test-HttpOk "http://127.0.0.1:17345/health") {
    Write-Host "Agent CIE attivo su http://127.0.0.1:17345/health"
} elseif (Test-Path (Join-Path $CieDir "cie_reader.exe")) {
    Write-Host "ATTENZIONE: agent CIE non risponde. Avvia 'LabRepair CIE Agent' dal Desktop."
}

if (Test-HttpOk "http://127.0.0.1:17346/health") {
    Write-Host "Agent stampanti attivo su http://127.0.0.1:17346/health"
} elseif (Test-Path (Join-Path $PrinterDir "printer_agent.ps1")) {
    Write-Host "ATTENZIONE: agent stampanti non risponde."
}

Write-Host ""
Write-Host "Installazione completata."
Write-Host "  App:        $appVbs"
Write-Host "  Collegamento Desktop: LabRepair"
Write-Host "  Server:     $Origin"
Write-Host "Apri LabRepair dal Desktop. In Anagrafica usa Leggi CIE."
Write-Host "In Parametri -> Stampanti usa Rileva dal sistema."

if (-not $SkipLaunch -and (Test-Path $appVbs) -and $browser) {
    Start-Process "wscript.exe" -ArgumentList "//nologo `"$appVbs`""
}
