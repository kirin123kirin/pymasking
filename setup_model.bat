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

rem ── 展開先が違う場合は INSTALL_DIR にコピーして再起動 ─────────
if /i not "%REPO_DIR:~0,-1%"=="%INSTALL_DIR%" (
    echo.
    echo [情報] ファイルを %INSTALL_DIR% にコピー中...
    if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
    robocopy "%REPO_DIR:~0,-1%" "%INSTALL_DIR%" /E /XD "%REPO_DIR:~0,-1%\scripts\runtime" /NFL /NDL /NJH /NJS >nul
    echo コピー完了。%INSTALL_DIR% からセットアップを続行します...
    echo.
    start "" /wait "%INSTALL_DIR%\setup_model.bat"
    exit /b 0
)

rem ── DLL 探索パスを事前設定 ────────────────────────────────────
rem  embedded Python の .pyd ファイルが numpy/.libs の DLL を見つけられるよう
rem  RUNTIME_DIR と numpy .libs を PATH の先頭に追加する
set NUMPY_LIBS=%RUNTIME_DIR%\Lib\site-packages\numpy\.libs
set PATH=%RUNTIME_DIR%;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

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

rem VC++ ランタイム DLL をコピー（DLL load 対策）
for %%D in (msvcp140.dll vcruntime140.dll vcruntime140_1.dll concrt140.dll) do (
    if exist "%SystemRoot%\System32\%%D" (
        copy /y "%SystemRoot%\System32\%%D" "%RUNTIME_DIR%\%%D" >nul 2>&1
    )
)
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

rem numpy .libs が生成されたら PATH に追加
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

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
"%PYTHON%" "%INSTALL_DIR%\scripts\download_model.py"
if errorlevel 1 goto :error

rem ── [7/7] JMnedict 姓名データ ────────────────────────────────
echo.
echo [7/7] JMnedict 姓名データを取得中（約30MB、初回のみ）...
"%PYTHON%" "%INSTALL_DIR%\scripts\download_names.py"
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
