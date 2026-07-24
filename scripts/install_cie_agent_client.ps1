# Installa l'agent CIE locale sul PC client (lettore Bit4id).
# Uso: .\scripts\install_cie_agent_client.ps1

$ErrorActionPreference = "Stop"

if ($PSScriptRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
} else {
    $RepoRoot = (Get-Location).Path
}

$SourceDir = Join-Path $RepoRoot "tools\cie_reader\publish"
$TargetDir = Join-Path $env:LOCALAPPDATA "LabRepairCieAgent"
$Exe = Join-Path $TargetDir "cie_reader.exe"

if (-not (Test-Path (Join-Path $SourceDir "cie_reader.exe"))) {
    Write-Host "Manca cie_reader.exe in $SourceDir"
    Write-Host "Sul server di sviluppo esegui: tools\cie_reader\build.ps1"
    exit 1
}

Write-Host "Installazione agent CIE in: $TargetDir"
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
Copy-Item (Join-Path $SourceDir "*") $TargetDir -Recurse -Force

$desktop = [Environment]::GetFolderPath("Desktop")
$startup = [Environment]::GetFolderPath("Startup")
$vbsLauncher = Join-Path $PSScriptRoot "LabRepairCieAgent.vbs"
$batLauncher = Join-Path $PSScriptRoot "LabRepairCieAgent.bat"

function New-Shortcut($path, $target, $arguments, $description) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $target
    if ($arguments) { $lnk.Arguments = $arguments }
    $lnk.WorkingDirectory = Split-Path $target
    $lnk.Description = $description
    $lnk.Save()
}

# Collegamento desktop: avvia agent visibile (utile per debug)
New-Shortcut `
    (Join-Path $desktop "LabRepair CIE Agent.lnk") `
    $Exe `
    "--serve" `
    "Agent lettore CIE per LabRepair"

# Avvio automatico con Windows (finestra nascosta via VBS)
if (Test-Path $vbsLauncher) {
    New-Shortcut `
        (Join-Path $startup "LabRepair CIE Agent.lnk") `
        "wscript.exe" `
        "//nologo `"$vbsLauncher`"" `
        "Avvia agent CIE LabRepair all'accesso"
}

Write-Host ""
Write-Host "Verifica .NET 8 Desktop Runtime..."
$dotnetOk = $false
try {
    $runtimes = & dotnet --list-runtimes 2>$null
    if ($runtimes -match "Microsoft\.WindowsDesktop\.App 8\.") {
        $dotnetOk = $true
    }
} catch {
    $dotnetOk = $false
}
if (-not $dotnetOk) {
    Write-Host "ATTENZIONE: installa .NET 8 Desktop Runtime se l'agent non parte."
    Write-Host "https://dotnet.microsoft.com/download/dotnet/8.0"
}

# Avvia agent sulla porta standard
$health = $null
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:17345/health" -UseBasicParsing -TimeoutSec 2
} catch {
    $health = $null
}

if (-not $health -or $health.StatusCode -ne 200) {
    if (Test-Path $vbsLauncher) {
        Start-Process "wscript.exe" -ArgumentList "//nologo `"$vbsLauncher`"" -WindowStyle Hidden
        Start-Sleep -Seconds 2
    } else {
        Start-Process -FilePath $Exe -ArgumentList "--serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
}

try {
    $ok = Invoke-WebRequest -Uri "http://127.0.0.1:17345/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "Agent CIE attivo: HTTP $($ok.StatusCode)"
    Write-Host $ok.Content
} catch {
    Write-Host "Agent non raggiungibile. Avvia manualmente LabRepair CIE Agent dal Desktop."
}

Write-Host ""
Write-Host "Fatto. Apri LabRepair su QUESTO PC e usa Leggi CIE in Anagrafica."
