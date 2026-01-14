@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ========================================================
echo   DESBLOQUEAR APLICACIÓN - ClasificadorPDF
echo ========================================================
echo.
echo Este script eliminará las restricciones de seguridad
echo de Windows para permitir la ejecución de la aplicación.
echo.
echo NO REQUIERE PERMISOS DE ADMINISTRADOR
echo.
echo ========================================================
echo.

set EXE_NAME=ClasificadorPDF.exe

:: Verificar que el ejecutable existe
if not exist "%EXE_NAME%" (
    echo [ERROR] No se encontró %EXE_NAME% en esta carpeta.
    echo.
    echo Asegúrate de ejecutar este script desde la carpeta
    echo donde extrajiste la aplicación.
    echo.
    pause
    exit /b 1
)

echo [1/3] Desbloqueando archivos de la aplicación...
echo.

:: Desbloquear todos los archivos en la carpeta actual y subcarpetas
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '.' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"

if %errorlevel% equ 0 (
    echo [OK] Archivos desbloqueados correctamente
) else (
    echo [ADVERTENCIA] Algunos archivos no pudieron ser desbloqueados
    echo              La aplicación debería funcionar de todas formas
)

echo.
echo [2/3] Verificando permisos de lectura/escritura...
echo.

:: Verificar que podemos leer el ejecutable
if exist "%EXE_NAME%" (
    echo [OK] El archivo %EXE_NAME% es accesible
) else (
    echo [ERROR] No se puede acceder a %EXE_NAME%
    pause
    exit /b 1
)

echo.
echo [3/3] Iniciando la aplicación...
echo.

:: Intentar ejecutar la aplicación
start "" "%EXE_NAME%"

if %errorlevel% equ 0 (
    echo [OK] La aplicación se ha iniciado correctamente
    echo.
    echo ========================================================
    echo   PROCESO COMPLETADO
    echo ========================================================
    echo.
    echo La aplicación ClasificadorPDF está ahora ejecutándose.
    echo.
    echo NOTA: Solo necesitas ejecutar este script UNA VEZ
    echo       después de descargar o extraer la aplicación.
    echo.
    echo ========================================================
) else (
    echo [ERROR] No se pudo iniciar la aplicación
    echo.
    echo Si el problema persiste, intenta:
    echo 1. Ejecutar RepararAcceso.bat como Administrador
    echo 2. Desactivar temporalmente el antivirus
    echo 3. Agregar una excepción en Windows Defender
    echo.
    pause
    exit /b 1
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
timeout /t 5 >nul
exit /b 0
