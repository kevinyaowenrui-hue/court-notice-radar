# -*- coding: utf-8 -*-
"""
Restore All Desktop Shortcuts with Exact Original Parameters
Uses win32com WScript.Shell to cleanly write UTF-8 Windows .lnk files.
"""
import os
import sys
from pathlib import Path
import win32com.client

desktop_path = Path(os.environ["USERPROFILE"]) / "Desktop"

shortcuts_def = [
    {
        "name": "3D Solar.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\3D world\launch_solar3d.vbs"',
        "work_dir": r"F:\antigravity exports\3D world",
        "icon": r"F:\antigravity exports\3D world\solar3d.ico,0",
        "desc": "3D 太阳系观测台 (Solar3D)",
    },
    {
        "name": "Cinema Lingo.lnk",
        "target": r"C:\Users\kevin\.gemini\antigravity\StartCinemaLingo.bat",
        "args": "",
        "work_dir": r"C:\Users\kevin\.gemini\antigravity",
        "icon": "",
        "desc": "Cinema Lingo - 影视英语沉浸学习工具",
    },
    {
        "name": "cleanmaster.exe - 快捷方式.lnk",
        "target": r"D:\装机\装机软件\PCMaster\cleanmaster.exe",
        "args": "",
        "work_dir": r"D:\装机\装机软件\PCMaster",
        "icon": "",
        "desc": "CleanMaster 电脑清理大师",
    },
    {
        "name": "C盘缓存清理工具.exe - 快捷方式.lnk",
        "target": r"F:\codex exports\cleaner\c-drive-cleaner\C盘缓存清理工具.exe",
        "args": "",
        "work_dir": r"F:\codex exports\cleaner\c-drive-cleaner",
        "icon": r"F:\codex exports\cleaner\c-drive-cleaner\CDriveCleaner.ico,0",
        "desc": "C盘缓存清理工具",
    },
    {
        "name": "C盘清理.exe - 快捷方式.lnk",
        "target": r"F:\codex exports\cleaner\c-drive-cleaner\C盘缓存清理工具.exe",
        "args": "",
        "work_dir": r"F:\codex exports\cleaner\c-drive-cleaner",
        "icon": r"F:\codex exports\cleaner\c-drive-cleaner\CDriveCleaner.ico,0",
        "desc": "C盘清理",
    },
    {
        "name": "geek.exe - 快捷方式.lnk",
        "target": r"D:\装机\装机软件\geek.exe",
        "args": "",
        "work_dir": r"D:\装机\装机软件",
        "icon": "",
        "desc": "Geek Uninstaller",
    },
    {
        "name": "GoodGoods Lab - 良品研选.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\best prouduct affiliate\launch_goodgoods.vbs"',
        "work_dir": r"F:\antigravity exports\best prouduct affiliate",
        "icon": r"F:\antigravity exports\best prouduct affiliate\goodgoods.ico,0",
        "desc": "良品研选 GoodGoods Lab - 全球平价正品好物指南",
    },
    {
        "name": "GoodGoods Lab - 平价好物.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\best prouduct affiliate\launch_goodgoods.vbs"',
        "work_dir": r"F:\antigravity exports\best prouduct affiliate",
        "icon": r"F:\antigravity exports\best prouduct affiliate\goodgoods.ico,0",
        "desc": "良品研选 GoodGoods Lab",
    },
    {
        "name": "Into Vincent · 梵高画中无尽.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\codex exports\van goch\scripts\launch.vbs"',
        "work_dir": r"F:\codex exports\van goch",
        "icon": r"F:\codex exports\van goch\public\icon\app-icon.ico,0",
        "desc": "Into Vincent · 梵高画作无限穿行",
    },
    {
        "name": "Music Player.lnk",
        "target": r"F:\Node.js\npm.cmd",
        "args": "start",
        "work_dir": r"F:\antigravity exports\music player",
        "icon": r"F:\antigravity exports\music player\app_icon.ico,0",
        "desc": "Music Player 本地音乐播放器",
    },
    {
        "name": "ReversePrompt.lnk",
        "target": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "args": r'-ExecutionPolicy Bypass -WindowStyle Hidden -File "f:\antigravity exports\prompts reverse\web\run_app.ps1"',
        "work_dir": r"f:\antigravity exports\prompts reverse\web",
        "icon": r"C:\Users\kevin\.gemini\antigravity\brain\5c824f89-52bb-49ba-8cc7-83fa09b66b6f\cartoon_app_icon.ico,0",
        "desc": "ReversePrompt 反向提示词工作站",
    },
    {
        "name": "RootLingo.lnk",
        "target": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "args": r'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "F:\codex exports\新东方词根词缀\scripts\start-rootlingo.ps1"',
        "work_dir": r"F:\codex exports\新东方词根词缀",
        "icon": r"F:\codex exports\新东方词根词缀\assets\desktop\rootlingo-app-icon.ico,0",
        "desc": "RootLingo 英语词根词缀记忆工作站",
    },
    {
        "name": "Stacher7.lnk",
        "target": r"C:\Users\kevin\AppData\Local\Stacher7\Stacher7.exe",
        "args": "",
        "work_dir": r"C:\Users\kevin\AppData\Local\Stacher7",
        "icon": "",
        "desc": "Stacher 媒体下载器",
    },
    {
        "name": "Tactile Tetris.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"f:\antigravity exports\Tetris\launch.vbs"',
        "work_dir": r"f:\antigravity exports\Tetris",
        "icon": r"f:\antigravity exports\Tetris\icon.ico,0",
        "desc": "Tactile Tetris 客制化机械触感 ASMR 俄罗斯方块",
    },
    {
        "name": "TaleGlow 绘光童语.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\英语绘本\launch_storycomet.vbs"',
        "work_dir": r"F:\antigravity exports\英语绘本",
        "icon": r"F:\antigravity exports\英语绘本\storycomet.ico,0",
        "desc": "TaleGlow 绘光童语 - 3D少儿英语绘本馆",
    },
    {
        "name": "StoryComet 英语绘本.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\英语绘本\launch_storycomet.vbs"',
        "work_dir": r"F:\antigravity exports\英语绘本",
        "icon": r"F:\antigravity exports\英语绘本\storycomet.ico,0",
        "desc": "StoryComet 星彗英语绘本馆",
    },
    {
        "name": "VibeReading 电子书阅读器.lnk",
        "target": r"f:\antigravity exports\VibeReading\启动VibeReading.bat",
        "args": "",
        "work_dir": r"f:\antigravity exports\VibeReading",
        "icon": r"f:\antigravity exports\VibeReading\public\favicon.ico,0",
        "desc": "VibeReading 电子书阅读器",
    },
    {
        "name": "中华诗脉.lnk",
        "target": r"C:\WINDOWS\system32\wscript.exe",
        "args": r'"F:\antigravity exports\chinese poets\launch.vbs"',
        "work_dir": r"F:\antigravity exports\chinese poets",
        "icon": r"F:\antigravity exports\chinese poets\poet_mascot_icon.ico,0",
        "desc": "中华诗脉 - 历代诗词全景脉络",
    },
    {
        "name": "人工智能.xlsx - 快捷方式.lnk",
        "target": r"F:\人工智能\人工智能.xlsx",
        "args": "",
        "work_dir": r"F:\人工智能",
        "icon": "",
        "desc": "人工智能.xlsx",
    },
    {
        "name": "人工智能导出 - 快捷方式.lnk",
        "target": r"F:\人工智能导出",
        "args": "",
        "work_dir": r"F:\人工智能导出",
        "icon": "",
        "desc": "人工智能导出 文件夹",
    },
    {
        "name": "单词宇宙 3D.lnk",
        "target": r"F:\antigravity exports\universe words\start_universe.bat",
        "args": "",
        "work_dir": r"F:\antigravity exports\universe words",
        "icon": r"F:\antigravity exports\universe words\universe_icon.ico,0",
        "desc": "启动 3D 单词宇宙系统",
    },
    {
        "name": "声动音标 EchoPhonics.lnk",
        "target": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "args": r'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "f:\antigravity exports\英语音标\start-echophonics.ps1"',
        "work_dir": r"f:\antigravity exports\英语音标",
        "icon": r"f:\antigravity exports\英语音标\echophonics.ico,0",
        "desc": "声动音标 EchoPhonics",
    },
    {
        "name": "正本清源.lnk",
        "target": r"F:\antigravity exports\正本清源\正本清源.exe",
        "args": "",
        "work_dir": r"F:\antigravity exports\正本清源",
        "icon": r"F:\antigravity exports\正本清源\app_icon.ico,0",
        "desc": "正本清源 · 破谬堂 - 传世文句与名言曲解溯源工作站",
    },
    {
        "name": "私人影院.lnk",
        "target": r"F:\codex exports\movie hub\run.vbs",
        "args": "",
        "work_dir": r"F:\codex exports\movie hub",
        "icon": r"F:\codex exports\movie hub\MyCinema_Icon.ico,0",
        "desc": "私人影院",
    },
]

def restore_shortcuts():
    shell = win32com.client.Dispatch("WScript.Shell")
    restored_count = 0
    
    print(f"Desktop location: {desktop_path}")
    print(f"Total shortcuts to restore: {len(shortcuts_def)}")
    print("-" * 60)
    
    for item in shortcuts_def:
        lnk_file = desktop_path / item["name"]
        try:
            shortcut = shell.CreateShortcut(str(lnk_file))
            shortcut.TargetPath = item["target"]
            if item["args"]:
                shortcut.Arguments = item["args"]
            if item["work_dir"]:
                shortcut.WorkingDirectory = item["work_dir"]
            if item["icon"]:
                shortcut.IconLocation = item["icon"]
            if item.get("desc"):
                shortcut.Description = item["desc"]
            shortcut.Save()
            
            exists = lnk_file.exists()
            size = lnk_file.stat().st_size if exists else 0
            print(f"[OK] {item['name']} -> Exists: {exists}, Size: {size} bytes")
            restored_count += 1
        except Exception as e:
            print(f"[FAIL] {item['name']}: {e}")
            
    print("-" * 60)
    print(f"Completed restoring {restored_count}/{len(shortcuts_def)} shortcuts.")

if __name__ == "__main__":
    restore_shortcuts()
