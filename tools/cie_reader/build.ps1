$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$outDir = Join-Path $root "publish"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

dotnet publish ".\CieReader.csproj" `
  -c Release `
  -r win-x64 `
  --self-contained false `
  -o $outDir

Write-Host "Built: $(Join-Path $outDir 'cie_reader.exe')"
