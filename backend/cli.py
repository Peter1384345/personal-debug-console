"""
纯控制台（CLI）模式入口
- 交互式菜单：磁盘体检 / 进程扫描 / 浏览目录 / 定位路径 / 通知告警
- 支持 rich 富文本渲染，降级 ASCII 友好
"""

import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from modules import disk_manager, service_monitor, notifier  # noqa: E402
from modules.notifier import (  # noqa: E402
    print_panel, print_table, progress_bar, rich_available, _console,
)
from colorama import Fore, Style, init  # noqa: E402

init()


SEP = Fore.LIGHTBLACK_EX + "─" * 68 + Style.RESET_ALL
LOGO = rf"""
{Fore.LIGHTCYAN_EX}       ╭──────────────────────────────────╮
{Fore.LIGHTCYAN_EX}       │     🔧  个 人 调 试 台  🔧      │
{Fore.LIGHTCYAN_EX}       │   Debug Console · Command Line  │
{Fore.LIGHTCYAN_EX}       ╰──────────────────────────────────╯
{Style.RESET_ALL}"""


def header(title: str):
    print()
    print(SEP)
    print(f"  {Fore.LIGHTMAGENTA_EX}✦{Style.RESET_ALL}  {Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(SEP)


# ───────────────────────── 磁盘体检 ─────────────────────────

def cmd_disk_check():
    header("💽 磁盘使用体检")
    disks = disk_manager.list_disks()
    if not disks:
        print(f"{Fore.LIGHTRED_EX}未检测到任何磁盘（可能权限不足）{Style.RESET_ALL}")
        return
    cols = [
        {"label": "挂载点", "key": "mp", "style": "cyan"},
        {"label": "类型", "key": "fs", "style": "white"},
        {"label": "总量", "key": "t", "justify": "right"},
        {"label": "已用", "key": "u", "justify": "right", "style": "yellow"},
        {"label": "空闲", "key": "f", "justify": "right", "style": "green"},
        {"label": "使用率", "key": "p", "justify": "left"},
    ]
    rows = []
    styles = {}
    for i, d in enumerate(disks):
        percent = d["percent"]
        rows.append([
            d["mountpoint"], d["fstype"],
            f"{d['total_gb']} GB", f"{d['used_gb']} GB", f"{d['free_gb']} GB",
            progress_bar(percent, 24),
        ])
        if d["status"] == "danger":
            styles[i] = "bold red"
        elif d["status"] == "warning":
            styles[i] = "bold yellow"
    print_table("磁盘分区", cols, rows, styles)

    # 告警通知
    dangerous = [d for d in disks if d["status"] in ("danger", "warning")]
    if dangerous:
        msg_lines = []
        for d in dangerous:
            tag = "🔴 告急" if d["status"] == "danger" else "🟡 预警"
            msg_lines.append(f"{tag} {d['mountpoint']}  已用 {d['used_gb']}/{d['total_gb']} GB ({d['percent']}%)")
        notifier.desktop_notify(
            f"磁盘告警：{len(dangerous)} 个分区吃紧",
            "\n".join(msg_lines), warn_mode=True,
        )
    else:
        notifier.desktop_notify("磁盘状态良好 ✅", "所有分区使用率健康")


# ───────────────────────── 目录浏览 ─────────────────────────

def cmd_browse():
    header("📂 目录浏览器（按类型着色）")
    default_path = os.path.expanduser("~")
    prompt = f"  请输入要浏览的路径 [回车=主目录 {default_path}]: "
    path = input(prompt).strip() or default_path

    ans = input("  是否递归估算子文件夹大小？(会慢一些) [y/N]: ").strip().lower()
    include_dir_size = ans == "y"

    print(f"  正在扫描 {path} ...")
    data = disk_manager.browse_directory(path, include_dir_size=include_dir_size)
    if "error" in data:
        print(f"{Fore.LIGHTRED_EX}× 错误：{data['error']}{Style.RESET_ALL}")
        return

    print(f"\n  当前路径：{Fore.LIGHTCYAN_EX}{data['current_path']}{Style.RESET_ALL}"
          f"   共 {Fore.LIGHTGREEN_EX}{data['total_items']}{Style.RESET_ALL} 项")

    # Summary
    cols = [
        {"label": "类型", "style": "cyan"},
        {"label": "数量", "justify": "right"},
        {"label": "大小", "justify": "right"},
    ]
    rows = []
    for key, v in data["summary"].items():
        if v["count"] == 0:
            continue
        rows.append([f"{v['label']}", f"{v['count']}", v["size_human"]])
    if rows:
        print_table("📊 按类型汇总", cols, rows)

    # Items 前 30 条
    cols2 = [
        {"label": "图标", "style": "white"},
        {"label": "名称", "style": "cyan", "overflow": "fold"},
        {"label": "类型", "style": "white"},
        {"label": "大小", "justify": "right"},
    ]
    rows2 = []
    styles2 = {}
    items = data["items"][:40]
    for i, it in enumerate(items):
        # 简易着色：根据文件类型加前缀色块
        rows2.append([it["icon"], it["name"], it["category_label"], it["size_human"] if it["size_bytes"] else "-"])
    title = f"条目预览（前 {len(items)} / {data['total_items']}）"
    print_table(title, cols2, rows2, styles2)

    # 提示可打开
    while True:
        ans = input("\n  🔎 输入序号打开文件夹/文件，输入 0 返回主菜单 > ").strip()
        if not ans or ans == "0":
            return
        try:
            idx = int(ans) - 1
            if 0 <= idx < len(items):
                target = items[idx]["path"]
                r = notifier.open_in_file_manager(target, select=os.path.isfile(target))
                print(f"  → {r['msg']}")
            else:
                print("  × 序号越界")
        except ValueError:
            # 当作路径再浏览一次
            if os.path.exists(ans):
                # 复用逻辑：递归一次会很麻烦，简单提示
                print(f"  💡 提示：输入 'b' 后在下一轮粘贴该路径可继续浏览")
            else:
                print("  × 请输入数字")


# ───────────────────────── 进程扫描 ─────────────────────────

def cmd_process_scan():
    header("🛰️  后台服务扫描 & 分类")
    print("  收集进程 CPU/内存数据，约需 2 秒 ...")
    procs = service_monitor.list_processes(sort_by="mem", include_cmdline=True)
    if procs and "error" in procs[0]:
        print(f"{Fore.LIGHTRED_EX}× {procs[0]['error']}{Style.RESET_ALL}")
        return
    summary = service_monitor.process_summary(procs)

    # 汇总面板
    body = (
        f"  总进程数：{summary['total']}　　总内存：{summary['total_mem_human']}　　总CPU：{summary['total_cpu']:.1f}%\n"
        f"  🟢 有益  {summary['beneficial']['count']:>4} 个   内存 {summary['beneficial']['mem_human']}\n"
        f"  🟠 无益  {summary['unnecessary']['count']:>4} 个   内存 {summary['unnecessary']['mem_human']}\n"
        f"  ⚪ 未知  {summary['unknown']['count']:>4} 个   内存 {summary['unknown']['mem_human']}"
    )
    print_panel("📊 进程分类总览", body, "cyan")

    # 推送通知
    notifier.notify_unnecessary_procs(procs, top_n=5)

    # Top 无益/可疑
    bad = [p for p in procs if p.get("category") == "unnecessary"][:12]
    if bad:
        cols = [
            {"label": "PID", "justify": "right", "style": "yellow"},
            {"label": "进程名", "style": "cyan"},
            {"label": "内存", "justify": "right"},
            {"label": "CPU%", "justify": "right"},
            {"label": "分类原因", "overflow": "fold"},
        ]
        rows = []
        for p in bad:
            mem_s = f"{p['mem_rss_mb']:.0f}MB" if p['mem_rss_mb'] < 1024 else f"{p['mem_rss_mb']/1024:.1f}GB"
            rows.append([
                str(p["pid"]), p["name"], mem_s, f"{p['cpu_percent']:.1f}", p.get("reason", "")
            ])
        print_table("⚠️  无益/可疑进程 TOP", cols, rows)

    # Top 内存榜
    cols2 = [
        {"label": "PID", "justify": "right", "style": "cyan"},
        {"label": "进程名", "style": "white"},
        {"label": "分类", "style": "magenta"},
        {"label": "内存", "justify": "right"},
        {"label": "CPU%", "justify": "right"},
    ]
    rows2 = []
    styles2 = {}
    for i, p in enumerate(procs[:15]):
        mem_s = f"{p['mem_rss_mb']:.0f}MB" if p['mem_rss_mb'] < 1024 else f"{p['mem_rss_mb']/1024:.1f}GB"
        rows2.append([
            str(p["pid"]), p["name"], p["category_label"], mem_s, f"{p['cpu_percent']:.1f}"
        ])
        if p["category"] == "unnecessary":
            styles2[i] = "bold orange1"
        elif p["category"] == "beneficial":
            styles2[i] = "green"
    print_table("🔥 内存占用榜 TOP 15", cols2, rows2, styles2)

    # 交互：定位或杀死
    while True:
        print("\n  子操作：[L] 定位进程路径  [K] 终止进程  [N] 再次推送可疑项通知  [回车] 返回")
        action = input("  > ").strip().lower()
        if not action:
            return
        if action == "n":
            n = notifier.notify_unnecessary_procs(procs)
            print(f"  → 已通知 {n} 条")
            continue
        if action in ("l", "k"):
            try:
                pid = int(input("  请输入 PID > ").strip())
            except ValueError:
                print("  × PID 必须是数字")
                continue
            if action == "l":
                info = service_monitor.locate_process(pid)
                if not info.get("ok"):
                    print(f"  × {info.get('msg')}")
                    continue
                print(f"  {Fore.LIGHTCYAN_EX}进程名{Style.RESET_ALL}：{info['name']}")
                print(f"  {Fore.LIGHTCYAN_EX}EXE路径{Style.RESET_ALL}：{info['exe_path'] or '(未知)'}")
                print(f"  {Fore.LIGHTCYAN_EX}所在目录{Style.RESET_ALL}：{info['exe_dir'] or '-'}")
                print(f"  {Fore.LIGHTCYAN_EX}工作目录{Style.RESET_ALL}：{info['cwd'] or '-'}")
                if info.get("cmdline"):
                    cl = info["cmdline"]
                    if len(cl) > 200:
                        cl = cl[:200] + " …"
                    print(f"  {Fore.LIGHTCYAN_EX}命令行{Style.RESET_ALL}：{cl}")
                if info.get("exe_path"):
                    r = notifier.open_in_file_manager(info["exe_dir"] or info["exe_path"],
                                                     select=bool(info.get("exe_exists")))
                    print(f"  → {r['msg']}")
            else:
                force = input("  强制终止？（y/N）> ").strip().lower() == "y"
                r = service_monitor.kill_process(pid, force=force)
                print(f"  → {'✅' if r['ok'] else '❌'} {r['msg']}")


# ───────────────────────── 主菜单 ─────────────────────────

MENU = [
    ("1", "💽  磁盘使用体检（带桌面通知告警）", cmd_disk_check),
    ("2", "📂  目录浏览器 + 按类型着色", cmd_browse),
    ("3", "🛰️  后台服务扫描 & 分类（有益/无益/未知）", cmd_process_scan),
    ("4", "🌐  切换到 Web UI 模式", "__WEB__"),
    ("0", "🚪  退出调试台", "__EXIT__"),
]


def main():
    # 欢迎
    if rich_available():
        _console.print(LOGO, highlight=False)
        _console.print(
            "  [dim]Tip：输入编号可执行对应操作；任何时候按 Ctrl+C 可打断[/dim]"
        )
    else:
        print(LOGO)
        print("  (安装 rich 可获得更漂亮的输出：pip install rich)")

    while True:
        try:
            print("\n" + SEP)
            print(f"  {Style.BRIGHT}📋 主菜单{Style.RESET_ALL}")
            print(SEP)
            for k, desc, _ in MENU:
                pad = " " if len(k) == 1 else ""
                print(f"  {Fore.LIGHTYELLOW_EX}[{k}]{Style.RESET_ALL}{pad} {desc}")
            choice = input(f"\n  {Fore.LIGHTMAGENTA_EX}❯{Style.RESET_ALL} 选择操作 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  👋 再见，祝调试愉快")
            return

        match = None
        for k, _, fn in MENU:
            if choice == k:
                match = fn
                break
        if match is None:
            print(f"  {Fore.LIGHTRED_EX}× 无效选项{Style.RESET_ALL}")
            continue
        if match == "__EXIT__":
            print("  👋 再见")
            return
        if match == "__WEB__":
            # 启动 web 服务器
            from app import run_server
            try:
                run_server()
            except KeyboardInterrupt:
                print("\n  🌐 Web UI 已停止，返回命令行")
            continue
        try:
            match()
        except KeyboardInterrupt:
            print("\n  ⏸️  已中断当前操作")
        except Exception as e:
            print(f"  {Fore.LIGHTRED_EX}× 操作出错：{e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
