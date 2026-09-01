#!/usr/bin/env bash
# 个人调试台 · 一键打包脚本（当前平台）
# Linux / macOS 运行：./build.sh
# Windows 运行：     见 build.bat
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

NAME="个人调试台"
ENTRY="start.py"
DIST_DIR="$HERE/dist"
BUILD_DIR="$HERE/build"

echo "==> 清理旧产物 …"
rm -rf "$DIST_DIR" "$BUILD_DIR" "${NAME}.spec"

echo "==> 安装 / 校验 PyInstaller …"
python3 -m pip install --quiet --upgrade pyinstaller

SEP=":"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) SEP=";" ;;
esac

echo "==> 开始打包 (add-data separator: '$SEP') …"
pyinstaller \
  -F \
  --clean \
  -n "$NAME" \
  --add-data "frontend${SEP}frontend" \
  --collect-all plyer \
  --collect-all psutil \
  --collect-all flask \
  --collect-all flask_cors \
  --hidden-import plyer.platforms.linux.notification \
  --hidden-import plyer.platforms.macosx.notification \
  --hidden-import plyer.platforms.win.notification \
  "$ENTRY"

echo
echo "✅ 打包完成！产物："
ls -lh "$DIST_DIR"
