@echo off
REM Comprueba que el bot sigue corriendo y lo arranca si se ha caido.

cd /d "%~dp0.."

powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }) { exit 0 } else { exit 1 }"
if %errorlevel% equ 0 exit /b 0

echo [%date% %time%] El bot no estaba corriendo, lo arranco >> "data\tracker.log"
start "" /min "%~dp0iniciar.bat"
