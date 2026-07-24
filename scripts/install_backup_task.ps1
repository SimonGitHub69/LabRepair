# Registra backup PostgreSQL LabRepair in Utilità di pianificazione Windows.
# Eseguire come Amministratore sul server del cliente:
#   .\scripts\install_backup_task.ps1
#   .\scripts\install_backup_task.ps1 -Time "02:30" -KeepDays 21
#   .\scripts\install_backup_task.ps1 -Time "02:30" -KeepDays 21 -PgDumpPath "D:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
#   .\scripts\install_backup_task.ps1 -Uninstall

param(
    [string]$TaskName = "LabRepair_PostgreSQL_Backup",
    [string]$Time = "02:00",
    [int]$KeepDays = 14,
    [string]$BackupDir = "",
    [string]$PgDumpPath = "",
    [switch]$Uninstall
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

$BackupScript = Join-Path $Root "scripts\backup_db.ps1"
if (-not (Test-Path $BackupScript)) {
    Write-Error "Script non trovato: $BackupScript"
}

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Attivita rimossa: $TaskName"
    exit 0
}

# Prova un backup subito per verificare .env e pg_dump.
$testArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BackupScript, "-KeepDays", "$KeepDays")
if ($BackupDir) {
    $testArgs += @("-BackupDir", $BackupDir)
}
if ($PgDumpPath) {
    $testArgs += @("-PgDumpPath", $PgDumpPath)
}
Write-Host "Verifica backup di prova..."
& powershell.exe @testArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backup di prova fallito: sistema la configurazione prima di schedulare."
}

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$BackupScript`" -KeepDays $KeepDays"
if ($BackupDir) {
    $actionArgs += " -BackupDir `"$BackupDir`""
}
if ($PgDumpPath) {
    $actionArgs += " -PgDumpPath `"$PgDumpPath`""
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host ""
Write-Host "Attivita registrata: $TaskName"
Write-Host "  Orario: ogni giorno alle $Time"
Write-Host "  Conservazione: $KeepDays giorni"
Write-Host "  Script: $BackupScript"
if ($BackupDir) {
    Write-Host "  Cartella: $BackupDir"
} else {
    Write-Host "  Cartella: $Root\backups"
}
Write-Host ""
Write-Host "Comandi utili:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
Write-Host "  .\scripts\install_backup_task.ps1 -Uninstall"
