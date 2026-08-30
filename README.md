# 个人调试台 · 下载分支

这个 `release` 分支只放分发产物，不包含源码。想读源码请回 `main` 分支。

## 下载

| 文件 | 说明 | 大小 |
|------|------|------|
| [PersonalDebugConsole.exe](./PersonalDebugConsole.exe) | Windows 桌面版，双击运行 | 22.1 MB |
| [PersonalDebugConsole-Portable.html](./PersonalDebugConsole-Portable.html) | 便携版网页，单文件免安装 | 53.1 KB |

> 更友好的下载/介绍页：通过 GitHub Pages 访问本分支的根目录 `index.html`。

## 快速开始

1. 下载 `PersonalDebugConsole.exe`（推荐）。
2. 双击运行，会自动打开浏览器访问本地服务。
3. 服务地址默认在 `http://127.0.0.1:7788`，端口被占会自动顺延。
4. `Ctrl+C` 或关闭窗口退出。

## 便携版网页怎么用

- 单独打开：展示浏览器可见的系统信息（CPU 线程、屏幕、内存、网络、电池等）。
- 搭配 exe 打开：当本机 exe 在跑时，便携版会自动连上 `127.0.0.1:7788`，解锁磁盘、文件、进程全能力。

## 校验

```text
b9b919dd3b4ed8df4b01edc6f4f927b1c91df663e8e0451dbd968df3ef3d9dca *PersonalDebugConsole.exe
4086ddf033c1ed08003e9e2c49c42eedcade08273b93127c4ab014f6d8502de2 *PersonalDebugConsole-Portable.html
```

也可查看 [SHA256SUMS.txt](./SHA256SUMS.txt)。

## 版本

```json
{
  "version": "1.0.0",
  "date": "2026-08-31"
}
```
