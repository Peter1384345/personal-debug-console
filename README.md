# 🔧 个人调试台 · Personal Debug Console

> 一款走「手绘 + 暗夜暖调贴纸风」的系统调试工具箱。既能在浏览器里美美的看，也能一条命令直接在终端里交互。
>
> 刻意避开了常见 AI 模板冷蓝色 + 完美对称卡片的风格，换成手写标题、旋转贴纸卡、涂鸦 SVG 装饰、纸带胶布角标等「有温度」的元素。

---

## ⬇️ 直接下载（无需安装 Python）

> 所有分发产物都在 [`release`](https://github.com/Peter1384345/personal-debug-console/tree/release) 分支，下载表如下：

| 版本 | 文件 | 说明 |
|---|---|---|
| 🖥️ **Windows 桌面版** | [`PersonalDebugConsole.exe`](https://github.com/Peter1384345/personal-debug-console/raw/release/PersonalDebugConsole.exe) | 单个 exe，双击运行 |
| 📄 **便携版网页** | [`PersonalDebugConsole-Portable.html`](https://github.com/Peter1384345/personal-debug-console/raw/release/PersonalDebugConsole-Portable.html) | 一个 HTML 文件，可拷进 U 盘 |
| 🌐 **下载主页** | [GitHub Pages](https://peter1384345.github.io/personal-debug-console/) | 含介绍、版本、SHA256 校验 |

桌面版双击后会自动启动本地服务并打开浏览器；便携版单独打开时展示浏览器可见的系统信息，若本机 exe 在跑则自动连上后端，解锁磁盘 / 文件 / 进程全能力。

---

## ✨ 核心功能

### ① 磁盘 & 文件管理（彩色图标 + 告警）
- 自动扫描所有磁盘分区（Windows 盘符 / Linux / macOS 挂载点通吃）
- 可视化进度条显示使用率：`正常 / 预警 ≥75% / 告急 ≥90%`
- 到阈值的分区会**自动弹桌面通知 + 控制台高亮告警**
- **按文件类型用 10 种配色分类**，一眼就能看出图片 / 视频 / 代码 / 压缩包 / 可执行 ……
- 点击任意条目可以**直接在系统文件管理器里打开**（支持选中具体文件高亮）
- 面包屑 + 上级 / 主目录 / 刷新一键跳，估算子目录大小可切换

| 类型 | 图标 | 颜色 | 说明 |
|---|---|---|---|
| 📁 文件夹 | 蓝 `#60a5fa` | 目录 |
| 🖼️ 图片 | 粉 `#f472b6` | jpg/png/gif/svg/webp/heic… |
| 📄 文档 | 绿 `#34d399` | pdf/docx/xlsx/pptx/txt/md/csv… |
| 🎵 音频 | 紫 `#a78bfa` | mp3/wav/flac/m4a… |
| 🎬 视频 | 橙 `#fb923c` | mp4/mkv/mov/avi/webm… |
| 💻 代码 | 青 `#22d3ee` | py/js/ts/java/go/rs/sh… |
| 🗜️ 压缩包 | 黄 `#facc15` | zip/rar/7z/tar.gz… |
| ⚙️ 可执行 | 红 `#ef4444` | exe/msi/dmg/deb/apk… |
| 🔤 字体 | 品红 `#e879f9` | ttf/otf/woff2… |
| ❓ 其他 | 灰 `#94a3b8` | 未命中以上的扩展 |

### ② 后台服务监控（有益 / 无益 / 未知 自动分类）
- 采集每个进程的 **PID / PPID / 用户名 / CPU% / 内存 / 线程数 / 启动时间 / EXE 路径 / 命令行 / 工作目录**
- **三层分类引擎**，内置超过 **150+ 条规则**：
  - **白名单匹配**（100+ 条）：系统核心（svchost.exe / systemd / kernel_task）、可信浏览器与 IDE、驱动容器、常用办公/通讯软件…… 按可信度分 1~3 级
  - **路径规则**：位于 `System32 / /usr/bin / /System/Library / Program Files / Applications` 自动视为可信
  - **关键词黑名单**（60+ 条）：广告推广、捆绑、矿机、远控木马、勒索特征、命令行编码执行、临时目录启动
  - **启发式**：命令行含矿池地址 / 隐藏窗口参数 / `powershell -enc` / `.tmp` 执行 → 标记无益/可疑
- **一键桌面通知**可疑进程（按内存排序取 Top 5）
- 任意进程可 **📍 定位路径**（在文件管理器打开 EXE 所在目录并高亮），或直接 **🗑️ 终止 / 强制终止**
- 支持按分类筛选、搜索、点击表头排序

### ③ 控制台通知 & 路径指定
- 优先走 **plyer 跨平台桌面通知**（Windows / macOS / Linux 都出弹框）
- 失败时自动降级为 **colorama 控制台彩色告警**（不会漏消息）
- 定位路径：自动调用 `explorer /select`、`open -R`、`xdg-open` + 常见 Linux 桌面文件管理器
- 可选「在终端里打开这个目录」
- CLI 模式全部基于 **rich 富文本表格 + Panel 面板**，也可降级普通 ASCII

---

## 🗂️ 项目结构

```
personal-debug-console/
├── start.py                     # 统一入口（必看）
├── requirements.txt             # 依赖清单
├── backend/
│   ├── app.py                   # Flask Web 后端 + 静态页面托管
│   ├── cli.py                   # 命令行交互模式（纯终端 Rich 表格）
│   └── modules/
│       ├── __init__.py
│       ├── disk_manager.py      # 磁盘扫描 + 文件浏览 + 颜色分类
│       ├── service_monitor.py   # 进程扫描 + 有益/无益/未知 分类引擎
│       └── notifier.py          # 桌面通知 + 路径打开 + Rich 控制台渲染
├── frontend/
│   ├── index.html               # 主页（手绘装饰 + SVG 图标）
│   ├── css/style.css            # 暗夜暖调贴纸风格样式（~700 行）
│   └── js/app.js                # Tab 切换、磁盘/进程 UI、Toast、排序筛选
├── packaging/
│   ├── launcher.py              # 桌面版启动入口：自动挑端口 + 自动开浏览器
│   ├── build_exe.py             # 一键打包脚本
│   ├── make_icon.py             # 生成 exe 图标
│   └── app.ico                  # 打包用图标
└── portable/
    └── PersonalDebugConsole-Portable.html   # 单文件便携版网页
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd personal-debug-console
python start.py install        # 或：pip install -r requirements.txt
```

> 推荐 **Python ≥ 3.9**。Linux 上如果没有 x11/D-Bus 桌面环境，桌面通知会自动降级为控制台彩色提示，功能不受影响。

### 2. 启动

#### 方式 A：交互式选择（最简单）
```bash
python start.py
# ↓ 选 1 = Web UI，选 2 = CLI
```

#### 方式 B：直接启动 Web UI
```bash
python start.py web                       # 默认 http://127.0.0.1:7788
python start.py web -p 8888               # 指定端口
python start.py web --host 0.0.0.0        # 局域网可访问（小心权限）
```

打开浏览器访问 `http://127.0.0.1:7788` 即可看到界面。

#### 方式 C：直接进入命令行模式
```bash
python start.py cli
```
```
  ╭──────────────────────────────────╮
  │     🔧  个 人 调 试 台  🔧      │
  │   Debug Console · Command Line  │
  ╰──────────────────────────────────╯
  [1] 💽  磁盘使用体检（带桌面通知告警）
  [2] 📂  目录浏览器 + 按类型着色
  [3] 🛰️  后台服务扫描 & 分类（有益/无益/未知）
  [4] 🌐  切换到 Web UI 模式
  [0] 🚪  退出调试台
  ❯ 选择操作 >
```

---

## 📦 一键下载（推荐！）

> 不想折腾 Python 环境？直接下载对应平台的单文件可执行程序，**双击即用**。
> 便携 HTML 版单文件即可打开，展示完整 UI 设计（演示模式，访问真实系统请用二进制版）。

### 🍱 产物总览

| 平台 / 产物 | 下载 | 大小 | 说明 |
|---|---|---|---|
| 🪟 **Windows (x64)** | [⬇️ PersonalDebugConsole-v1.0.0-windows.exe][dl-win] | ~32 MB | 单文件 exe · 双击直接启动 Web UI |
| 🐧 **Linux (x64)** | [⬇️ PersonalDebugConsole-v1.0.0-linux][dl-linux] | ~24 MB | ELF 单文件 · 加执行权限后 `./` 运行 |
| 🍎 **macOS (x64/arm64)** | [⬇️ PersonalDebugConsole-v1.0.0-macos][dl-macos] | ~32 MB | Mach-O 单文件 · `chmod +x` 后运行 |
| 🌐 **便携 HTML 演示版** | [⬇️ PersonalDebugConsole-portable.html][dl-portable] | ~100 KB | 单文件 · 浏览器直接打开 · 零依赖离线可用 |

> **自动构建**：推送到 `v*` tag 会触发 [GitHub Actions 工作流][workflow] 自动打包三平台并上传 Release。
> 注：CI 产物文件名用 ASCII（`PersonalDebugConsole-…`）以避免跨平台编码问题，运行后内部界面标题仍为「个人调试台」。

[dl-win]:      https://github.com/Peter1384345/personal-debug-console/releases/download/v1.0.0/PersonalDebugConsole-v1.0.0-windows.exe
[dl-linux]:    https://github.com/Peter1384345/personal-debug-console/releases/download/v1.0.0/PersonalDebugConsole-v1.0.0-linux
[dl-macos]:    https://github.com/Peter1384345/personal-debug-console/releases/download/v1.0.0/PersonalDebugConsole-v1.0.0-macos
[dl-portable]: https://github.com/Peter1384345/personal-debug-console/raw/builds/v1.0.0/portable.html
[workflow]:    https://github.com/Peter1384345/personal-debug-console/actions/workflows/build-release.yml

### 🧱 二进制版运行方式

```bash
# Linux / macOS — 加执行权限后双击或命令行启动
chmod +x PersonalDebugConsole-v1.0.0-linux
./PersonalDebugConsole-v1.0.0-linux                  # 交互式：选 1 = Web UI
./PersonalDebugConsole-v1.0.0-linux web              # 直接启动 Web UI（默认 7788 端口）
./PersonalDebugConsole-v1.0.0-linux cli              # 直接进入命令行模式

# Windows — 双击 .exe 即可
# 或在 PowerShell 里：
.\PersonalDebugConsole-v1.0.0-windows.exe web -p 8888
```

### 🖨️ 从源码自行打包（贡献者 / 自定义）

项目自带 **一键打包脚本**：

| 平台 | 脚本 | 命令 |
|---|---|---|
| Windows | `build.bat` | 双击或 `cmd /c build.bat` |
| Linux / macOS | `build.sh` | `bash build.sh` |
| 跨平台（手动） | PyInstaller | 见下方命令 |

```bash
pip install pyinstaller
cd personal-debug-console

# Windows：
pyinstaller -F -n PersonalDebugConsole --add-data "frontend;frontend" --collect-all plyer --collect-all psutil --collect-all flask --collect-all flask_cors start.py

# macOS / Linux：
pyinstaller -F -n PersonalDebugConsole --add-data "frontend:frontend" --collect-all plyer --collect-all psutil --collect-all flask --collect-all flask_cors start.py
```

产物在 `dist/PersonalDebugConsole(.exe)`，双击即可启动（运行后界面标题显示「个人调试台」）。

---

## 🎨 设计亮点（和 AI 模板风的区别）

| 一般 AI 生成 UI | 本项目 |
|---|---|
| 冷蓝色主色、科技感渐变 | **暖棕黑底 + 奶油色字** + 金色/玫红主渐变 |
| 完美对齐、统一圆角、严格栅格 | **卡片随机 ±1° 旋转**、便签贴纸 + 胶带角标、不规则形状 |
| iconfont / Lucide / Heroicons 三套图标 | 全站 **手写 SVG 装饰**（星星、箭头、花、闪电）+ Emoji 语义图标 |
| Inter / SF Pro 标准 UI 字 | **Caveat 手写体做标题** + JetBrains Mono 做数据 + Inter 正文 |
| 毛玻璃太纯 + 模糊到虚 | **纸质噪点纹理叠加** + 10 余种不同透明度/饱和度的玻璃层级 |
| 对称四象限 Dashboard | 左 1.35 : 右 1 的**不对称两栏**、2×2 统计卡与长条报告卡混合 |
| Toast 一律右下角白底黑字 | 玻璃拟态 + 动画进出场 + 按等级换色 |

---

## 📡 API 接口一览

万一你想接其他前端，直接 HTTP 调就行：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/disks` | 所有分区使用率 |
| GET  | `/api/categories` | 10 种文件分类（含颜色/图标） |
| GET  | `/api/browse?path=…&dirsize=1` | 浏览目录 |
| POST | `/api/open-path` `{path,select,where}` | 文件管理器 / 终端打开路径 |
| GET  | `/api/processes?sort=mem&category=unnecessary&q=chrome` | 进程列表 + 汇总 |
| GET  | `/api/process/<pid>/locate` | 查询进程 EXE / CWD / 命令行 |
| POST | `/api/process/<pid>/kill` `{force:true}` | 终止进程 |
| POST | `/api/process/notify` `{top_n:5}` | 桌面通知可疑进程 |
| POST | `/api/notify` `{title,message,warn,timeout}` | 通用桌面通知 |

---

## ⚠️ 权限说明

- **Linux**：部分系统进程（PID 1 等）和其他用户进程需要 `sudo` 才能看到路径/命令行
- **Windows**：终止系统服务需要管理员权限的终端
- **macOS**：定位 `~/Library` 下的路径需要在「系统设置 → 隐私 → 文件与文件夹」里给终端/ Python 授权

授权越多，进程表越完整。

---

## 🧩 可扩展点

- `backend/modules/disk_manager.py:FILE_CATEGORIES` → 增加/修改文件类型配色
- `backend/modules/service_monitor.py:BENEFICIAL_WHITELIST` → 为常用程序追加白名单
- `backend/modules/service_monitor.py:HARMFUL_KEYWORDS` → 补充黑名单关键词
- `frontend/css/style.css` 顶部的 `:root` 变量 → 一键换肤

祝调试愉快 🎉
