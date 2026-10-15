
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('C:\Users\kevin\Desktop\法院案件公示与法拍监控雷达.lnk')
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Output "--- SHORTCUT INFO ---"
Write-Output ("Target: " + $sc.TargetPath)
Write-Output ("Args:   " + $sc.Arguments)
Write-Output ("WorkDir:" + $sc.WorkingDirectory)
Write-Output ("Icon:   " + $sc.IconLocation)
