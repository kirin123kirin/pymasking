@echo off
setlocal
set REPO_DIR=%~dp0
set PYTHON=%REPO_DIR%scripts\runtime\python.exe
set GINZA_MODEL_PATH=%REPO_DIR%data\models\ja_ginza
set MODEL_CACHE_DIR=%REPO_DIR%data\models\hf_cache
set PYTHONPATH=%REPO_DIR%

set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\.libs
if not exist "%NUMPY_LIBS%" set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\libs
set PYMUPDF_DIR=%REPO_DIR%scripts\runtime\Lib\site-packages\pymupdf
set PATH=%REPO_DIR%scripts\runtime;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%
if exist "%PYMUPDF_DIR%" set PATH=%PYMUPDF_DIR%;%PATH%

if not exist "%PYTHON%" (
    echo [ERROR] Python runtime not found: %PYTHON%
    echo         Please run setup_model.bat first.
    pause
    exit /b 1
)

if not exist "%GINZA_MODEL_PATH%\meta.json" (
    echo [WARNING] GiNZA model not found: %GINZA_MODEL_PATH%
    echo          Please run setup_model.bat first.
    echo          Running in fallback mode ^(without GiNZA^).
    echo(
)

set PORT=59631
if not "%1"=="" set PORT=%1

echo Starting Web UI: http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.

cd /d "%REPO_DIR%"
"%PYTHON%" -m pymasking.cli.main web --port %PORT%
exit /b 0
