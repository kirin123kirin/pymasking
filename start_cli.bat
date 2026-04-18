@echo off
setlocal
set REPO_DIR=%~dp0
set PYTHON=%REPO_DIR%scripts\runtime\python.exe
set GINZA_MODEL_PATH=%REPO_DIR%data\models\ja_ginza
set PYTHONPATH=%REPO_DIR%

rem DLL 探索パス：runtime 本体と numpy の .libs を先頭に追加
set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\.libs
set PATH=%REPO_DIR%scripts\runtime;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

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

"%PYTHON%" -m pymasking.cli.main %*
