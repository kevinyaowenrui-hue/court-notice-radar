# -*- coding: utf-8 -*-
"""
法拍雷达 · 司法拍卖与法院公告监控工作站 - 桌面端启动主程序
集成本地 FastAPI 服务、定时采集调度器与 原生独立桌面窗口 (基于 WebView2)
"""
import sys
import os
import time
import socket
import threading
import traceback
import urllib.request
import webbrowser
import subprocess
import multiprocessing

# 确定工作目录与运行时根路径
if getattr(sys, 'frozen', False):
    ROOT_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    RUN_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    RUN_DIR = ROOT_DIR

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 确保控制台与标准输出在无黑窗口(console=False)模式下静默写入本地日志文件，避免因 NoneType.write 崩溃
LOG_FILE = os.path.join(RUN_DIR, "radar_app.log")
try:
    with open(LOG_FILE, "a", encoding="utf-8") as _f:
        _f.write(f"\n[Boot] Top-level script executing, RUN_DIR={RUN_DIR}\n")
except Exception:
    pass

class SafeLogWriter:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._term = sys.stdout
        self.encoding = "utf-8"

    def write(self, s: str):
        if self._term:
            try:
                self._term.write(s)
            except Exception:
                pass
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(s)
        except Exception:
            pass

    def flush(self):
        if self._term:
            try:
                self._term.flush()
            except Exception:
                pass

    def isatty(self):
        return False

    def readable(self):
        return False

    def writable(self):
        return True

    def seekable(self):
        return False

# 重定向标准输出与错误流
sys.stdout = SafeLogWriter(LOG_FILE)
sys.stderr = SafeLogWriter(LOG_FILE)

# 全局未捕获异常捕获
def handle_exception(exc_type, exc_value, exc_traceback):
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"\n[FATAL ERROR] {time.strftime('%Y-%m-%d %H:%M:%S')}\n{err}\n")

sys.excepthook = handle_exception
if hasattr(threading, 'excepthook'):
    threading.excepthook = lambda args: handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

def find_available_port(default_port: int = 5220) -> int:
    """寻找本地空闲可用端口"""
    for port in range(default_port, default_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return default_port

def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    """轮询等待本地服务启动就绪"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/stats", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def start_backend_server(port: int):
    """在后台线程中启动 FastAPI 核心服务"""
    try:
        import uvicorn
        from backend.app import app
        print(f"[*] 正在启动 FastAPI 核心服务: 127.0.0.1:{port} ...")
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
            log_config=None
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"[!] 后台服务启动异常: {traceback.format_exc()}")

def get_recent_log_lines(filepath: str, n: int = 30) -> str:
    """读取指定日志文件最后 n 行"""
    if not os.path.exists(filepath):
        return "暂无日志记录"
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except Exception as e:
        return f"读取日志文件失败: {e}"

class DiagnosticApi:
    def __init__(self, port: int):
        self.port = port
        self._window = None

    def set_window(self, win):
        self._window = win

    def repair_database(self):
        """执行本地数据库完整性校验与修复并重启服务"""
        try:
            from backend.database import DB_PATH, SEED_PATH, ensure_db_integrity
            print("[Diagnostic] User triggered database repair...")
            ensure_db_integrity(DB_PATH, SEED_PATH)
            from backend.clean_and_migrate_db import clean_database
            clean_database(DB_PATH)
            
            # 重新启动服务线程
            server_thread = threading.Thread(target=start_backend_server, args=(self.port,), daemon=True)
            server_thread.start()
            
            ready = wait_for_server(f"http://127.0.0.1:{self.port}", timeout=10.0)
            if ready and self._window:
                self._window.load_url(f"http://127.0.0.1:{self.port}")
                return {"success": True, "message": "数据库自检与修复成功，正在转入系统工作台..."}
            return {"success": False, "message": "数据库修复成功，但服务启动仍超时，请检查下方日志。"}
        except Exception as e:
            return {"success": False, "message": f"修复执行失败: {str(e)}"}

def build_diagnostic_html(log_text: str) -> str:
    import html as html_lib
    escaped_logs = html_lib.escape(log_text)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>法拍雷达 · 本地服务异常诊断</title>
  <style>
    body {{ background-color: #0b0f19; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif; padding: 40px; margin: 0; }}
    .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 28px; max-width: 900px; margin: 0 auto; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
    h1 {{ color: #f87171; font-size: 20px; margin-top: 0; display: flex; align-items: center; gap: 10px; }}
    p {{ color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 8px 0 16px 0; }}
    pre {{ background: #020617; border: 1px solid #334155; border-radius: 8px; padding: 14px; font-family: Consolas, Monaco, monospace; font-size: 12px; color: #fca5a5; max-height: 320px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
    .btn {{ background: #f59e0b; color: #020617; border: none; font-weight: bold; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
    .btn:hover {{ background: #d97706; }}
    .status {{ margin-top: 14px; font-size: 13px; color: #38bdf8; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>⚠️ 本地后端服务启动超时 / 异常诊断</h1>
    <p>系统检测到后台服务启动异常。通常由于 SQLite 数据库文件损坏、端口冲突或退出未截断引起。以下是 <code>radar_app.log</code> 最近 30 行报错记录：</p>
    <pre>{escaped_logs}</pre>
    <div style="margin-top: 20px;">
      <button class="btn" onclick="doRepair()">🛠️ 一键重置 / 修复本地数据库</button>
      <div id="status" class="status"></div>
    </div>
  </div>
  <script>
    function doRepair() {{
      const s = document.getElementById('status');
      s.innerText = '正在执行数据库自检与修复，请稍候...';
      if (window.pywebview && window.pywebview.api) {{
        window.pywebview.api.repair_database().then(res => {{
          s.innerText = res.message;
        }}).catch(err => {{
          s.innerText = '修复出错: ' + err;
        }});
      }} else {{
        s.innerText = 'WebView API 未就绪，请稍后刷新重试。';
      }}
    }}
  </script>
</body>
</html>"""

def main():
    multiprocessing.freeze_support()
    print(f"\n==========================================")
    print(f"[*] 法拍雷达桌面端启动 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] 运行路径: {RUN_DIR}")
    print(f"==========================================")

    port = find_available_port(5220)
    server_url = f"http://127.0.0.1:{port}"
    print(f"[*] 绑定本地服务端口: {port}，主界面地址: {server_url}")

    # 1. 启动后台服务线程
    server_thread = threading.Thread(target=start_backend_server, args=(port,), daemon=True)
    server_thread.start()

    # 2. 等待本地核心服务就绪
    is_ready = wait_for_server(server_url, timeout=12.0)
    diagnostic_api = DiagnosticApi(port)

    # 3. 优先使用 pywebview 唤起独立无边框桌面原生窗口 (WebView2)
    use_webview_success = False
    try:
        import webview
        print("[*] 正在加载桌面原生应用容器 (WebView2)...")
        if is_ready:
            window = webview.create_window(
                title="法拍雷达 · 司法拍卖与法院公告监控工作站",
                url=server_url,
                width=1440,
                height=900,
                min_size=(1024, 680),
                background_color='#0b0f19'
            )
        else:
            print("[!] 服务未就绪，向窗口载入本地错误诊断页面...")
            recent_logs = get_recent_log_lines(LOG_FILE, n=30)
            diagnostic_html = build_diagnostic_html(recent_logs)
            window = webview.create_window(
                title="法拍雷达 · 服务异常诊断",
                html=diagnostic_html,
                js_api=diagnostic_api,
                width=1200,
                height=800,
                min_size=(900, 600),
                background_color='#0b0f19'
            )
            diagnostic_api.set_window(window)

        use_webview_success = True
        webview.start()
    except Exception as e:
        print(f"[!] pywebview 启动异常: {e}，正在切换至备用桌面窗口模式...")

    # 4. 容灾备用方案：如果 pywebview 启动失败，尝试调用系统 Edge 的独立应用窗口模式 (--app)
    if not use_webview_success:
        try:
            print("[*] 正在唤起系统 Edge 独立工作站窗口 (--app)...")
            edge_cmd = [
                "msedge.exe",
                f"--app={server_url}",
                "--window-size=1440,900"
            ]
            proc = subprocess.Popen(edge_cmd)
            proc.wait()
        except Exception as e:
            print(f"[!] Edge 窗口启动异常: {e}，正在打开默认浏览器...")
            webbrowser.open(server_url)
            while True:
                time.sleep(1)

if __name__ == "__main__":
    main()
