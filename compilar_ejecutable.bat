@echo off
chcp 65001 >nul
title Termómetro Digital PBA — Compilar a Ejecutable (.exe)
cd /d "%~dp0"

echo ======================================================================
echo    📦 COMPILACIÓN DE EJECUTABLE AUTÓNOMO (.EXE) CON PYINSTALLER
echo ======================================================================

REM Verificar entorno virtual
if not exist "venv\Scripts\pyinstaller.exe" (
    echo [*] Instalando PyInstaller en el entorno virtual...
    "venv\Scripts\pip.exe" install pyinstaller
)

echo [*] Compilando Termómetro Digital con termometro.spec...
"venv\Scripts\pyinstaller.exe" termometro.spec --noconfirm

if errorlevel 1 (
    echo [ERROR] Falló la compilación del ejecutable.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo    ✓ ¡COMPILACIÓN EXITOSA!
echo    El ejecutable se encuentra en: dist\TermometroDigital\TermometroDigital.exe
echo ======================================================================
pause
