@echo off
if "%~1"=="" (
    echo Usage: mask FILE [--mode blackout^|unique]
    exit /b 1
)
"%~dp0..\python.exe" -m pymasking.cli.main mask %*
