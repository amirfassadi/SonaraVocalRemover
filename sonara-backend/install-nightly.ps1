<#
Run this script to install heavy Python dependencies during off-hours.
It installs the full `requirements.txt` using the project's venv.
Schedule it with Windows Task Scheduler to run at night (e.g., 02:00).
#>

Set-Location -Path "$PSScriptRoot"
if (-not (Test-Path '.venv')) {
    python -m venv .venv
}

Write-Output "Activating venv and installing full requirements..."
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

Write-Output "Installation complete."
