#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键把「个人调试台」打包成单个 exe。

用法：
    pip install pyinstaller
    python packaging/build_exe.py

产物：
    dist/PersonalDebugConsole.exe       单文件，可直接分发
    dist/PersonalDebugConsole-Portable.html

说明：
    --onefile 每次启动会把资源解包到临时目录，所以首次启动稍慢（约 1~3 秒），
    换来的是「一个文件拷走就能跑」，对这种小工具更合适。
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "PersonalDebugConsole"
ENTRY = ROOT / "packaging" / "launcher.py"
ICON = ROOT / "packaging" / "app.ico"
PORTABLE_HTML = ROOT / "portable" / "PersonalDebugConsole-Portable.html"

DIST_DIR = ROOT / "dist"
WORK_DIR = ROOT / "build_pyinstaller"   # 已在 .gitignore 中忽略


def build_pyinstaller_args() -> list:
    sep = ";" if platform.system() == "Windows" else ":"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",                     # 保留控制台：能看到地址、能 Ctrl+C 退出
        "--name", NAME,
        "--paths", str(ROOT / "backend"),
        # 前端静态资源整个塞进去
        "--add-data", f"{ROOT / 'frontend'}{sep}frontend",
        # plyer 的桌面通知后端是运行时动态加载的，必须整包收集
        "--collect-all", "plyer",
        "--hidden-import", "app",
        "--hidden-import", "cli",
        "--hidden-import", "modules",
        "--hidden-import", "modules.disk_manager",
        "--hidden-import", "modules.service_monitor",
        "--hidden-import", "modules.notifier",
        "--hidden-import", "colorama",
        "--hidden-import", "rich",
        # 用不上的 GUI 栈，砍掉能省好几 MB
        "--exclude-module", "tkinter",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide2",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pytest",
        "--distpath", str(DIST_DIR),
        "--workpath", str(WORK_DIR),
        "--specpath", str(WORK_DIR),
    ]

    if ICON.exists():
        args += ["--icon", str(ICON)]

    args.append(str(ENTRY))
    return args


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def main() -> int:
    if not ENTRY.exists():
        print(f"× 找不到入口脚本：{ENTRY}")
        return 1
    if not (ROOT / "frontend" / "index.html").exists():
        print(f"× 找不到前端目录：{ROOT / 'frontend'}")
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    args = build_pyinstaller_args()
    print("▶", " ".join(a if " " not in a else f'"{a}"' for a in args[3:]))
    print()

    rc = subprocess.call(args)
    if rc != 0:
        print(f"\n× PyInstaller 退出码 {rc}，打包失败。")
        return rc

    exe = DIST_DIR / (NAME + (".exe" if platform.system() == "Windows" else ""))
    if not exe.exists():
        print(f"× 没找到产物：{exe}")
        return 1

    print("\n" + "-" * 54)
    print(f"  ✓ {exe.name}   {human_size(exe.stat().st_size)}")
    print(f"    位置：{exe}")

    if PORTABLE_HTML.exists():
        target = DIST_DIR / PORTABLE_HTML.name
        shutil.copy2(PORTABLE_HTML, target)
        print(f"  ✓ {target.name}   {human_size(target.stat().st_size)}")

    print("-" * 54)
    print("\n  双击 exe 即可启动，会自动打开浏览器。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
