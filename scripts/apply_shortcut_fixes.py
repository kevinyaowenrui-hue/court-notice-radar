# -*- coding: utf-8 -*-
"""
Apply fixes for Cinema Lingo, VibeReading, and TaleGlow shortcuts.
"""
import os
import win32com.client

desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
shell = win32com.client.Dispatch("WScript.Shell")

# 1. Fix Cinema Lingo icon
cinema_lnk = os.path.join(desktop, "Cinema Lingo.lnk")
cinema_ico = r"C:\Users\kevin\.gemini\antigravity\CinemaLingoIcon.ico"
if os.path.exists(cinema_lnk) and os.path.exists(cinema_ico):
    sc = shell.CreateShortcut(cinema_lnk)
    sc.IconLocation = f"{cinema_ico},0"
    sc.Save()
    print("[FIXED] Cinema Lingo icon set to:", cinema_ico)

# 2. Fix VibeReading icon
vibe_lnk = os.path.join(desktop, "VibeReading 电子书阅读器.lnk")
vibe_ico = r"f:\antigravity exports\VibeReading\public\vibereading.ico"
if os.path.exists(vibe_lnk) and os.path.exists(vibe_ico):
    sc = shell.CreateShortcut(vibe_lnk)
    sc.IconLocation = f"{vibe_ico},0"
    sc.Save()
    print("[FIXED] VibeReading icon set to:", vibe_ico)

# 3. Fix TaleGlow shortcut
taleglow_lnk = os.path.join(desktop, "TaleGlow 绘光童语.lnk")
pythonw_exe = r"C:\Users\kevin\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
taleglow_pyw = r"F:\antigravity exports\英语绘本\launcher.pyw"
taleglow_ico = r"F:\antigravity exports\英语绘本\storycomet.ico"
taleglow_dir = r"F:\antigravity exports\英语绘本"

if os.path.exists(taleglow_lnk) and os.path.exists(pythonw_exe) and os.path.exists(taleglow_pyw):
    sc = shell.CreateShortcut(taleglow_lnk)
    sc.TargetPath = pythonw_exe
    sc.Arguments = f'"{taleglow_pyw}"'
    sc.WorkingDirectory = taleglow_dir
    sc.IconLocation = f"{taleglow_ico},0"
    sc.Description = "TaleGlow 绘光童语 - 3D少儿英语绘本馆"
    sc.Save()
    print("[FIXED] TaleGlow shortcut configured with pythonw launcher:", taleglow_pyw)

print("All 3 shortcuts updated successfully!")
