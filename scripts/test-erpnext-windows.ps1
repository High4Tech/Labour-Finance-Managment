#requires -Version 5.1
<#
  PLUS POINT upstream ERPNext verification using WINDOWS Docker Desktop only.
  No Ubuntu / WSL commands are necessary.
  Official pwd.yml is a DISPOSABLE test stack, never production or a custom-app base.
  Run from PowerShell:
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-erpnext-windows.ps1
  Requires internet and working Linux Docker Desktop engine.
#>
[CmdletBinding()]
param(
    [int]$Port = 8080,
    [int]$TimeoutSeconds = 900,
    [switch]$StopAfterTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$work = Join-Path $root '.local\upstream-smoke'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$original = Join-Path $work 'pwd.yml'
$override = Join-Path $work 'loopback.yml'
$project = 'pluspoint-upstream-smoke'
$base = "http://127.0.0.1:$Port"
$compose = @('compose','-p',$project,'-f',$original,'-f',$override)
function DockerCompose {
    & docker @compose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed (exit $LASTEXITCODE)." }
}
try {
    $engine = (& docker info --format '{{.OSType}}' 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') {
        throw "Docker Linux engine unavailable: $engine"
    }
    Write-Host 'PASS Docker Desktop Linux engine'

    Write-Host 'Fetching official frappe/frappe_docker disposable test stack...'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/frappe/frappe_docker/main/pwd.yml' -OutFile $original
    # Keep test framework major/minor stable even if the upstream demo tag changes.
    $upstreamText = Get-Content -Raw $original
    if ($upstreamText -notmatch 'frappe/erpnext:v[0-9]+\.[0-9]+\.[0-9]+') {
        throw 'Official demo compose file no longer contains expected frappe/erpnext image tags.'
    }
    $upstreamText = [regex]::Replace($upstreamText, 'frappe/erpnext:v[0-9]+\.[0-9]+\.[0-9]+', 'frappe/erpnext:v16.51.1')
    Set-Content -Path $original -Value $upstreamText -Encoding UTF8

    # Compose v2.24.4+ !override prevents the original wildcard port from remaining published.
    @"
services:
  frontend:
    ports: !override
      - "127.0.0.1:${Port}:8080"
"@ | Set-Content -Encoding UTF8 $override
    Write-Host 'Pulling and starting official ERPNext Docker containers (may take several minutes)...'
    DockerCompose up -d

    Write-Host "Waiting up to $TimeoutSeconds seconds for $base/api/method/ping ..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $ping = Invoke-RestMethod -Uri "$base/api/method/ping" -TimeoutSec 8
            if ($ping.message -eq 'pong') { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 10
    }
    if (-not $ready) {
        DockerCompose ps
        & docker @compose logs --tail 100 create-site
        throw "FAIL ERPNext API readiness: $base did not respond in time"
    }
    Write-Host 'PASS Live HTTP API ping'

    $apps = & docker @compose exec -T backend bench --site frontend list-apps
    if ($LASTEXITCODE -ne 0) { throw 'FAIL bench list-apps' }
    $appsText = $apps | Out-String
    if ($appsText -notmatch '(?m)^\s*frappe\b' -or $appsText -notmatch '(?m)^\s*erpnext\b') {
        throw "FAIL expected Frappe and ERPNext installed apps: $appsText"
    }
    Write-Host 'PASS Frappe and ERPNext installed on test site'

    $db = & docker @compose exec -T backend bench --site frontend execute frappe.db.exists DocType ToDo
    if ($LASTEXITCODE -ne 0 -or ($db | Out-String) -notmatch 'ToDo') {
        throw "FAIL MariaDB DocType read: $db"
    }
    Write-Host 'PASS Actual site database read (ToDo DocType)'

    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $body = @{ usr = 'Administrator'; pwd = 'admin' } | ConvertTo-Json -Compress
    $login = Invoke-RestMethod -Uri "$base/api/method/login" -Method Post -Body $body -ContentType 'application/json' -WebSession $session -TimeoutSec 20
    if ($login.message -notmatch 'Logged In') { throw "FAIL administrator demo login: $($login.message)" }
    Write-Host 'PASS Authenticated login on disposable demo'
    $companies = Invoke-RestMethod -Uri "$base/api/resource/Company?limit_page_length=1" -Method Get -WebSession $session -TimeoutSec 20
    if ($null -eq $companies.data) { throw 'FAIL Company endpoint did not return data key' }
    Write-Host 'PASS Authenticated ERPNext Company endpoint'

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $latencies = New-Object 'System.Collections.Generic.List[double]'
    for ($i = 0; $i -lt 20; $i++) {
        $sw.Restart()
        $p = Invoke-RestMethod -Uri "$base/api/method/ping" -TimeoutSec 12
        if ($p.message -ne 'pong') { throw "FAIL ping during performance sampling at request $i" }
        $latencies.Add($sw.Elapsed.TotalMilliseconds)
    }
    $sorted = @($latencies | Sort-Object)
    $p95 = $sorted[[math]::Ceiling(0.95 * $sorted.Count) - 1]
    Write-Host ("PASS 20 sequential API responses; median {0:N1} ms, p95 {1:N1} ms (NOT a load test)" -f $sorted[9], $p95)
    Write-Host 'PASS Baseline ERPNext verification completed. HRMS and custom PLUS POINT APIs NOT YET TESTED.'
} catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($StopAfterTest) {
        Write-Host 'Stopping disposable demo and removing test volumes...'
        & docker @compose down -v --remove-orphans | Out-Host
    } else {
        Write-Host "Demo stack remains running at $base (Administrator/admin; LOCAL TEST ONLY)."
        Write-Host 'Stop/remove later: docker compose -p pluspoint-upstream-smoke -f .local/upstream-smoke/pwd.yml -f .local/upstream-smoke/loopback.yml down -v'
    }
}
