@echo off
:: ============================================================
:: rebuild_entry_points.bat
::
:: Python runtime を別の PC / 別フォルダに移動した後、
:: Scripts\ 配下の entry point (.exe) を再構築する。
::
:: 使い方:
::   ダブルクリック          → PyPI から再インストール（要ネット）
::   rebuild_entry_points.bat --wheel  → 同梱 wheel からオフライン再インストール
:: ============================================================
setlocal

:: このバッチファイルと同じフォルダを runtime root とみなす
set RUNTIME_ROOT=%~dp0

:: python.exe を探す（runtime root 直下、または Scripts\ 直下）
if exist "%RUNTIME_ROOT%python.exe" (
    set PYTHON="%RUNTIME_ROOT%python.exe"
    goto :found
)
if exist "%RUNTIME_ROOT%Scripts\python.exe" (
    set PYTHON="%RUNTIME_ROOT%Scripts\python.exe"
    goto :found
)

echo [Error] python.exe が見つかりません。
echo このバッチファイルを Python runtime のルートフォルダに置いてください。
pause
exit /b 1

:found
echo Python : %PYTHON%
echo.

%PYTHON% "%RUNTIME_ROOT%scripts\rebuild_entry_points.py" %*

echo.
if %errorlevel% equ 0 (
    echo [OK] entry point の再構築が完了しました。
) else (
    echo [Error] 再構築に失敗しました。
)
pause
