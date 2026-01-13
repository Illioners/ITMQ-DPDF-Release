$certPassword = "ClasificadorPDF2026"
$certName = "ClasificadorPDF Code Signing"
$pfxPath = "$PSScriptRoot\TC_CodeSigning.pfx"

Write-Host "Creating Self-Signed Certificate '$certName'..."

# Create the certificate
$cert = New-SelfSignedCertificate -CertStoreLocation Cert:\CurrentUser\My -Subject "CN=$certName" -Type CodeSigningCert -KeyUsage DigitalSignature -KeyAlgorithm RSA -KeyLength 2048 -NotAfter (Get-Date).AddYears(5)

# Create a secure password
$password = ConvertTo-SecureString -String $certPassword -Force -AsPlainText

# Export to PFX
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password

Write-Host "Certificate created successfully at: $pfxPath"
Write-Host "Password: $certPassword"
Write-Host "IMPORTANTE: Debe instalar este certificado en 'Entidades de certificación raíz de confianza' en las máquinas donde se use."
