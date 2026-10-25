$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument '/c "cd /d ""d:\data\face recognition\rohit"" && python main.py"'
Register-ScheduledTask -TaskName "ClassEyeLive" -Action $action -Force
Start-ScheduledTask -TaskName "ClassEyeLive"
Start-Sleep -Seconds 2
$p = Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle, MainWindowHandle
$p
