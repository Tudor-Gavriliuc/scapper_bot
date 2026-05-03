Param(
    [string]$ProjectPath = "D:\Scrapper\promo-scraper-bot",
    [string]$OutZip = "D:\Scrapper\promo-scraper-bot-deploy.zip"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $ProjectPath)) {
    throw "Project path not found: $ProjectPath"
}

if (Test-Path $OutZip) {
    Remove-Item $OutZip -Force
}

$excludeDirs = @(
    ".venv",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules"
)

$excludeFiles = @(
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.db-shm",
    "*.db-wal"
)

$tempDir = Join-Path $env:TEMP ("promo-scraper-bot-deploy-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    $staging = Join-Path $tempDir "promo-scraper-bot"
    New-Item -ItemType Directory -Path $staging | Out-Null

    Get-ChildItem -Path $ProjectPath -Force | ForEach-Object {
        $name = $_.Name

        if ($excludeDirs -contains $name) {
            return
        }

        $skipFile = $false
        if ($_.PSIsContainer -eq $false) {
            foreach ($pattern in $excludeFiles) {
                if ($name -like $pattern) {
                    $skipFile = $true
                    break
                }
            }
        }

        if ($skipFile) {
            return
        }

        Copy-Item -Path $_.FullName -Destination (Join-Path $staging $name) -Recurse -Force
    }

    Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $OutZip -Force
    Write-Host "Bundle created: $OutZip"
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
}
