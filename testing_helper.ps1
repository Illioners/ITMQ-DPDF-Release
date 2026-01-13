# Script de Ayuda para Testing - ClasificadorPDF v1.3.0
# Este script facilita la preparación del entorno de testing

param(
    [switch]$PrepareEnv,
    [switch]$RunApp,
    [switch]$CheckStatus,
    [switch]$CleanEnv
)

$TestingDir = "C:\Testing\ClasificadorPDF_v1.3.0"
$SourceDir = $PSScriptRoot
$DistDir = Join-Path $SourceDir "dist"

function Prepare-Environment {
    Write-Host "`n=== Preparando Entorno de Testing ===" -ForegroundColor Cyan
    
    # Crear directorios
    if (Test-Path $TestingDir) {
        Write-Host "⚠️  El directorio de testing ya existe" -ForegroundColor Yellow
        $response = Read-Host "¿Desea eliminarlo y recrearlo? (s/n)"
        if ($response -eq 's') {
            Remove-Item $TestingDir -Recurse -Force
            Write-Host "✓ Directorio eliminado" -ForegroundColor Green
        } else {
            Write-Host "Continuando sin eliminar..." -ForegroundColor Yellow
        }
    }
    
    if (-not (Test-Path $TestingDir)) {
        New-Item -ItemType Directory -Path $TestingDir | Out-Null
        New-Item -ItemType Directory -Path "$TestingDir\test_pdfs" | Out-Null
        Write-Host "✓ Directorios creados" -ForegroundColor Green
    }
    
    # Copiar ejecutables
    Write-Host "`nCopiando ejecutables..." -ForegroundColor Cyan
    
    $mainExe = Join-Path $DistDir "ClasificadorPDF.exe"
    $updaterExe = Join-Path $DistDir "ITMQ-Updater.exe"
    
    if (Test-Path $mainExe) {
        Copy-Item $mainExe $TestingDir -Force
        Write-Host "✓ ClasificadorPDF.exe copiado" -ForegroundColor Green
        
        $hash = (Get-FileHash -Path $mainExe -Algorithm SHA256).Hash
        Write-Host "  SHA256: $hash" -ForegroundColor Gray
    } else {
        Write-Host "✗ No se encontró ClasificadorPDF.exe" -ForegroundColor Red
    }
    
    if (Test-Path $updaterExe) {
        Copy-Item $updaterExe $TestingDir -Force
        Write-Host "✓ ITMQ-Updater.exe copiado" -ForegroundColor Green
    } else {
        Write-Host "✗ No se encontró ITMQ-Updater.exe" -ForegroundColor Red
    }
    
    Write-Host "`n=== Entorno Preparado ===" -ForegroundColor Green
    Write-Host "Ubicación: $TestingDir" -ForegroundColor Cyan
    Write-Host "`nColoca tus PDFs de prueba en: $TestingDir\test_pdfs\" -ForegroundColor Yellow
}

function Run-Application {
    Write-Host "`n=== Ejecutando Aplicación ===" -ForegroundColor Cyan
    
    $appPath = Join-Path $TestingDir "ClasificadorPDF.exe"
    
    if (Test-Path $appPath) {
        Write-Host "Iniciando ClasificadorPDF.exe..." -ForegroundColor Cyan
        Write-Host "Observa la ventana de la aplicación y cualquier error en consola`n" -ForegroundColor Yellow
        
        # Cambiar al directorio de testing y ejecutar
        Push-Location $TestingDir
        Start-Process $appPath
        Pop-Location
        
        Write-Host "✓ Aplicación iniciada" -ForegroundColor Green
    } else {
        Write-Host "✗ No se encontró el ejecutable en $TestingDir" -ForegroundColor Red
        Write-Host "Ejecuta primero: .\testing_helper.ps1 -PrepareEnv" -ForegroundColor Yellow
    }
}

function Check-Status {
    Write-Host "`n=== Estado del Sistema de Testing ===" -ForegroundColor Cyan
    
    # Verificar ejecutables en dist
    Write-Host "`n[Ejecutables Compilados]" -ForegroundColor Yellow
    Get-ChildItem -Path $DistDir -Filter "*.exe" | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.Name): ${size}MB (${_}.LastWriteTime)" -ForegroundColor Gray
    }
    
    # Verificar entorno de testing
    Write-Host "`n[Entorno de Testing]" -ForegroundColor Yellow
    if (Test-Path $TestingDir) {
        Write-Host "  Directorio: $TestingDir ✓" -ForegroundColor Green
        
        $testExe = Join-Path $TestingDir "ClasificadorPDF.exe"
        if (Test-Path $testExe) {
            $size = [math]::Round((Get-Item $testExe).Length / 1MB, 2)
            Write-Host "  ClasificadorPDF.exe: ${size}MB ✓" -ForegroundColor Green
        } else {
            Write-Host "  ClasificadorPDF.exe: No encontrado ✗" -ForegroundColor Red
        }
        
        # Contar PDFs de prueba
        $pdfCount = (Get-ChildItem -Path "$TestingDir\test_pdfs" -Filter "*.pdf" -ErrorAction SilentlyContinue).Count
        Write-Host "  PDFs de prueba: $pdfCount archivos" -ForegroundColor Gray
        
    } else {
        Write-Host "  Entorno no preparado ✗" -ForegroundColor Red
        Write-Host "  Ejecuta: .\testing_helper.ps1 -PrepareEnv" -ForegroundColor Yellow
    }
    
    # Verificar configuración
    Write-Host "`n[Configuración]" -ForegroundColor Yellow
    $versionFile = Join-Path $SourceDir "version.json"
    if (Test-Path $versionFile) {
        $version = (Get-Content $versionFile | ConvertFrom-Json).version
        Write-Host "  Versión: $version" -ForegroundColor Gray
    }
    
    Write-Host ""
}

function Clean-Environment {
    Write-Host "`n=== Limpiando Entorno de Testing ===" -ForegroundColor Cyan
    
    if (Test-Path $TestingDir) {
        Remove-Item $TestingDir -Recurse -Force
        Write-Host "✓ Entorno de testing eliminado" -ForegroundColor Green
    } else {
        Write-Host "No hay entorno de testing para limpiar" -ForegroundColor Yellow
    }
}

# Ejecutar funciones según parámetros
if ($PrepareEnv) {
    Prepare-Environment
}
elseif ($RunApp) {
    Run-Application
}
elseif ($CheckStatus) {
    Check-Status
}
elseif ($CleanEnv) {
    Clean-Environment
}
else {
    Write-Host "`n=== Testing Helper - ClasificadorPDF ===" -ForegroundColor Cyan
    Write-Host "`nUso:" -ForegroundColor Yellow
    Write-Host "  .\testing_helper.ps1 -PrepareEnv  : Prepara el entorno de testing"
    Write-Host "  .\testing_helper.ps1 -RunApp      : Ejecuta la aplicación"
    Write-Host "  .\testing_helper.ps1 -CheckStatus : Verifica el estado"
    Write-Host "  .\testing_helper.ps1 -CleanEnv    : Limpia el entorno de testing"
    Write-Host ""
}
