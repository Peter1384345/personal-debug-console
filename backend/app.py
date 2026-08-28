"""
Flask Web API：为前端提供磁盘/进程数据
- 同时也托管静态前端页面
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# 让模块导入在不同运行路径下都正确
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from modules import disk_manager, service_monitor, notifier  # noqa: E402


FRONTEND_DIR = _BACKEND_DIR.parent / "frontend"
STATIC_DIR = FRONTEND_DIR  # send_from_directory 直接从这里取文件

app = Flask(__name__, static_folder=None)
CORS(app)


# ──────────────────────── 静态页面托管 ────────────────────────

@app.route("/")
def _index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def _static(filename):
    target = STATIC_DIR / filename
    if target.exists() and target.is_file():
        return send_from_directory(STATIC_DIR, filename)
    # SPA 兜底
    return send_from_directory(STATIC_DIR, "index.html")


# ──────────────────────── API: 磁盘与文件 ────────────────────────

@app.get("/api/disks")
def api_disks():
    return jsonify({"ok": True, "data": disk_manager.list_disks()})


@app.get("/api/categories")
def api_categories():
    return jsonify({"ok": True, "data": disk_manager.get_categories()})


@app.get("/api/browse")
def api_browse():
    path = request.args.get("path") or None
    include_dir_size = request.args.get("dirsize", "0") in ("1", "true", "yes")
    result = disk_manager.browse_directory(path, include_dir_size=include_dir_size)
    if "error" in result:
        return jsonify({"ok": False, "msg": result["error"], "data": result}), 400
    return jsonify({"ok": True, "data": result})


@app.post("/api/open-path")
def api_open_path():
    body = request.get_json(silent=True) or {}
    path = body.get("path")
    select = bool(body.get("select", False))
    where = body.get("where", "file")  # file | terminal
    if where == "terminal":
        res = notifier.open_in_terminal(path)
    else:
        res = notifier.open_in_file_manager(path, select=select)
    return jsonify(res)


# ──────────────────────── API: 进程监控 ────────────────────────

@app.get("/api/processes")
def api_processes():
    sort_by = request.args.get("sort", "mem")
    include_cmd = request.args.get("cmdline", "1") in ("1", "true", "yes")
    category = request.args.get("category")  # beneficial/unnecessary/unknown
    search = (request.args.get("q") or "").strip().lower()
    procs = service_monitor.list_processes(sort_by=sort_by, include_cmdline=include_cmd)

    if category:
        procs = [p for p in procs if p.get("category") == category]
    if search:
        procs = [p for p in procs if search in p.get("name", "").lower()
                 or search in (p.get("exe_path") or "").lower()
                 or search in str(p.get("pid"))]

    summary = service_monitor.process_summary(procs)
    return jsonify({"ok": True, "data": {"list": procs, "summary": summary}})


@app.get("/api/process/summary")
def api_proc_summary():
    procs = service_monitor.list_processes(sort_by="mem", include_cmdline=False)
    return jsonify({"ok": True, "data": service_monitor.process_summary(procs)})


@app.post("/api/process/notify")
def api_proc_notify():
    body = request.get_json(silent=True) or {}
    top_n = int(body.get("top_n", 5))
    procs = service_monitor.list_processes(sort_by="mem", include_cmdline=False)
    n = notifier.notify_unnecessary_procs(procs, top_n=top_n)
    return jsonify({"ok": True, "notified": n, "msg": f"已通知 {n} 条可疑项"})


@app.get("/api/process/<int:pid>/locate")
def api_proc_locate(pid):
    return jsonify(service_monitor.locate_process(pid))


@app.post("/api/process/<int:pid>/kill")
def api_proc_kill(pid):
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))
    return jsonify(service_monitor.kill_process(pid, force=force))


@app.post("/api/notify")
def api_notify():
    body = request.get_json(silent=True) or {}
    notifier.desktop_notify(
        title=body.get("title", "个人调试台"),
        message=body.get("message", ""),
        timeout=int(body.get("timeout", 8)),
        warn_mode=bool(body.get("warn", False)),
    )
    return jsonify({"ok": True})


# ──────────────────────── 启动入口 ────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 7788, debug: bool = False):
    print(f"\n🚀 个人调试台 Web UI 已启动：http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_server()
