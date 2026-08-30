#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人调试台 · 桌面版启动器（PyInstaller 打包入口）

设计目标：双击 exe 就能用，机器上不需要装 Python。

    PersonalDebugConsole.exe                 -> 自动起 Web UI 并打开浏览器
    PersonalDebugConsole.exe web -p 9000     -> 指定端口
    PersonalDebugConsole.exe web --public    -> 局域网可访问
    PersonalDebugConsole.exe cli             -> 命令行交互模式
    PersonalDebugConsole.exe --help

源码态下同样可直接运行：python packaging/launcher.py
"""

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_NAME = "个人调试台"
APP_VERSION = "1.0.0"
DEFAULT_PORT = 7788


def _utf8_console():
    """Windows 控制台代码页五花八门，统一成 UTF-8 免得打印中文炸掉。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _base_dir() -> Path:
    """打包后资源解包在 sys._MEIPASS；源码态取仓库根目录。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "."))
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
BACKEND_DIR = BASE_DIR / "backend"

# backend 必须先进 sys.path，后面 `import app` 才找得到
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def find_free_port(start: int = DEFAULT_PORT, tries: int = 30) -> int:
    """从 7788 开始找第一个空闲端口，避免端口被占时直接崩给用户看。"""
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def _banner():
    bar = "=" * 54
    print("\n" + bar)
    print(f"   {APP_NAME}  ·  Personal Debug Console  v{APP_VERSION}")
    print(bar + "\n")


def _load_flask_app():
    """导入后端 Flask app，并把前端目录钉死到正确的位置。"""
    import app as app_module

    # app.py 自己按 __file__ 推断 frontend 路径，打包环境下显式覆盖更稳
    frontend = BASE_DIR / "frontend"
    app_module.FRONTEND_DIR = frontend
    app_module.STATIC_DIR = frontend
    return app_module.app


def run_web(port=None, host="127.0.0.1", open_browser=True):
    if not (BASE_DIR / "frontend" / "index.html").exists():
        print(f"  × 找不到前端资源：{BASE_DIR / 'frontend'}")
        print("  这个 exe 可能不完整，请重新下载。")
        return 1

    try:
        flask_app = _load_flask_app()
    except Exception as exc:  # noqa: BLE001
        print(f"  × 后端加载失败：{exc}")
        return 1

    if port is None:
        port = find_free_port()
    url = f"http://127.0.0.1:{port}" if host in ("127.0.0.1", "localhost") else f"http://{host}:{port}"

    _banner()
    print(f"   服务地址 : {url}")
    print(f"   资源目录 : {BASE_DIR}")
    print("\n   保持本窗口开启即可使用；按 Ctrl+C 或直接关窗口退出。\n")

    if open_browser:
        def _open_later():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=_open_later, daemon=True).start()

    try:
        flask_app.run(host=host, port=port, debug=False, use_reloader=False)
    except OSError as exc:
        print(f"\n  × 端口 {port} 启动失败：{exc}")
        print("   换一个端口试试：PersonalDebugConsole.exe web -p 9000\n")
        return 1
    except KeyboardInterrupt:
        print("\n  已停止。")
    return 0


def run_cli():
    try:
        from cli import main as cli_main
    except Exception as exc:  # noqa: BLE001
        print(f"  × 命令行模块加载失败：{exc}")
        return 1
    _banner()
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\n  已退出。")
    return 0


def main(argv=None):
    _utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        # 双击进来的场景：直接给 Web UI，别弹交互式菜单让人懵
        return run_web()

    cmd = argv[0].lower()

    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    if cmd in ("cli", "cmd", "console", "terminal"):
        return run_cli()

    if cmd in ("web", "serve", "server", "ui", "gui"):
        port = None
        host = "127.0.0.1"
        no_browser = False
        i = 1
        while i < len(argv):
            arg = argv[i]
            if arg in ("-p", "--port") and i + 1 < len(argv):
                port = int(argv[i + 1]); i += 2
            elif arg.startswith("--port="):
                port = int(arg.split("=", 1)[1]); i += 1
            elif arg in ("-H", "--host") and i + 1 < len(argv):
                host = argv[i + 1]; i += 2
            elif arg.startswith("--host="):
                host = arg.split("=", 1)[1]; i += 1
            elif arg == "--public":
                host = "0.0.0.0"; i += 1
            elif arg == "--no-browser":
                no_browser = True; i += 1
            elif arg.isdigit():
                port = int(arg); i += 1
            else:
                i += 1
        return run_web(port=port, host=host, open_browser=not no_browser)

    print(f"未知参数：{cmd}\n")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main() or 0)
