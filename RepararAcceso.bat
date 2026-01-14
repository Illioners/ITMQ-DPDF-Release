@echo off
setlocal enabledelayedexpansion
echo ==================================================
echo   REPARADOR DE ACCESO - ClasificadorPDF
echo ==================================================
echo.

:: Verificar permisos de Administrador
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Este script requiere ejecutarse como ADMINISTRADOR.
    echo Por favor, haz clic derecho y selecciona "Ejecutar como administrador".
    echo.
    pause
    exit /b
)

set EXE_NAME=ClasificadorPDF.exe

if not exist "%EXE_NAME%" (
    echo [ERROR] No se encontro %EXE_NAME% en esta carpeta.
    echo Asegurate de poner este script dentro de la carpeta del programa.
    echo.
    pause
    exit /b
)

echo [INFO] Desbloqueando archivos en esta carpeta (incluyendo subcarpetas)...
powershell -Command "Get-ChildItem -Path '.' -Recurse | Unblock-File"

echo [INFO] Verificando permisos de seguridad...
icacls "." /grant %USERNAME%:(OI)(CI)F /T >nul 2>&1

echo.
echo [OK] El programa y sus dependencias han sido procesados.
echo Intentando abrir la aplicacion...
start "" "%EXE_NAME%"

echo.
echo Presiona cualquier tecla para cerrar...
pause > nul
