@echo off
setlocal EnableDelayedExpansion

set "RUNTIME=%~dp0"
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

set "USER_PATH="
for /f "skip=2 delims=" %%L in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "LINE=%%L"
    for /f "tokens=3*" %%A in ("!LINE!") do set "USER_PATH=%%A %%B"
)
for /l %%i in (1,1,5) do if defined USER_PATH (if "!USER_PATH:~-1!"==" " set "USER_PATH=!USER_PATH:~0,-1!")

echo [1/4] Checking PATH for runtime folder...
call :add_to_path "%RUNTIME%"

set "USER_PATH="
for /f "skip=2 delims=" %%L in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "LINE=%%L"
    for /f "tokens=3*" %%A in ("!LINE!") do set "USER_PATH=%%A %%B"
)
for /l %%i in (1,1,5) do if defined USER_PATH (if "!USER_PATH:~-1!"==" " set "USER_PATH=!USER_PATH:~0,-1!")

echo [2/4] Checking PATH for Scripts folder...
call :add_to_path "%SCRIPTS%"
echo.

echo [3/4] Copying batch files to Scripts folder...
if not exist "%SCRIPTS%\" mkdir "%SCRIPTS%"
for %%F in ("%~dp0scripts\mask.bat" "%~dp0scripts\masking.bat" "%~dp0scripts\masking-download.bat") do (
    copy /y "%%F" "%SCRIPTS%\" >nul
    if errorlevel 1 (echo [Error] Failed to copy %%~nxF) else (echo [OK] %%~nxF)
)
echo.

echo [4/4] Copying masking.bat to Desktop...
set "DESKTOP=%USERPROFILE%\Desktop"
if not exist "%DESKTOP%\" set "DESKTOP=%USERPROFILE%\デスクトップ"
copy /y "%LOCALAPPDATA%\Program\python\Scripts\masking.bat" "%DESKTOP%\masking.bat" >nul
if errorlevel 1 (echo [Error] Failed to copy masking.bat to Desktop.) else (echo [OK] masking.bat copied to Desktop.)

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
echo ;!USER_PATH!; | findstr /i /c:";%ADD_PATH%;" >nul 2>&1
if not errorlevel 1 (echo [PATH] Already registered: %ADD_PATH% & exit /b 0)
echo [PATH] Adding: %ADD_PATH%
if defined USER_PATH (setx PATH "!USER_PATH!;%ADD_PATH%") else (setx PATH "%ADD_PATH%")
set "PATH=%PATH%;%ADD_PATH%"
exit /b 0
