param(
    [string]$BaseUrl = "http://127.0.0.1:8282",
    [string]$BackendUrl = "",
    [int]$TimeoutSeconds = 5,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Invoke-CheckJson {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $started = Get-Date
        $response = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSeconds
        $latencyMs = [math]::Round(((Get-Date) - $started).TotalMilliseconds)
        return [ordered]@{
            name = $Name
            ok = $true
            url = $Url
            latency_ms = $latencyMs
            response = $response
            error = $null
        }
    }
    catch {
        return [ordered]@{
            name = $Name
            ok = $false
            url = $Url
            latency_ms = $null
            response = $null
            error = $_.Exception.Message
        }
    }
}

function Invoke-CheckWeb {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $started = Get-Date
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing
        $latencyMs = [math]::Round(((Get-Date) - $started).TotalMilliseconds)
        return [ordered]@{
            name = $Name
            ok = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
            url = $Url
            latency_ms = $latencyMs
            status_code = $response.StatusCode
            error = $null
        }
    }
    catch {
        return [ordered]@{
            name = $Name
            ok = $false
            url = $Url
            latency_ms = $null
            status_code = $null
            error = $_.Exception.Message
        }
    }
}

$base = $BaseUrl.TrimEnd("/")
$checks = @()
$checks += Invoke-CheckJson -Name "liveness" -Url "$base/liveness"
$checks += Invoke-CheckJson -Name "readiness" -Url "$base/readiness"
$checks += Invoke-CheckWeb -Name "initconfig" -Url "$base/openavatarchat/initconfig"
$checks += Invoke-CheckJson -Name "trusted_sessions" -Url "$base/lingjing/avatar/sessions"

if ($BackendUrl.Trim()) {
    $backend = $BackendUrl.TrimEnd("/")
    $checks += Invoke-CheckJson -Name "backend_health" -Url "$backend/api/health"
}

$listening = Get-NetTCPConnection -LocalPort ([int]([Uri]$base).Port) -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1 -Property LocalAddress, LocalPort, OwningProcess

$summary = [ordered]@{
    ok = -not ($checks | Where-Object { -not $_.ok })
    base_url = $base
    backend_url = $(if ($BackendUrl.Trim()) { $BackendUrl.TrimEnd("/") } else { $null })
    listening = $null -ne $listening
    owning_process = $(if ($listening) { $listening.OwningProcess } else { $null })
    checks = $checks
    restart_hint = "If sidecar endpoints time out, stop only the OpenAvatarChat uv/python process on this port, then restart with config/lingjing_trusted_liteavatar_edge_tts.yaml."
}

if ($Json) {
    $summary | ConvertTo-Json -Depth 8
}
else {
    "Avatar sidecar healthcheck: $($summary.base_url)"
    "Overall: $(if ($summary.ok) { 'OK' } else { 'FAILED' })"
    "Listening: $($summary.listening) PID=$($summary.owning_process)"
    foreach ($check in $checks) {
        $status = if ($check.ok) { "OK" } else { "FAIL" }
        $latency = if ($null -ne $check.latency_ms) { "$($check.latency_ms)ms" } else { "-" }
        "$status`t$($check.name)`t$latency`t$($check.url)"
        if (-not $check.ok -and $check.error) {
            "  error: $($check.error)"
        }
    }
    "Restart hint: $($summary.restart_hint)"
}
