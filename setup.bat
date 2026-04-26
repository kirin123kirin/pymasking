@echo off
:: ============================================================
:: setup.bat
::
:: Python runtime を展開・移設した後の初期セットアップ。
::   1. python.exe のフォルダ を ユーザー PATH に追加
::   2. Scripts フォルダ を ユーザー PATH に追加
::   3. entry point (.exe) を現在のパスで再構築
::
:: このファイルを Python runtime のルートフォルダに置き
:: ダブルクリックして実行してください。
:: ============================================================
setlocal EnableDelayedExpansion

:: ── パス設定 ─────────────────────────────────────────────────
set "RUNTIME=%~dp0"
if "%RUNTIME:~-1%"=="\" set "RUNTIME=%RUNTIME:~0,-1%"
set "SCRIPTS=%RUNTIME%\Scripts"
set "PYTHON=%RUNTIME%\python.exe"
set "REBUILD=%~dp0scripts\rebuild_entry_points.py"

:: ── 事前確認 ─────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [Error] python.exe が見つかりません: %PYTHON%
    echo このファイルを Python runtime のルートフォルダに置いてください。
    pause & exit /b 1
)
if not exist "%REBUILD%" (
    echo [Error] rebuild_entry_points.py が見つかりません: %REBUILD%
    pause & exit /b 1
)

echo ========================================
echo  pymasking セットアップ
echo ========================================
echo Python  : %PYTHON%
echo Scripts : %SCRIPTS%
echo.

:: ── ユーザー PATH をレジストリから取得 ──────────────────────
:: 出力例: "    PATH    REG_EXPAND_SZ    C:\foo;C:\bar"
set "USER_PATH="
for /f "skip=2 delims=" %%L in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "LINE=%%L"
    :: "REG_EXPAND_SZ    " または "REG_SZ    " より後ろを抽出
    for /f "tokens=3*" %%A in ("!LINE!") do set "USER_PATH=%%A %%B"
)
:: 末尾の余分なスペースを除去
if defined USER_PATH (
    set "USER_PATH=!USER_PATH: =!"
    :: 末尾スペース除去（トリム）
    for /l %%i in (1,1,5) do if "!USER_PATH:~-1!"==" " set "USER_PATH=!USER_PATH:~0,-1!"
)

:: ── RUNTIME を PATH に追加 ────────────────────────────────────
call :add_to_path "%RUNTIME%"

:: 追加後にレジストリを再取得（SCRIPTS 追加時に最新値を使うため）
set "USER_PATH="
for /f "skip=2 delims=" %%L in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "LINE=%%L"
    for /f "tokens=3*" %%A in ("!LINE!") do set "USER_PATH=%%A %%B"
)
for /l %%i in (1,1,5) do if defined USER_PATH (if "!USER_PATH:~-1!"==" " set "USER_PATH=!USER_PATH:~0,-1!")

:: ── SCRIPTS を PATH に追加 ────────────────────────────────────
call :add_to_path "%SCRIPTS%"

echo.

:: ── entry point 再構築 ────────────────────────────────────────
echo [3/3] entry point を再構築しています...
"%PYTHON%" "%REBUILD%"
if errorlevel 1 (
    echo.
    echo [Error] entry point の再構築に失敗しました。
    pause & exit /b 1
)

echo.
echo ========================================
echo  セットアップ完了！
echo  新しいコマンドプロンプトを開いて
echo  masking コマンドを実行してください。
echo ========================================
pause
exit /b 0


:: ============================================================
:: サブルーチン: PATH に追加（既存の場合はスキップ）
:: 引数 %1: 追加するパス（引用符付きで渡す）
:: ============================================================
:add_to_path
set "ADD_PATH=%~1"
set "STEP_NUM="

:: すでに含まれているか確認（大文字小文字無視）
echo ;!USER_PATH!; | findstr /i /c:";%ADD_PATH%;" >nul 2>&1
if not errorlevel 1 (
    echo [PATH済み] %ADD_PATH%
    exit /b 0
)

echo [PATH追加] %ADD_PATH%
if defined USER_PATH (
    setx PATH "!USER_PATH!;%ADD_PATH%"
) else (
    setx PATH "%ADD_PATH%"
)

:: 現在のセッションにも即時反映
set "PATH=%PATH%;%ADD_PATH%"
exit /b 0
