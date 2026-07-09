param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Stop-IfGitFailed {
    param(
        [string]$StepName
    )

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Git failed during: $StepName" -ForegroundColor Red
        Write-Host "The project was NOT pushed to GitHub." -ForegroundColor Red
        Write-Host ""
        Write-Host "If the error mentions Git LFS or disk space, free more space on drive C: and run this script again." -ForegroundColor Yellow
        Write-Host "If Git says authentication failed, sign in to GitHub from VS Code or Git Credential Manager." -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if (-not $Message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Message = "Update Canri AI - $timestamp"
}

Write-Host "Checking Canri AI Git status..."
$status = git status --porcelain
Stop-IfGitFailed "git status"

if (-not $status) {
    Write-Host "No changes to push. Canri AI is already synced." -ForegroundColor Green
    exit 0
}

Write-Host "Adding changed files..."
git add .
Stop-IfGitFailed "git add"

Write-Host "Creating commit..."
git commit -m "$Message"
Stop-IfGitFailed "git commit"

Write-Host "Pushing to GitHub..."
git push
Stop-IfGitFailed "git push"

Write-Host ""
Write-Host "Canri AI was pushed to GitHub successfully." -ForegroundColor Green
