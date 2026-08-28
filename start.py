#!/usr/bin/env python3
"""
个人调试台 · 统一启动入口
用法：
  python start.py            # 交互式选择模式
  python start.py web        # 直接启动 Web UI (默认 http://127.0.0.1:7788)
  python start.py web -p 8888  # 指定端口
  python start.py cli        # 直接进入命令行交互模式
  python start.py install    # 安装依赖
"""

import os
import sys
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from colorama import Fore, Style, init as _cinit
_cinit()


LOGO = f"""
{Fore.LIGHTCYAN_EX}        ╭────────────────────────────────────────╮
{Fore.LIGHTCYAN_EX}        │   🔧  个 人 调 试 台 · Debug Console   │
{Fore.LIGHTCYAN_EX}        ╰────────────────────────────────────────╯
{Style.RESET_ALL}"""


def check_deps():
    """检查依赖，给出友好提示"""
    missing = []
    for mod, pkg in [
        ("flask", "flask"),
        ("flask_cors", "flask-cors"),
        ("psutil", "psutil"),
        ("colorama", "colorama"),
    ]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    # rich / plyer 是可选的
    for mod, pkg in [("rich", "rich"), ("plyer", "plyer")]:
        try:
            __import__(mod)
        except ImportError:
            print(f"  {Fore.LIGHTBLACK_EX}· 可选依赖缺失：{pkg}（某些功能会降级）{Style.RESET_ALL}")
    if missing:
        print(f"\n  {Fore.LIGHTRED_EX}缺少必要依赖：{', '.join(missing)}{Style.RESET_ALL}")
        print(f"  请先执行：{Fore.LIGHTYELLOW_EX}python start.py install{Style.RESET_ALL}")
        print(f"  或手动：{Fore.LIGHTYELLOW_EX}pip install -r requirements.txt{Style.RESET_ALL}\n")
        return False
    return True


def cmd_install():
    import subprocess
    print("  📦 正在安装依赖 …")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")]
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\n  ⏸️  已中断")
        return 1


def cmd_cli():
    if not check_deps():
        return 1
    # 切换到 backend 目录再执行 cli.py 主逻辑
    os.chdir(BACKEND)
    from cli import main
    try:
        main()
    except KeyboardInterrupt:
        print("\n  👋 再见")
    return 0


def cmd_web(port=7788, host="127.0.0.1"):
    if not check_deps():
        return 1
    os.chdir(BACKEND)
    from app import run_server
    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        print("\n  🌐 Web UI 已停止")
    return 0


def interactive():
    print(LOGO)
    print(f"  {Fore.LIGHTBLACK_EX}Python {platform.python_version()} · {platform.system()} {platform.release()}{Style.RESET_ALL}")
    print()
    if not check_deps():
        # 提示安装
        ans = input("  是否现在自动安装依赖？[Y/n] > ").strip().lower()
        if ans in ("", "y", "yes"):
            rc = cmd_install()
            if rc != 0:
                print("  安装失败，请手动执行 pip install -r requirements.txt")
                return 1
        else:
            return 1
    print()
    print(f"  {Fore.LIGHTYELLOW_EX}[1]{Style.RESET_ALL} 🌐 Web UI 模式  （默认端口 7788，浏览器里交互）")
    print(f"  {Fore.LIGHTYELLOW_EX}[2]{Style.RESET_ALL} ⌨️  控制台 CLI 模式  （纯命令行，有富文本表格）")
    print(f"  {Fore.LIGHTYELLOW_EX}[3]{Style.RESET_ALL} 📦 安装 / 重装依赖")
    print(f"  {Fore.LIGHTYELLOW_EX}[0]{Style.RESET_ALL} 🚪 退出")
    while True:
        try:
            choice = input(f"\n  {Fore.LIGHTMAGENTA_EX}❯{Style.RESET_ALL} 请选择模式 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if choice == "1":
            port_s = input(f"  端口 (回车=7788) > ").strip()
            port = int(port_s) if port_s.isdigit() else 7788
            return cmd_web(port=port)
        if choice == "2":
            return cmd_cli()
        if choice == "3":
            cmd_install(); continue
        if choice in ("0", "q", "quit", "exit"):
            print("  👋 再见"); return 0
        print(f"  {Fore.LIGHTRED_EX}× 无效选项{Style.RESET_ALL}")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(interactive() or 0)

    mode = args[0].lower()
    rest = args[1:]

    if mode in ("install", "setup", "dep", "deps"):
        sys.exit(cmd_install() or 0)

    if mode in ("cli", "cmd", "console", "terminal"):
        sys.exit(cmd_cli() or 0)

    if mode in ("web", "serve", "server", "ui", "gui"):
        port = 7788
        host = "127.0.0.1"
        i = 0
        while i < len(rest):
            a = rest[i]
            if a in ("-p", "--port") and i + 1 < len(rest):
                port = int(rest[i+1]); i += 2
            elif a.startswith("--port="):
                port = int(a.split("=",1)[1]); i += 1
            elif a in ("-H", "--host") and i + 1 < len(rest):
                host = rest[i+1]; i += 2
            elif a.startswith("--host="):
                host = a.split("=",1)[1]; i += 1
            elif a == "--public":
                host = "0.0.0.0"; i += 1
            elif a.isdigit():
                port = int(a); i += 1
            else:
                i += 1
        sys.exit(cmd_web(port=port, host=host) or 0)

    if mode in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)

    print(f"未知参数：{mode}\n")
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
