@echo off
REM Quita las tareas programadas y para el bot. Ejecutar como administrador.

schtasks /end /tn "CryptoPriceTracker" 2>nul
schtasks /delete /tn "CryptoPriceTracker" /f 2>nul
schtasks /delete /tn "CryptoPriceTracker-Vigia" /f 2>nul

taskkill /f /im python.exe /fi "WINDOWTITLE eq CryptoPriceTracker*" 2>nul

echo.
echo Tareas eliminadas.
pause
