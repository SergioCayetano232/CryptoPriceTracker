@echo off
REM Crea la tarea programada que mantiene el bot funcionando.
REM Ejecutar como administrador (boton derecho > Ejecutar como administrador).

cd /d "%~dp0"

REM Arranca al encender el equipo. Si el bot se cierra, la tarea vuelve
REM a lanzarlo a los 5 minutos porque se repite cada hora y solo corre
REM si no hay ya una instancia en marcha.
schtasks /create ^
    /tn "CryptoPriceTracker" ^
    /tr "\"%~dp0iniciar.bat\"" ^
    /sc onstart ^
    /delay 0001:00 ^
    /ru "%USERNAME%" ^
    /rl highest ^
    /f

if %errorlevel% neq 0 goto error

REM Segunda tarea: cada 15 min comprueba que sigue vivo y lo revive.
schtasks /create ^
    /tn "CryptoPriceTracker-Vigia" ^
    /tr "\"%~dp0revisar.bat\"" ^
    /sc minute ^
    /mo 15 ^
    /ru "%USERNAME%" ^
    /rl highest ^
    /f

if %errorlevel% neq 0 goto error

echo.
echo Listo. El bot arranca al encender el servidor y se revisa cada 15 minutos.
echo.
echo Arrancarlo ahora sin reiniciar:
echo     schtasks /run /tn "CryptoPriceTracker"
echo.
pause
exit /b 0

:error
echo.
echo Fallo al crear la tarea. Ejecuta este archivo como administrador.
pause
exit /b 1
