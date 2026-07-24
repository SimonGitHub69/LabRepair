# Abilita la webcam Nilox quando LabRepair e' aperto in HTTP sulla LAN
# (Chrome/Edge bloccano getUserMedia fuori da localhost/HTTPS).
#
# Uso sul PC cassa (dove e' collegata la Nilox):
#   .\scripts\enable_chrome_webcam_lan.ps1
#   .\scripts\enable_chrome_webcam_lan.ps1 -Origin "http://192.168.1.10:8000"
#
# Crea un collegamento Desktop "LabRepair (Webcam)" che apre Chrome
# con l'origine trattata come sicura.

param(
    [string]$Origin = ""
)

$ErrorActionPreference = "Stop"

function Find-Browser {
    $candidates = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }
    return $null
}

if (-not $Origin) {
    $envFile = Join-Path (Split-Path -Parent $PSScriptRoot) ".env"
    if (Test-Path $envFile) {
        $hostsLine = Get-Content $envFile | Where-Object { $_ -match '^\s*ALLOWED_HOSTS\s*=' } | Select-Object -First 1
        if ($hostsLine) {
            $hosts = ($hostsLine -replace '^\s*ALLOWED_HOSTS\s*=\s*', '').Split(',') |
                ForEach-Object { $_.Trim() } |
                Where-Object { $_ -and $_ -notin @('127.0.0.1', 'localhost') }
            if ($hosts.Count -gt 0) {
                $Origin = "http://$($hosts[0]):8000"
            }
        }
    }
}

if (-not $Origin) {
    $Origin = Read-Host "URL LabRepair (es. http://192.168.1.10:8000)"
}

$Origin = $Origin.Trim().TrimEnd('/')
if ($Origin -notmatch '^https?://') {
    $Origin = "http://$Origin"
}

$browser = Find-Browser
if (-not $browser) {
    Write-Error "Chrome o Edge non trovati. Installali e riprova."
}

$profileDir = Join-Path $env:LOCALAPPDATA "LabRepairChromeWebcam"
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

$args = @(
    "--user-data-dir=`"$profileDir`"",
    "--unsafely-treat-insecure-origin-as-secure=$Origin",
    "--disable-features=InsecureDownloadWarnings",
    $Origin
)

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "LabRepair (Webcam).lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $browser
$shortcut.Arguments = ($args -join " ")
$shortcut.WorkingDirectory = Split-Path $browser
$shortcut.IconLocation = "$browser,0"
$shortcut.Description = "LabRepair con webcam abilitata su HTTP LAN"
$shortcut.Save()

Write-Host ""
Write-Host "Creato collegamento: $lnkPath"
Write-Host "Origine abilitata:   $Origin"
Write-Host "Browser:             $browser"
Write-Host ""
Write-Host "Apri SOLO quel collegamento sul PC della Nilox (non il Chrome normale)."
Write-Host "Alla prima foto concedi il permesso fotocamera."
Write-Host ""
