# Imposta la policy Chrome/Edge che nasconde "Non sicuro" per LabRepair su HTTP LAN.
# Uso (PowerShell come Amministratore sul PC server o client):
#   .\scripts\enable_not_secure_hide.ps1
#   .\scripts\enable_not_secure_hide.ps1 -Origin "http://192.168.200.30:8000"

param(
    [string]$Origin = ""
)

$ErrorActionPreference = "Stop"

if (-not $Origin) {
    $originFile = Join-Path $PSScriptRoot "origin.txt"
    if (Test-Path $originFile) {
        $Origin = (Get-Content $originFile -TotalCount 1).Trim()
    }
}
if (-not $Origin) {
    $Origin = "http://192.168.200.30:8000"
}

$Origin = $Origin.Trim().TrimEnd("/")
if ($Origin -notmatch "^https?://") {
    $Origin = "http://$Origin"
}

function Set-OriginPolicy {
    param([string]$RootKey)
    $path = Join-Path $RootKey "OverrideSecurityRestrictionsOnInsecureOrigin"
    New-Item -Path $path -Force | Out-Null
    New-ItemProperty -Path $path -Name "1" -Value $Origin -PropertyType String -Force | Out-Null
}

$targets = @(
    "HKCU:\Software\Policies\Google\Chrome",
    "HKCU:\Software\Policies\Microsoft\Edge"
)

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if ($isAdmin) {
    $targets += @(
        "HKLM:\SOFTWARE\Policies\Google\Chrome",
        "HKLM:\SOFTWARE\Policies\Microsoft\Edge"
    )
}

foreach ($root in $targets) {
    Set-OriginPolicy -RootKey $root
    Write-Host "Policy impostata: $root -> $Origin"
}

Write-Host ""
Write-Host "Chiudi COMPLETAMENTE Chrome e Edge (Task Manager se serve), poi riapri LabRepair dal collegamento App."
if (-not $isAdmin) {
    Write-Host "Suggerimento: riesegui come Amministratore per applicare anche la policy di macchina (HKLM)."
}
