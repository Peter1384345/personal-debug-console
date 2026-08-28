"""
后台服务 / 进程监控模块
- 采集全部进程信息（CPU、内存、路径、用户、命令行）
- 基于规则 + 白名单/黑名单 + 启发式判断 有益/无益/未知
- 支持按路径定位进程、杀死进程
"""

import os
import time
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Tuple, Optional

try:
    import psutil
except ImportError:
    psutil = None


# ─────────────────────── 进程分类白名单 / 黑名单 ───────────────────────

# 【有益进程】关键系统服务、常见开发工具、日常软件
# 规则：进程名(小写) → (可信等级 0~3, 说明)
# 3=操作系统核心，2=厂商签名软件，1=常见安全/开发工具
BENEFICIAL_WHITELIST: Dict[str, Tuple[int, str]] = {
    # ===== Windows 核心 =====
    "system": (3, "Windows 系统内核"),
    "registry": (3, "Windows 注册表进程"),
    "smss.exe": (3, "会话管理器"),
    "csrss.exe": (3, "客户端/服务器运行时"),
    "wininit.exe": (3, "Windows 启动进程"),
    "winlogon.exe": (3, "登录进程"),
    "services.exe": (3, "服务控制管理器"),
    "lsass.exe": (3, "本地安全机构"),
    "svchost.exe": (3, "服务宿主进程"),
    "explorer.exe": (3, "文件资源管理器"),
    "taskmgr.exe": (3, "任务管理器"),
    "dwm.exe": (3, "桌面窗口管理器"),
    "sihost.exe": (3, "Shell 基础设施"),
    "ctfmon.exe": (3, "CTF 加载器"),
    "searchindexer.exe": (3, "Windows 搜索索引"),
    "searchhost.exe": (3, "Windows 搜索宿主"),
    "runtimebroker.exe": (2, "运行时代理"),
    "backgroundtaskhost.exe": (2, "后台任务宿主"),
    "fontdrvhost.exe": (2, "字体驱动宿主"),
    "audiodg.exe": (2, "音频设备图形隔离"),
    "spoolsv.exe": (3, "打印后台处理"),
    "conhost.exe": (2, "控制台窗口宿主"),
    "dllhost.exe": (2, "COM  surrogate"),
    "shellexperiencehost.exe": (2, "Shell 体验宿主"),
    "startmenuexperiencehost.exe": (2, "开始菜单宿主"),
    "textinputhost.exe": (2, "文本输入宿主"),
    "securityhealthservice.exe": (2, "Windows 安全中心服务"),
    "securityhealthsystray.exe": (2, "Windows 安全中心托盘"),
    "msmpeng.exe": (2, "Windows Defender 杀毒引擎"),
    "mssense.exe": (2, "Windows Defender ATP"),
    "wmiprvse.exe": (2, "WMI 提供程序宿主"),
    "wudfhost.exe": (2, "Windows 驱动程序基础"),
    "userinit.exe": (3, "用户初始化"),
    "cmd.exe": (2, "命令提示符"),
    "powershell.exe": (2, "PowerShell"),
    "pwsh.exe": (2, "PowerShell 7+"),
    "python.exe": (2, "Python 解释器"),
    "pythonw.exe": (2, "Python GUI 解释器"),
    "node.exe": (1, "Node.js 运行时"),
    "java.exe": (1, "Java 虚拟机"),
    "javaw.exe": (1, "Java GUI 虚拟机"),

    # ===== Linux / macOS 核心 =====
    "systemd": (3, "系统服务管理器"),
    "init": (3, "init 进程"),
    "kthreadd": (3, "内核线程"),
    "ksoftirqd": (3, "软中断守护"),
    "kworker": (3, "内核工作队列"),
    "rcu_sched": (3, "RCU 调度"),
    "migration": (3, "迁移进程"),
    "watchdog": (3, "看门狗"),
    "udevd": (3, "设备管理"),
    "systemd-journald": (3, "systemd 日志"),
    "systemd-logind": (3, "systemd 登录"),
    "systemd-udevd": (3, "systemd udev"),
    "dbus-daemon": (3, "D-Bus 消息总线"),
    "dbus-session": (3, "D-Bus 会话"),
    "sshd": (3, "SSH 守护"),
    "cron": (3, "计划任务"),
    "crond": (3, "计划任务"),
    "login": (3, "登录"),
    "bash": (2, "Bash shell"),
    "zsh": (2, "Zsh shell"),
    "fish": (2, "Fish shell"),
    "sudo": (2, "sudo"),
    "apt": (2, "apt 包管理"),
    "dnf": (2, "dnf 包管理"),
    "yum": (2, "yum 包管理"),
    "pacman": (2, "pacman 包管理"),
    "launchd": (3, "macOS 服务管理"),
    "kernel_task": (3, "macOS 内核任务"),
    "launchservicesd": (3, "macOS 启动服务"),
    "coreservicesd": (3, "macOS 核心服务"),
    "windowmanager": (3, "窗口管理器"),
    "gnome-shell": (3, "GNOME Shell"),
    "kwin_x11": (3, "KDE 窗口管理器"),
    "xfwm4": (3, "XFCE 窗口管理器"),
    "plasmashell": (3, "KDE Plasma"),
    "dock": (3, "macOS Dock"),
    "finder": (3, "macOS Finder"),

    # ===== 常见浏览器 / 开发工具（可信） =====
    "chrome.exe": (2, "Google Chrome"),
    "msedge.exe": (2, "Microsoft Edge"),
    "firefox.exe": (2, "Firefox"),
    "brave.exe": (2, "Brave 浏览器"),
    "safari": (2, "Safari"),
    "code.exe": (1, "VS Code 编辑器"),
    "codium.exe": (1, "VSCodium"),
    "idea64.exe": (1, "IntelliJ IDEA"),
    "pycharm64.exe": (1, "PyCharm"),
    "webstorm64.exe": (1, "WebStorm"),
    "goland64.exe": (1, "GoLand"),
    "clion64.exe": (1, "CLion"),
    "eclipse.exe": (1, "Eclipse"),
    "jetbrains-toolbox.exe": (1, "JetBrains Toolbox"),
    "docker.exe": (1, "Docker"),
    "dockerd.exe": (1, "Docker 守护"),
    "com.docker.service": (1, "Docker 服务"),
    "wsl.exe": (1, "WSL"),
    "wslhost.exe": (1, "WSL 宿主"),
    "vmmem": (2, "虚拟机内存"),
    "vmware.exe": (1, "VMware"),
    "virtualboxvm.exe": (1, "VirtualBox"),
    "git.exe": (1, "Git"),
    "git-bash.exe": (1, "Git Bash"),
    "npm.exe": (1, "npm"),
    "pnpm.exe": (1, "pnpm"),
    "yarn.exe": (1, "yarn"),
    "cmake.exe": (1, "CMake"),
    "gcc.exe": (1, "GCC"),
    "g++.exe": (1, "G++"),
    "clang.exe": (1, "Clang"),
    "rustc.exe": (1, "Rustc"),
    "cargo.exe": (1, "Cargo"),
    "go.exe": (1, "Go 编译器"),

    # ===== 常用办公 / 通信 =====
    "outlook.exe": (2, "Outlook 邮件"),
    "winword.exe": (2, "Microsoft Word"),
    "excel.exe": (2, "Microsoft Excel"),
    "powerpnt.exe": (2, "Microsoft PowerPoint"),
    "onenote.exe": (2, "OneNote"),
    "teams.exe": (2, "Microsoft Teams"),
    "msteams.exe": (2, "Teams (新版)"),
    "wechat.exe": (2, "微信"),
    "weixin.exe": (2, "微信"),
    "qq.exe": (2, "QQ"),
    "tim.exe": (2, "TIM"),
    "dingtalk.exe": (2, "钉钉"),
    "lark.exe": (2, "飞书"),
    "feishu.exe": (2, "飞书"),
    "slack.exe": (2, "Slack"),
    "telegram.exe": (2, "Telegram"),
    "discord.exe": (2, "Discord"),
    "whatsapp.exe": (2, "WhatsApp"),
    "spotify.exe": (2, "Spotify"),
    "notepad++.exe": (1, "Notepad++"),
    "obs64.exe": (1, "OBS Studio"),
    "obs32.exe": (1, "OBS Studio"),
    "vlc.exe": (2, "VLC 播放器"),
    "potplayermini.exe": (2, "PotPlayer"),
    "7zfm.exe": (2, "7-Zip"),
    "7zg.exe": (2, "7-Zip"),
    "everything.exe": (2, "Everything 搜索"),
    "sublime_text.exe": (1, "Sublime Text"),

    # ===== 显卡 / 驱动 =====
    "nvcontainer.exe": (2, "NVIDIA 容器"),
    "nvdisplay.container.exe": (2, "NVIDIA 显示容器"),
    "nvidia share.exe": (2, "NVIDIA Share"),
    "amd software:adrenalin.exe": (2, "AMD Adrenalin"),
    "radeonsoftware.exe": (2, "AMD Radeon Software"),
    "igfxem.exe": (2, "Intel 显卡模块"),
    "igfxCUIService.exe": (2, "Intel 显卡 UI 服务"),
}

# 【无益进程】广告、推广、挖矿、流氓软件、可疑项
HARMFUL_KEYWORDS: List[Tuple[str, str]] = [
    # 广告 / 推广
    ("ads", "广告模块"),
    ("advert", "广告程序"),
    ("promo", "推广"),
    ("offer", "捆绑推广"),
    ("bundle", "捆绑安装"),
    ("updater_", "可疑升级程序"),
    ("update_checker", "可疑升级检查"),
    ("gamebox", "游戏盒子/推广"),
    ("gamemini", "小游戏推广"),
    ("minigame", "小游戏推广"),
    ("desktop_pet", "桌面宠物（非必要）"),
    ("desktoppet", "桌面宠物"),
    ("desktopnews", "桌面新闻（弹窗）"),
    ("popup", "弹窗程序"),
    ("notice_", "可疑通知程序"),
    ("float", "悬浮窗推广"),
    ("screensaver", "屏幕保护（可疑）"),
    ("lunabox", "LunaBox 捆绑"),
    ("2345", "2345 系列（谨慎）"),
    ("haozip", "好压（含推广）"),
    ("360sd", "360 杀毒"),
    ("360tray", "360 托盘"),
    ("360safe", "360 安全卫士"),
    ("360chrome", "360 浏览器"),
    ("zhuDongFangYu", "主动防御（国产安全系）"),
    ("QQPCRTP", "QQ 软件管理"),
    ("Tencentdl", "腾讯下载组件"),
    ("ksoftmgr", "金山软件管理"),
    ("kwatch", "金山毒霸"),
    ("kxetray", "金山毒霸托盘"),
    ("ksafesvc", "金山卫士"),
    ("baidu", "百度系列（谨慎）"),
    ("baiduan", "百度杀毒"),
    ("baiduantivirus", "百度杀毒"),
    ("Sogou", "搜狗（含推广）"),
    ("sogoucloud", "搜狗云"),
    ("youdao", "有道"),

    # 挖矿 / 远程木马 / 后门特征
    ("xmrig", "XMRig 挖矿程序"),
    ("minerd", "挖矿程序"),
    ("cpuminer", "CPU 挖矿"),
    ("ethminer", "以太坊挖矿"),
    ("claymore", "Claymore 挖矿"),
    ("nicehash", "NiceHash 挖矿"),
    ("phoenixminer", "凤凰挖矿"),
    ("teamviewer", "TeamViewer（远程工具）"),
    ("anydesk", "AnyDesk（远程工具）"),
    ("supremo", "SupRemo（远程工具）"),
    ("radmin", "Radmin 远程"),
    ("vnc", "VNC 远程"),
    ("trojan", "木马特征"),
    ("rat_", "远程访问木马"),
    ("c2_", "C2 服务器特征"),
    ("mimikatz", "Mimikatz 凭证窃取"),
    ("cobaltstrike", "CobaltStrike"),
    ("meterpreter", "Meterpreter"),
    ("ransom", "勒索特征"),
    ("decrypt", "勒索解密器"),

    # 非常见位置启动
    ("temp\\", "临时目录启动（可疑）"),
    ("tmp/", "临时目录启动（可疑）"),
    ("appdata\\roaming\\", "漫游配置启动（谨慎）"),
    ("programdata\\", "ProgramData 启动（谨慎）"),
    ("recycle.bin", "回收站启动（高度可疑）"),
]


# ─────────────────────── 进程分类 ───────────────────────

@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    name: str
    username: str
    cpu_percent: float
    mem_percent: float
    mem_rss_mb: float
    num_threads: int
    status: str
    create_time: float
    exe_path: str
    cmdline: str
    cwd: str
    # 分类相关
    category: str           # beneficial / unnecessary / unknown
    category_label: str     # 人类可读
    trust_level: int        # 0 未知，1~3 可信等级，-1 可疑
    reason: str             # 分类原因
    color: str              # 前端显示色
    bg: str

    def to_dict(self):
        return asdict(self)


def _color_for_category(cat: str, trust: int) -> Tuple[str, str]:
    if cat == "beneficial":
        if trust >= 3:
            return "#22d3ee", "rgba(34,211,238,0.12)"   # 青色 系统核心
        if trust == 2:
            return "#34d399", "rgba(52,211,153,0.12)"   # 绿色 可信
        return "#a3e635", "rgba(163,230,53,0.12)"       # 黄绿
    if cat == "unnecessary":
        if trust == -2:
            return "#ef4444", "rgba(239,68,68,0.16)"    # 红 高危
        return "#f97316", "rgba(249,115,22,0.14)"       # 橙 无益
    return "#94a3b8", "rgba(148,163,184,0.12)"         # 灰 未知


def _classify(name: str, exe: str, cmdline: str) -> Tuple[str, str, int, str]:
    """返回 (category, label, trust_level, reason)"""
    name_low = name.lower()

    # 1) 白名单命中
    if name_low in BENEFICIAL_WHITELIST:
        trust, desc = BENEFICIAL_WHITELIST[name_low]
        return "beneficial", "有益", trust, f"白名单：{desc}"

    # 路径是 Windows 系统目录的 → 算作有益但未知具体名
    if exe:
        exe_low = exe.lower()
        if "\\windows\\system32\\" in exe_low or "\\windows\\syswow64\\" in exe_low:
            return "beneficial", "有益（系统目录）", 2, f"位于系统目录: {exe}"
        if "/usr/bin/" in exe_low or "/usr/sbin/" in exe_low or "/sbin/" in exe_low or "/bin/" == exe_low[:5]:
            return "beneficial", "有益（系统目录）", 2, f"位于系统目录: {exe}"
        if "/system/library/" in exe_low or "/library/" in exe_low:
            return "beneficial", "有益（系统目录）", 2, f"位于系统目录: {exe}"
        if "\\program files\\" in exe_low or "\\program files (x86)\\" in exe_low:
            return "unknown", "未知（程序目录）", 1, f"位于 Program Files: {exe}"
        if "/applications/" in exe_low:
            return "unknown", "未知（应用程序）", 1, f"位于 /Applications: {exe}"

    # 2) 关键词黑名单
    haystack = f"{name} {exe} {cmdline}".lower()
    for kw, reason in HARMFUL_KEYWORDS:
        if kw.lower() in haystack:
            return "unnecessary", "无益/可疑", -1, f"命中关键词「{kw}」：{reason}"

    # 3) 启发式：命令行含挖矿池地址、隐藏窗口参数等
    if any(x in haystack for x in ["stratum+tcp", "stratum+ssl", "pool.", "mine.", "miningpool"]):
        return "unnecessary", "无益/可疑", -2, "疑似挖矿（命令行含矿池参数）"
    if any(x in haystack for x in [" -hidden ", " /hidden ", " --hidden "]):
        return "unnecessary", "无益/可疑", -1, "进程以隐藏模式启动"
    if any(x in haystack for x in ["powershell -enc", "powershell -e ", "cmd /c powershell", "base64"]):
        return "unnecessary", "无益/可疑", -2, "命令行含编码执行痕迹"
    if ".tmp\\" in haystack or ".tmp/" in haystack or haystack.endswith(".tmp"):
        return "unnecessary", "无益/可疑", -1, "临时文件执行"

    return "unknown", "未知", 0, "未命中规则，需人工判断"


def _human_mem(b: int) -> float:
    return round(b / (1024 * 1024), 2)


def list_processes(sort_by: str = "mem", include_cmdline: bool = True) -> List[Dict]:
    """获取全部进程并分类"""
    if not psutil:
        return [{"error": "缺少 psutil 依赖，请先安装：pip install psutil"}]

    results: List[ProcessInfo] = []

    # 第一次 CPU 采样，预热
    for p in psutil.process_iter(["pid"]):
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(0.25)

    for p in psutil.process_iter([
        "pid", "ppid", "name", "username", "cpu_percent",
        "memory_percent", "memory_info", "num_threads",
        "status", "create_time", "exe", "cmdline", "cwd",
    ]):
        try:
            info = p.info
            exe = info.get("exe") or ""
            cmd_list = info.get("cmdline") or []
            cmdline = " ".join(cmd_list) if include_cmdline and cmd_list else ""
            cwd = ""
            try:
                cwd = info.get("cwd") or p.cwd()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            cat, cat_label, trust, reason = _classify(info.get("name", ""), exe, cmdline)
            color, bg = _color_for_category(cat, trust)
            mem_info = info.get("memory_info")
            mem_rss_mb = _human_mem(mem_info.rss) if mem_info else 0.0

            results.append(ProcessInfo(
                pid=info.get("pid", 0),
                ppid=info.get("ppid", 0),
                name=info.get("name") or "(未知)",
                username=info.get("username") or "",
                cpu_percent=round(info.get("cpu_percent") or 0.0, 1),
                mem_percent=round(info.get("memory_percent") or 0.0, 2),
                mem_rss_mb=mem_rss_mb,
                num_threads=info.get("num_threads") or 0,
                status=info.get("status") or "",
                create_time=info.get("create_time") or 0,
                exe_path=exe,
                cmdline=cmdline,
                cwd=cwd,
                category=cat,
                category_label=cat_label,
                trust_level=trust,
                reason=reason,
                color=color,
                bg=bg,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 排序
    sort_key = {
        "mem": lambda x: -x.mem_rss_mb,
        "cpu": lambda x: -x.cpu_percent,
        "pid": lambda x: x.pid,
        "name": lambda x: x.name.lower(),
    }.get(sort_by, lambda x: -x.mem_rss_mb)
    results.sort(key=sort_key)

    return [r.to_dict() for r in results]


def process_summary(procs: Optional[List[Dict]] = None) -> Dict:
    """统计各分类数量、内存、CPU"""
    if procs is None:
        procs = list_processes(sort_by="mem", include_cmdline=False)
    summary = {
        "total": 0,
        "beneficial": {"count": 0, "mem_mb": 0.0, "cpu": 0.0, "label": "有益",
                       "color": "#34d399", "bg": "rgba(52,211,153,0.12)"},
        "unnecessary": {"count": 0, "mem_mb": 0.0, "cpu": 0.0, "label": "无益/可疑",
                        "color": "#f97316", "bg": "rgba(249,115,22,0.14)"},
        "unknown": {"count": 0, "mem_mb": 0.0, "cpu": 0.0, "label": "未知",
                    "color": "#94a3b8", "bg": "rgba(148,163,184,0.12)"},
        "total_mem_mb": 0.0,
        "total_cpu": 0.0,
    }
    for p in procs:
        summary["total"] += 1
        summary["total_mem_mb"] += p.get("mem_rss_mb", 0)
        summary["total_cpu"] += p.get("cpu_percent", 0)
        cat = p.get("category", "unknown")
        if cat not in summary:
            cat = "unknown"
        summary[cat]["count"] += 1
        summary[cat]["mem_mb"] += p.get("mem_rss_mb", 0)
        summary[cat]["cpu"] += p.get("cpu_percent", 0)

    # 人类可读
    for k in ("beneficial", "unnecessary", "unknown"):
        m = summary[k]["mem_mb"]
        summary[k]["mem_human"] = f"{m:.1f} MB" if m < 1024 else f"{m/1024:.2f} GB"
    m = summary["total_mem_mb"]
    summary["total_mem_human"] = f"{m:.1f} MB" if m < 1024 else f"{m/1024:.2f} GB"
    return summary


def kill_process(pid: int, force: bool = False) -> Dict:
    """杀死指定进程"""
    if not psutil:
        return {"ok": False, "msg": "缺少 psutil 依赖"}
    try:
        p = psutil.Process(pid)
        name = p.name()
        if force:
            p.kill()
        else:
            p.terminate()
        return {"ok": True, "msg": f"已发送 {'强制' if force else ''}终止信号: PID {pid} ({name})"}
    except psutil.NoSuchProcess:
        return {"ok": False, "msg": f"进程不存在: PID {pid}"}
    except psutil.AccessDenied:
        return {"ok": False, "msg": f"权限不足，无法终止 PID {pid}（尝试管理员/root）"}
    except Exception as e:
        return {"ok": False, "msg": f"终止失败: {e}"}


def locate_process(pid: int) -> Dict:
    """获取进程的完整路径 + 命令行 + 工作目录，供控制台/文件管理器定位"""
    if not psutil:
        return {"ok": False, "msg": "缺少 psutil 依赖"}
    try:
        p = psutil.Process(pid)
        try:
            exe = p.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            exe = ""
        try:
            cwd = p.cwd()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            cwd = ""
        try:
            cmdline = " ".join(p.cmdline())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            cmdline = ""
        return {
            "ok": True,
            "pid": pid,
            "name": p.name(),
            "exe_path": exe,
            "exe_exists": bool(exe) and os.path.exists(exe),
            "exe_dir": os.path.dirname(exe) if exe else "",
            "cwd": cwd,
            "cmdline": cmdline,
        }
    except psutil.NoSuchProcess:
        return {"ok": False, "msg": f"进程不存在: PID {pid}"}
    except Exception as e:
        return {"ok": False, "msg": f"查询失败: {e}"}
