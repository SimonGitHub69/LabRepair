# Avvio LabRepair in produzione (Windows)
# Uso:
#   .\scripts\prod_install.ps1
#   .\scripts\prod_start.ps1

$ErrorActionPreference = "Stop"
# Cartella progetto = padre di scripts\ (usa $PSScriptRoot; non incollare lo script nel terminale)
if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root
Write-Host "Cartella progetto: $Root"

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Crea il virtualenv: python -m venv .venv"
    exit 1
}

$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Manca .env in $Root"
    Write-Host "Esegui: Copy-Item .env.example .env   poi configura DATABASE_URL e ALLOWED_HOSTS"
    exit 1
}

Write-Host "Installazione dipendenze..."
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Installazione dipendenze fallita."
    exit $LASTEXITCODE
}

$MssqlReq = Join-Path $Root "requirements-mssql.txt"
if (Test-Path $MssqlReq) {
    Write-Host "Verifica pyodbc (sync MSSQL / gestionale)..."
    & $Python -c "import pyodbc; print('pyodbc', pyodbc.version)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "pyodbc gia' disponibile: sync MSSQL utilizzabile."
    } else {
        Write-Host "Tentativo installazione pyodbc..."
        # 1) Solo wheel precompilata (niente compilazione).
        & $Python -m pip install --only-binary=:all: -r $MssqlReq
        if ($LASTEXITCODE -ne 0) {
            # 2) Compilazione con Visual C++ Build Tools se presenti.
            $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
            $vcvars = $null
            if (Test-Path $vswhere) {
                $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
                if ($vsPath) {
                    $candidate = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
                    if (Test-Path $candidate) { $vcvars = $candidate }
                }
            }
            if ($vcvars) {
                Write-Host "Build Tools trovati: ricompilo pyodbc con vcvars64..."
                $pipCmd = "`"$Python`" -m pip install -r `"$MssqlReq`""
                cmd.exe /c "`"$vcvars`" && $pipCmd"
            } else {
                & $Python -m pip install -r $MssqlReq
            }
        }
        & $Python -c "import pyodbc; print('pyodbc', pyodbc.version)" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "pyodbc non installato."
            Write-Warning "Su Python 3.14 serve Visual C++ Build Tools oppure una wheel precompilata."
            Write-Warning "LabRepair funziona comunque; sync MSSQL/Gestionale resta disabilitato."
            Write-Warning "Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/"
        } else {
            Write-Host "pyodbc installato correttamente."
        }
    }
}

& $Python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Installazione OK. Avvio manuale: .\scripts\prod_start.ps1"
Write-Host "Servizio Windows (avvio automatico): apri PowerShell come Amministratore e lancia"
Write-Host "  .\scripts\install_service.ps1"
