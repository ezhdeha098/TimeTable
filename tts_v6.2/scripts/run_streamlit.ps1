<#
PowerShell helper script to create a virtual environment, install requirements, and run the Streamlit app.

You can run this from anywhere; it will switch to the repository root automatically.

Examples:
  # From repo root
  & .\scripts\run_streamlit.ps1

  # From scripts folder
  & .\run_streamlit.ps1
#>

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

# Resolve repository root (parent of this script's folder)
$repoRoot = Split-Path -Path $PSScriptRoot -Parent
Set-Location $repoRoot

$venvPath = Join-Path $repoRoot ".venv"
$reqFile = Join-Path $repoRoot "requirements.txt"
$appFile = Join-Path $repoRoot "app.py"

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath..."
    # Prefer 'py -3' if py launcher exists; else fall back to 'python'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venvPath
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $venvPath
    } else {
        throw "Python not found. Install Python 3 and ensure 'python' or 'py' is on PATH."
    }
}

# Use venv Python/pip explicitly to avoid PATH issues
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$venvPip = "$venvPython"  # use python -m pip for reliability

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found at $venvPython"
}

if (Test-Path $reqFile) {
    Write-Host "Installing requirements from $reqFile (this may take a minute)..."
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r $reqFile
} else {
    Write-Host "requirements.txt not found at $reqFile. Skipping dependency install."
}

if (-not (Test-Path $appFile)) {
    throw "app.py not found at $appFile"
}

Write-Host "Launching Streamlit app (app.py)..."
& $venvPython -m streamlit run $appFile
