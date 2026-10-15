# -*- coding: utf-8 -*-
"""
Script to create the desktop shortcut with custom icon
"""
import os
import sys
import shutil
import subprocess

def create_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    # Also verify with PowerShell environment
    ps_cmd = "[Environment]::GetFolderPath('Desktop')"
    try:
        res = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True).strip()
        if res and os.path.exists(res):
            desktop = res
    except Exception as e:
        print("Note getting desktop:", e)

    shortcut_name = "法院案件公示与法拍监控雷达.lnk"
    shortcut_path = os.path.join(desktop, shortcut_name)

    pythonw_path = shutil.which("pythonw")
    if not pythonw_path:
        pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")

    project_dir = r"f:\antigravity exports\报纸采集"
    target_script = os.path.join(project_dir, "launcher.pyw")
    icon_path = os.path.join(project_dir, "assets", "radar_icon.ico")

    print(f"Desktop Path: {desktop}")
    print(f"Shortcut Path: {shortcut_path}")
    print(f"Pythonw Path: {pythonw_path}")
    print(f"Target Script: {target_script}")
    print(f"Icon Path: {icon_path}")

    # Use PowerShell COM object to create exact Windows .lnk
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{pythonw_path}'
$Shortcut.Arguments = '"{target_script}"'
$Shortcut.WorkingDirectory = '{project_dir}'
$Shortcut.IconLocation = '{icon_path}, 0'
$Shortcut.Description = '法院案件公示与法拍监控雷达 · 河南专属与全国法拍'
$Shortcut.WindowStyle = 7  # Minimized / silent
$Shortcut.Save()
Write-Host "Shortcut created successfully"
"""
    cmd = ["powershell", "-NoProfile", "-Command", ps_script]
    subprocess.run(cmd, check=True)
    print("Desktop shortcut created successfully!")

if __name__ == '__main__':
    create_shortcut()
