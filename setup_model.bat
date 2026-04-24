@echo off
setlocal
set REPO_DIR=%~dp0
set INSTALL_DIR=%LOCALAPPDATA%\pymasking
set RUNTIME_DIR=%INSTALL_DIR%\scripts\runtime
set PYTHON=%RUNTIME_DIR%\python.exe

echo ============================================================
echo  pymasking Setup
echo  Install directory: %INSTALL_DIR%
echo ============================================================

if /i not "%REPO_DIR:~0,-1%"=="%INSTALL_DIR%" (
    echo.
    echo [INFO] Copying files to %INSTALL_DIR%...
    if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
    robocopy "%REPO_DIR:~0,-1%" "%INSTALL_DIR%" /E /XD "%REPO_DIR:~0,-1%\scripts\runtime" /NFL /NDL /NJH /NJS >nul
    echo Copy complete. Continuing setup from %INSTALL_DIR%...
    echo.
    start "" /wait "%INSTALL_DIR%\setup_model.bat"
    exit /b 0
)

set NUMPY_LIBS=%RUNTIME_DIR%\Lib\site-packages\numpy\.libs
if not exist "%NUMPY_LIBS%" set NUMPY_LIBS=%RUNTIME_DIR%\Lib\site-packages\numpy\libs
set PATH=%RUNTIME_DIR%;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

echo.
echo [1/8] Preparing Python 3.12.10 embedded runtime...
if exist "%PYTHON%" (
    echo Using existing Python runtime: %PYTHON%
    goto :copy_dlls
)

set EMBED_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
set EMBED_ZIP=%TEMP%\python-3.12.10-embed-amd64.zip

echo Downloading: %EMBED_URL%
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%EMBED_URL%' -OutFile '%EMBED_ZIP%'"
if errorlevel 1 goto :error

echo Extracting to: %RUNTIME_DIR%
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
powershell -NoProfile -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%RUNTIME_DIR%' -Force"
if errorlevel 1 goto :error
del "%EMBED_ZIP%"

powershell -NoProfile -Command ^
  "(Get-Content '%RUNTIME_DIR%\python312._pth') -replace '#import site','import site' | Set-Content '%RUNTIME_DIR%\python312._pth'"
if errorlevel 1 goto :error

:copy_dlls
set VCRT_MISSING=0
for %%D in (msvcp140.dll vcruntime140.dll vcruntime140_1.dll) do (
    if not exist "%SystemRoot%\System32\%%D" set VCRT_MISSING=1
)
if %VCRT_MISSING%==1 (
    echo   Visual C++ Redistributable not found. Installing...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%TEMP%\vc_redist.x64.exe'"
    "%TEMP%\vc_redist.x64.exe" /install /quiet /norestart
    del /f /q "%TEMP%\vc_redist.x64.exe"
)
for %%D in (msvcp140.dll msvcp140_1.dll msvcp140_2.dll vcruntime140.dll vcruntime140_1.dll concrt140.dll) do (
    if exist "%SystemRoot%\System32\%%D" (
        copy /y "%SystemRoot%\System32\%%D" "%RUNTIME_DIR%\%%D" >nul 2>&1
    )
)
echo Python runtime ready: %RUNTIME_DIR%

:install_pip
powershell -NoProfile -Command ^
  "$p='%RUNTIME_DIR%\python312._pth'; if(Test-Path $p){$c=(Get-Content $p -Raw); if($c -notmatch 'import site'){$c+=[Environment]::NewLine+'import site'}; if($c -notmatch [regex]::Escape('%INSTALL_DIR%')){$c+=[Environment]::NewLine+'%INSTALL_DIR%'}; Set-Content $p $c.TrimEnd()}"
echo.
echo [2/8] Installing pip...
"%PYTHON%" -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo pip is already installed.
    goto :install_torch
)
set GETPIP=%TEMP%\get-pip.py
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'"
if errorlevel 1 goto :error
"%PYTHON%" "%GETPIP%" --no-warn-script-location
if errorlevel 1 goto :error
del "%GETPIP%"

:install_deps
echo.
echo [3/8] Installing dependencies...
"%PYTHON%" -m pip install --no-warn-script-location ^
  click flask python-docx openpyxl python-pptx ^
  Pillow PyMuPDF python-dateutil ^
  pyperclip chardet pywin32 pytesseract ^
  ja-ginza spacy
if errorlevel 1 goto :error

if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%

echo.
echo [4/8] Installing SudachiDict_full (high-accuracy dictionary, ~800MB)...
"%PYTHON%" -m pip install --no-warn-script-location sudachipy sudachidict_full
if errorlevel 1 goto :error

echo.
echo [5/8] Downloading JMnedict name data (~30MB, first run only)...
set PYTHONPATH=%INSTALL_DIR%
"%PYTHON%" "%INSTALL_DIR%\scripts\download_names.py"
if errorlevel 1 (
    echo [WARNING] Failed to download JMnedict data.
    echo          Running in GiNZA-only mode.
)

echo.
echo [6/8] Installing Tesseract OCR v5.5.0 with Japanese language data...
set TESSERACT_DIR=%INSTALL_DIR%\scripts\tesseract
set TESSERACT_EXE=%TESSERACT_DIR%\tesseract.exe
if exist "%TESSERACT_EXE%" (
    echo Tesseract already installed: %TESSERACT_EXE%
    goto :tesseract_done
)
set TESS_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe
set TESS_INSTALLER=%TEMP%\tesseract-setup.exe
echo Downloading Tesseract installer (~60MB)...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%TESS_URL%' -OutFile '%TESS_INSTALLER%'"
if errorlevel 1 (
    echo [WARNING] Failed to download Tesseract.
    echo          Please install manually from:
    echo          https://github.com/UB-Mannheim/tesseract/wiki
    echo          Install to: %TESSERACT_DIR%
    echo          Include jpn language data during installation.
    goto :tesseract_done
)
echo Installing Tesseract to %TESSERACT_DIR%...
"%TESS_INSTALLER%" /S /D=%TESSERACT_DIR%
del "%TESS_INSTALLER%" >nul 2>&1
if not exist "%TESSERACT_EXE%" (
    echo [WARNING] Tesseract installation failed.
    goto :tesseract_done
)
echo Downloading Japanese language data...
set TESSDATA_DIR=%TESSERACT_DIR%\tessdata
set TESSDATA_BASE=https://github.com/tesseract-ocr/tessdata/raw/main
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%TESSDATA_BASE%/jpn.traineddata' -OutFile '%TESSDATA_DIR%\jpn.traineddata'"
if errorlevel 1 echo [WARNING] Failed to download jpn.traineddata.
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%TESSDATA_BASE%/jpn_vert.traineddata' -OutFile '%TESSDATA_DIR%\jpn_vert.traineddata'"
if errorlevel 1 echo [WARNING] Failed to download jpn_vert.traineddata.
if not exist "%TESSDATA_DIR%\script" mkdir "%TESSDATA_DIR%\script"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%TESSDATA_BASE%/script/Japanese.traineddata' -OutFile '%TESSDATA_DIR%\script\Japanese.traineddata'"
if errorlevel 1 echo [WARNING] Failed to download script/Japanese.traineddata.
echo Tesseract installed: %TESSERACT_EXE%
:tesseract_done

echo.
echo [7/8] Removing obsolete surya-ocr models (if any)...
set OLD_MODEL_CACHE=%INSTALL_DIR%\data\models\hf_cache
if exist "%OLD_MODEL_CACHE%" (
    echo   Removing %OLD_MODEL_CACHE% ...
    rmdir /s /q "%OLD_MODEL_CACHE%"
)

echo.
echo [8/8] Removing obsolete surya-ocr package (if installed)...
"%PYTHON%" -m pip uninstall -y surya-ocr torch >nul 2>&1

echo.
echo [Post-1] Generating favicon.ico...
set FAVICON_PNG=%INSTALL_DIR%\pymasking\web\static\favicon.png
set FAVICON_ICO=%INSTALL_DIR%\pymasking\web\static\favicon.ico
if exist "%FAVICON_PNG%" (
    "%PYTHON%" -c "from PIL import Image; img=Image.open(r'%FAVICON_PNG%'); img.save(r'%FAVICON_ICO%', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])" >nul 2>&1
)

echo.
echo [Post-2] Creating desktop shortcut...
set LNK=%USERPROFILE%\Desktop\pymasking.lnk
powershell -NoProfile -Command ^
  "$s=New-Object -Com WScript.Shell; $sc=$s.CreateShortcut('%LNK%'); $sc.TargetPath='%INSTALL_DIR%\start_web.bat'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.IconLocation='%INSTALL_DIR%\pymasking\web\static\favicon.ico,0'; $sc.Description='pymasking Web UI'; $sc.Save()"
if errorlevel 1 (
    echo [WARNING] Failed to create desktop shortcut.
) else (
    echo Created pymasking.lnk on desktop.
)

echo.
echo [Post-3] Removing temporary files...
if exist "%INSTALL_DIR%\scripts\download_names.py"        del /f /q "%INSTALL_DIR%\scripts\download_names.py"
if exist "%INSTALL_DIR%\scripts\download_surya_models.py" del /f /q "%INSTALL_DIR%\scripts\download_surya_models.py"
if exist "%INSTALL_DIR%\data\JMnedict.xml.gz"             del /f /q "%INSTALL_DIR%\data\JMnedict.xml.gz"

echo.
echo ============================================================
echo  Setup Complete
echo  Install directory : %INSTALL_DIR%
echo  GiNZA model       : scripts\runtime\Lib\site-packages\ja_ginza
echo  Tesseract OCR     : %INSTALL_DIR%\scripts\tesseract\tesseract.exe
echo  Desktop           : pymasking.lnk (Web UI shortcut)
echo  mask.bat          : Mask file or clipboard
echo  unmask.bat        : Unmask file or clipboard
echo  start_web.bat     : Launch Web UI
echo ============================================================
pause
exit /b 0

:error
echo.
echo An error occurred.
pause
exit /b 1
