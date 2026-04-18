@echo off
setlocal
set REPO_DIR=%~dp0
set PYTHON=%REPO_DIR%scripts\runtime\python.exe
set GINZA_MODEL_PATH=%REPO_DIR%data\models\ja_ginza
set PYTHONPATH=%REPO_DIR%

if not exist "%PYTHON%" (
    echo [エラー] Python runtime が見つかりません: %PYTHON%
    echo         setup_model.bat を先に実行してください。
    pause
    exit /b 1
)

if not exist "%GINZA_MODEL_PATH%\meta.json" (
    echo [警告] モデルが見つかりません: %GINZA_MODEL_PATH%
    echo        setup_model.bat を先に実行してください。
    echo        GiNZA なしのフォールバックモードで動作します。
    echo.
)

set PORT=59631
if not "%1"=="" set PORT=%1

echo Web UI を起動します: http://127.0.0.1:%PORT%
echo 停止するには Ctrl+C を押してください。
echo.

"%PYTHON%" -m pymasking.cli.main web --port %PORT%
