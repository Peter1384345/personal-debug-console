"""
磁盘与文件管理模块
- 扫描所有盘符/分区的使用情况
- 浏览目录内容并按文件类型分配图标颜色
"""

import os
import shutil
import string
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

try:
    import psutil
except ImportError:
    psutil = None


# ───────────────────────── 文件类型 → 颜色/图标映射 ─────────────────────────

FILE_CATEGORIES = [
    {
        "key": "folder",
        "label": "文件夹",
        "icon": "📁",
        "color": "#60a5fa",
        "bg": "rgba(96,165,250,0.15)",
        "exts": [],
    },
    {
        "key": "image",
        "label": "图片",
        "icon": "🖼️",
        "color": "#f472b6",
        "bg": "rgba(244,114,182,0.15)",
        "exts": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic"],
    },
    {
        "key": "doc",
        "label": "文档",
        "icon": "📄",
        "color": "#34d399",
        "bg": "rgba(52,211,153,0.15)",
        "exts": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".rtf", ".odt", ".csv"],
    },
    {
        "key": "audio",
        "label": "音频",
        "icon": "🎵",
        "color": "#a78bfa",
        "bg": "rgba(167,139,250,0.15)",
        "exts": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    },
    {
        "key": "video",
        "label": "视频",
        "icon": "🎬",
        "color": "#fb923c",
        "bg": "rgba(251,146,60,0.15)",
        "exts": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"],
    },
    {
        "key": "code",
        "label": "代码",
        "icon": "💻",
        "color": "#22d3ee",
        "bg": "rgba(34,211,238,0.15)",
        "exts": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
                 ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".rb",
                 ".php", ".swift", ".kt", ".sh", ".bat", ".ps1", ".json", ".xml", ".yaml", ".yml"],
    },
    {
        "key": "archive",
        "label": "压缩包",
        "icon": "🗜️",
        "color": "#facc15",
        "bg": "rgba(250,204,21,0.15)",
        "exts": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"],
    },
    {
        "key": "exe",
        "label": "可执行",
        "icon": "⚙️",
        "color": "#ef4444",
        "bg": "rgba(239,68,68,0.15)",
        "exts": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage", ".apk"],
    },
    {
        "key": "font",
        "label": "字体",
        "icon": "🔤",
        "color": "#e879f9",
        "bg": "rgba(232,121,249,0.15)",
        "exts": [".ttf", ".otf", ".woff", ".woff2", ".eot"],
    },
    {
        "key": "other",
        "label": "其他",
        "icon": "❓",
        "color": "#94a3b8",
        "bg": "rgba(148,163,184,0.15)",
        "exts": [],
    },
]


def categorize(path: str, is_dir: bool) -> Dict:
    if is_dir:
        return FILE_CATEGORIES[0]
    ext = Path(path).suffix.lower()
    for cat in FILE_CATEGORIES[1:-1]:  # 跳过 folder 和 other
        if ext in cat["exts"]:
            return cat
    return FILE_CATEGORIES[-1]  # other


# ───────────────────────────── 盘符 / 分区 ─────────────────────────────

@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    status: str  # normal / warning / danger

    def to_dict(self):
        return asdict(self)


def _status_from_percent(p: float) -> str:
    if p >= 90:
        return "danger"
    if p >= 75:
        return "warning"
    return "normal"


def list_disks() -> List[Dict]:
    """返回所有磁盘分区的使用情况（含 Linux / macOS / Windows）"""
    disks: List[DiskInfo] = []

    if psutil:
        for part in psutil.disk_partitions(all=False):
            try:
                usage = shutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            total = usage.total / (1024 ** 3)
            used = usage.used / (1024 ** 3)
            free = usage.free / (1024 ** 3)
            percent = (used / total * 100) if total else 0
            disks.append(DiskInfo(
                device=part.device,
                mountpoint=part.mountpoint,
                fstype=part.fstype or "未知",
                total_gb=round(total, 2),
                used_gb=round(used, 2),
                free_gb=round(free, 2),
                percent=round(percent, 1),
                status=_status_from_percent(percent),
            ))
    else:
        # Windows 盘符兜底方案
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        usage = shutil.disk_usage(drive)
                        total = usage.total / (1024 ** 3)
                        used = usage.used / (1024 ** 3)
                        percent = (used / total * 100) if total else 0
                        disks.append(DiskInfo(
                            device=drive,
                            mountpoint=drive,
                            fstype="NTFS",
                            total_gb=round(total, 2),
                            used_gb=round(used, 2),
                            free_gb=round(usage.free / (1024 ** 3), 2),
                            percent=round(percent, 1),
                            status=_status_from_percent(percent),
                        ))
                    except (PermissionError, OSError):
                        continue

    return [d.to_dict() for d in disks]


# ───────────────────────────── 目录浏览 ─────────────────────────────

@dataclass
class FileItem:
    name: str
    path: str
    is_dir: bool
    size_bytes: int
    size_human: str
    category_key: str
    category_label: str
    icon: str
    color: str
    bg: str
    modified: float

    def to_dict(self):
        return asdict(self)


def _human_size(n: int) -> str:
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < step:
            return f"{n:.1f} {unit}"
        n /= step
    return f"{n:.1f} PB"


def _safe_dir_size(path: str, depth: int = 2) -> int:
    """估算文件夹大小（避免过深导致卡顿）"""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False) and depth > 0:
                        total += _safe_dir_size(entry.path, depth - 1)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total


def browse_directory(path: Optional[str] = None, include_dir_size: bool = False) -> Dict:
    """
    浏览指定目录
    返回: { current_path, parent, items: [...], summary: {...} }
    """
    if not path:
        # 默认：用户主目录
        path = os.path.expanduser("~")
    path = os.path.abspath(path)

    if not os.path.exists(path):
        return {"error": f"路径不存在: {path}", "current_path": path}

    if not os.path.isdir(path):
        return {"error": f"不是目录: {path}", "current_path": path}

    items: List[FileItem] = []
    summary = {c["key"]: {"count": 0, "size": 0, "label": c["label"], "color": c["color"]} for c in FILE_CATEGORIES}

    parent = os.path.dirname(path) if os.path.dirname(path) != path else None

    try:
        with os.scandir(path) as scanner:
            entries = list(scanner)
    except (PermissionError, OSError) as e:
        return {"error": f"无法访问: {e}", "current_path": path, "parent": parent}

    # 排序：文件夹在前，然后按名称
    entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))

    for entry in entries:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
            if is_dir:
                size = _safe_dir_size(entry.path, 1) if include_dir_size else 0
            else:
                size = entry.stat(follow_symlinks=False).st_size
            modified = entry.stat(follow_symlinks=False).st_mtime
        except (PermissionError, OSError):
            is_dir = entry.is_dir()
            size = 0
            modified = 0

        cat = categorize(entry.path, is_dir)
        item = FileItem(
            name=entry.name,
            path=entry.path,
            is_dir=is_dir,
            size_bytes=size,
            size_human=_human_size(size),
            category_key=cat["key"],
            category_label=cat["label"],
            icon=cat["icon"],
            color=cat["color"],
            bg=cat["bg"],
            modified=modified,
        )
        items.append(item)

        s = summary[cat["key"]]
        s["count"] += 1
        s["size"] += size

    # summary 里 size 加人类可读
    for v in summary.values():
        v["size_human"] = _human_size(v["size"])

    return {
        "current_path": path,
        "parent": parent,
        "items": [i.to_dict() for i in items],
        "total_items": len(items),
        "summary": summary,
    }


def get_categories() -> List[Dict]:
    """返回所有文件类型的分类信息，供前端 legend 使用"""
    return [
        {k: c[k] for k in ("key", "label", "icon", "color", "bg")}
        for c in FILE_CATEGORIES
    ]
