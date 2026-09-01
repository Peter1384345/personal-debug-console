@echo off
REM 个人调试台 · Windows 一键打包脚本
REM 直接双击运行，或在 cmd / PowerShell 里执行 build.bat

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "NAME=PersonalDebugConsole"
set "LABEL=个人调试台"
set "ENTRY=start.py"

echo ==^> 清理旧产物 ...
if exist dist  rmdir /s /q dist
if exist build rmdir /s /q build
if exist "%NAME%.spec" del /q "%NAME%.spec"

echo ==^> 安装 / 校验 PyInstaller ...
python -m pip install --quiet --upgrade pyinstaller || goto :err

echo ==^> 开始打包 ...
pyinstaller ^
  -F ^
  --clean ^
  -n "%NAME%" ^
  --add-data "frontend;frontend" ^
  --collect-all plyer ^
  --collect-all psutil ^
  --collect-all flask ^
  --collect-all flask_cors ^
  --hidden-import plyer.platforms.linux.notification ^
  --hidden-import plyer.platforms.macosx.notification ^
  --hidden-import plyer.platforms.win.notification ^
  "%ENTRY%" || goto :err

echo.
echo ============================================================
echo   ✅ 打包完成！产物位于 dist\%NAME%.exe (label=%LABEL%)
echo ============================================================
dir /b dist
exit /b 0

:err
echo.
echo ❌ 打包失败，请查看上方日志
exit /b 1
