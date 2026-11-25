param([string]$Destination = (Join-Path $PSScriptRoot 'backups'))
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$file=Join-Path $Destination ('seas-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.dump')
# pg_dump runs inside the container; copying the archive avoids PowerShell binary redirection.
docker compose exec -T db pg_dump -U seas -d seas -Fc -f /tmp/seas-backup.dump
if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el respaldo.' }
docker compose cp db:/tmp/seas-backup.dump $file
if ($LASTEXITCODE -ne 0) { throw 'No se pudo copiar el respaldo.' }
Write-Host "Respaldo creado: $file"
