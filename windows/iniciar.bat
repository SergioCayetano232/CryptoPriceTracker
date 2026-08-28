@echo off
title CryptoPriceTracker
REM Arranca el vigilante. Esto es lo que lanza la tarea programada.

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo No se encuentra el entorno virtual.
    echo Ejecuta primero:  python -m venv .venv
    echo Y despues:        .venv\Scripts\activate  y  pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo No se encuentra el archivo .env con el token de Telegram.
    echo Copia .env.example a .env y rellenalo.
    pause
    exit /b 1
)

if not exist "data" mkdir data

REM Si ya hay uno corriendo no arrancamos otro, avisaria por duplicado.
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }) { exit 0 } else { exit 1 }"
if %errorlevel% equ 0 (
    echo El bot ya esta funcionando. No arranco otro.
    timeout /t 5 >nul
    exit /b 0
)

REM Si el log pasa de 5 MB lo guardamos como .old y empezamos otro.
if exist "data\tracker.log" (
    for %%A in ("data\tracker.log") do if %%~zA GTR 5000000 (
        move /y "data\tracker.log" "data\tracker.log.old" >nul
    )
)

echo Vigilando precios. Puedes minimizar esta ventana.
echo Para pararlo, cierra la ventana o pulsa Ctrl+C.
echo.

.venv\Scripts\python.exe main.py --loop >> "data\tracker.log" 2>&1
