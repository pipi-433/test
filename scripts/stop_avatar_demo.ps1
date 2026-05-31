param(
    [string]$ProjectRoot = "D:\py\dota",
    [int[]]$Ports = @(8282, 8011, 8000, 8015, 5174),
    [switch]$ForceAll,
    [switch]$Preview
)

$ErrorActionPreference = "Stop"

function Get-ListenerPid {
    param([int]$Port)

    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
}

function Get-ProcessInfo {
    param([int]$ProcessId)

    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
}

function Test-ProjectDemoProcess {
    param(
        [object]$ProcessInfo,
        [string]$Root
    )

    if (-not $ProcessInfo) {
        return $false
    }

    $cmd = [string]$ProcessInfo.CommandLine
    $exe = [string]$ProcessInfo.ExecutablePath

    if ($ForceAll) {
        return $true
    }

        $looksLikeDemo = (
            $cmd.Contains("OpenAvatarChat") -or
            $cmd.Contains("LiveTalking") -or
            $cmd.Contains("app.py --transport webrtc") -or
            $cmd.Contains("src/demo.py") -or
        $cmd.Contains("lingjing_trusted_liteavatar_edge_tts.yaml") -or
        $cmd.Contains("lingjing_trusted_liteavatar_fast.yaml") -or
        $cmd.Contains("uvicorn app.main:app") -or
        $cmd.Contains("npm --prefix .\frontend run dev") -or
            $cmd.Contains("AVATAR_SIDECAR_BASE_URL") -or
            $cmd.Contains("AVATAR_LIVETALKING_BASE_URL") -or
            $cmd.Contains("avatar_backend") -or
            $cmd.Contains("avatar_sidecar") -or
            $cmd.Contains("livetalking_sidecar") -or
            $cmd.Contains("avatar_frontend") -or
        ($cmd.Contains(".sidecar-python") -and $cmd.Contains("multiprocessing.spawn"))
    )
    $belongsToProject = (
        $cmd.Contains($Root) -or
        $exe.Contains($Root) -or
        $cmd.Contains("uvicorn app.main:app") -or
        $cmd.Contains("app.py --transport webrtc") -or
        $cmd.Contains("lingjing_trusted_liteavatar_edge_tts.yaml") -or
        $cmd.Contains("lingjing_trusted_liteavatar_fast.yaml")
    )

    return ($belongsToProject -and $looksLikeDemo)
}

function Get-Descendants {
    param([int[]]$ParentIds)

    $all = Get-CimInstance Win32_Process
    $found = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    foreach ($id in $ParentIds) {
        $queue.Enqueue($id)
    }

    while ($queue.Count -gt 0) {
        $parent = $queue.Dequeue()
        foreach ($child in ($all | Where-Object { $_.ParentProcessId -eq $parent })) {
            if (-not $found.Contains([int]$child.ProcessId)) {
                $found.Add([int]$child.ProcessId)
                $queue.Enqueue([int]$child.ProcessId)
            }
        }
    }

    return $found.ToArray()
}

function Get-OrphanedSidecarWorkerPids {
    param([string]$Root)

    $sidecarPython = Join-Path $Root ".sidecar-python"
    return Get-CimInstance Win32_Process |
        Where-Object {
            $cmd = [string]$_.CommandLine
            $cmd.Contains($sidecarPython) -and
            $cmd.Contains("multiprocessing.spawn") -and
            -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue)
        } |
        Select-Object -ExpandProperty ProcessId
}

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$portPids = @()
foreach ($port in $Ports) {
    $pids = @(Get-ListenerPid -Port $port)
    if ($pids.Count -eq 0) {
        "Port ${port}: no listener"
    }
    else {
        foreach ($processId in $pids) {
            "Port ${port}: listener PID=$processId"
            $portPids += [int]$processId
        }
    }
}

$candidatePids = @($portPids + (Get-Descendants -ParentIds $portPids)) | Sort-Object -Unique
$orphanedSidecarWorkerPids = @(Get-OrphanedSidecarWorkerPids -Root $root)
if ($orphanedSidecarWorkerPids.Count -gt 0) {
    "Found orphaned sidecar worker PIDs: $($orphanedSidecarWorkerPids -join ',')"
    $candidatePids = @($candidatePids + $orphanedSidecarWorkerPids) | Sort-Object -Unique
}

$safeTargets = @()
foreach ($processId in $candidatePids) {
    $info = Get-ProcessInfo -ProcessId $processId
    if (Test-ProjectDemoProcess -ProcessInfo $info -Root $root) {
        $safeTargets += [ordered]@{
            pid = [int]$processId
            name = $info.Name
            command_line = $info.CommandLine
        }
    }
    elseif ($info) {
        "Skip PID=$processId because it does not look like a $root avatar demo process."
    }
}

if ($safeTargets.Count -eq 0) {
    "No avatar demo processes to stop."
    return
}

"Stopping avatar demo processes:"
foreach ($target in ($safeTargets | Sort-Object -Property pid -Descending)) {
    "  PID=$($target.pid) $($target.name)"
    if (-not $Preview) {
        Stop-Process -Id $target.pid -Force -ErrorAction SilentlyContinue
    }
}

if ($Preview) {
    "Preview only; no processes were stopped."
    return
}

Start-Sleep -Seconds 2
foreach ($port in $Ports) {
    $remaining = @(Get-ListenerPid -Port $port)
    if ($remaining.Count -eq 0) {
        "Port ${port}: stopped"
    }
    else {
        "Port ${port}: still listening PID=$($remaining -join ',')"
    }
}
