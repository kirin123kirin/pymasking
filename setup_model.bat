@echo off
setlocal
set REPO_DIR=%~dp0
set INSTALL_DIR=%LOCALAPPDATA%\pymasking
set RUNTIME_DIR=%INSTALL_DIR%\scripts\runtime
set PYTHON=%RUNTIME_DIR%\python.exe

echo ============================================================
echo  pymasking セットアップ
echo  インストール先: %INSTALL_DIR%
echo ============================================================

rem ── インストール先の確認 ──────────────────────────────────────
if /i not "%REPO_DIR:~0,-1%"=="%INSTALL_DIR%" (
    echo.
    echo [警告] このフォルダを以下の場所に展開して実行してください:
    echo        %INSTALL_DIR%
    echo.
    echo        現在の場所: %REPO_DIR%
    echo        このまま続行しますか？ 続行する場合は何かキーを押してください。
    pause >nul
)

rem ── [1/7] Python 3.12.10 embedded ────────────────────────────
echo.
echo [1/7] Python 3.12.10 embedded ランタイムを準備中...
if exist "%PYTHON%" (
    echo 既存の Python runtime を使用します: %PYTHON%
    goto :install_pip
)

set EMBED_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
set EMBED_ZIP=%TEMP%\python-3.12.10-embed-amd64.zip

echo ダウンロード中: %EMBED_URL%
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%EMBED_URL%' -OutFile '%EMBED_ZIP%'"
if errorlevel 1 goto :error

echo 解凍中: %RUNTIME_DIR%
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
powershell -NoProfile -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%RUNTIME_DIR%' -Force"
if errorlevel 1 goto :error
del "%EMBED_ZIP%"

rem site-packages を有効化（#import site のコメントアウトを解除）
powershell -NoProfile -Command ^
  "(Get-Content '%RUNTIME_DIR%\python312._pth') -replace '#import site','import site' | Set-Content '%RUNTIME_DIR%\python312._pth'"
if errorlevel 1 goto :error
echo Python runtime 準備完了: %RUNTIME_DIR%

:install_pip
rem ── [2/7] pip ─────────────────────────────────────────────────
echo.
echo [2/7] pip をインストール中...
"%PYTHON%" -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo pip は既にインストール済みです。
    goto :install_deps
)
set GETPIP=%TEMP%\get-pip.py
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'"
if errorlevel 1 goto :error
"%PYTHON%" "%GETPIP%" --no-warn-script-location
if errorlevel 1 goto :error
del "%GETPIP%"

:install_deps
rem ── [3/7] 依存パッケージ ──────────────────────────────────────
echo.
echo [3/7] 依存パッケージをインストール中...
"%PYTHON%" -m pip install --no-warn-script-location ^
  click flask python-docx openpyxl python-pptx ^
  Pillow PyMuPDF pytesseract python-dateutil ^
  pyperclip chardet pywin32
if errorlevel 1 goto :error

rem ── [4/7] spaCy / ja-ginza ────────────────────────────────────
echo.
echo [4/7] spaCy / ja-ginza をインストール中...
"%PYTHON%" -m pip install --no-warn-script-location ja-ginza spacy
if errorlevel 1 goto :error

rem ── [5/7] SudachiDict_full ────────────────────────────────────
echo.
echo [5/7] SudachiDict_full をインストール中（高精度辞書 約800MB）...
"%PYTHON%" -m pip install --no-warn-script-location sudachidict_full
if errorlevel 1 (
    echo [警告] sudachidict_full のインストールに失敗しました。
    echo        標準辞書（sudachidict_core）で動作します。
)

rem ── [6/7] GiNZA モデルをコピー ───────────────────────────────
echo.
echo [6/7] GiNZA モデルをリポジトリ内にコピー中...
set PYTHONPATH=%INSTALL_DIR%
"%PYTHON%" "%REPO_DIR%scripts\download_model.py"
if errorlevel 1 goto :error

rem ── [7/7] JMnedict 姓名データ ────────────────────────────────
echo.
echo [7/7] JMnedict 姓名データを取得中（約30MB、初回のみ）...
"%PYTHON%" "%REPO_DIR%scripts\download_names.py"
if errorlevel 1 (
    echo [警告] JMnedict の取得に失敗しました。
    echo        GiNZA 単体モードで動作します。
)

rem ── favicon.ico 生成 ──────────────────────────────────────────
echo.
echo [後処理1] favicon.ico を生成中...
set FAVICON_PNG=%INSTALL_DIR%\pymasking\web\static\favicon.png
set FAVICON_ICO=%INSTALL_DIR%\pymasking\web\static\favicon.ico
if exist "%FAVICON_PNG%" (
    "%PYTHON%" -c "from PIL import Image; img=Image.open(r'%FAVICON_PNG%'); img.save(r'%FAVICON_ICO%', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])" >nul 2>&1
)

rem ── デスクトップにショートカット作成（1回のみ） ──────────────
echo.
echo [後処理2] デスクトップにショートカットを作成中...
set LNK=%USERPROFILE%\Desktop\pymasking.lnk
powershell -NoProfile -Command ^
  "$s=New-Object -Com WScript.Shell; $sc=$s.CreateShortcut('%LNK%'); $sc.TargetPath='%INSTALL_DIR%\start_web.bat'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.IconLocation='%INSTALL_DIR%\pymasking\web\static\favicon.ico,0'; $sc.Description='pymasking Web UI'; $sc.Save()"
if errorlevel 1 (
    echo [警告] ショートカットの作成に失敗しました。
) else (
    echo デスクトップに pymasking.lnk を作成しました。
)

rem ── 不要ファイルを削除 ────────────────────────────────────────
echo.
echo [後処理3] 不要ファイルを削除中...
if exist "%INSTALL_DIR%\scripts\download_model.py"  del /f /q "%INSTALL_DIR%\scripts\download_model.py"
if exist "%INSTALL_DIR%\scripts\download_names.py"  del /f /q "%INSTALL_DIR%\scripts\download_names.py"
if exist "%INSTALL_DIR%\data\JMnedict.xml.gz"        del /f /q "%INSTALL_DIR%\data\JMnedict.xml.gz"
if exist "%INSTALL_DIR%\pyproject.toml"              del /f /q "%INSTALL_DIR%\pyproject.toml"

echo.
echo ============================================================
echo  セットアップ完了
echo  インストール先   : %INSTALL_DIR%
echo  GINZA モデル     : %INSTALL_DIR%\data\models\ja_ginza
echo  デスクトップ     : pymasking.lnk（Web UI ショートカット）
echo  start_cli.bat    : CLI 起動
echo  start_web.bat    : Web UI 起動
echo ============================================================
pause
exit /b 0

:error
echo.
echo エラーが発生しました。
pause
exit /b 1
