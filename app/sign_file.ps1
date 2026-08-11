param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,

    [Parameter(Mandatory = $true)]
    [string]$Thumbprint,

    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

$resolved = (Resolve-Path -LiteralPath $FilePath).Path
$cleanThumbprint = ($Thumbprint -replace "\s", "").ToUpperInvariant()
$certificatePath = "Cert:\CurrentUser\My\$cleanThumbprint"

if (-not (Test-Path -LiteralPath $certificatePath)) {
    throw "Сертификат подписи не найден: $cleanThumbprint"
}

$certificate = Get-Item -LiteralPath $certificatePath
if (-not $certificate.HasPrivateKey) {
    throw "У сертификата нет закрытого ключа: $cleanThumbprint"
}

$codeSigningOid = "1.3.6.1.5.5.7.3.3"
$ekuExtension = $certificate.Extensions | Where-Object {
    $_.Oid.Value -eq "2.5.29.37"
}
$canSignCode = $ekuExtension.EnhancedKeyUsages | Where-Object {
    $_.Value -eq $codeSigningOid
}
if (-not $canSignCode) {
    throw "Сертификат не предназначен для подписи программ: $cleanThumbprint"
}

$parameters = @{
    FilePath = $resolved
    Certificate = $certificate
    HashAlgorithm = "SHA256"
}
if ($TimestampServer) {
    $parameters.TimestampServer = $TimestampServer
}

$signature = Set-AuthenticodeSignature @parameters
if ($signature.Status -ne "Valid") {
    throw "Windows не признала подпись действительной: $($signature.Status) — $($signature.StatusMessage)"
}

Write-Output "Подписано: $resolved"
Write-Output "Сертификат: $($certificate.Subject)"
Write-Output "Отпечаток: $cleanThumbprint"
