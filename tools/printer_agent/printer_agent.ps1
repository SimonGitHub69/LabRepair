# Agent locale stampanti Windows per LabRepair (PC client / cassa).
# - GET  /printers  elenco stampanti del PC
# - POST /print     stampa HTML sulla stampante indicata (es. buste)
param(
    [int]$Port = 17346
)

$ErrorActionPreference = "SilentlyContinue"

function Get-PrinterPayload {
    $items = @()
    $seen = @{}

    foreach ($row in @(
        Get-CimInstance -ClassName Win32_Printer
        Get-Printer
    )) {
        if (-not $row) { continue }
        $batch = @($row)
        foreach ($printer in $batch) {
            $name = [string]$printer.Name
            if ([string]::IsNullOrWhiteSpace($name)) { continue }
            $key = $name.ToLowerInvariant()
            if ($seen.ContainsKey($key)) { continue }
            $seen[$key] = $true
            $items += [ordered]@{
                nome        = $name
                driver      = [string]$printer.DriverName
                porta       = [string]$printer.PortName
                predefinita = [bool]$printer.Default
            }
        }
    }

    return ,$items
}

function Find-BrowserExe {
    $candidates = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return $path
        }
    }
    return $null
}

function Resolve-PrinterName([string]$Requested) {
    $wanted = ($Requested -as [string]).Trim()
    if ([string]::IsNullOrWhiteSpace($wanted)) {
        return $null
    }
    $printers = Get-PrinterPayload
    foreach ($item in $printers) {
        if ([string]$item.nome -eq $wanted) {
            return [string]$item.nome
        }
    }
    foreach ($item in $printers) {
        if ([string]$item.nome.ToLowerInvariant() -eq $wanted.ToLowerInvariant()) {
            return [string]$item.nome
        }
    }
    return $null
}

function Read-RequestBodyText($request) {
    $reader = New-Object System.IO.StreamReader($request.InputStream, [System.Text.Encoding]::UTF8)
    try {
        return $reader.ReadToEnd()
    } finally {
        $reader.Close()
    }
}

function ConvertFrom-JsonSafe([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }
    try {
        return $Text | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-DefaultPrinterName {
    foreach ($row in @(Get-CimInstance -ClassName Win32_Printer -Filter "Default = TRUE")) {
        $name = [string]$row.Name
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            return $name
        }
    }
    return $null
}

function Set-DefaultPrinterByName([string]$PrinterName) {
    $wanted = ($PrinterName -as [string]).Trim()
    if ([string]::IsNullOrWhiteSpace($wanted)) {
        return $false
    }
    $escaped = $wanted.Replace("\", "\\").Replace("'", "\'")
    $printer = Get-CimInstance -ClassName Win32_Printer -Filter "Name = '$escaped'" | Select-Object -First 1
    if (-not $printer) {
        return $false
    }
    $result = Invoke-CimMethod -InputObject $printer -MethodName SetDefaultPrinter
    return ($result.ReturnValue -eq 0)
}

function Inject-AutoPrintScript([string]$Html) {
    $script = @"
<script>
(function () {
  function go() {
    try { window.focus(); } catch (e) {}
    try { window.print(); } catch (e) {}
    setTimeout(function () {
      try { window.close(); } catch (e) {}
    }, 1200);
  }
  if (document.readyState === "complete") {
    setTimeout(go, 250);
  } else {
    window.addEventListener("load", function () { setTimeout(go, 250); });
  }
})();
</script>
"@
    if ($Html -match "(?i)</body>") {
        return [regex]::Replace($Html, "(?i)</body>", ($script + "</body>"), 1)
    }
    return ($Html + $script)
}

function Write-BrowserPrintProfile([string]$ProfileRoot, [string]$PrinterName) {
    $defaultDir = Join-Path $ProfileRoot "Default"
    New-Item -ItemType Directory -Path $defaultDir -Force | Out-Null

    # Preferenze sticky: Chrome/Edge scelgono questa stampante con --kiosk-printing.
    $appStateObj = [ordered]@{
        version               = 2
        selectedDestinationId = $PrinterName
        recentDestinations    = @(
            [ordered]@{
                id      = $PrinterName
                origin  = "local"
                account = ""
            }
        )
        isLandscape           = $false
        marginsType           = 0
        isHeaderFooterEnabled = $false
        isCssBackgroundEnabled = $true
    }
    $appState = ($appStateObj | ConvertTo-Json -Compress -Depth 6)
    $prefs = [ordered]@{
        printing = [ordered]@{
            print_preview_sticky_settings = [ordered]@{
                appState = $appState
            }
        }
        savefile = [ordered]@{
            default_directory = $ProfileRoot
        }
        bookmark_bar = [ordered]@{
            show_on_all_tabs = $false
        }
        browser = [ordered]@{
            has_seen_welcome_page = $true
            check_default_browser = $false
        }
        distribution = [ordered]@{
            skip_first_run_ui            = $true
            show_welcome_page            = $false
            import_search_engine         = $false
            import_history               = $false
            do_not_create_desktop_shortcut = $true
        }
    }
    $prefsPath = Join-Path $defaultDir "Preferences"
    [System.IO.File]::WriteAllText(
        $prefsPath,
        ($prefs | ConvertTo-Json -Compress -Depth 8),
        [System.Text.UTF8Encoding]::new($false)
    )

    $localState = [ordered]@{
        profile = [ordered]@{
            info_cache = [ordered]@{
                Default = [ordered]@{
                    name = "Default"
                }
            }
            last_used = "Default"
        }
    }
    [System.IO.File]::WriteAllText(
        (Join-Path $ProfileRoot "Local State"),
        ($localState | ConvertTo-Json -Compress -Depth 6),
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Print-HtmlToPrinter {
    param(
        [Parameter(Mandatory = $true)][string]$Html,
        [Parameter(Mandatory = $true)][string]$PrinterName
    )

    $resolved = Resolve-PrinterName $PrinterName
    if (-not $resolved) {
        return @{
            ok      = $false
            message = "Stampante non trovata su questo PC: $PrinterName"
        }
    }

    $browser = Find-BrowserExe
    if (-not $browser) {
        return @{
            ok      = $false
            message = "Chrome o Edge non trovati: necessari per stampare la busta."
        }
    }

    $workDir = Join-Path $env:TEMP ("LabRepairPrint_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    $htmlPath = Join-Path $workDir "busta.html"
    $profileDir = Join-Path $workDir "browser-profile"
    $previousDefault = $null
    $changedDefault = $false
    $browserProc = $null

    try {
        # Stampa diretta HTML → stampante (niente PDF / printto → niente Acrobat).
        $printHtml = Inject-AutoPrintScript $Html
        [System.IO.File]::WriteAllText($htmlPath, $printHtml, [System.Text.UTF8Encoding]::new($false))
        Write-BrowserPrintProfile -ProfileRoot $profileDir -PrinterName $resolved

        $previousDefault = Get-DefaultPrinterName
        if ($previousDefault -ne $resolved) {
            $changedDefault = Set-DefaultPrinterByName $resolved
        }

        $fileUri = ([Uri]$htmlPath).AbsoluteUri
        $args = @(
            "--user-data-dir=`"$profileDir`"",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--kiosk-printing",
            "--window-position=-32000,-32000",
            "--window-size=900,700",
            $fileUri
        )

        $browserProc = Start-Process -FilePath $browser -ArgumentList $args -PassThru -WindowStyle Minimized
        if (-not $browserProc) {
            return @{
                ok      = $false
                message = "Impossibile avviare il browser per la stampa."
            }
        }

        # Attendi lo spool (il browser spesso non esce da solo dopo window.print).
        $deadline = (Get-Date).AddSeconds(25)
        while ((Get-Date) -lt $deadline) {
            if ($browserProc.HasExited) {
                break
            }
            Start-Sleep -Milliseconds 400
        }
        if (-not $browserProc.HasExited) {
            Stop-Process -Id $browserProc.Id -Force -ErrorAction SilentlyContinue
            try { $null = $browserProc.WaitForExit(5000) } catch { }
        }

        # Tempo allo spooler prima di cancellare i file temporanei.
        Start-Sleep -Seconds 2

        return @{
            ok       = $true
            message  = "Busta inviata a $resolved"
            printer  = $resolved
        }
    } catch {
        return @{
            ok      = $false
            message = "Errore stampa busta: $($_.Exception.Message)"
        }
    } finally {
        if ($browserProc -and -not $browserProc.HasExited) {
            try { Stop-Process -Id $browserProc.Id -Force -ErrorAction SilentlyContinue } catch { }
        }
        if ($changedDefault -and $previousDefault) {
            try { Set-DefaultPrinterByName $previousDefault | Out-Null } catch { }
        }
        try {
            Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
        } catch { }
    }
}

function Write-CorsHeaders($response) {
    $response.Headers["Access-Control-Allow-Origin"] = "*"
    $response.Headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    $response.Headers["Access-Control-Allow-Headers"] = "Content-Type"
    $response.Headers["Access-Control-Max-Age"] = "86400"
}

function Write-JsonResponse($response, [int]$statusCode, $payload) {
    Write-CorsHeaders $response
    $response.StatusCode = $statusCode
    $response.ContentType = "application/json; charset=utf-8"
    $json = $payload | ConvertTo-Json -Compress -Depth 6
    $buffer = [System.Text.Encoding]::UTF8.GetBytes($json)
    $response.ContentLength64 = $buffer.Length
    $response.OutputStream.Write($buffer, 0, $buffer.Length)
    $response.OutputStream.Close()
}

$prefix = "http://127.0.0.1:$Port/"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)

try {
    $listener.Start()
} catch {
    Write-Error "Impossibile avviare l'agent stampanti su $prefix : $_"
    exit 1
}

while ($listener.IsListening) {
    $context = $null
    try {
        $context = $listener.GetContext()
    } catch {
        break
    }

    $request = $context.Request
    $response = $context.Response
    $path = ($request.Url.AbsolutePath.TrimEnd("/") + "/").ToLowerInvariant()

    if ($request.HttpMethod -eq "OPTIONS") {
        Write-CorsHeaders $response
        $response.StatusCode = 204
        $response.Close()
        continue
    }

    if ($path -eq "/health/") {
        Write-JsonResponse $response 200 @{
            ok      = $true
            service = "LabRepairPrinterAgent"
            port    = $Port
        }
        continue
    }

    if ($path -eq "/printers/") {
        $printers = Get-PrinterPayload
        Write-JsonResponse $response 200 @{
            ok       = $true
            printers = $printers
            total    = $printers.Count
        }
        continue
    }

    if ($path -eq "/print/" -and $request.HttpMethod -eq "POST") {
        $bodyText = Read-RequestBodyText $request
        $payload = ConvertFrom-JsonSafe $bodyText
        if (-not $payload) {
            Write-JsonResponse $response 400 @{
                ok      = $false
                message = "JSON non valido"
            }
            continue
        }

        $printerName = [string]($payload.printer)
        $html = [string]($payload.html)
        if ([string]::IsNullOrWhiteSpace($printerName)) {
            Write-JsonResponse $response 400 @{
                ok      = $false
                message = "Indicare la stampante (campo printer)."
            }
            continue
        }
        if ([string]::IsNullOrWhiteSpace($html)) {
            Write-JsonResponse $response 400 @{
                ok      = $false
                message = "Documento HTML mancante."
            }
            continue
        }

        $result = Print-HtmlToPrinter -Html $html -PrinterName $printerName
        $code = if ($result.ok) { 200 } else { 500 }
        Write-JsonResponse $response $code $result
        continue
    }

    Write-JsonResponse $response 404 @{
        ok      = $false
        message = "Endpoint non trovato"
    }
}
