param(
    [ValidateSet("Unsigned", "Signed")]
    [string]$Mode = "Unsigned",

    [string]$CertificateThumbprint,

    # Used internally by Inno Setup to sign the installer and uninstaller.
    [string]$SignFile
)

$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installer = Join-Path $appDir "dist\installer\Avtoreya-Setup.exe"

function Assert-LastExitCode([string]$Name) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

function Find-InnoCompiler {
    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @()
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    }
    if ($env:ProgramFiles) {
        $candidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "Inno Setup 6 was not found. Install it and retry."
}

function Invoke-CodeSigning([string]$FilePath, [string]$Thumbprint) {
    $resolved = (Resolve-Path -LiteralPath $FilePath).Path
    $cleanThumbprint = ($Thumbprint -replace "\s", "").ToUpperInvariant()
    if ([string]::IsNullOrWhiteSpace($cleanThumbprint)) {
        throw "A certificate thumbprint is required for Signed mode."
    }

    $certificate = $null
    foreach ($store in @("CurrentUser", "LocalMachine")) {
        $certificatePath = "Cert:\$store\My\$cleanThumbprint"
        if (Test-Path -LiteralPath $certificatePath) {
            $certificate = Get-Item -LiteralPath $certificatePath
            break
        }
    }
    if (-not $certificate) {
        throw "The code-signing certificate was not found: $cleanThumbprint"
    }
    if (-not $certificate.HasPrivateKey) {
        throw "The certificate has no private key: $cleanThumbprint"
    }

    $codeSigningOid = "1.3.6.1.5.5.7.3.3"
    $ekuExtension = $certificate.Extensions | Where-Object {
        $_.Oid.Value -eq "2.5.29.37"
    }
    $canSignCode = $ekuExtension.EnhancedKeyUsages | Where-Object {
        $_.Value -eq $codeSigningOid
    }
    if (-not $canSignCode) {
        throw "The certificate is not valid for code signing: $cleanThumbprint"
    }

    $signature = Set-AuthenticodeSignature `
        -FilePath $resolved `
        -Certificate $certificate `
        -HashAlgorithm "SHA256" `
        -TimestampServer "http://timestamp.digicert.com"
    if ($signature.Status -ne "Valid") {
        throw "Windows rejected the signature for ${resolved}: $($signature.Status)"
    }
    Write-Output "Signed: $resolved"
}

# Inno Setup invokes this script again for each file it needs to sign.
if (-not [string]::IsNullOrWhiteSpace($SignFile)) {
    if ($Mode -ne "Signed") {
        throw "-SignFile is only valid in Signed mode."
    }
    Invoke-CodeSigning -FilePath $SignFile -Thumbprint $CertificateThumbprint
    exit 0
}

if ($Mode -eq "Signed" -and [string]::IsNullOrWhiteSpace($CertificateThumbprint)) {
    throw "Signed mode requires -CertificateThumbprint."
}
if ($Mode -eq "Unsigned" -and -not [string]::IsNullOrWhiteSpace($CertificateThumbprint)) {
    throw "A certificate thumbprint can only be used with -Mode Signed."
}

$python = (Get-Command "python.exe" -ErrorAction Stop).Source
$node = (Get-Command "node.exe" -ErrorAction Stop).Source
$iscc = Find-InnoCompiler
$specFiles = @(Get-ChildItem -LiteralPath $appDir -Filter "*.spec" -File)
if ($specFiles.Count -ne 1) {
    throw "Expected exactly one PyInstaller .spec file in $appDir."
}
$specFile = $specFiles[0].FullName

Push-Location $appDir
try {
    Write-Output "1/4 Checking Python syntax..."
    & $python -m compileall -q ".\main.py" ".\windows_startup.py" ".\tests"
    Assert-LastExitCode "Python syntax check"

    Write-Output "2/4 Running unit tests..."
    & $python -m unittest discover -s ".\tests" -v
    Assert-LastExitCode "Unit tests"

    Write-Output "3/4 Checking UI JavaScript syntax..."
    $tempJs = Join-Path ([System.IO.Path]::GetTempPath()) ("avtoreya-ui-{0}.js" -f [guid]::NewGuid().ToString("N"))
    try {
        $html = Get-Content -Raw ".\ui.html"
        $matches = [regex]::Matches($html, '(?s)<script(?:\s[^>]*)?>(.*?)</script>')
        if ($matches.Count -eq 0) {
            throw "No inline JavaScript was found in ui.html."
        }
        $javascript = ($matches | ForEach-Object { $_.Groups[1].Value }) -join "`n"
        Set-Content -LiteralPath $tempJs -Value $javascript -Encoding UTF8
        & $node --check $tempJs
        Assert-LastExitCode "JavaScript syntax check"
    }
    finally {
        if (Test-Path -LiteralPath $tempJs) {
            Remove-Item -LiteralPath $tempJs -Force
        }
    }

    Write-Output "4/4 Building the application and installer ($Mode)..."
    & $python -m PyInstaller --noconfirm --clean $specFile
    Assert-LastExitCode "PyInstaller"

    # Inspect only executables located directly inside an onedir application
    # folder. This ignores obsolete one-file artifacts in dist and avoids
    # embedding non-ASCII paths that Windows PowerShell 5.1 can misread.
    $appExecutables = @(
        Get-ChildItem -LiteralPath (Join-Path $appDir "dist") -Directory |
            Where-Object { $_.Name -ne "installer" } |
            ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Filter "*.exe" -File }
    )
    if ($appExecutables.Count -ne 1) {
        throw "Expected one onedir application executable after PyInstaller, found $($appExecutables.Count)."
    }
    $appExe = $appExecutables[0].FullName

    if (Test-Path -LiteralPath $installer) {
        Remove-Item -LiteralPath $installer -Force
    }

    if ($Mode -eq "Signed") {
        Invoke-CodeSigning -FilePath $appExe -Thumbprint $CertificateThumbprint

        # Inno replaces $q with a quote and $f with its quoted file path.
        # Reusing the active host works in Windows PowerShell 5.1 and pwsh.
        $powerShell = (Get-Process -Id $PID).Path
        $thisScript = $MyInvocation.MyCommand.Path
        $signCommand = "`$q$powerShell`$q -NoProfile -ExecutionPolicy Bypass -File `$q$thisScript`$q -Mode Signed -CertificateThumbprint `$q$CertificateThumbprint`$q -SignFile `$f"
        & $iscc "/DSignedBuild=1" "/Savtoreya=$signCommand" ".\installer.iss"
    }
    else {
        & $iscc ".\installer.iss"
    }
    Assert-LastExitCode "Inno Setup"

    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Inno Setup did not create the expected installer: $installer"
    }

    if ($Mode -eq "Signed") {
        foreach ($file in @($appExe, $installer)) {
            $signature = Get-AuthenticodeSignature -LiteralPath $file
            if ($signature.Status -ne "Valid") {
                throw "Invalid signature for ${file}: $($signature.Status)"
            }
        }
        Write-Output "Signed installer ready: $installer"
        Write-Warning "A locally valid signature does not guarantee SmartScreen trust. Public trust also depends on the certificate and publisher reputation."
    }
    else {
        Write-Output "Unsigned installer ready: $installer"
        Write-Warning "Windows may show SmartScreen. Publish this file as unsigned and do not claim a trusted publisher."
    }
}
finally {
    Pop-Location
}
