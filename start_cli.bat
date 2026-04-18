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

rem ── CLI 実行（引数をそのまま渡す） ───────────────────────────
pymasking %*
