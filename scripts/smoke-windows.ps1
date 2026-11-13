# Tests the exact distributable ZIP, away from the checkout and without Python on PATH.
[CmdletBinding()]
param(
    [string]$Archive = (Join-Path (Split-Path -Parent $PSScriptRoot) 'dist/FrameWise-windows-x64.zip'),
    [string]$Report = (Join-Path (Split-Path -Parent $PSScriptRoot) 'dist/windows-smoke.json')
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Windows is required for the executable smoke test.' }
$Archive = (Resolve-Path $Archive).Path
$Report = [System.IO.Path]::GetFullPath($Report)
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('FrameWise smoke ' + [guid]::NewGuid().ToString('N'))
$oldPath = $env:PATH
$oldAppData = $env:LOCALAPPDATA
$oldPythonHome = $env:PYTHONHOME
$oldPythonPath = $env:PYTHONPATH
$process = $null
$result = [ordered]@{
    status = 'failed'; tested_utc = [DateTime]::UtcNow.ToString('o')
    os = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
    archive_sha256 = (Get-FileHash $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    test = 'Extracted x64 GUI --smoke-test, isolated app data, no Python on PATH, working directory outside source'
    exit_code = $null; error = $null
}
try {
    New-Item $tempRoot -ItemType Directory -Force | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $tempRoot
    $exe = Join-Path $tempRoot 'FrameWise/FrameWise.exe'
    if (-not (Test-Path $exe -PathType Leaf)) { throw 'ZIP does not contain FrameWise/FrameWise.exe' }
    $env:LOCALAPPDATA = Join-Path $tempRoot 'isolated user data'
    New-Item $env:LOCALAPPDATA -ItemType Directory -Force | Out-Null
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
    # -NoProfile does not affect the executable; all runtime imports must come from its bundle.
    $process = Start-Process -FilePath $exe -ArgumentList '--smoke-test' -WorkingDirectory $tempRoot -PassThru
    if (-not $process.WaitForExit(60000)) {
        $process.Kill($true)
        $process.WaitForExit()
        throw 'Extracted executable did not finish GUI smoke test within 60 seconds'
    }
    $process.Refresh()
    $result.exit_code = $process.ExitCode
    if ($process.ExitCode -ne 0) { throw "Extracted executable exited with code $($process.ExitCode)" }
    # Fresh app-data creation witnesses App construction, not just an early zero exit.
    if (-not (Test-Path (Join-Path $env:LOCALAPPDATA 'FrameWise') -PathType Container)) {
        throw 'Executable exited without constructing the application (isolated app-data directory absent)'
    }
    $result.status = 'passed'
    Write-Output 'Packaged Windows GUI smoke test passed (Python/Tcl/Tk resolved from bundle).'
} catch {
    $result.error = $_.Exception.Message
    throw
} finally {
    $env:PATH = $oldPath
    $env:LOCALAPPDATA = $oldAppData
    $env:PYTHONHOME = $oldPythonHome
    $env:PYTHONPATH = $oldPythonPath
    New-Item (Split-Path -Parent $Report) -ItemType Directory -Force | Out-Null
    $result | ConvertTo-Json -Depth 4 | Set-Content $Report -Encoding utf8
    if ($null -ne $process) { $process.Dispose() }
    if (Test-Path $tempRoot) { Remove-Item $tempRoot -Recurse -Force }
}
