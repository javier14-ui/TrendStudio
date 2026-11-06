param([string]$PythonPath = '', [string]$DistPath = 'dist', [string]$WorkPath = 'build')
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $project
if (-not $PythonPath -and -not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.14 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python 3.14.' }
}
$python = if ($PythonPath) { (Resolve-Path -LiteralPath $PythonPath).Path } else { Join-Path $project '.venv\Scripts\python.exe' }
& $python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias.' }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas.' }
& $python scripts\collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Falló la recopilación de licencias.' }
if (-not (Test-Path -LiteralPath 'licenses\Qt\LGPL-3.0.txt')) {
    & $python scripts\fetch_qt_notices.py
    if ($LASTEXITCODE -ne 0) { throw 'Falló la descarga de avisos Qt.' }
}
& $python -m PyInstaller --noconfirm --distpath $DistPath --workpath $WorkPath TrendStudio.spec
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación.' }
$target = Join-Path $DistPath 'TrendStudio'
Copy-Item -LiteralPath README.md, LICENSE, THIRD_PARTY_NOTICES.md, CHANGELOG.md -Destination $target
Copy-Item -LiteralPath docs -Destination $target -Recurse -Force
Copy-Item -LiteralPath scripts\Crear-acceso-directo.ps1 -Destination $target
& (Join-Path $target 'TrendStudio.exe') --verify-install (Join-Path $target 'verificacion-instalacion.json')
if ($LASTEXITCODE -ne 0) { throw 'Falló la verificación del ejecutable.' }
Compress-Archive -Path $target -DestinationPath (Join-Path $DistPath 'TrendStudio-Windows-x64.zip') -Force
Write-Output "Listo: $DistPath\TrendStudio-Windows-x64.zip"
