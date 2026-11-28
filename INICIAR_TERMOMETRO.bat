@echo off
chcp 65001 >nul
title Termómetro Digital PBA — Centro de Control Autónomo
cd /d "%~dp0"

echo ======================================================================
echo    🌡️  INICIANDO TERMÓMETRO DIGITAL PBA (MODO AUTÓNOMO)
echo ======================================================================

REM Verificar si existe el entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo [!] No se detectó el entorno virtual configurado.
    echo [*] Iniciando instalación automática de dependencias...
    call INSTALAR_DEPENDENCIAS.bat
    if errorlevel 1 (
        echo [ERROR] No se pudo completar la instalación.
        pause
        exit /b 1
    )
)

REM Ejecutar el Launcher interactivo con el Python del entorno virtual
"venv\Scripts\python.exe" launcher.py %*

if errorlevel 1 (
    echo.
    echo Ocurrió un error al ejecutar el programa.
    pause
)
