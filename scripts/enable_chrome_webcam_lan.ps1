# Crea l'app Desktop "LabRepair" sul PC cassa (webcam Nilox su HTTP LAN).
#
# Uso:
#   .\scripts\enable_chrome_webcam_lan.ps1 -Origin "http://192.168.200.30:8000"
#
# In alternativa, senza PowerShell: copia scripts\LabRepairApp.bat sul Desktop.

param(
    [string]$Origin = ""
)

$ErrorActionPreference = "Stop"

function Find-Browser {
    $candidates = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }
    return $null
}

if (-not $Origin) {
    $Origin = Read-Host "URL LabRepair (es. http://192.168.200.30:8000)"
}

$Origin = $Origin.Trim().TrimEnd('/')
if ($Origin -notmatch '^https?://') {
    $Origin = "http://$Origin"
}

$browser = Find-Browser
if (-not $browser) {
    Write-Error "Chrome o Edge non trovati. Installali e riprova."
}

$profileDir = Join-Path $env:LOCALAPPDATA "LabRepairApp"
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

# --app = finestra senza barra indirizzi (sembra un'app)
$argLine = @(
    "--app=`"$Origin`"",
    "--app-window-size=1400,900",
    "--user-data-dir=`"$profileDir`"",
    "--unsafely-treat-insecure-origin-as-secure=$Origin",
    "--disable-features=InsecureDownloadWarnings"
) -join " "

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "LabRepair.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $browser
$shortcut.Arguments = $argLine
$shortcut.WorkingDirectory = Split-Path $browser
$shortcut.IconLocation = "$browser,0"
$shortcut.Description = "LabRepair"
$shortcut.Save()

# Copia anche il .bat sul Desktop (facile da spostare su altri PC)
$batSrc = Join-Path $PSScriptRoot "LabRepairApp.bat"
$batDst = Join-Path $desktop "LabRepairApp.bat"
if (Test-Path $batSrc) {
    $batText = Get-Content $batSrc -Raw
    $batText = $batText -replace 'set "ORIGIN=http://[^"]+"', ("set `"ORIGIN=$Origin`"")
    Set-Content -Path $batDst -Value $batText -Encoding ASCII
}

Write-Host ""
Write-Host "App creata sul Desktop: LabRepair"
Write-Host "URL: $Origin"
Write-Host "Apri 'LabRepair' (o LabRepairApp.bat) e concedi la fotocamera alla prima foto."
Write-Host "La barra gialla di Chrome e' normale: puoi chiuderla."
Write-Host ""
