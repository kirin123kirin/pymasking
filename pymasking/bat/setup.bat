@echo off
setlocal EnableDelayedExpansion

for /f "delims=" %%R in ("%~dp0..\..\..\..\") do set "RUNTIME=%%~fR"
if "%RUNTIME:~-1%"=="\" set "RUNTIME=%RUNTIME:~0,-1%"
set "SCRIPTS=%RUNTIME%\Scripts"
set "PYTHON=%RUNTIME%\python.exe"

if not exist "%PYTHON%" (
    echo [Error] python.exe not found: %PYTHON%
    pause & exit /b 1
)

echo ========================================
echo  pymasking Setup
echo ========================================
echo Python  : %PYTHON%
echo Scripts : %SCRIPTS%
echo.

echo [1/3] Checking PATH for runtime folder...
call :add_to_path "%RUNTIME%"

echo [2/3] Checking PATH for Scripts folder...
call :add_to_path "%SCRIPTS%"
echo.

echo [3/3] Copying batch files to Scripts folder...
if not exist "%SCRIPTS%\" mkdir "%SCRIPTS%"
for %%F in ("%~dp0mask.bat" "%~dp0masking.bat" "%~dp0masking-download.bat" "%~dp0masking.lnk") do (
    copy /y "%%F" "%SCRIPTS%\" >nul
    if errorlevel 1 (echo [Error] Failed to copy %%~nxF) else (echo [OK] %%~nxF)
)
echo.

echo ========================================
echo  Setup complete!
echo  Open a new command prompt and run:
echo    masking.bat
echo ========================================
pause
exit /b 0

:add_to_path
set "ADD_PATH=%~1"
echo ;%PATH%; | findstr /i /c:";%ADD_PATH%;" >nul 2>&1
if not errorlevel 1 (echo [PATH] Already in PATH: %ADD_PATH% & exit /b 0)
echo [PATH] Adding: %ADD_PATH%
set "REG_PATH="
for /f "skip=2 delims=" %%L in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "LINE=%%L"
    for /f "tokens=3*" %%A in ("!LINE!") do set "REG_PATH=%%A %%B"
)
for /l %%i in (1,1,5) do if defined REG_PATH (if "!REG_PATH:~-1!"==" " set "REG_PATH=!REG_PATH:~0,-1!")
if defined REG_PATH (setx PATH "!REG_PATH!;%ADD_PATH%") else (setx PATH "%ADD_PATH%")
set "PATH=%PATH%;%ADD_PATH%"
exit /b 0
