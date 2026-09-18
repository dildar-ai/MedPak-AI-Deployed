# MedPak AI - Deploy backend to a Hugging Face Docker Space
#
# Prerequisites:
#   1. Create the Space first: https://huggingface.co/new-space
#      Name: medpak-ai-backend | SDK: Docker | Public
#   2. Have an HF write token ready: https://huggingface.co/settings/tokens
#      (git will ask for it as the password; username = your HF username)
#
# Usage (from the backend\ folder):
#   .\deploy_to_hf.ps1 -HfUser <your-hf-username> -SpaceName medpak-ai-backend

param(
    [Parameter(Mandatory = $true)][string]$HfUser,
    [Parameter(Mandatory = $true)][string]$SpaceName
)

$ErrorActionPreference = "Stop"
$HfUser = $HfUser.ToLower()
$SpaceName = $SpaceName.ToLower()

$spaceUrl = "https://huggingface.co/spaces/$HfUser/$SpaceName"
$appUrl = "https://$HfUser-$SpaceName.hf.space"

if (-not (Test-Path ".\main.py")) { throw "Run this script from the backend\ folder." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Install git first: https://git-scm.com" }
git lfs version *> $null
if ($LASTEXITCODE -ne 0) { throw "Install Git LFS first: https://git-lfs.com" }

Write-Host "Deploying MedPak AI backend to: $spaceUrl" -ForegroundColor Cyan

$tmp = Join-Path $env:TEMP "medpak_hf_deploy"

if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
git clone $spaceUrl $tmp
if ($LASTEXITCODE -ne 0) {
    throw "Clone failed. Create the Space first at https://huggingface.co/new-space (SDK: Docker, Public)."
}

# Copy backend files - exclude secrets, caches, private user data and local
# runtime state (the app recreates empty DBs on first boot):
#   users.db      : real emails + password hashes - NEVER leave this machine
#   live_prices.db / history.db : runtime caches
#   chroma_store  : RAG index - rebuilt automatically in the background on boot
robocopy . $tmp /E /XD __pycache__ venv .venv .git chroma_store /XF .env *.pyc *.log history.db users.db live_prices.db *.db-wal *.db-shm deploy_to_hf.ps1 | Out-Null

Push-Location $tmp
try {
    git config user.name $HfUser
    git config user.email "$HfUser@users.noreply.huggingface.co"
    # pharmapedia.db (15 MB) exceeds HF's 10 MB plain-git limit - track *.db
    # with Git LFS (Hugging Face fully supports LFS in Spaces).
    git lfs install
    "*.db filter=lfs diff=lfs merge=lfs -text" | Out-File -FilePath .gitattributes -Encoding ascii
    git add -A
    # dvago_products.txt is gitignored locally but wanted in the image (warm price index)
    git add -f scrapers/dvago_products.txt 2>$null
    git commit -m "MedPak AI backend deploy"
    git push
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Push failed - when prompted: username = $HfUser, password = HF write token." -ForegroundColor Yellow
        Write-Host "Retry manually:  cd $tmp ;  git push"
        exit 1
    }
} finally {
    Pop-Location
}

Remove-Item -Recurse -Force $tmp

Write-Host ""
Write-Host "Deployed! First build takes ~8-15 min (installs PyTorch CPU + EasyOCR)." -ForegroundColor Green
Write-Host "  Space:  $spaceUrl"
Write-Host "  API:    $appUrl/api/health"
Write-Host ""
Write-Host "Next: add these secrets in Space Settings -> Variables and secrets:" -ForegroundColor Cyan
Write-Host "  GROQ_API_KEY = gsk_...      (https://console.groq.com/keys)"
Write-Host "  SECRET_KEY   = <long random string>"
Write-Host "  CORS_ORIGINS = [`"*`"]"
Write-Host "  DEBUG        = false"
