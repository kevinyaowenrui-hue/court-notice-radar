# -*- coding: utf-8 -*-
import subprocess

ps_script = """
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('C:\\Users\\kevin\\Desktop\\法院案件公示与法拍监控雷达.lnk')
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Output "--- SHORTCUT INFO ---"
Write-Output ("Target: " + $sc.TargetPath)
Write-Output ("Args:   " + $sc.Arguments)
Write-Output ("WorkDir:" + $sc.WorkingDirectory)
Write-Output ("Icon:   " + $sc.IconLocation)
"""

with open("scripts/temp_check.ps1", "w", encoding="utf-8") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/temp_check.ps1"], capture_output=True)
print(res.stdout.decode('utf-8', errors='ignore'))
