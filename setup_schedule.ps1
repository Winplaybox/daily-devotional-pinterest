# Run this script once in PowerShell to schedule daily 6:00 AM automatic Pinterest posting
param(
    [string]$Time = "06:00",
    [string]$Religions = "hindu",
    [string]$Languages = "gu,hi,en"
)

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python).Source
$TaskName = "DailyDevotionalPinterest"

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "main.py --religions $Religions --languages $Languages --publish" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Description "Generates daily devotional artwork with date and publishes to Pinterest." `
    -Force

Write-Host "Scheduled task '$TaskName' created to run daily at $Time."
