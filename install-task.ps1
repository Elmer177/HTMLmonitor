# Register a Windows scheduled task that runs "monitor.py --loop" at startup.
# Run from an elevated (Administrator) PowerShell in this folder:
#   powershell -ExecutionPolicy Bypass -File .\install-task.ps1
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads BOM-less UTF-8 as Shift-JIS.
$ErrorActionPreference = "Stop"
$TaskName = "HTMLMonitor"
$Dir = $PSScriptRoot
$Pythonw = Join-Path $Dir ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $Pythonw)) { throw "Not found: $Pythonw  (create .venv first, see README)" }
if (-not (Test-Path (Join-Path $Dir ".env"))) { throw "Not found: .env  (copy .env.example to .env)" }

$action    = New-ScheduledTaskAction -Execute $Pythonw -Argument "monitor.py --loop" -WorkingDirectory $Dir
$trigger   = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Registered and started task '$TaskName'. Log: $Dir\logs\monitor.log"
