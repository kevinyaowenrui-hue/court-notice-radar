# PowerShell script to create desktop shortcut
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "法院案件公示与法拍监控雷达.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "C:\Users\kevin\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
$Shortcut.Arguments = '"f:\antigravity exports\报纸采集\launcher.pyw"'
$Shortcut.WorkingDirectory = "f:\antigravity exports\报纸采集"
$Shortcut.IconLocation = "f:\antigravity exports\报纸采集\assets\radar_icon.ico, 0"
$Shortcut.Description = "法院案件公示与法拍监控雷达 · 豫法雷达"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
Write-Output "SUCCESS: $ShortcutPath"
