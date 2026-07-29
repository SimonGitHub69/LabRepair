# Agent locale stampanti Windows per LabRepair (PC client / cassa).
# Il browser chiama http://127.0.0.1:17346/printers e legge le stampanti del PC utente.
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

function Write-CorsHeaders($response) {
    $response.Headers["Access-Control-Allow-Origin"] = "*"
    $response.Headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
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

    Write-JsonResponse $response 404 @{
        ok      = $false
        message = "Endpoint non trovato"
    }
}
