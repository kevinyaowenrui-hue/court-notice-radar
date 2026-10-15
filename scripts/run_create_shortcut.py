# -*- coding: utf-8 -*-
"""
Create CourtNoticeRadar Windows Shortcut with high-res icon
"""
import os
import subprocess

ps_content = """# PowerShell script to create desktop shortcut
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "法院案件公示与法拍监控雷达.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "C:\\Users\\kevin\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\pythonw.exe"
$Shortcut.Arguments = '\"f:\\antigravity exports\\报纸采集\\launcher.pyw\"'
$Shortcut.WorkingDirectory = "f:\\antigravity exports\\报纸采集"
$Shortcut.IconLocation = "f:\\antigravity exports\\报纸采集\\assets\\radar_icon.ico, 0"
$Shortcut.Description = "法院案件公示与法拍监控雷达 · 豫法雷达"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
Write-Output "SUCCESS: $ShortcutPath"
"""

ps_path = r"f:\antigravity exports\报纸采集\scripts\create_shortcut_utf8.ps1"
with open(ps_path, "w", encoding="utf-8-sig") as f:
    f.write(ps_content)

res = subprocess.run(
    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path],
    capture_output=True,
    text=True,
    encoding="utf-8"
)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
print("Returncode:", res.returncode)
