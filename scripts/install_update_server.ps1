# Aggiornamento automatico LabRepair sul server (estrai zip + doppio clic INSTALLA.bat).
# Uso:
#   .\scripts\install_update_server.ps1
#   .\scripts\install_update_server.ps1 -TargetRoot "C:\LabRepair"
#   .\scripts\install_update_server.ps1 -TargetRoot "C:\LabRepair" -Silent

param(
    [string]$TargetRoot = "",
    [string]$PackageRoot = "",
    [string]$ServiceName = "LabRepair",
    [switch]$Silent,
    [switch]$SkipStart,
    [switch]$SkipPermissions
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Request-AdminRelaunch {
    param([string]$PkgRoot, [string]$TgtRoot)
    $argList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-PackageRoot", $PkgRoot,
        "-TargetRoot", $TgtRoot,
        "-ServiceName", $ServiceName
    )
    if ($Silent) { $argList += "-Silent" }
    if ($SkipStart) { $argList += "-SkipStart" }
    if ($SkipPermissions) { $argList += "-SkipPermissions" }
    $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList -Wait -PassThru
    exit $p.ExitCode
}

function Resolve-PackageRoot {
    if ($PackageRoot) { return (Resolve-Path $PackageRoot).Path }
    if ($PSScriptRoot) {
        $candidate = Split-Path -Parent $PSScriptRoot
        if (Test-Path (Join-Path $candidate "manage.py")) { return $candidate }
        if (Test-Path (Join-Path $candidate "apps")) { return $candidate }
    }
    return (Get-Location).Path
}

function Copy-UpdateTree {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path $Source)) { return }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -Path $Source -Recurse -Force | ForEach-Object {
        $rel = $_.FullName.Substring($Source.Length).TrimStart("\")
        if ($rel -match '(^|\\)\.env$') { return }
        if ($rel -match '\\__pycache__\\|\.pyc$|\.pyo$|\\\.pytest_cache\\|\\\.mypy_cache\\') { return }
        $target = Join-Path $Destination $rel
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        } else {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            Copy-Item -Path $_.FullName -Destination $target -Force
        }
    }
}

$Pkg = Resolve-PackageRoot
$DefaultTarget = "C:\LabRepair"

if (-not $TargetRoot) {
    if ($Silent) {
        $TargetRoot = $DefaultTarget
    } else {
        Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
        $typed = [Microsoft.VisualBasic.Interaction]::InputBox(
            "Cartella di installazione LabRepair sul server (non sovrascrive .env).",
            "Aggiornamento LabRepair",
            $DefaultTarget
        )
        if ([string]::IsNullOrWhiteSpace($typed)) {
            Write-Host "Aggiornamento annullato."
            exit 1
        }
        $TargetRoot = $typed.Trim().TrimEnd("\")
    }
}

if (-not (Test-IsAdmin)) {
    Write-Host "Richiesta elevazione amministratore..."
    Request-AdminRelaunch -PkgRoot $Pkg -TgtRoot $TargetRoot
}

if (-not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    $ok = [Microsoft.VisualBasic.Interaction]::MsgBox(
        "Hai gia' fatto il backup di PostgreSQL?`r`n`r`nPacchetto: $Pkg`r`nDestinazione: $TargetRoot`r`n`r`nIl file .env non verra' sovrascritto.",
        4 + 32 + 256,
        "Aggiornamento LabRepair"
    )
    if ($ok -ne 6) {
        Write-Host "Aggiornamento annullato."
        exit 1
    }
}

if (-not (Test-Path $TargetRoot)) {
    Write-Error "Cartella destinazione non trovata: $TargetRoot"
}
if (-not (Test-Path (Join-Path $TargetRoot ".env"))) {
    Write-Error "Manca .env in $TargetRoot - interrotto per sicurezza."
}
if (-not (Test-Path (Join-Path $TargetRoot ".venv\Scripts\python.exe"))) {
    Write-Error "Virtualenv non trovato in $TargetRoot\.venv - installazione non valida."
}
if (-not (Test-Path (Join-Path $Pkg "manage.py")) -and -not (Test-Path (Join-Path $Pkg "apps"))) {
    Write-Error "Pacchetto aggiornamento non valido: $Pkg"
}

Write-Host "LabRepair - aggiornamento server"
Write-Host "Pacchetto:     $Pkg"
Write-Host "Installazione: $TargetRoot"
Write-Host ""

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
$wasRunning = $false
if ($svc) {
    $wasRunning = ($svc.Status -eq "Running")
    Write-Host "Fermo servizio $ServiceName..."
    $nssmCandidates = @(
        (Join-Path $TargetRoot "tools\nssm\nssm.exe"),
        (Join-Path $Pkg "tools\nssm\nssm.exe")
    )
    $nssm = $nssmCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($nssm) {
        & $nssm stop $ServiceName confirm
    } else {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Chiude eventuali Waitress/python sulla cartella target (finestra manuale)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^(python|pythonw)\.exe$' -and
        $_.CommandLine -and
        $_.CommandLine -like "*$TargetRoot*" -and
        ($_.CommandLine -match 'waitress|manage\.py|config\.wsgi')
    } |
    ForEach-Object {
        Write-Host "Chiudo processo PID $($_.ProcessId)..."
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

$sameRoot = ([IO.Path]::GetFullPath($Pkg).TrimEnd("\").ToLowerInvariant() -eq
    [IO.Path]::GetFullPath($TargetRoot).TrimEnd("\").ToLowerInvariant())

if (-not $sameRoot) {
    Write-Host "Copio file aggiornamento (escluso .env)..."
    $dirs = @("apps", "config", "templates", "static", "scripts", "tools")
    foreach ($dir in $dirs) {
        $src = Join-Path $Pkg $dir
        if (Test-Path $src) {
            Copy-UpdateTree -Source $src -Destination (Join-Path $TargetRoot $dir)
        }
    }
    $files = @("manage.py", "requirements.txt", "requirements-mssql.txt", ".env.example", "VERSION", "AGGIORNAMENTO.txt")
    foreach ($file in $files) {
        $src = Join-Path $Pkg $file
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $TargetRoot $file) -Force
        }
    }
} else {
    Write-Host "Pacchetto estratto sopra l'installazione: salto copia file."
}

Set-Location $TargetRoot

$clear = Join-Path $TargetRoot "scripts\clear_pycache.ps1"
$prod = Join-Path $TargetRoot "scripts\prod_install.ps1"
if (-not (Test-Path $clear)) { Write-Error "Manca $clear" }
if (-not (Test-Path $prod)) { Write-Error "Manca $prod" }

Write-Host "Pulizia cache Python..."
& $clear
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installazione dipendenze / migrate / collectstatic..."
& $prod
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPermissions) {
    $python = Join-Path $TargetRoot ".venv\Scripts\python.exe"
    Write-Host "Ricostruzione privilegi menu..."
    & $python manage.py rebuild_labrepair_permissions --reset-groups
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipStart) {
    $svcNow = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svcNow -and $wasRunning) {
        Write-Host "Riavvio servizio $ServiceName..."
        $nssm = Join-Path $TargetRoot "tools\nssm\nssm.exe"
        if (Test-Path $nssm) {
            & $nssm start $ServiceName
        } else {
            Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
        }
    } elseif (-not $svcNow -and -not $Silent) {
        Write-Host "Nessun servizio Windows trovato. Avvio Waitress in questa finestra..."
        Write-Host "Chiudi la finestra per fermare LabRepair, oppure installa il servizio con scripts\install_service.ps1"
        & (Join-Path $TargetRoot "scripts\prod_start.ps1")
        exit 0
    } elseif ($svcNow -and -not $wasRunning) {
        Write-Host "Servizio $ServiceName lasciato fermo (era gia' spento)."
        Write-Host "Per avviarlo: nssm start $ServiceName"
    }
}

Write-Host ""
Write-Host "Aggiornamento completato."
Write-Host "Verifica login, negozio, Parametri PC e stampa busta."
if (-not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    [Microsoft.VisualBasic.Interaction]::MsgBox(
        "Aggiornamento LabRepair completato.",
        64,
        "LabRepair"
    ) | Out-Null
}
