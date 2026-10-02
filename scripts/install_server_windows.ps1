# Prima installazione LabRepair su Windows 10/11 (server).
# Uso (dal pacchetto): doppio clic su INSTALLA.bat
#   .\scripts\install_server_windows.ps1
#   .\scripts\install_server_windows.ps1 -TargetRoot "C:\LabRepair" -Silent
#
# Se mancano, lo script scarica e installa:
#   - Python 3.12+
#   - PostgreSQL 17 (crea utente/database labrepair)

param(
    [string]$TargetRoot = "",
    [string]$PackageRoot = "",
    [string]$ServiceName = "LabRepair",
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8000,
    [int]$Threads = 6,
    [string]$AllowedHosts = "",
    [string]$DatabaseUrl = "",
    [string]$DbName = "labrepair",
    [string]$DbUser = "labrepair",
    [string]$DbPassword = "",
    [string]$PostgresSuperPassword = "",
    [switch]$Silent,
    [switch]$SkipService,
    [switch]$SkipPermissions,
    [switch]$SkipPostgreSQL,
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"

# Usati dalle funzioni di download/install (impostati dopo Resolve-PackageRoot).
$script:Pkg = ""

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
        "-ServiceName", $ServiceName,
        "-ListenHost", $ListenHost,
        "-Port", $Port,
        "-Threads", $Threads
    )
    if ($AllowedHosts) { $argList += @("-AllowedHosts", $AllowedHosts) }
    if ($DatabaseUrl) { $argList += @("-DatabaseUrl", $DatabaseUrl) }
    if ($DbName) { $argList += @("-DbName", $DbName) }
    if ($DbUser) { $argList += @("-DbUser", $DbUser) }
    if ($DbPassword) { $argList += @("-DbPassword", $DbPassword) }
    if ($PostgresSuperPassword) { $argList += @("-PostgresSuperPassword", $PostgresSuperPassword) }
    if ($Silent) { $argList += "-Silent" }
    if ($SkipService) { $argList += "-SkipService" }
    if ($SkipPermissions) { $argList += "-SkipPermissions" }
    if ($SkipPostgreSQL) { $argList += "-SkipPostgreSQL" }
    if ($SkipPython) { $argList += "-SkipPython" }
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

function Refresh-PathEnv {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function New-RandomPassword {
    param([int]$Length = 24)
    return -join (
        (48..57) + (65..90) + (97..122) |
            Get-Random -Count $Length |
            ForEach-Object { [char]$_ }
    )
}

function Find-PythonCommand {
    Refresh-PathEnv
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($tag in @("-3.14", "-3.13", "-3.12", "-3")) {
            try {
                $out = & py $tag -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $out) {
                    return ($out | Select-Object -First 1).ToString().Trim()
                }
            } catch { }
        }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and ($cmd.Source -notmatch "WindowsApps")) {
            try {
                $ver = & $cmd.Source -c "import sys; print(sys.version_info[:2] >= (3, 12))" 2>$null
                if ($LASTEXITCODE -eq 0 -and ($ver -match "True")) {
                    return $cmd.Source
                }
            } catch { }
        }
    }
    foreach ($candidate in @(
        "${env:ProgramFiles}\Python312\python.exe",
        "${env:ProgramFiles}\Python313\python.exe",
        "${env:ProgramFiles}\Python314\python.exe",
        "${env:LocalAppData}\Programs\Python\Python312\python.exe",
        "${env:LocalAppData}\Programs\Python\Python313\python.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) {
            try {
                $ver = & $candidate -c "import sys; print(sys.version_info[:2] >= (3, 12))" 2>$null
                if ($LASTEXITCODE -eq 0 -and ($ver -match "True")) {
                    return $candidate
                }
            } catch { }
        }
    }
    return $null
}

function Get-LocalPythonInstaller {
    $patterns = @(
        "python-3.12*-amd64.exe",
        "python-3.13*-amd64.exe",
        "python-*-amd64.exe",
        "python-windows-amd64.exe"
    )
    $redist = Join-Path $script:Pkg "redist"
    if (-not (Test-Path $redist)) { return $null }
    foreach ($pattern in $patterns) {
        $found = Get-ChildItem -Path $redist -Filter $pattern -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Install-PythonWindows {
    $installer = Get-LocalPythonInstaller
    if (-not $installer) {
        $downloadDir = Join-Path $env:TEMP "LabRepair_installers"
        New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
        $installer = Join-Path $downloadDir "python-3.12.10-amd64.exe"
        $url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
        Write-Host "Download Python 3.12 (~25 MB)..."
        Write-Host "  $url"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        } catch {
            throw "Download Python fallito: $_. Metti l'installer in redist\python-*-amd64.exe e riprova."
        }
    } else {
        Write-Host "Uso installer Python locale: $installer"
    }

    if (-not (Test-Path $installer) -or ((Get-Item $installer).Length -lt 5MB)) {
        throw "Installer Python non valido: $installer"
    }

    Write-Host "Installazione Python (silenziosa)..."
    $args = @(
        "/quiet",
        "InstallAllUsers=1",
        "PrependPath=1",
        "Include_launcher=1",
        "Include_pip=1",
        "Include_test=0",
        "SimpleInstall=1"
    )
    $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
        throw "Installazione Python fallita (codice $($p.ExitCode))."
    }

    Refresh-PathEnv
    $deadline = (Get-Date).AddMinutes(2)
    $python = $null
    do {
        Start-Sleep -Seconds 2
        $python = Find-PythonCommand
        if ($python) { break }
    } while ((Get-Date) -lt $deadline)

    if (-not $python) {
        throw "Python installato ma non trovato nel PATH. Riavvia PowerShell e rilancia INSTALLA.bat."
    }
    Write-Host "Python disponibile: $python"
    return $python
}

function Find-PsqlExe {
    Refresh-PathEnv
    $cmd = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }

    $roots = @(
        ${env:ProgramW6432},
        ${env:ProgramFiles},
        ${env:ProgramFiles(x86)},
        "C:\Program Files",
        "C:\Program Files (x86)"
    ) | Where-Object { $_ } | Select-Object -Unique

    foreach ($root in $roots) {
        foreach ($ver in @("18", "17", "16", "15", "14")) {
            $path = Join-Path $root "PostgreSQL\$ver\bin\psql.exe"
            if (Test-Path -LiteralPath $path) { return $path }
        }
    }
    return $null
}

function Test-PostgreSQLReady {
    param([string]$PsqlPath, [string]$SuperPassword = "")
    if (-not $PsqlPath -or -not (Test-Path $PsqlPath)) { return $false }
    $prev = $env:PGPASSWORD
    try {
        if ($SuperPassword) { $env:PGPASSWORD = $SuperPassword }
        $out = & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -tAc "SELECT 1" 2>$null
        return ($LASTEXITCODE -eq 0 -and ($out -match "1"))
    } catch {
        return $false
    } finally {
        if ($null -ne $prev) { $env:PGPASSWORD = $prev } else { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
    }
}

function Get-LocalPostgresInstaller {
    $redist = Join-Path $script:Pkg "redist"
    if (-not (Test-Path $redist)) { return $null }
    $found = Get-ChildItem -Path $redist -Filter "postgresql*windows*.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    $named = Join-Path $redist "postgresql-windows-x64.exe"
    if (Test-Path $named) { return $named }
    return $null
}

function Install-PostgreSQLWindows {
    param([string]$SuperPassword)
    $installer = Get-LocalPostgresInstaller
    if (-not $installer) {
        $downloadDir = Join-Path $env:TEMP "LabRepair_installers"
        New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
        $installer = Join-Path $downloadDir "postgresql-windows-x64.exe"
        $url = "https://get.enterprisedb.com/postgresql/postgresql-17.5-1-windows-x64.exe"
        Write-Host "Download PostgreSQL 17 (~300 MB, puo' richiedere alcuni minuti)..."
        Write-Host "  $url"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        } catch {
            throw "Download PostgreSQL fallito: $_. Metti l'installer in redist\postgresql-windows-x64.exe e riprova."
        }
    } else {
        Write-Host "Uso installer PostgreSQL locale: $installer"
    }

    if (-not (Test-Path $installer) -or ((Get-Item $installer).Length -lt 10MB)) {
        throw "Installer PostgreSQL non valido: $installer"
    }

    $prefix = Join-Path ${env:ProgramFiles} "PostgreSQL\17"
    $dataDir = Join-Path $prefix "data"
    Write-Host "Installazione PostgreSQL in corso..."
    # Start-Process unisce -ArgumentList con spazi: valori con spazi/backslash
    # vanno quotati in una sola stringa, altrimenti l'installer EDB spezza
    # "NT AUTHORITY\NetworkService" e fallisce.
    $argLine = @(
        "--mode unattended",
        "--unattendedmodeui minimal",
        "--superpassword `"$SuperPassword`"",
        "--servicename postgresql-x64-17",
        "--serverport 5432",
        "--prefix `"$prefix`"",
        "--datadir `"$dataDir`"",
        "--install_runtimes 1"
    ) -join " "
    $p = Start-Process -FilePath $installer -ArgumentList $argLine -Wait -PassThru
    if ($p.ExitCode -ne 0) {
        throw "Installazione PostgreSQL fallita (codice $($p.ExitCode))."
    }

    Refresh-PathEnv
    $deadline = (Get-Date).AddMinutes(4)
    $psql = $null
    do {
        Start-Sleep -Seconds 3
        $psql = Find-PsqlExe
        if ($psql -and (Test-PostgreSQLReady -PsqlPath $psql -SuperPassword $SuperPassword)) {
            break
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $psql) {
        throw "PostgreSQL installato ma psql.exe non trovato."
    }
    if (-not (Test-PostgreSQLReady -PsqlPath $psql -SuperPassword $SuperPassword)) {
        throw "PostgreSQL non risponde su 127.0.0.1:5432. Controlla il servizio postgresql-x64-17."
    }
    return $psql
}

function Ensure-LabRepairDatabase {
    param(
        [string]$PsqlPath,
        [string]$SuperPassword,
        [string]$Name,
        [string]$UserName,
        [string]$Password
    )
    $prev = $env:PGPASSWORD
    $env:PGPASSWORD = $SuperPassword
    try {
        $roleExists = (& $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$UserName'" 2>$null)
        if ($roleExists -notmatch "1") {
            Write-Host "Creo utente database $UserName..."
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE $UserName LOGIN PASSWORD '$Password';"
            if ($LASTEXITCODE -ne 0) { throw "Creazione ruolo $UserName fallita." }
        } else {
            Write-Host "Utente $UserName gia' presente: aggiorno password..."
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE $UserName WITH LOGIN PASSWORD '$Password';"
        }

        $dbExists = (& $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$Name'" 2>$null)
        if ($dbExists -notmatch "1") {
            Write-Host "Creo database $Name..."
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $Name OWNER $UserName;"
            if ($LASTEXITCODE -ne 0) { throw "Creazione database $Name fallita." }
        } else {
            Write-Host "Database $Name gia' presente."
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "ALTER DATABASE $Name OWNER TO $UserName;"
        }
        & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -d $Name -v ON_ERROR_STOP=1 -c "GRANT ALL ON SCHEMA public TO $UserName;"
    } finally {
        if ($null -ne $prev) { $env:PGPASSWORD = $prev } else { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
    }
}

function Copy-InstallTree {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path $Source)) { return }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -Path $Source -Recurse -Force | ForEach-Object {
        $rel = $_.FullName.Substring($Source.Length).TrimStart("\")
        if ($rel -match '(^|\\)\.env$') { return }
        if ($rel -match '(^|\\)\.venv(\\|$)') { return }
        if ($rel -match '\\__pycache__\\|\.pyc$|\.pyo$|\\\.pytest_cache\\|\\\.mypy_cache\\|\\bin\\|\\obj\\') {
            return
        }
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

function Get-DefaultAllowedHosts {
    $hostList = [System.Collections.Generic.List[string]]::new()
    [void]$hostList.Add("127.0.0.1")
    [void]$hostList.Add("localhost")
    try {
        $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -and
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.PrefixOrigin -ne "WellKnown"
            } |
            Select-Object -ExpandProperty IPAddress -Unique
        foreach ($ip in $ips) {
            if (-not $hostList.Contains($ip)) { [void]$hostList.Add($ip) }
        }
    } catch { }
    return ($hostList -join ",")
}

function New-EnvFile {
    param(
        [string]$ExamplePath,
        [string]$EnvPath,
        [string]$Hosts,
        [string]$DbUrl,
        [int]$HttpPort
    )
    if (-not (Test-Path $ExamplePath)) {
        Write-Error "Manca .env.example nel pacchetto."
    }
    $content = Get-Content -Path $ExamplePath -Raw -Encoding UTF8
    if (-not $Hosts) {
        $Hosts = Get-DefaultAllowedHosts
    }
    if (-not $DbUrl) {
        $DbUrl = "postgres://labrepair:labrepair@127.0.0.1:5432/labrepair"
    }

    $secret = New-RandomPassword -Length 48
    $content = $content -replace "(?m)^SECRET_KEY=.*$", "SECRET_KEY=$secret"
    $content = $content -replace "(?m)^DEBUG=.*$", "DEBUG=False"
    $content = $content -replace "(?m)^ALLOWED_HOSTS=.*$", "ALLOWED_HOSTS=$Hosts"
    $content = $content -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=$DbUrl"

    $csrfOrigins = @()
    foreach ($h in ($Hosts -split ",")) {
        $h = $h.Trim()
        if (-not $h) { continue }
        $csrfOrigins += "http://${h}:${HttpPort}"
    }
    if ($csrfOrigins.Count -gt 0) {
        $csrfLine = "CSRF_TRUSTED_ORIGINS=" + ($csrfOrigins -join ",")
        if ($content -match "(?m)^#?\s*CSRF_TRUSTED_ORIGINS=") {
            $content = $content -replace "(?m)^#?\s*CSRF_TRUSTED_ORIGINS=.*$", $csrfLine
        } else {
            $content = $content.TrimEnd() + "`r`n" + $csrfLine + "`r`n"
        }
    }

    # django-environ rifiuta commenti con spazi iniziali / BOM UTF-8.
    $content = $content -replace '(?m)^\s+#', '#'
    $content = $content.TrimStart([char]0xFEFF)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($EnvPath, $content, $utf8NoBom)
}

# --- main ---
$script:Pkg = Resolve-PackageRoot
$DefaultTarget = "C:\LabRepair"

if (-not $TargetRoot) {
    if ($Silent) {
        $TargetRoot = $DefaultTarget
    } else {
        Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
        $typed = [Microsoft.VisualBasic.Interaction]::InputBox(
            "Cartella di installazione LabRepair sul server Windows.",
            "Installazione LabRepair",
            $DefaultTarget
        )
        if ([string]::IsNullOrWhiteSpace($typed)) {
            Write-Host "Installazione annullata."
            exit 1
        }
        $TargetRoot = $typed.Trim().TrimEnd("\")
    }
}

if (-not (Test-IsAdmin)) {
    Write-Host "Richiesta elevazione amministratore..."
    Request-AdminRelaunch -PkgRoot $script:Pkg -TgtRoot $TargetRoot
}

if (-not (Test-Path (Join-Path $script:Pkg "manage.py"))) {
    Write-Error "Pacchetto server non valido (manca manage.py): $($script:Pkg)"
}

$existingEnv = Test-Path (Join-Path $TargetRoot ".env")
if ($existingEnv -and -not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    $ok = [Microsoft.VisualBasic.Interaction]::MsgBox(
        "Nella cartella $TargetRoot esiste gia' un'installazione (.env presente).`r`n`r`nContinuare aggiornando i file senza sovrascrivere .env?",
        4 + 48 + 256,
        "Installazione LabRepair"
    )
    if ($ok -ne 6) {
        Write-Host "Installazione annullata."
        exit 1
    }
}

if (-not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    $ok = [Microsoft.VisualBasic.Interaction]::MsgBox(
        "L'installer puo' scaricare e installare automaticamente:`r`n- Python 3.12 (se manca)`r`n- PostgreSQL 17 + database labrepair (se manca)`r`n`r`nServe connessione Internet al primo avvio.`r`n`r`nPacchetto: $($script:Pkg)`r`nDestinazione: $TargetRoot`r`nPorta: $Port`r`n`r`nProcedere?",
        4 + 32 + 256,
        "Installazione LabRepair"
    )
    if ($ok -ne 6) {
        Write-Host "Installazione annullata."
        exit 1
    }
}

Write-Host "LabRepair - installazione server Windows"
Write-Host "Pacchetto:     $($script:Pkg)"
Write-Host "Installazione: $TargetRoot"
Write-Host ""

# --- Python ---
$systemPython = Find-PythonCommand
if (-not $systemPython) {
    if ($SkipPython) {
        Write-Error "Python 3.12+ non trovato e -SkipPython attivo."
    }
    Write-Host "Python non trovato: installazione automatica..."
    $systemPython = Install-PythonWindows
} else {
    Write-Host "Python trovato: $systemPython"
}

# --- PostgreSQL ---
if (-not $DbPassword) { $DbPassword = New-RandomPassword -Length 20 }
if (-not $PostgresSuperPassword) { $PostgresSuperPassword = New-RandomPassword -Length 24 }
$autoDatabaseUrl = "postgres://${DbUser}:${DbPassword}@127.0.0.1:5432/${DbName}"

if (-not $SkipPostgreSQL) {
    $psql = Find-PsqlExe
    $pgReady = $false
    if ($psql) {
        # Se Postgres e' gia' installato ma non conosciamo la password superuser,
        # potremmo non riuscire a creare DB: in quel caso chiediamo DATABASE_URL.
        $pgReady = Test-PostgreSQLReady -PsqlPath $psql -SuperPassword $PostgresSuperPassword
        if (-not $pgReady) {
            $pgReady = Test-PostgreSQLReady -PsqlPath $psql -SuperPassword ""
        }
    }

    if (-not $psql -or -not $pgReady) {
        Write-Host "PostgreSQL non pronto: installazione automatica..."
        $psql = Install-PostgreSQLWindows -SuperPassword $PostgresSuperPassword
        $credsFile = Join-Path $TargetRoot "POSTGRES_ADMIN.txt"
        New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null
        Set-Content -Path $credsFile -Value @"
PostgreSQL installato da LabRepair
=================================
Superuser: postgres
Password:  $PostgresSuperPassword
Servizio:  postgresql-x64-17
Porta:     5432

Conserva questo file in un posto sicuro, poi eliminalo dal server.
"@ -Encoding UTF8
        Write-Host "Password admin PostgreSQL salvata in: $credsFile"
    } else {
        Write-Host "PostgreSQL gia' disponibile: $psql"
    }

    if (-not $DatabaseUrl) {
        # Con password superuser nota (installazione fresca) creiamo ruolo/DB.
        if (Test-PostgreSQLReady -PsqlPath $psql -SuperPassword $PostgresSuperPassword) {
            Ensure-LabRepairDatabase -PsqlPath $psql -SuperPassword $PostgresSuperPassword `
                -Name $DbName -UserName $DbUser -Password $DbPassword
            $DatabaseUrl = $autoDatabaseUrl
            Write-Host "DATABASE_URL configurato per utente $DbUser / database $DbName"
        } elseif (-not $Silent) {
            Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
            $typedDb = [Microsoft.VisualBasic.Interaction]::InputBox(
                "PostgreSQL e' presente ma non e' stato possibile creare automaticamente il database.`r`nInserisci DATABASE_URL (es. postgres://labrepair:PASSWORD@127.0.0.1:5432/labrepair).",
                "LabRepair - Database",
                $autoDatabaseUrl
            )
            if (-not [string]::IsNullOrWhiteSpace($typedDb)) {
                $DatabaseUrl = $typedDb.Trim()
            } else {
                $DatabaseUrl = $autoDatabaseUrl
            }
        } else {
            $DatabaseUrl = $autoDatabaseUrl
        }
    }
} elseif (-not $DatabaseUrl) {
    $DatabaseUrl = $autoDatabaseUrl
}

New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null

$sameRoot = (
    [IO.Path]::GetFullPath($script:Pkg).TrimEnd("\").ToLowerInvariant() -eq
    [IO.Path]::GetFullPath($TargetRoot).TrimEnd("\").ToLowerInvariant()
)

if (-not $sameRoot) {
    Write-Host "Copio file applicazione..."
    $dirs = @("apps", "config", "templates", "static", "scripts", "tools", "docs", "redist")
    foreach ($dir in $dirs) {
        $src = Join-Path $script:Pkg $dir
        if (Test-Path $src) {
            Copy-InstallTree -Source $src -Destination (Join-Path $TargetRoot $dir)
        }
    }
    $files = @(
        "manage.py",
        "requirements.txt",
        "requirements-mssql.txt",
        ".env.example",
        "VERSION",
        "LEGGIMI.txt",
        "INSTALLA.bat"
    )
    foreach ($file in $files) {
        $src = Join-Path $script:Pkg $file
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $TargetRoot $file) -Force
        }
    }
} else {
    Write-Host "Pacchetto gia' nella cartella destinazione: salto copia file."
}

Set-Location $TargetRoot

$envPath = Join-Path $TargetRoot ".env"
$examplePath = Join-Path $TargetRoot ".env.example"
if (-not (Test-Path $envPath)) {
    Write-Host "Creo .env..."
    if (-not $Silent -and -not $AllowedHosts) {
        Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
        $defaultHosts = Get-DefaultAllowedHosts
        $typedHosts = [Microsoft.VisualBasic.Interaction]::InputBox(
            "ALLOWED_HOSTS: IP/hostname del server (virgola, senza http://).`r`nIncludi l'IP di rete se i client devono connettersi da altri PC.",
            "LabRepair - Host",
            $defaultHosts
        )
        if (-not [string]::IsNullOrWhiteSpace($typedHosts)) {
            $AllowedHosts = $typedHosts.Trim()
        } else {
            $AllowedHosts = $defaultHosts
        }
    }
    New-EnvFile -ExamplePath $examplePath -EnvPath $envPath -Hosts $AllowedHosts -DbUrl $DatabaseUrl -HttpPort $Port
} else {
    Write-Host "Mantengo .env esistente."
    # Se abbiamo appena creato/allineato il DB, aggiorna comunque DATABASE_URL.
    if ($DatabaseUrl) {
        $envText = Get-Content -Path $envPath -Raw -Encoding UTF8
        if ($envText -match "(?m)^DATABASE_URL=") {
            $envText = $envText -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=$DatabaseUrl"
        } else {
            $envText = $envText.TrimEnd() + "`r`nDATABASE_URL=$DatabaseUrl`r`n"
        }
        Set-Content -Path $envPath -Value $envText -Encoding UTF8
        Write-Host "DATABASE_URL aggiornato in .env esistente."
    }
}

$venvPython = Join-Path $TargetRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $systemPython = Find-PythonCommand
    if (-not $systemPython) {
        Write-Error "Python 3.12+ non trovato dopo l'installazione."
    }
    Write-Host "Creo virtualenv con: $systemPython"
    & $systemPython -m venv (Join-Path $TargetRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Creazione virtualenv fallita."
    }
}

$clear = Join-Path $TargetRoot "scripts\clear_pycache.ps1"
$prod = Join-Path $TargetRoot "scripts\prod_install.ps1"
if (Test-Path $clear) {
    Write-Host "Pulizia cache Python..."
    & $clear
}
Write-Host "Dipendenze, migrate, collectstatic..."
& $prod
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    Write-Error "prod_install.ps1 fallito (codice $LASTEXITCODE). Controlla DATABASE_URL in .env e che PostgreSQL sia avviato."
}

if (-not $SkipPermissions) {
    Write-Host "Ricostruzione privilegi menu..."
    & $venvPython manage.py rebuild_labrepair_permissions --reset-groups
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        Write-Warning "rebuild_labrepair_permissions non riuscito (codice $LASTEXITCODE)."
    }
}

if (-not $SkipService) {
    Write-Host "Installazione servizio Windows..."
    $svcScript = Join-Path $TargetRoot "scripts\install_service.ps1"
    if (-not (Test-Path $svcScript)) {
        Write-Error "Manca scripts\install_service.ps1 in $TargetRoot"
    }
    try {
        $svcArgs = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $svcScript,
            "-ServiceName", $ServiceName,
            "-ListenHost", $ListenHost,
            "-Port", $Port,
            "-Threads", $Threads
        )
        $svcProc = Start-Process -FilePath "powershell.exe" -ArgumentList $svcArgs -Wait -PassThru -NoNewWindow
        if ($svcProc.ExitCode -ne 0) {
            throw "install_service.ps1 codice $($svcProc.ExitCode)"
        }
        $check = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $check) {
            throw "Servizio $ServiceName non creato."
        }
    } catch {
        Write-Error "Installazione servizio fallita: $_.`r`nRiprova come Amministratore:`r`n  cd `"$TargetRoot`"`r`n  powershell -ExecutionPolicy Bypass -File .\scripts\install_service.ps1 -Port $Port"
    }
} else {
    Write-Host "Servizio non installato (-SkipService). Avvio manuale: .\scripts\prod_start.ps1"
}

Write-Host ""
Write-Host "Installazione completata."
Write-Host "Cartella: $TargetRoot"
Write-Host "URL: http://127.0.0.1:${Port}/"

$svcOk = $false
$svcStatus = "non installato"
if (-not $SkipService) {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -ne "Running") {
            Write-Host "Avvio servizio $ServiceName..."
            try {
                Start-Service $ServiceName -ErrorAction Stop
                Start-Sleep -Seconds 3
                $svc.Refresh()
            } catch {
                Write-Warning "Avvio servizio fallito: $_"
            }
        }
        $svc.Refresh()
        $svcStatus = $svc.Status.ToString()
        $svcOk = ($svc.Status -eq "Running")
        Write-Host "Servizio $ServiceName : $svcStatus"
    } else {
        Write-Warning "Servizio $ServiceName non trovato. Avvio manuale: .\scripts\prod_start.ps1"
    }
}

$url = "http://127.0.0.1:${Port}/"
Write-Host "Crea un utente admin (se non esiste):"
Write-Host "  .\.venv\Scripts\python.exe manage.py createsuperuser"
Write-Host ""

if ($svcOk) {
    try { Start-Process $url } catch { }
}

if (-not $Silent) {
    Add-Type -AssemblyName Microsoft.VisualBasic | Out-Null
    $msg = if ($svcOk) {
        "Installazione LabRepair completata.`r`n`r`nIl server e' un servizio Windows (nessuna finestra).`r`nStato: $svcStatus`r`n`r`nApro il browser su:`r`n$url`r`n`r`nPoi crea l'utente admin:`r`n.\.venv\Scripts\python.exe manage.py createsuperuser"
    } else {
        "Installazione file completata, ma il servizio non risulta avviato ($svcStatus).`r`n`r`nControlla:`r`n1) services.msc -> LabRepair`r`n2) C:\LabRepair\logs\waitress.err.log`r`n3) PowerShell admin:`r`n   Start-Service LabRepair`r`n`r`nPoi apri $url"
    }
    [Microsoft.VisualBasic.Interaction]::MsgBox($msg, $(if ($svcOk) { 64 } else { 48 }), "LabRepair") | Out-Null
}
