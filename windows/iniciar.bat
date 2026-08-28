@echo off
REM Arranca el vigilante. Esto es lo que lanza la tarea programada.

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo No se encuentra el entorno virtual.
    echo Ejecuta primero: python -m venv .venv
    exit /b 1
)

if not exist "data" mkdir data

REM Si el log pasa de 5 MB lo guardamos como .old y empezamos otro.
if exist "data\tracker.log" (
    for %%A in ("data\tracker.log") do if %%~zA GTR 5000000 (
        move /y "data\tracker.log" "data\tracker.log.old" >nul
    )
)

.venv\Scripts\python.exe main.py --loop >> "data\tracker.log" 2>&1
