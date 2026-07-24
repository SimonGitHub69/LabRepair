# Rimuove il servizio Windows LabRepair.
# Eseguire come Amministratore:
#   .\scripts\uninstall_service.ps1

param(
    [string]$ServiceName = "LabRepair"
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Esegui PowerShell come Amministratore."
}

if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}

$NssmExe = Join-Path $Root "tools\nssm\nssm.exe"
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "Servizio $ServiceName non trovato."
    exit 0
}

if (Test-Path $NssmExe) {
    & $NssmExe stop $ServiceName confirm
    Start-Sleep -Seconds 2
    & $NssmExe remove $ServiceName confirm
} else {
    Stop-Service $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName | Out-Null
}

Write-Host "Servizio $ServiceName rimosso."
