param(
    [string]$ProjectRoot = "D:\py\dota",
    [string]$Voice = "zh-CN-XiaoxiaoNeural",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$script = Join-Path $root "scripts\generate_avatar_clips.py"
$liveTalkingPython = Join-Path $root "external\LiveTalking\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $liveTalkingPython)) {
    throw "Missing LiveTalking venv python: $liveTalkingPython"
}

$args = @($script, "--voice", $Voice)
if ($Force) {
    $args += "--force"
}

& $liveTalkingPython @args
