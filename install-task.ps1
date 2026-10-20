# Windows のタスクスケジューラに「起動時に monitor.py --loop を常駐させる」タスクを登録する。
# 管理者権限の PowerShell で、このフォルダから実行:  powershell -ExecutionPolicy Bypass -File .\install-task.ps1
$ErrorActionPreference = "Stop"
$TaskName = "HTMLMonitor"
$Dir = $PSScriptRoot
$Pythonw = Join-Path $Dir ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $Pythonw)) { throw "$Pythonw がありません。先に README のセットアップ手順で .venv を作ってください。" }
if (-not (Test-Path (Join-Path $Dir ".env"))) { throw ".env がありません。.env.example をコピーして作ってください。" }

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
Write-Host "タスク '$TaskName' を登録して起動しました。ログ: $Dir\logs\monitor.log"
