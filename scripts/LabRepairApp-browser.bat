@echo off
REM LabRepair - modalita' browser completa (se l'App non mostra il login)
set "ORIGIN=http://192.168.200.30:8000"
if exist "%~dp0origin.txt" set /p ORIGIN=<"%~dp0origin.txt"
if "%ORIGIN:~-1%"=="/" set "ORIGIN=%ORIGIN:~0,-1%"
set "LOGIN=%ORIGIN%/login/?app=1&pc=%COMPUTERNAME%"
set "PROFILE=%LOCALAPPDATA%\LabRepairApp"
set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER (echo Browser non trovato & pause & exit /b 1)
if not exist "%PROFILE%" mkdir "%PROFILE%"
reg add "HKCU\Software\Policies\Google\Chrome\OverrideSecurityRestrictionsOnInsecureOrigin" /v 1 /t REG_SZ /d "%ORIGIN%" /f >nul 2>&1
reg add "HKCU\Software\Policies\Microsoft\Edge\OverrideSecurityRestrictionsOnInsecureOrigin" /v 1 /t REG_SZ /d "%ORIGIN%" /f >nul 2>&1
start "" "%BROWSER%" --user-data-dir="%PROFILE%" --unsafely-treat-insecure-origin-as-secure=%ORIGIN% --test-type --disable-features=InsecureDownloadWarnings,HttpsFirstBalancedModeAutoEnable,HttpsUpgrades,HttpsFirstModeV2 "%LOGIN%"
exit /b 0
