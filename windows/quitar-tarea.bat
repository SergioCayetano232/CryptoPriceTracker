@echo off
REM Quita las tareas programadas y para el bot. Ejecutar como administrador.

schtasks /end /tn "CryptoPriceTracker" 2>nul
schtasks /delete /tn "CryptoPriceTracker" /f 2>nul
schtasks /delete /tn "CryptoPriceTracker-Vigia" /f 2>nul

REM Por lo que lanza, no por el titulo: sin sesion iniciada no hay ventana.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py --loop*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo.
echo Tareas eliminadas.
pause
