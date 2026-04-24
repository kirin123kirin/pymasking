@echo off
setlocal
set REPO_DIR=%~dp0
set PYTHON=%REPO_DIR%scripts\runtime\python.exe
set PYTHONPATH=%REPO_DIR%

set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\.libs
if not exist "%NUMPY_LIBS%" set NUMPY_LIBS=%REPO_DIR%scripts\runtime\Lib\site-packages\numpy\libs
set PYMUPDF_DIR=%REPO_DIR%scripts\runtime\Lib\site-packages\pymupdf
set TESSERACT_DIR=%REPO_DIR%scripts\tesseract
if exist "%TESSERACT_DIR%\tessdata" set TESSDATA_PREFIX=%TESSERACT_DIR%\tessdata
set PATH=%REPO_DIR%scripts\runtime;%PATH%
if exist "%NUMPY_LIBS%" set PATH=%NUMPY_LIBS%;%PATH%
if exist "%PYMUPDF_DIR%" set PATH=%PYMUPDF_DIR%;%PATH%
if exist "%TESSERACT_DIR%" set PATH=%TESSERACT_DIR%;%PATH%

if not exist "%PYTHON%" (
    echo [ERROR] Python runtime not found: %PYTHON%
    echo         Please run setup_model.bat first.
    pause
    exit /b 1
)

cd /d "%REPO_DIR%"
"%PYTHON%" -m pymasking.cli.main mask %*
