@echo off
REM Dice si el bot esta funcionando y ensena las ultimas lineas del log.

cd /d "%~dp0.."

powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }) { exit 0 } else { exit 1 }"
if %errorlevel% equ 0 (
    echo   El bot esta FUNCIONANDO.
) else (
    echo   El bot esta PARADO.
)

echo.
echo   Ultimas lineas del log:
echo.
if exist "data\tracker.log" (
    powershell -NoProfile -Command "Get-Content 'data\tracker.log' -Tail 15"
) else (
    echo   (todavia no hay log)
)
echo.
pause
