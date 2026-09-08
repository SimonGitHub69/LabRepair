# Rimuove LabRepair dal PC client Windows (app, agent CIE, agent stampanti).
# Uso: .\scripts\uninstall_client_windows.ps1
# Dal pacchetto: doppio clic su DISINSTALLA.bat

param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

$AppDir = Join-Path $env:LOCALAPPDATA "LabRepair"
$CieDir = Join-Path $env:LOCALAPPDATA "LabRepairCieAgent"
$PrinterDir = Join-Path $env:LOCALAPPDATA "LabRepairPrinterAgent"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Startup = [Environment]::GetFolderPath("Startup")
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\LabRepair"

if (-not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    $ok = [Microsoft.VisualBasic.Interaction]::MsgBox(
        "Rimuovere LabRepair da questo PC (app, agent CIE e stampanti)?",
        4 + 32,
        "Disinstallazione LabRepair"
    )
    if ($ok -ne 6) {
        Write-Host "Disinstallazione annullata."
        exit 0
    }
}

function Stop-MatchingProcess($name, $pathFragment) {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq $name -and $_.CommandLine -and ($_.CommandLine -like "*$pathFragment*")
        } |
        ForEach-Object {
            try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch { }
        }
}

Write-Host "Arresto agent..."
Stop-MatchingProcess "cie_reader.exe" "LabRepairCieAgent"
Stop-MatchingProcess "powershell.exe" "printer_agent.ps1"
Start-Sleep -Seconds 1

$shortcutNames = @(
    (Join-Path $Desktop "LabRepair.lnk"),
    (Join-Path $Desktop "LabRepair CIE Agent.lnk"),
    (Join-Path $Startup "LabRepair CIE Agent.lnk"),
    (Join-Path $Startup "LabRepair Printer Agent.lnk")
)
foreach ($lnk in $shortcutNames) {
    if (Test-Path $lnk) { Remove-Item $lnk -Force }
}
if (Test-Path $StartMenu) {
    Remove-Item $StartMenu -Recurse -Force
}

foreach ($dir in @($AppDir, $CieDir, $PrinterDir)) {
    if (Test-Path $dir) {
        Remove-Item $dir -Recurse -Force
        Write-Host "Rimossa $dir"
    }
}

Write-Host "Disinstallazione completata."
