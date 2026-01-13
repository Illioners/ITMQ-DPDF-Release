# Script para generar certificado de firma de código (PFX)
$ErrorActionPreference = "Stop"

# Verificación de privilegios de administrador
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Este script DEBE ejecutarse como ADMINISTRADOR." -ForegroundColor Red
    Write-Host "Por favor, cierra esta ventana, abre PowerShell como Administrador y vuelve a intentarlo." -ForegroundColor Yellow
    pause
    exit
}

$subject = "CN=ITMQ-Developer"
$pfxName = "TC_CodeSigning.pfx"
$password = Read-Host -Prompt "Ingresa una contraseña para el archivo PFX" -AsSecureString

Write-Host "`nGenerando certificado autofirmado..." -ForegroundColor Cyan
# Usamos CertStoreLocation para asegurar que se guarde en el contexto del usuario actual
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -FriendlyName "ITMQ Code Signing" -NotAfter (Get-Date).AddYears(3) -CertStoreLocation "Cert:\CurrentUser\My"

Write-Host "Exportando a $pfxName..." -ForegroundColor Cyan
$pfxPath = Join-Path -Path $PSScriptRoot -ChildPath $pfxName

# Exportar el certificado a PFX
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password

Write-Host "`n¡ÉXITO! Certificado generado en: $pfxPath" -ForegroundColor Green
Write-Host "Puedes usar este archivo y la contraseña que elegiste en el ITMQ-Signer." -ForegroundColor Yellow
