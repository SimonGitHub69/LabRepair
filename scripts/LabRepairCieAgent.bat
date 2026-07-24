@echo off
setlocal
set "AGENT_DIR=%LOCALAPPDATA%\LabRepairCieAgent"
set "EXE=%AGENT_DIR%\cie_reader.exe"

if not exist "%EXE%" (
    echo Agent CIE non installato in %AGENT_DIR%
    echo Esegui install_cie_agent_client.ps1 oppure copia la cartella publish li'.
    pause
    exit /b 1
)

echo Avvio agent CIE su http://127.0.0.1:17345/
echo Lascia questa finestra aperta mentre usi LabRepair.
echo.
"%EXE%" --serve
exit /b %ERRORLEVEL%
