param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Checking Canri AI Git status..."

$status = git status --porcelain

if (-not $status) {
    Write-Host "No changes to push. Canri AI is already synced."
    exit 0
}

if (-not $Message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Message = "Update Canri AI - $timestamp"
}

Write-Host "Adding changes..."
git add .

Write-Host "Creating commit: $Message"
git commit -m "$Message"

Write-Host "Pushing to GitHub..."
git push

Write-Host "Done. Canri AI was pushed to GitHub."
