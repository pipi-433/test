param(
  [switch]$TryClone
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ExternalDir = Join-Path $ProjectRoot "external"
$OpenAvatarChatDir = Join-Path $ExternalDir "OpenAvatarChat"
$LocalUv = Join-Path $ProjectRoot ".sidecar-tools\Scripts\uv.exe"
$LocalPythonInstallDir = Join-Path $ProjectRoot ".sidecar-python"
$LocalUvCacheDir = Join-Path $ProjectRoot ".sidecar-cache"

function Invoke-Check {
  param(
    [string]$Name,
    [scriptblock]$Command
  )

  Write-Host "== $Name =="
  try {
    & $Command
  } catch {
    Write-Host "FAILED: $($_.Exception.Message)"
  }
  Write-Host ""
}

Push-Location $ProjectRoot

Invoke-Check "git status --short" { git status --short }
Invoke-Check "git log --oneline -5" { git log --oneline -5 }
Invoke-Check "git --version" { git --version }
Invoke-Check "git lfs version" { git lfs version }
Invoke-Check "docker --version" { docker --version }
Invoke-Check "docker compose version" { docker compose version }
Invoke-Check "nvidia-smi" { nvidia-smi }
Invoke-Check "python --version" { python --version }
Invoke-Check "node --version" { node --version }
Invoke-Check "npm --version" { npm --version }
Invoke-Check "uv --version" {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv --version
  } elseif (Test-Path -LiteralPath $LocalUv) {
    & $LocalUv --version
  } else {
    Write-Host "uv is not installed. Do not install globally without workspace/outside-path approval."
  }
}

Invoke-Check "workspace-managed Python 3.11" {
  if (-not (Test-Path -LiteralPath $LocalUv)) {
    Write-Host "local uv is missing: $LocalUv"
    return
  }
  $env:UV_PYTHON_INSTALL_DIR = $LocalPythonInstallDir
  $env:UV_CACHE_DIR = $LocalUvCacheDir
  & $LocalUv python find 3.11 --managed-python
  $ManagedPython = Join-Path $LocalPythonInstallDir "cpython-3.11-windows-x86_64-none\python.exe"
  if (Test-Path -LiteralPath $ManagedPython) {
    & $ManagedPython --version
  } else {
    Write-Host "managed Python shim not found at $ManagedPython"
  }
}

Invoke-Check "OpenAvatarChat Python compatibility" {
  if (-not (Test-Path -LiteralPath $OpenAvatarChatDir)) {
    Write-Host "external/OpenAvatarChat is missing."
    return
  }
  $env:UV_PYTHON_INSTALL_DIR = $LocalPythonInstallDir
  $env:UV_CACHE_DIR = $LocalUvCacheDir
  if (Test-Path -LiteralPath $LocalUv) {
    Push-Location $OpenAvatarChatDir
    & $LocalUv python find 3.11 --managed-python
    & $LocalUv python find 3.12
    Pop-Location
  } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    Push-Location $OpenAvatarChatDir
    uv python find 3.11
    uv python find 3.12
    Pop-Location
  } else {
    Write-Host "uv is unavailable; cannot check pyproject Python requirement."
  }
}

Invoke-Check "OpenAvatarChat dependency smoke" {
  if (-not (Test-Path -LiteralPath $OpenAvatarChatDir)) {
    Write-Host "external/OpenAvatarChat is missing."
    return
  }
  if (-not (Test-Path -LiteralPath $LocalUv)) {
    Write-Host "local uv is missing: $LocalUv"
    return
  }
  $env:UV_PYTHON_INSTALL_DIR = $LocalPythonInstallDir
  $env:UV_CACHE_DIR = $LocalUvCacheDir
  $env:PATH = "$(Split-Path -Parent $LocalUv);$env:PATH"
  Push-Location $OpenAvatarChatDir
  & $LocalUv run --python 3.11 python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
  & $LocalUv run --python 3.11 python -c "import onnxruntime; print('onnxruntime', onnxruntime.__version__)"
  & $LocalUv run --python 3.11 python -c "import dashscope; print('dashscope import ok')"
  & $LocalUv run --python 3.11 python -c "import transformers; print('transformers', transformers.__version__)"
  & $LocalUv run --python 3.11 python -c "import funasr; print('funasr', funasr.__version__ if hasattr(funasr, '__version__') else 'ok')"
  & $LocalUv run --python 3.11 python -c "import vocos; print('vocos import ok')"
  Write-Host "sidecar dependency smoke ok"
  Pop-Location
}

Invoke-Check "external ignore guard" {
  if (Test-Path -LiteralPath (Join-Path $ExternalDir ".gitignore")) {
    Get-Content -LiteralPath (Join-Path $ExternalDir ".gitignore")
  } else {
    Write-Host "external/.gitignore is missing."
  }
}

if ($TryClone) {
  Invoke-Check "OpenAvatarChat clone attempt" {
    if (Test-Path -LiteralPath $OpenAvatarChatDir) {
      Write-Host "external/OpenAvatarChat already exists; skip clone."
    } else {
      git clone --depth 1 https://github.com/HumanAIGC-Engineering/OpenAvatarChat.git external\OpenAvatarChat
    }
  }
}

Pop-Location
