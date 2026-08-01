$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$lambdaRoot = Join-Path $root "lambda_tools"
$distRoot = Join-Path $lambdaRoot "dist"
$buildRoot = Join-Path $lambdaRoot ".lambda_build"

if (-not (Test-Path $lambdaRoot)) {
    throw "lambda_tools folder not found: $lambdaRoot"
}

$excluded = @(
    "shared_lambda",
    "dist",
    ".lambda_build",
    "tests",
    "tool_schemas",
    "__pycache__",
    ".pytest_cache"
)

$functionDirs = Get-ChildItem -Path $lambdaRoot -Directory |
    Where-Object { $excluded -notcontains $_.Name }

if (-not $functionDirs) {
    throw "No Lambda function folders found under $lambdaRoot"
}

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null

if (Test-Path $buildRoot) {
    Remove-Item -Recurse -Force $buildRoot
}
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

foreach ($dir in $functionDirs) {
    $stage = Join-Path $buildRoot $dir.Name
    $zipPath = Join-Path $distRoot "$($dir.Name).zip"

    New-Item -ItemType Directory -Force -Path $stage | Out-Null

    Copy-Item -Path (Join-Path $dir.FullName "*") -Destination $stage -Recurse -Force

    $shared = Join-Path $lambdaRoot "shared_lambda"
    if (Test-Path $shared) {
        Copy-Item -Path $shared -Destination (Join-Path $stage "shared_lambda") -Recurse -Force
    }

    Get-ChildItem -Path $stage -Recurse -Directory -Force |
        Where-Object { $_.Name -in @("__pycache__", ".pytest_cache") } |
        Remove-Item -Recurse -Force

    Get-ChildItem -Path $stage -Recurse -File -Force |
        Where-Object { $_.Name -like "*.pyc" -or $_.Name -eq ".env" } |
        Remove-Item -Force

    if (Test-Path $zipPath) {
        Remove-Item -Force $zipPath
    }

    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
    Write-Host "Created $zipPath"
}

Remove-Item -Recurse -Force $buildRoot
Write-Host "Done. Zip files are in $distRoot"
