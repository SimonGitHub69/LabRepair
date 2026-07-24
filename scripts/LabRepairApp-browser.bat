@echo off
REM LabRepair - modalita' browser completa (se l'App non mostra il login)
set "ORIGIN=http://192.168.200.30:8000"
set "LOGIN=http://192.168.200.30:8000/login/?app=1&pc=%COMPUTERNAME%"
set "PROFILE=%LOCALAPPDATA%\LabRepairApp"
set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER (echo Browser non trovato & pause & exit /b 1)
if not exist "%PROFILE%" mkdir "%PROFILE%"
start "" "%BROWSER%" --user-data-dir="%PROFILE%" --unsafely-treat-insecure-origin-as-secure=%ORIGIN% --test-type --disable-features=InsecureDownloadWarnings "%LOGIN%"
exit /b 0
