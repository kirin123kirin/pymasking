@echo off
setlocal
set REPO_DIR=%~dp0

rem ── GiNZA モデルをリポジトリ内から参照 ──────────────────────
set GINZA_MODEL_PATH=%REPO_DIR%models\ja_ginza

rem ── モデルが未セットアップの場合は警告 ───────────────────────
if not exist "%GINZA_MODEL_PATH%\meta.json" (
    echo [警告] モデルが見つかりません: %GINZA_MODEL_PATH%
    echo        setup_model.bat を先に実行してください。
    echo        GiNZA なしのフォールバックモードで動作します。
    echo.
)

rem ── Web サーバー起動 ──────────────────────────────────────────
set PORT=5000
if not "%1"=="" set PORT=%1

echo Web UI を起動します: http://127.0.0.1:%PORT%
echo 停止するには Ctrl+C を押してください。
echo.

pymasking web --port %PORT%
