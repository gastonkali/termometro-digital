@echo off
chcp 65001 >nul
title Termómetro Digital PBA — Instalador de Dependencias
cd /d "%~dp0"

echo ======================================================================
echo    🔧 INSTALACIÓN DE DEPENDENCIAS Y NAVEGADOR PLAYWRIGHT
echo ======================================================================

REM 1. Verificar Python instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no se encuentra en el PATH del sistema.
    echo Por favor instalá Python 3.10 o superior marcando "Add Python to PATH".
    pause
    exit /b 1
)

REM 2. Crear entorno virtual si no existe
if not exist "venv\Scripts\python.exe" (
    echo [*] Creando entorno virtual aislado (venv)...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [✓] Entorno virtual creado exitosamente.
)

REM 3. Actualizar pip e instalar paquetes
echo [*] Instalando librerías requeridas (Flask, Playwright, Scikit-learn, etc.)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Error durante la instalación de paquetes con pip.
    pause
    exit /b 1
)

REM 4. Instalar Chromium para Playwright
echo [*] Instalando binarios de Chromium para navegación con Playwright...
"venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo [ERROR] Falló la instalación de Chromium para Playwright.
    pause
    exit /b 1
)

REM 5. Configurar archivo .env base si no existe
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Generando archivo .env a partir de .env.example...
        copy ".env.example" ".env" >nul
    )
)

echo.
echo ======================================================================
echo    ✓ ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!
echo    Ya podés hacer doble clic en INICIAR_TERMOMETRO.bat
echo ======================================================================
timeout /t 5 >nul
