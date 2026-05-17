param(
    [string]$ProjectRoot = "D:\py\dota",
    [int]$SidecarPort = 8282,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5174,
    [string]$SidecarConfigName = "",
    [double]$MinFreeGB = 8.0,
    [switch]$ForceLowMemory,
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$OpenWebUI,
    [switch]$OpenVisitor
)

$ErrorActionPreference = "Stop"

function Get-FreeMemoryGB {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round($os.FreePhysicalMemory / 1MB, 2)
}

function Stop-OrphanedSidecarWorkers {
    param([string]$Root)

    $sidecarPython = Join-Path $Root ".sidecar-python"
    $orphans = Get-CimInstance Win32_Process |
        Where-Object {
            $cmd = [string]$_.CommandLine
            $cmd.Contains($sidecarPython) -and
            $cmd.Contains("multiprocessing.spawn") -and
            -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue)
        }
    foreach ($orphan in $orphans) {
        "Stopping orphaned sidecar worker PID=$($orphan.ProcessId)"
        Stop-Process -Id $orphan.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Get-Listener {
    param([int]$Port)

    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1 -Property LocalAddress, LocalPort, OwningProcess
}

function Wait-JsonEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 3
        }
        catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for $Url. Last error: $lastError"
}

function Start-HiddenPowerShell {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$ScriptBlockText,
        [string]$LogDirectory
    )

    New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outLog = Join-Path $LogDirectory "$Name`_$stamp.out.log"
    $errLog = Join-Path $LogDirectory "$Name`_$stamp.err.log"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($ScriptBlockText))
    $process = Start-Process -FilePath powershell.exe `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded) `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru

    return [ordered]@{
        name = $Name
        launcher_pid = $process.Id
        stdout = $outLog
        stderr = $errLog
    }
}

$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
Stop-OrphanedSidecarWorkers -Root $project
$openAvatarDir = Join-Path $project "external\OpenAvatarChat"
$uvExe = Join-Path $project ".sidecar-tools\Scripts\uv.exe"
$fastConfigName = "lingjing_trusted_liteavatar_fast.yaml"
$stableConfigName = "lingjing_trusted_liteavatar_edge_tts.yaml"
if (-not $SidecarConfigName) {
    $fastConfigPath = Join-Path $openAvatarDir "config\$fastConfigName"
    if (Test-Path -LiteralPath $fastConfigPath) {
        $SidecarConfigName = $fastConfigName
    }
    else {
        $SidecarConfigName = $stableConfigName
    }
}
$sidecarConfig = Join-Path $openAvatarDir "config\$SidecarConfigName"
$runtimeDll = Join-Path $openAvatarDir ".runtime-dll"
$sidecarTools = Join-Path $project ".sidecar-tools\Scripts"
$logDir = Join-Path $project "external\run_logs"

if (-not (Test-Path -LiteralPath $openAvatarDir)) {
    throw "Missing OpenAvatarChat sidecar workspace: $openAvatarDir"
}
if (-not (Test-Path -LiteralPath $uvExe)) {
    throw "Missing uv executable: $uvExe"
}
if (-not (Test-Path -LiteralPath $sidecarConfig)) {
    throw "Missing LiteAvatar trusted config: $sidecarConfig"
}

$freeBefore = Get-FreeMemoryGB
$sidecarListener = Get-Listener -Port $SidecarPort
$backendListener = Get-Listener -Port $BackendPort

"Avatar demo startup"
"Project: $project"
"Sidecar config: config/$SidecarConfigName"
"Backend API: http://127.0.0.1:$BackendPort"
"Visitor UI: http://127.0.0.1:$FrontendPort/"
"Free memory: $freeBefore GB"

if (-not $sidecarListener -and -not $ForceLowMemory -and $freeBefore -lt $MinFreeGB) {
    throw "Free memory is $freeBefore GB, below MinFreeGB=$MinFreeGB. Close other apps or rerun with -ForceLowMemory."
}

if ($sidecarListener) {
    "Sidecar already listening on port $SidecarPort, PID=$($sidecarListener.OwningProcess)."
    "If you need the Task 07.6G fast config, stop the old sidecar first with scripts\stop_avatar_demo.ps1 and rerun this script."
}
else {
    $pathValue = "$runtimeDll;$sidecarTools;$env:PATH"
$sidecarScript = @"
`$env:PATH = '$pathValue'
`$env:PYTHONUTF8 = '1'
`$env:PYTHONIOENCODING = 'utf-8'
& '$uvExe' run --python 3.11 src/demo.py --host 127.0.0.1 --port $SidecarPort --config config/$SidecarConfigName
"@
    $sidecarStarted = Start-HiddenPowerShell -Name "avatar_sidecar" -WorkingDirectory $openAvatarDir -ScriptBlockText $sidecarScript -LogDirectory $logDir
    "Started sidecar launcher PID=$($sidecarStarted.launcher_pid)"
    "  stdout: $($sidecarStarted.stdout)"
    "  stderr: $($sidecarStarted.stderr)"
}

$sidecarReady = Wait-JsonEndpoint -Url "http://127.0.0.1:$SidecarPort/readiness" -TimeoutSeconds 180
"Sidecar readiness: $($sidecarReady.status)"

if (-not $SkipBackend) {
    $backendListener = Get-Listener -Port $BackendPort
    if ($backendListener) {
        "Backend already listening on port $BackendPort, PID=$($backendListener.OwningProcess)."
        "If visitor/Kiosk avatar buttons still return mode=mock, stop the old demo backend first with scripts\stop_avatar_demo.ps1 and rerun this script."
    }
    else {
        $backendScript = @"
`$env:AVATAR_SPEAKER_MODE = 'sidecar'
`$env:AVATAR_SIDECAR_ADAPTER = 'http_json'
`$env:AVATAR_SIDECAR_BASE_URL = 'http://127.0.0.1:$SidecarPort'
`$env:AVATAR_SIDECAR_SPEAK_PATH = '/lingjing/avatar/speak'
`$env:AVATAR_SIDECAR_CLIP_PATH = '/lingjing/avatar/play-clip'
`$env:PYTHONUTF8 = '1'
`$env:PYTHONIOENCODING = 'utf-8'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort
"@
        $backendStarted = Start-HiddenPowerShell -Name "avatar_backend" -WorkingDirectory $project -ScriptBlockText $backendScript -LogDirectory $logDir
        "Started backend launcher PID=$($backendStarted.launcher_pid)"
        "  stdout: $($backendStarted.stdout)"
        "  stderr: $($backendStarted.stderr)"
    }

    $backendReady = Wait-JsonEndpoint -Url "http://127.0.0.1:$BackendPort/api/health" -TimeoutSeconds 60
    "Backend health: $($backendReady.status)"
}

if (-not $SkipFrontend) {
    $frontendListener = Get-Listener -Port $FrontendPort
    if ($frontendListener) {
        "Frontend already listening on port $FrontendPort, PID=$($frontendListener.OwningProcess)."
        "Vite /api proxy expects the backend on http://127.0.0.1:$BackendPort."
    }
    else {
        $frontendScript = @"
npm --prefix .\frontend run dev -- --host 127.0.0.1 --port $FrontendPort
"@
        $frontendStarted = Start-HiddenPowerShell -Name "avatar_frontend" -WorkingDirectory $project -ScriptBlockText $frontendScript -LogDirectory $logDir
        "Started frontend launcher PID=$($frontendStarted.launcher_pid)"
        "  stdout: $($frontendStarted.stdout)"
        "  stderr: $($frontendStarted.stderr)"
        Start-Sleep -Seconds 3
    }
}

$healthcheck = Join-Path $project "scripts\avatar_sidecar_healthcheck.ps1"
if (Test-Path -LiteralPath $healthcheck) {
    $healthcheckArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $healthcheck,
        "-BaseUrl", "http://127.0.0.1:$SidecarPort"
    )
    if (-not $SkipBackend) {
        $healthcheckArgs += @("-BackendUrl", "http://127.0.0.1:$BackendPort")
    }
    powershell @healthcheckArgs
}

$sessions = Invoke-RestMethod -Uri "http://127.0.0.1:$SidecarPort/lingjing/avatar/sessions" -TimeoutSec 5
$freeAfter = Get-FreeMemoryGB
"Free memory after startup: $freeAfter GB"
"Active session: $($sessions.active_session_id)"
if (-not $sessions.active_session_id) {
    "Open WebUI and create an RTC session before sending speech: http://127.0.0.1:$SidecarPort"
}

if ($OpenWebUI) {
    Start-Process "http://127.0.0.1:$SidecarPort"
}

if ($OpenVisitor) {
    Start-Process "http://127.0.0.1:$FrontendPort/"
}
