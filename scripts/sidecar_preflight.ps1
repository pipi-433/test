param(
  [switch]$TryClone
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ExternalDir = Join-Path $ProjectRoot "external"
$OpenAvatarChatDir = Join-Path $ExternalDir "OpenAvatarChat"

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
  $LocalUv = Join-Path $ProjectRoot ".sidecar-tools\Scripts\uv.exe"
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv --version
  } elseif (Test-Path -LiteralPath $LocalUv) {
    & $LocalUv --version
  } else {
    Write-Host "uv is not installed. Do not install globally without workspace/outside-path approval."
  }
}

Invoke-Check "OpenAvatarChat Python compatibility" {
  $LocalUv = Join-Path $ProjectRoot ".sidecar-tools\Scripts\uv.exe"
  if (-not (Test-Path -LiteralPath $OpenAvatarChatDir)) {
    Write-Host "external/OpenAvatarChat is missing."
    return
  }
  if (Test-Path -LiteralPath $LocalUv) {
    Push-Location $OpenAvatarChatDir
    & $LocalUv python find 3.11
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
