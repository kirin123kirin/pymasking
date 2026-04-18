@echo off
setlocal
set REPO_DIR=%~dp0
set PYTHON=%REPO_DIR%scripts\runtime\python.exe
set GINZA_MODEL_PATH=%REPO_DIR%data\models\ja_ginza
set PYTHONPATH=%REPO_DIR%

set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\.libs
set PATH=%REPO_DIR%scripts\runtime;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

if not exist "%PYTHON%" (
    echo [ERROR] Python runtime not found: %PYTHON%
    echo         Please run setup_model.bat first.
    pause
    exit /b 1
)

if not exist "%GINZA_MODEL_PATH%\meta.json" (
    echo [WARNING] GiNZA model not found: %GINZA_MODEL_PATH%
    echo          Please run setup_model.bat first.
    echo          Running in fallback mode (without GiNZA).
    echo.
)

"%PYTHON%" -m pymasking.cli.main %*
