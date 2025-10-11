@echo off
REM Install RAG Email System as Windows Service using NSSM
REM Download NSSM from: https://nssm.cc/download

SET SERVICE_NAME=RAGEmailSystem
SET PYTHON_PATH=C:\Python\python.exe
SET SCRIPT_PATH=%~dp0..\daemon_runner.py
SET WORKING_DIR=%~dp0..

echo Installing %SERVICE_NAME% as Windows Service...
echo.

REM Install service
nssm install %SERVICE_NAME% "%PYTHON_PATH%" "%SCRIPT_PATH%"

REM Configure service
nssm set %SERVICE_NAME% AppDirectory "%WORKING_DIR%"
nssm set %SERVICE_NAME% DisplayName "RAG Email System"
nssm set %SERVICE_NAME% Description "Automated email processing system with RAG and Odoo integration"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

REM Configure logging
nssm set %SERVICE_NAME% AppStdout "%WORKING_DIR%\logs\service.log"
nssm set %SERVICE_NAME% AppStderr "%WORKING_DIR%\logs\service_error.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4

REM Configure restart behavior
nssm set %SERVICE_NAME% AppRestartDelay 5000
nssm set %SERVICE_NAME% AppThrottle 10000

echo.
echo Service installed successfully!
echo.
echo To start the service, run:
echo   nssm start %SERVICE_NAME%
echo.
echo To check status:
echo   nssm status %SERVICE_NAME%
echo.
echo To stop the service:
echo   nssm stop %SERVICE_NAME%
echo.
echo To uninstall:
echo   nssm remove %SERVICE_NAME% confirm
echo.

pause
