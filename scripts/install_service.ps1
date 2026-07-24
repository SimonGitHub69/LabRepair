# Installa LabRepair come servizio Windows (NSSM + Waitress).
# Eseguire come Amministratore:
#   .\scripts\install_service.ps1
# Opzioni:
#   .\scripts\install_service.ps1 -Port 8000 -ServiceName LabRepair

param(
    [string]$ServiceName = "LabRepair",
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8000,
    [int]$Threads = 6
)

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "Esegui PowerShell come Amministratore."
    }
}

Assert-Admin

if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$LogsDir = Join-Path $Root "logs"
$ToolsDir = Join-Path $Root "tools\nssm"
$NssmExe = Join-Path $ToolsDir "nssm.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Virtualenv non trovato: $Python - esegui prima .\scripts\prod_install.ps1"
}
if (-not (Test-Path $EnvFile)) {
    Write-Error "Manca .env in $Root"
}

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

if (-not (Test-Path $NssmExe)) {
    Write-Host "Download NSSM..."
    $zipPath = Join-Path $env:TEMP "nssm-labrepair.zip"
    $extractPath = Join-Path $env:TEMP "nssm-labrepair"
    # Build 2.24-101 consigliato per Windows 10/Server 2016+
    $url = "https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip"
    Invoke-WebRequest -Uri $url -OutFile $zipPath
    if (Test-Path $extractPath) {
        Remove-Item $extractPath -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    $found = Get-ChildItem -Path $extractPath -Recurse -Filter "nssm.exe" |
        Where-Object { $_.FullName -match '\\win64\\nssm\.exe$' } |
        Select-Object -First 1
    if (-not $found) {
        Write-Error "nssm.exe (win64) non trovato nello zip scaricato."
    }
    Copy-Item $found.FullName $NssmExe -Force
    Write-Host "NSSM installato in $NssmExe"
}

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Servizio $ServiceName gia presente: lo aggiorno."
    & $NssmExe stop $ServiceName confirm
    Start-Sleep -Seconds 2
    & $NssmExe remove $ServiceName confirm
    Start-Sleep -Seconds 1
}

$AppParams = "-m waitress --listen=${ListenHost}:${Port} --threads=$Threads config.wsgi:application"

Write-Host "Installazione servizio $ServiceName..."
& $NssmExe install $ServiceName $Python $AppParams
& $NssmExe set $ServiceName AppDirectory $Root
& $NssmExe set $ServiceName DisplayName "LabRepair"
& $NssmExe set $ServiceName Description "LabRepair (Django + Waitress) - gestione riparazioni"
& $NssmExe set $ServiceName Start SERVICE_AUTO_START
& $NssmExe set $ServiceName AppStdout (Join-Path $LogsDir "waitress.out.log")
& $NssmExe set $ServiceName AppStderr (Join-Path $LogsDir "waitress.err.log")
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateBytes 1048576
& $NssmExe set $ServiceName AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=config.settings"
& $NssmExe set $ServiceName AppExit Default Restart
& $NssmExe set $ServiceName AppRestartDelay 3000
& $NssmExe set $ServiceName AppNoConsole 1

# Porta firewall (idempotente)
$ruleName = "LabRepair HTTP $Port"
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "Regola firewall creata: TCP $Port"
}

Start-Service $ServiceName
Start-Sleep -Seconds 2
$svc = Get-Service $ServiceName
Write-Host ""
Write-Host "Servizio: $($svc.Name) - stato: $($svc.Status)"
Write-Host "URL: http://127.0.0.1:${Port}/"
Write-Host "Log: $LogsDir"
Write-Host ""
Write-Host "Comandi utili:"
Write-Host "  Start-Service $ServiceName"
Write-Host "  Stop-Service $ServiceName"
Write-Host "  Restart-Service $ServiceName"
Write-Host "  .\scripts\uninstall_service.ps1"
