<#
.SYNOPSIS
    Cross-platform PowerShell helper script for local CDC Kinesis pipeline operations.
.EXAMPLE
    .\run.ps1 up
    .\run.ps1 test
    .\run.ps1 seed
#>

param (
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("up", "down", "restart", "logs", "test", "lint", "seed", "package", "help")]
    [string]$Command
)

switch ($Command) {
    "up" {
        Write-Host "Starting PostgreSQL container with CDC logical replication..." -ForegroundColor Cyan
        docker compose up -d postgres
    }
    "down" {
        Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
        docker compose down
    }
    "restart" {
        Write-Host "Restarting Docker containers..." -ForegroundColor Yellow
        docker compose restart
    }
    "logs" {
        docker compose logs -f postgres
    }
    "test" {
        Write-Host "Running pytest unit tests..." -ForegroundColor Green
        python -m pytest tests -v
    }
    "lint" {
        Write-Host "Running ruff check..." -ForegroundColor Green
        python -m ruff check .
    }
    "seed" {
        Write-Host "Running synthetic CDC stream producer..." -ForegroundColor Cyan
        python scripts/stream_producer.py --count 10 --rate 2.0
    }
    "package" {
        Write-Host "Packaging Lambda source code..." -ForegroundColor Cyan
        if (-not (Test-Path "dist")) { New-Item -ItemType Directory -Path "dist" | Out-Null }
        Compress-Archive -Path "src\*" -DestinationPath "dist\lambda_transform.zip" -Force
        Write-Host "Package created at dist\lambda_transform.zip" -ForegroundColor Green
    }
    "help" {
        Write-Host "Commands: up, down, restart, logs, test, lint, seed, package" -ForegroundColor White
    }
}
