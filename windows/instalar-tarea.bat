@echo off
REM Crea la tarea programada que mantiene el bot funcionando.
REM Ejecutar como administrador (boton derecho > Ejecutar como administrador).

cd /d "%~dp0"

echo.
echo Te va a pedir tu contrasena de Windows dos veces, una por tarea.
echo Hace falta para que el bot arranque aunque nadie inicie sesion.
echo.

REM Arranca al encender el equipo, un minuto despues para que haya red.
schtasks /create ^
    /tn "CryptoPriceTracker" ^
    /tr "\"%~dp0iniciar.bat\"" ^
    /sc onstart ^
    /delay 0001:00 ^
    /ru "%USERDOMAIN%\%USERNAME%" ^
    /rp * ^
    /rl highest ^
    /f

if %errorlevel% neq 0 goto error

REM Segunda tarea: cada 15 min comprueba que sigue vivo y lo revive.
schtasks /create ^
    /tn "CryptoPriceTracker-Vigia" ^
    /tr "\"%~dp0revisar.bat\"" ^
    /sc minute ^
    /mo 15 ^
    /ru "%USERDOMAIN%\%USERNAME%" ^
    /rp * ^
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
echo Fallo al crear la tarea. Revisa que lo ejecutas como administrador
echo y que la contrasena es la de tu usuario de Windows.
pause
exit /b 1
