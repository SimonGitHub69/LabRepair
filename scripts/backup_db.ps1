# Backup PostgreSQL di LabRepair (legge DATABASE_URL da .env).
# Uso:
#   .\scripts\backup_db.ps1
#   .\scripts\backup_db.ps1 -KeepDays 14 -BackupDir D:\Backup\LabRepair

param(
    [string]$BackupDir = "",
    [int]$KeepDays = 14,
    [string]$PgDumpPath = ""
)

$ErrorActionPreference = "Stop"

if ($PSScriptRoot) {
    $Root = Split-Path -Parent $PSScriptRoot
} else {
    $Root = (Get-Location).Path
}
Set-Location $Root

$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Error "Manca .env in $Root"
}

$envLine = (Get-Content $EnvFile -ErrorAction Stop |
    Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
    Select-Object -First 1)
if (-not $envLine) {
    Write-Error "DATABASE_URL non trovata in .env"
}
$url = ($envLine -replace '^\s*DATABASE_URL\s*=\s*', '').Trim().Trim('"').Trim("'")
if ($url -notmatch 'postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?\s]+)') {
    Write-Error "DATABASE_URL non riconosciuta"
}

$dbUser = $Matches[1]
$dbPass = [uri]::UnescapeDataString($Matches[2])
$dbHost = $Matches[3]
$dbPort = if ($Matches[4]) { $Matches[4] } else { "5432" }
$dbName = $Matches[5]

if (-not $BackupDir) {
    $BackupDir = Join-Path $Root "backups"
}
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

function Find-PgDump {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path -LiteralPath $Preferred)) {
        return $Preferred
    }
    $cmd = Get-Command pg_dump.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $roots = @(
        ${env:ProgramW6432},
        ${env:ProgramFiles},
        ${env:ProgramFiles(x86)},
        "C:\Program Files",
        "C:\Program Files (x86)",
        "D:\Program Files",
        "D:\Program Files (x86)",
        "E:\Program Files",
        "E:\Program Files (x86)"
    ) | Where-Object { $_ } | Select-Object -Unique

    $versions = @("18", "17", "16", "15", "14", "13")
    foreach ($root in $roots) {
        foreach ($ver in $versions) {
            $path = Join-Path $root "PostgreSQL\$ver\bin\pg_dump.exe"
            if (Test-Path -LiteralPath $path) {
                return $path
            }
        }
    }

    foreach ($root in $roots) {
        $pgRoot = Join-Path $root "PostgreSQL"
        if (-not (Test-Path -LiteralPath $pgRoot)) {
            continue
        }
        $found = Get-ChildItem -LiteralPath $pgRoot -Recurse -Filter "pg_dump.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\pgAdmin\\' } |
            Select-Object -First 1
        if ($found) {
            return $found.FullName
        }
    }

    # Registro installazione PostgreSQL (EnterpriseDB)
    foreach ($hive in @(
            "HKLM:\SOFTWARE\PostgreSQL\Installations",
            "HKLM:\SOFTWARE\WOW6432Node\PostgreSQL\Installations"
        )) {
        if (-not (Test-Path $hive)) {
            continue
        }
        Get-ChildItem $hive -ErrorAction SilentlyContinue | ForEach-Object {
            $base = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).BaseDirectory
            if ($base) {
                $path = Join-Path $base "bin\pg_dump.exe"
                if (Test-Path -LiteralPath $path) {
                    return $path
                }
            }
        }
    }

    return ""
}

$PgDump = Find-PgDump -Preferred $PgDumpPath
if (-not $PgDump) {
    Write-Error @"
pg_dump.exe non trovato.
Installa PostgreSQL (o solo i client tools) oppure indica il percorso:
  .\scripts\backup_db.ps1 -PgDumpPath "D:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
  .\scripts\install_backup_task.ps1 -PgDumpPath "D:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -Time "02:30" -KeepDays 21
"@
}
Write-Host "Uso pg_dump: $PgDump"

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $BackupDir ("{0}_{1}.dump" -f $dbName, $stamp)

Write-Host "Backup $dbName @ ${dbHost}:${dbPort} -> $outFile"

$env:PGPASSWORD = $dbPass
try {
    & $PgDump -h $dbHost -p $dbPort -U $dbUser -d $dbName -F c -b -f $outFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "pg_dump fallito con codice $LASTEXITCODE"
    }
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

$sizeMb = [math]::Round((Get-Item $outFile).Length / 1MB, 2)
Write-Host "OK: $outFile ($sizeMb MB)"

if ($KeepDays -gt 0) {
    $cutoff = (Get-Date).AddDays(-$KeepDays)
    Get-ChildItem -Path $BackupDir -Filter "*.dump" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Write-Host "Elimino backup vecchio: $($_.Name)"
            Remove-Item $_.FullName -Force
        }
}

exit 0
