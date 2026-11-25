$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Se creó .env. Configure las claves, la contraseña inicial y PostgreSQL; después vuelva a ejecutar este archivo.'
    exit 1
}
foreach ($line in Get-Content -LiteralPath '.env') {
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), 'Process')
    }
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Se requiere Python 3.12 o posterior.' }
}
& '.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& '.venv\Scripts\python.exe' manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'No se pudo conectar o migrar PostgreSQL. Revise .env y el servicio de base de datos.' }
& '.venv\Scripts\python.exe' manage.py seed_seas
if ($LASTEXITCODE -ne 0) { throw 'No se pudo cargar el catálogo.' }
Write-Host 'SEAS disponible en http://127.0.0.1:8000. Pulse Ctrl+C para detenerlo.'
& '.venv\Scripts\python.exe' -m waitress --listen=127.0.0.1:8000 seas.wsgi:application
