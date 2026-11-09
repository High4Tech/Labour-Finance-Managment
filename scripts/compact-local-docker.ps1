# Run only after a verified site backup. Does not prune images or volumes.
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOutput = Join-Path $taskRoot '.local\storage-compaction'
$taskDisk = 'D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx'
if (-not $Apply) { Write-Output "Would trim and compact $taskDisk, restarting only Docker Desktop. Use -Apply in an administrator PowerShell after backup."; exit 0 }
$taskAdmin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $taskAdmin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Windows administrator approval is required to compact the Docker virtual disk.' }
if ((Resolve-Path -LiteralPath $taskDisk).Path -ne $taskDisk) { throw 'Unexpected Docker data disk path.' }
$taskBackup = Join-Path $taskRoot '.local\backups\storage-cleanup-20261109\sites'
if (@(Get-ChildItem -LiteralPath $taskBackup -Filter '*database.sql.gz' -File).Count -lt 4) { throw 'Expected all four compressed site backups before compaction.' }
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
$taskBefore = (Get-Item -LiteralPath $taskDisk).Length
$taskStopped = $false
$taskResult = @{ before_bytes = $taskBefore; disk = $taskDisk; success = $false }
try {
    & wsl.exe -d docker-desktop -u root -- /sbin/fstrim -v /mnt/docker-desktop-disk *> (Join-Path $taskOutput 'trim.log')
    if ($LASTEXITCODE -ne 0) { throw 'Filesystem trim failed; no disk compaction attempted.' }
    $taskStopped = $true
    & docker desktop stop --timeout 60 *> (Join-Path $taskOutput 'stop.log')
    if ($LASTEXITCODE -ne 0) { throw 'Docker did not stop cleanly.' }
    # Do not shut down unrelated Ubuntu/WSL environments.
    & wsl.exe --terminate docker-desktop *> (Join-Path $taskOutput 'terminate.log')
    $taskExclusive = [IO.File]::Open($taskDisk, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $taskExclusive.Dispose()
    $taskCommands = Join-Path $taskOutput 'diskpart.txt'
    @("select vdisk file=`"$taskDisk`"", 'compact vdisk', 'exit') | Set-Content -LiteralPath $taskCommands -Encoding ascii
    & diskpart.exe /s $taskCommands *> (Join-Path $taskOutput 'compact.log')
    if ($LASTEXITCODE -ne 0 -or (Get-Content -LiteralPath (Join-Path $taskOutput 'compact.log') -Raw) -notmatch 'successfully compacted') { throw 'DiskPart did not confirm successful compaction. See compact.log.' }
    $taskResult.success = $true
} catch {
    $taskResult.error = $_.Exception.Message
} finally {
    $taskResult.after_bytes = (Get-Item -LiteralPath $taskDisk).Length
    $taskResult.reclaimed_bytes = $taskBefore - $taskResult.after_bytes
    if ($taskStopped) {
        & docker desktop start --timeout 60 *> (Join-Path $taskOutput 'start.log')
        $taskResult.restart_exit_code = $LASTEXITCODE
    }
    $taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'result.json') -Encoding utf8
}
if (-not $taskResult.success) { exit 1 }
