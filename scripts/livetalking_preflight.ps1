param(
  [string]$Root = "D:\py\dota",
  [switch]$SkipImportSmoke
)

$ErrorActionPreference = "Continue"

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host "== $Title =="
}

function Test-CommandExists {
  param([string]$Name)
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) {
    Write-Host "${Name}: $($cmd.Source)"
    return $true
  }
  Write-Host "${Name}: not found"
  return $false
}

if (-not (Test-Path $Root)) {
  Write-Error "Root not found: $Root"
  exit 1
}

Push-Location $Root
try {
  Write-Section "Workspace"
  Write-Host "Root: $Root"
  git status --short

  Write-Section "Ignored Protection"
  $ignore = git check-ignore -v external\LiveTalking 2>$null
  if ($ignore) {
    Write-Host "external\LiveTalking ignored by: $ignore"
  } else {
    Write-Warning "external\LiveTalking is not ignored. Do not add third-party source until ignore is fixed."
  }

  Write-Section "Tools"
  Test-CommandExists git | Out-Null
  git --version
  Test-CommandExists python | Out-Null
  python --version
  Test-CommandExists docker | Out-Null
  docker --version
  Test-CommandExists nvidia-smi | Out-Null
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,driver_version --format=csv,noheader,nounits

  Write-Section "LiveTalking Source"
  $lt = Join-Path $Root "external\LiveTalking"
  if (-not (Test-Path $lt)) {
    Write-Warning "external\LiveTalking not found. Clone source before deeper validation."
  } else {
    Write-Host "Path: $lt"
    git -C $lt remote -v
    git -C $lt log -1 --oneline
  }

  Write-Section "Required Lightweight Wav2Lip Assets"
  $model = Join-Path $lt "models\wav2lip.pth"
  $avatar = Join-Path $lt "data\avatars\wav2lip256_avatar1"
  if (Test-Path $model) {
    $modelInfo = Get-Item $model
    Write-Host "wav2lip model: present ($([math]::Round($modelInfo.Length / 1MB, 1)) MB)"
  } else {
    Write-Warning "wav2lip model missing: $model"
  }
  if (Test-Path $avatar) {
    Write-Host "avatar asset: present ($avatar)"
  } else {
    Write-Warning "avatar asset missing: $avatar"
  }

  Write-Section "Ports"
  Get-NetTCPConnection -LocalPort 8010,8282,8000,5174 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,State,OwningProcess |
    Format-Table -AutoSize

  if (-not $SkipImportSmoke -and (Test-Path (Join-Path $lt "app.py"))) {
    Write-Section "Import Smoke"
    Push-Location $lt
    try {
      $venvPython = Join-Path $lt ".venv\Scripts\python.exe"
      if (Test-Path $venvPython) {
        $pythonExe = $venvPython
      } else {
        $pythonExe = "python"
      }
      $codeText = @"
import importlib
mods = ['flask', 'aiohttp', 'aiortc', 'torch', 'cv2', 'soundfile', 'edge_tts']
for name in mods:
    importlib.import_module(name)
    print(f'{name}: ok')
try:
    import torch
    print('torch_cuda_available:', torch.cuda.is_available())
    print('torch_cuda_device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
except Exception as exc:
    print('torch_cuda_check_failed:', repr(exc))
"@
      $output = & $pythonExe -c $codeText 2>&1
      $code = $LASTEXITCODE
      Write-Host $output
      Write-Host "import smoke exit code: $code"
      if ($code -ne 0) {
        Write-Warning "LiveTalking dependencies are not installed or import smoke failed."
      }
    } finally {
      Pop-Location
    }
  }

  Write-Section "Suggested Start Command After Assets Exist"
  Write-Host "cd D:\py\dota\external\LiveTalking"
  Write-Host "python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts edgetts --listenport 8010 --max_session 1"
} finally {
  Pop-Location
}
