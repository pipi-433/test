param(
    [string]$ProjectRoot = "D:\py\dota"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$clipDir = Join-Path $root "external\avatar-clips"
$required = @(
    @{ clip_id = "welcome_intro_5s"; file = "welcome_intro_5s.wav"; duration_seconds = 5 },
    @{ clip_id = "lingshan_buddha_intro_45s"; file = "lingshan_buddha_intro_45s.wav"; duration_seconds = 45 },
    @{ clip_id = "fan_gong_intro_45s"; file = "fan_gong_intro_45s.wav"; duration_seconds = 45 },
    @{ clip_id = "jiulong_guanyu_intro_30s"; file = "jiulong_guanyu_intro_30s.wav"; duration_seconds = 30 }
)

"Avatar preset clip inventory"
"Clip directory: $clipDir"
if (-not (Test-Path -LiteralPath $clipDir)) {
    "Directory missing. Create it locally if you want low-latency preset clip playback."
}

foreach ($item in $required) {
    $path = Join-Path $clipDir $item.file
    $exists = Test-Path -LiteralPath $path
    $size = if ($exists) { [math]::Round((Get-Item -LiteralPath $path).Length / 1MB, 2) } else { 0 }
    [pscustomobject]@{
        clip_id = $item.clip_id
        file = $item.file
        duration_seconds = $item.duration_seconds
        exists = $exists
        size_mb = $size
        path = $path
    }
}
