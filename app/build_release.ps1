param(
    [Parameter(Mandatory = $true)]
    [string]$CertificateThumbprint
)

$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
$signScript = Join-Path $appDir "sign_file.ps1"
$appExe = Join-Path $appDir "dist\Книжница\Книжница.exe"
$powerShell = (Get-Command "pwsh.exe" -ErrorAction Stop).Source

if (-not (Test-Path -LiteralPath $iscc)) {
    throw "Не найден Inno Setup: $iscc"
}

Push-Location $appDir
try {
    python -m PyInstaller --noconfirm --clean ".\Книжница.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller завершился с кодом $LASTEXITCODE"
    }

    & $signScript -FilePath $appExe -Thumbprint $CertificateThumbprint

    # Inno сам заменяет $q на кавычку, а $f — на уже заключённый в кавычки путь.
    # Поэтому внутри /S нет настоящих вложенных кавычек, которые ISCC принял бы
    # за дополнительные имена .iss-файлов.
    $signCommand = "`$q$powerShell`$q -NoProfile -File `$q$signScript`$q -FilePath `$f -Thumbprint `$q$CertificateThumbprint`$q"
    $compiler = [System.Diagnostics.ProcessStartInfo]::new($iscc)
    $compiler.UseShellExecute = $false
    $compiler.WorkingDirectory = $appDir
    $compiler.ArgumentList.Add("/DSignedBuild=1")
    $compiler.ArgumentList.Add("/Sknizhnitsa=$signCommand")
    $compiler.ArgumentList.Add(".\installer.iss")
    $compilerProcess = [System.Diagnostics.Process]::Start($compiler)
    $compilerProcess.WaitForExit()
    if ($compilerProcess.ExitCode -ne 0) {
        throw "Inno Setup завершился с кодом $($compilerProcess.ExitCode)"
    }

    $installer = Join-Path $appDir "dist\installer\Книжница-Setup.exe"
    foreach ($file in @($appExe, $installer)) {
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -ne "Valid") {
            throw "Недействительная подпись: $file — $($signature.Status)"
        }
    }
    Write-Output "Готов подписанный установщик: $installer"
}
finally {
    Pop-Location
}
