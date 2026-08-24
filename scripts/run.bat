@echo off
set SCRIPT_DIR=C:\Users\virat.arya\ETG\SoftsDatabase - Documents\Database\Hardmine\News\scripts
set PYTHON=C:\Users\virat.arya\AppData\Local\Microsoft\WindowsApps\python.exe

"%PYTHON%" "%SCRIPT_DIR%\build.py"
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE%==0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\send_mail.ps1"
)

exit /b %EXIT_CODE%
