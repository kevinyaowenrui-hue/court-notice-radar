# -*- coding: utf-8 -*-
"""
CourtNoticeRadar Desktop Smart Launcher
Checks if the local backend server on port 5220 is running;
if not, starts it silently in the background, then opens the browser.
"""
import os
import sys
import time
import urllib.request
import webbrowser
import subprocess

PROJECT_DIR = r"f:\antigravity exports\报纸采集"
PORT = 5220
URL = f"http://127.0.0.1:{PORT}"

def is_server_running():
    try:
        req = urllib.request.urlopen(f"{URL}/api/stats", timeout=1.2)
        return req.getcode() == 200
    except Exception:
        return False

def start_server():
    python_exe = sys.executable
    env = os.environ.copy()
    env["SERVER_PORT"] = str(PORT)
    
    # 0x08000000 = CREATE_NO_WINDOW on Windows
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        [python_exe, "-m", "backend.app"],
        cwd=PROJECT_DIR,
        env=env,
        creationflags=CREATE_NO_WINDOW
    )

def main():
    if not is_server_running():
        start_server()
        for _ in range(30):
            time.sleep(0.2)
            if is_server_running():
                break

    # Open default browser to the system web UI
    webbrowser.open(URL)

if __name__ == '__main__':
    main()
