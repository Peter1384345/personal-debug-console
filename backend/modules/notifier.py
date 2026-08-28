"""
通知与路径定位模块
- 跨平台桌面通知（plyer → 降级到 colorama 控制台彩色输出）
- 在文件管理器中打开指定路径
- 富文本控制台输出（rich）
"""

import os
import sys
import platform
import subprocess
import threading
from typing import Optional

from colorama import Fore, Style, init as _colorama_init
_colorama_init()


# ─────────────────────── 桌面通知 ───────────────────────

_NOTIFIER_OK = False
try:
    from plyer import notification as _plyer_notify
    _NOTIFIER_OK = True
except Exception:
    _NOTIFIER_OK = False


def desktop_notify(title: str, message: str, timeout: int = 8,
                   app_name: str = "个人调试台", warn_mode: bool = False) -> bool:
    """
    发送跨平台桌面通知
    warn_mode=True 时会附加一个控制台高亮警告
    """
    ok = False
    if _NOTIFIER_OK:
        try:
            _plyer_notify.notify(
                title=title,
                message=message,
                app_name=app_name,
                timeout=timeout,
            )
            ok = True
        except Exception:
            ok = False
    # 控制台彩色兜底
    prefix_color = Fore.LIGHTRED_EX if warn_mode else Fore.LIGHTCYAN_EX
    marker = "⚠️" if warn_mode else "🔔"
    msg = (
        f"\n{prefix_color}{marker}  {Style.BRIGHT}{title}{Style.RESET_ALL}\n"
        f"      {Fore.WHITE}{message}{Style.RESET_ALL}\n"
    )
    sys.stdout.write(msg)
    sys.stdout.flush()
    return ok


def notify_unnecessary_procs(procs: list, top_n: int = 5) -> int:
    """
    对无益/可疑进程批量推送通知
    返回通知的条数
    """
    if not procs:
        return 0
    bad = [p for p in procs if p.get("category") == "unnecessary"]
    if not bad:
        desktop_notify("进程体检完毕 ✅", "未发现明显无益或可疑进程")
        return 0
    # 按内存取前 N 条合并
    bad.sort(key=lambda x: -(x.get("mem_rss_mb") or 0))
    top = bad[:top_n]
    lines = []
    for p in top:
        mem = p.get("mem_rss_mb") or 0
        mem_s = f"{mem:.0f}MB" if mem < 1024 else f"{mem/1024:.1f}GB"
        lines.append(f"• PID{p['pid']} {p.get('name','?')} [{mem_s}] {p.get('reason','')}")
    body = "\n".join(lines)
    if len(bad) > top_n:
        body += f"\n… 另外还有 {len(bad) - top_n} 条可疑进程"
    desktop_notify(
        f"发现 {len(bad)} 个无益/可疑进程 ⚠️",
        body,
        warn_mode=True,
    )
    return len(bad)


# ─────────────────────── 打开路径 ───────────────────────

def open_in_file_manager(path: str, select: bool = False) -> dict:
    """
    在系统文件管理器中打开路径
    select=True 时定位到具体文件并高亮选中
    """
    if not path:
        return {"ok": False, "msg": "路径为空"}
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return {"ok": False, "msg": f"路径不存在: {path}"}

    system = platform.system()
    try:
        if system == "Windows":
            if select and os.path.isfile(path):
                # 选中文件
                subprocess.Popen(["explorer", "/select,", path])
            else:
                os.startfile(path)  # type: ignore[attr-defined]
        elif system == "Darwin":
            if select and os.path.isfile(path):
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["open", path])
        else:  # Linux / BSD
            # 尝试 xdg-open，其次常见文件管理器
            try:
                subprocess.Popen(["xdg-open", path])
            except FileNotFoundError:
                for fm in ["nautilus", "dolphin", "thunar", "pcmanfm", "nemo"]:
                    try:
                        subprocess.Popen([fm, path])
                        break
                    except FileNotFoundError:
                        continue
        return {"ok": True, "msg": f"已在文件管理器打开: {path}"}
    except Exception as e:
        return {"ok": False, "msg": f"打开失败: {e}", "path": path}


def open_in_terminal(path: str) -> dict:
    """在终端中打开指定目录"""
    if not path:
        return {"ok": False, "msg": "路径为空"}
    if not os.path.isdir(path):
        path = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isdir(path):
        return {"ok": False, "msg": f"不是有效目录: {path}"}
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["cmd", "/K", "cd /d", path], cwd=path)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal", path])
        else:
            for term in ["gnome-terminal", "konsole", "xfce4-terminal", "x-terminal-emulator", "xterm"]:
                try:
                    subprocess.Popen([term, "--working-directory", path])
                    break
                except FileNotFoundError:
                    continue
        return {"ok": True, "msg": f"已在终端打开: {path}"}
    except Exception as e:
        return {"ok": False, "msg": f"打开失败: {e}"}


# ─────────────────────── 富文本控制台渲染 ───────────────────────

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import (
        BarColumn, Progress, SpinnerColumn, TextColumn,
    )
    from rich.text import Text
    _RICH_OK = True
    _console = Console()
except Exception:
    _RICH_OK = False
    _console = None


def rich_available() -> bool:
    return _RICH_OK


def print_panel(title: str, body: str, style: str = "cyan"):
    if not _RICH_OK:
        print(f"[{title}] {body}")
        return
    _console.print(Panel(body, title=title, border_style=style, expand=False))


def print_table(title: str, columns: list, rows: list, styles: Optional[dict] = None):
    """
    columns: [{'key','label','style','justify'}]
    rows: [list]
    styles: {row_index: 'style'}
    """
    if not _RICH_OK:
        print(f"\n=== {title} ===")
        header = " | ".join(c["label"] for c in columns)
        print(header)
        print("-" * len(header))
        for r in rows:
            print(" | ".join(str(x) for x in r))
        return
    t = Table(title=title, show_lines=False, header_style="bold magenta")
    for c in columns:
        t.add_column(c["label"], style=c.get("style", "white"),
                     justify=c.get("justify", "left"),
                     overflow=c.get("overflow", "fold"))
    for idx, r in enumerate(rows):
        s = styles.get(idx) if styles else None
        if s:
            t.add_row(*[Text(str(x), style=s) for x in r])
        else:
            t.add_row(*[str(x) for x in r])
    _console.print(t)


def progress_bar(title: str, percent: float, width: int = 40) -> str:
    """渲染一个简易 ASCII 进度条"""
    filled = int(width * percent / 100)
    filled = max(0, min(width, filled))
    if percent >= 90:
        color = Fore.LIGHTRED_EX
    elif percent >= 75:
        color = Fore.LIGHTYELLOW_EX
    else:
        color = Fore.LIGHTGREEN_EX
    bar = "█" * filled + "░" * (width - filled)
    return f"{color}{bar}{Style.RESET_ALL} {percent:>5.1f}%"
