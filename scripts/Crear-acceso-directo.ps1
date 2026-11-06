$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'TrendStudio.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Coloca este script junto a TrendStudio.exe.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$linkPath = Join-Path $desktop 'TrendStudio.lnk'
if (Test-Path -LiteralPath $linkPath) { throw 'Ya existe un acceso directo TrendStudio. No se reemplazó.' }
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = $exe
$link.WorkingDirectory = $PSScriptRoot
$link.Description = 'TrendStudio: radar e investigación con IA local opcional'
$link.Save()
Write-Output "Acceso directo creado: $linkPath"
