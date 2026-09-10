@echo off
set SCRIPT_DIR=C:\Users\virat.arya\ETG\SoftsDatabase - Documents\Database\Hardmine\News\scripts
set PYTHON=C:\Users\virat.arya\AppData\Local\Microsoft\WindowsApps\python.exe

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3 | Out-Null } catch { Start-Process -FilePath 'C:\Users\virat.arya\AppData\Local\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 5 }"

"%PYTHON%" "%SCRIPT_DIR%\build.py"
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE%==0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\send_mail.ps1"
)

exit /b %EXIT_CODE%
