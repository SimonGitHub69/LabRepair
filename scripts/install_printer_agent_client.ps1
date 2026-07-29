# Installa l'agent stampanti locale sul PC client (cassa / negozio).
# Uso: .\scripts\install_printer_agent_client.ps1

$ErrorActionPreference = "Stop"

if ($PSScriptRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
} else {
    $RepoRoot = (Get-Location).Path
}

$SourcePs1 = Join-Path $RepoRoot "tools\printer_agent\printer_agent.ps1"
$TargetDir = Join-Path $env:LOCALAPPDATA "LabRepairPrinterAgent"
$TargetPs1 = Join-Path $TargetDir "printer_agent.ps1"
$vbsLauncher = Join-Path $PSScriptRoot "LabRepairPrinterAgent.vbs"

if (-not (Test-Path $SourcePs1)) {
    Write-Error "Manca $SourcePs1"
}

Write-Host "Installazione agent stampanti in: $TargetDir"
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
Copy-Item $SourcePs1 $TargetPs1 -Force

$startup = [Environment]::GetFolderPath("Startup")
if (Test-Path $vbsLauncher) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $startup "LabRepair Printer Agent.lnk"))
    $lnk.TargetPath = "wscript.exe"
    $lnk.Arguments = "//nologo `"$vbsLauncher`""
    $lnk.Description = "Agent stampanti LabRepair all'accesso"
    $lnk.Save()
    Write-Host "Avvio automatico configurato in Startup."
}

& $vbsLauncher
Start-Sleep -Seconds 2

try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:17346/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "Agent attivo: $($health.Content)"
} catch {
    Write-Host "ATTENZIONE: agent non risponde su http://127.0.0.1:17346/health"
    Write-Host "Avvia LabRepair con LabRepairApp.vbs oppure esegui:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$TargetPs1`""
}

try {
    $printers = Invoke-WebRequest -Uri "http://127.0.0.1:17346/printers" -UseBasicParsing -TimeoutSec 5
    Write-Host "Stampanti rilevate sul PC:"
    Write-Host $printers.Content
} catch {
    Write-Host "Impossibile leggere /printers"
}

Write-Host ""
Write-Host "Fatto. Apri LabRepair con LabRepairApp.vbs e usa Parametri -> Stampanti -> Rileva dal sistema."
