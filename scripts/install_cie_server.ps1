# Configura lettore CIE sul SERVER del cliente (Bit4id collegato al server).
# Uso: .\scripts\install_cie_server.ps1

$ErrorActionPreference = "Stop"

if ($PSScriptRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
} else {
    $RepoRoot = (Get-Location).Path
}

$PublishDir = Join-Path $RepoRoot "tools\cie_reader\publish"
$Exe = Join-Path $PublishDir "cie_reader.exe"
$EnvFile = Join-Path $RepoRoot ".env"

Write-Host "LabRepair - setup CIE sul server"
Write-Host "Cartella: $RepoRoot"
Write-Host ""

if (-not (Test-Path $Exe)) {
    Write-Host "MANCA: $Exe"
    Write-Host "Copia tools\cie_reader\publish dal pacchetto di aggiornamento."
    exit 1
}

$sc = Get-Service -Name "SCardSvr" -ErrorAction SilentlyContinue
if ($sc) {
    if ($sc.Status -ne "Running") {
        Write-Host "Avvio servizio Smart Card (SCardSvr)..."
        Start-Service SCardSvr
    }
    Write-Host "Smart Card: $($sc.Status)"
} else {
    Write-Host "ATTENZIONE: servizio Smart Card non trovato."
}

$dotnetOk = $false
try {
    $runtimes = & dotnet --list-runtimes 2>$null
    if ($runtimes -match "Microsoft\.WindowsDesktop\.App 8\.") {
        $dotnetOk = $true
    }
} catch {}
if (-not $dotnetOk) {
    Write-Host "ATTENZIONE: installa .NET 8 Desktop Runtime sul server."
    Write-Host "https://dotnet.microsoft.com/download/dotnet/8.0"
} else {
    Write-Host ".NET 8 Desktop Runtime: OK"
}

if (Test-Path $EnvFile) {
    $envText = Get-Content $EnvFile -Raw
    if ($envText -notmatch "(?m)^CIE_READER_ON_SERVER=") {
        Add-Content $EnvFile "`nCIE_READER_ON_SERVER=True"
        Write-Host "Aggiunto CIE_READER_ON_SERVER=True in .env"
    } else {
        $envText = $envText -replace "(?m)^CIE_READER_ON_SERVER=.*$", "CIE_READER_ON_SERVER=True"
        Set-Content $EnvFile $envText.TrimEnd() -Encoding UTF8
        Write-Host "Impostato CIE_READER_ON_SERVER=True in .env"
    }
} else {
    Write-Host "Aggiungi in .env: CIE_READER_ON_SERVER=True"
}

Write-Host ""
Write-Host "Verifica lettore USB collegato al server (Gestione dispositivi -> Lettori smart card)."
Write-Host "Poi riavvia LabRepair e prova Anagrafica -> Leggi CIE da un PC in rete."
Write-Host ""
Write-Host "Test manuale (opzionale, con CIE sul lettore):"
Write-Host "  cd $PublishDir"
Write-Host "  .\cie_reader.exe --can 123456"
