# Build only: no optimization or machine configuration is changed.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Build with PowerShell 7 on Windows; PyInstaller cannot cross-compile Windows from Linux.' }
$project = Split-Path -Parent $PSScriptRoot
Push-Location $project
try {
    python -c "import sys, struct, tkinter; assert sys.version_info[:2] == (3, 13), 'Use CPython 3.13'; assert struct.calcsize('P') == 8, 'Use x64 Python'; root=tkinter.Tk(); root.withdraw(); root.update(); root.destroy()"
    if ($LASTEXITCODE -ne 0) { throw 'Python x64 / Tcl/Tk preflight failed' }
    python -m PyInstaller --noconfirm --clean --distpath dist --workpath build build-support/FrameWise.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed; inspect build/FrameWise/warn-FrameWise.txt and CI logs' }
    $bundle = Join-Path $project 'dist/FrameWise'
    Copy-Item README.md, LICENSE -Destination $bundle -Force
    if (Test-Path "$bundle/docs") { Remove-Item "$bundle/docs" -Recurse -Force }
    Copy-Item docs -Destination $bundle -Recurse
    python scripts/verify-bundle.py $bundle
    if ($LASTEXITCODE -ne 0) { throw 'Bundle validation failed' }
    $zip = Join-Path $project 'dist/FrameWise-windows-x64.zip'
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path $bundle -DestinationPath $zip -CompressionLevel Optimal
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  FrameWise-windows-x64.zip" | Set-Content (Join-Path $project 'dist/SHA256SUMS.txt') -Encoding ascii
    Write-Output "Built $zip (not smoke-tested until smoke-windows.ps1 succeeds)"
} finally { Pop-Location }
