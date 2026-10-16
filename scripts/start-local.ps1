#requires -Version 5.1
[CmdletBinding()]
param([switch]$RotateLocalCredentials, [switch]$WithPlatform)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$envFile = Join-Path $root '.env'
function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes)
}
function Invoke-Compose {
    & docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed with exit code $LASTEXITCODE" }
}
$settings = if (Test-Path $envFile) { Get-Content -Raw $envFile } else { "LOCAL_SITE=demo.localhost`nFRAPPE_PORT=8000`n" }
if ($RotateLocalCredentials -and (& docker volume ls -q --filter name=pluspoint-development_mariadb-data)) {
    throw 'Existing database detected. Rotate its credentials with a database migration; this option is for initial setup only.'
}
foreach ($name in @('PP_ADMIN_PASSWORD', 'PP_DB_PASSWORD')) {
    if ($RotateLocalCredentials -or $settings -notmatch "(?m)^$name=.{20,}$") {
        $settings = [regex]::Replace($settings, "(?m)^$name=.*\r?\n?", '')
        $settings += "$name=$(New-LocalSecret)`n"
    }
}
[System.IO.File]::WriteAllText($envFile, $settings)
Invoke-Compose up -d
Invoke-Compose exec -T --user root frappe chown frappe:frappe /home/frappe/frappe-bench
Invoke-Compose exec -T frappe python /workspace/scripts/bootstrap.py
if ($WithPlatform) {
    Invoke-Compose exec -T -e LOCAL_SITE=platform.localhost frappe python /workspace/scripts/bootstrap.py
    Invoke-Compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site platform.localhost set-config pp_control_plane True --parse'
    Invoke-Compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site platform.localhost execute plus_point.install.after_migrate'
}
# Start only if the prior bench process is absent. Re-running never creates duplicate servers.
& docker compose exec -T frappe pgrep -f 'honcho start' *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Compose exec -d frappe bash -lc 'cd /home/frappe/frappe-bench && bench start >> logs/bench-start.log 2>&1'
}
& docker compose exec -T frappe pgrep -f '/workspace/scripts/platform-worker.py' *> $null
if ($LASTEXITCODE -ne 0) { Invoke-Compose exec -d frappe python /workspace/scripts/platform-worker.py }
Write-Host 'PLUS POINT started. Local site and port are in .env; credentials were not printed.'
