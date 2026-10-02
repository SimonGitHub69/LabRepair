# Controlla aggiornamenti del client Windows all'avvio di LabRepair.
# Uso (dal launcher):
#   powershell -NoProfile -ExecutionPolicy Bypass -STA -File check_client_update.ps1 -Origin "http://..." -AppDir "..."

param(
    [Parameter(Mandatory = $true)]
    [string]$Origin,
    [Parameter(Mandatory = $true)]
    [string]$AppDir,
    [int]$TimeoutSec = 8
)

$ErrorActionPreference = "Stop"

function Normalize-Origin([string]$value) {
    $value = $value.Trim().TrimEnd("/")
    if ($value -notmatch "^https?://") {
        $value = "http://$value"
    }
    return $value
}

function Parse-Version([string]$value) {
    $parts = @()
    foreach ($token in ([regex]::Split(($value | ForEach-Object { $_.ToString() }), "[^\d]+"))) {
        if ($token -match "^\d+$") {
            $parts += [int]$token
        }
    }
    if ($parts.Count -eq 0) { return @(0) }
    return $parts
}

function Test-VersionNewer([string]$remote, [string]$local) {
    $a = @(Parse-Version $remote)
    $b = @(Parse-Version $local)
    $max = [Math]::Max($a.Count, $b.Count)
    for ($i = 0; $i -lt $max; $i++) {
        $av = if ($i -lt $a.Count) { $a[$i] } else { 0 }
        $bv = if ($i -lt $b.Count) { $b[$i] } else { 0 }
        if ($av -gt $bv) { return $true }
        if ($av -lt $bv) { return $false }
    }
    return $false
}

function New-UpdateProgressUi([string]$remoteVersion, [string]$localVersion) {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop | Out-Null
    Add-Type -AssemblyName System.Drawing -ErrorAction Stop | Out-Null

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "LabRepair - aggiornamento"
    $form.Size = New-Object System.Drawing.Size(460, 190)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.ShowInTaskbar = $true
    $form.ControlBox = $false

    $title = New-Object System.Windows.Forms.Label
    $title.Text = "Aggiornamento a LabRepair $remoteVersion"
    $title.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
    $title.AutoSize = $false
    $title.Size = New-Object System.Drawing.Size(420, 28)
    $title.Location = New-Object System.Drawing.Point(18, 16)

    $subtitle = New-Object System.Windows.Forms.Label
    $subtitle.Text = "Versione attuale: $localVersion"
    $subtitle.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $subtitle.ForeColor = [System.Drawing.Color]::DimGray
    $subtitle.AutoSize = $false
    $subtitle.Size = New-Object System.Drawing.Size(420, 22)
    $subtitle.Location = New-Object System.Drawing.Point(18, 44)

    $status = New-Object System.Windows.Forms.Label
    $status.Text = "Preparazione..."
    $status.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $status.AutoSize = $false
    $status.Size = New-Object System.Drawing.Size(420, 22)
    $status.Location = New-Object System.Drawing.Point(18, 78)
    $status.Name = "StatusLabel"

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Size = New-Object System.Drawing.Size(410, 22)
    $bar.Location = New-Object System.Drawing.Point(18, 108)
    $bar.Minimum = 0
    $bar.Maximum = 100
    $bar.Style = "Marquee"
    $bar.MarqueeAnimationSpeed = 30
    $bar.Name = "ProgressBar"

    $form.Controls.AddRange(@($title, $subtitle, $status, $bar))
    $form.Show()
    $form.Refresh()
    [System.Windows.Forms.Application]::DoEvents()

    return @{
        Form   = $form
        Status = $status
        Bar    = $bar
    }
}

function Set-UpdateProgress($ui, [string]$text, [int]$percent = -1) {
    if (-not $ui) { return }
    try {
        $ui.Status.Text = $text
        if ($percent -lt 0) {
            if ($ui.Bar.Style -ne "Marquee") {
                $ui.Bar.Style = "Marquee"
                $ui.Bar.MarqueeAnimationSpeed = 30
            }
        } else {
            if ($ui.Bar.Style -ne "Continuous") {
                $ui.Bar.Style = "Continuous"
            }
            $value = [Math]::Max(0, [Math]::Min(100, $percent))
            $ui.Bar.Value = $value
        }
        $ui.Form.Refresh()
        [System.Windows.Forms.Application]::DoEvents()
    } catch { }
}

function Close-UpdateProgress($ui) {
    if (-not $ui) { return }
    try {
        $ui.Form.Close()
        $ui.Form.Dispose()
    } catch { }
}

function Stop-LabRepairBrowser {
    # Chiusura forzata: evita il dialogo "Leave app?" di beforeunload.
    $profileHint = "LabRepairApp"
    foreach ($name in @("chrome.exe", "msedge.exe")) {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -eq $name -and $_.CommandLine -and ($_.CommandLine -like "*$profileHint*")
            } |
            ForEach-Object {
                try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch { }
            }
    }
}

$Origin = Normalize-Origin $Origin
if (-not (Test-Path $AppDir)) {
    New-Item -Type Directory -Force -Path $AppDir | Out-Null
}

$localVersionPath = Join-Path $AppDir "VERSION"
$localVersion = "0.0.0"
if (Test-Path $localVersionPath) {
    $line = (Get-Content -Path $localVersionPath -TotalCount 1 -ErrorAction SilentlyContinue)
    if ($line) { $localVersion = $line.ToString().Trim() }
}

$versionUrl = "$Origin/api/client/version/"
try {
    $info = Invoke-RestMethod -Uri $versionUrl -TimeoutSec $TimeoutSec
} catch {
    # Server irraggiungibile: avvia comunque.
    exit 0
}

$remoteVersion = [string]($info.version)
if (-not $remoteVersion) { exit 0 }
if (-not $info.available) { exit 0 }
if (-not (Test-VersionNewer $remoteVersion $localVersion)) { exit 0 }

$downloadUrl = [string]($info.download_url)
if (-not $downloadUrl) {
    $downloadUrl = "$Origin/api/client/download/"
}

$tempRoot = Join-Path $env:TEMP ("LabRepair_client_update_" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "client.zip"
$extractPath = Join-Path $tempRoot "extract"
New-Item -Type Directory -Force -Path $extractPath | Out-Null

$ui = $null
try {
    try {
        $ui = New-UpdateProgressUi -remoteVersion $remoteVersion -localVersion $localVersion
    } catch {
        $ui = $null
        try {
            Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null
            [System.Windows.Forms.MessageBox]::Show(
                "E' disponibile LabRepair client $remoteVersion (ora $localVersion).`nL'aggiornamento parte ora.",
                "LabRepair - aggiornamento",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Information
            ) | Out-Null
        } catch { }
    }

    Set-UpdateProgress $ui "Chiusura di LabRepair in esecuzione..."
    Stop-LabRepairBrowser
    Start-Sleep -Milliseconds 400

    Set-UpdateProgress $ui "Download del pacchetto in corso..." 0

    $wc = New-Object System.Net.WebClient
    if ($ui) {
        $wc.add_DownloadProgressChanged({
            param($sender, $e)
            $pct = [int]$e.ProgressPercentage
            $mbDone = [Math]::Round($e.BytesReceived / 1MB, 1)
            $mbTotal = [Math]::Round($e.TotalBytesToReceive / 1MB, 1)
            if ($e.TotalBytesToReceive -gt 0) {
                Set-UpdateProgress $ui ("Download: {0}% ({1} / {2} MB)" -f $pct, $mbDone, $mbTotal) $pct
            } else {
                Set-UpdateProgress $ui ("Download in corso... ({0} MB)" -f $mbDone)
            }
        })
    }
    try {
        $wc.DownloadFile($downloadUrl, $zipPath)
    } finally {
        $wc.Dispose()
    }

    Set-UpdateProgress $ui "Estrazione del pacchetto..." 
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    $installScript = Get-ChildItem -Path $extractPath -Recurse -Filter "install_client_windows.ps1" |
        Select-Object -First 1
    if (-not $installScript) {
        throw "Pacchetto client senza install_client_windows.ps1"
    }

    Set-UpdateProgress $ui "Installazione della versione $remoteVersion..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript.FullName `
        -Origin $Origin `
        -Silent `
        -SkipLaunch `
        -SkipDotNet

    Set-Content -Path $localVersionPath -Value $remoteVersion -Encoding ASCII

    Set-UpdateProgress $ui "Aggiornamento completato." 100
    Start-Sleep -Milliseconds 900
} catch {
    # Non bloccare l'apertura dell'app se l'update fallisce.
    if ($ui) {
        try {
            Set-UpdateProgress $ui "Aggiornamento non riuscito: si apre comunque LabRepair."
            Start-Sleep -Milliseconds 1200
        } catch { }
    }
    exit 0
} finally {
    Close-UpdateProgress $ui
    try {
        if (Test-Path $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    } catch { }
}

exit 0
