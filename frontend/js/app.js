/* ================================================================
   个人调试台 · Web UI 交互逻辑
   原生 JS，无框架依赖
   ================================================================ */

const API_BASE = "";  // 同源部署

// ----------------------- 工具函数 -----------------------

const $  = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));

function fmtBytes(bytes) {
  if (!bytes && bytes !== 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

function fmtMB(mb) {
  if (!mb && mb !== 0) return "—";
  return mb >= 1024 ? `${(mb/1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`;
}

async function apiGet(url, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const u = `${API_BASE}${url}${qs ? "?" + qs : ""}`;
  const r = await fetch(u, { headers: { "Accept": "application/json" } });
  return await r.json();
}
async function apiPost(url, body = {}) {
  const r = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return await r.json();
}

// ----------------------- Toast -----------------------

let toastIdSeq = 0;
function toast(title, message = "", type = "info", duration = 3800) {
  const icons = {
    info:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`,
    ok:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>`,
    warn:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>`,
  };
  const el = document.createElement("div");
  el.className = `toast ${type === "info" ? "" : type}`;
  el.id = `toast-${++toastIdSeq}`;
  el.innerHTML = `
    <div class="ico">${icons[type] ?? icons.info}</div>
    <div><b>${title}</b><span>${message}</span></div>
  `;
  $("#toast-wrap").appendChild(el);
  setTimeout(() => {
    el.classList.add("closing");
    setTimeout(() => el.remove(), 320);
  }, duration);
}

// ----------------------- 时钟 -----------------------

function tickClock() {
  const pad = (n) => String(n).padStart(2, "0");
  const d = new Date();
  const weekdays = ["周日","周一","周二","周三","周四","周五","周六"];
  const html =
    `<b>${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}</b>` +
    ` · ${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${weekdays[d.getDay()]}`;
  const el = $("#clock");
  if (el) el.innerHTML = html;
}

// ----------------------- Tab 切换 -----------------------

$$(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    $$(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const page = btn.dataset.page;
    $$(".page").forEach(p => p.classList.remove("active"));
    $(`#page-${page}`).classList.add("active");
    if (page === "proc" && !window._procLoaded) {
      loadProcesses();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

// ================================================================
// 磁盘 & 文件
// ================================================================

let categories = [];

async function loadCategories() {
  const r = await apiGet("/api/categories");
  if (r.ok) {
    categories = r.data;
    renderLegend();
  }
}

function renderLegend() {
  const el = $("#file-legend");
  if (!el) return;
  el.innerHTML = categories.map(c => `
    <div class="legend-item" style="--cat-color:${c.color};--cat-bg:${c.bg}">
      <span class="swatch"></span>${c.icon} ${c.label}
    </div>
  `).join("");
}

async function loadDisks() {
  const wrap = $("#disk-list");
  const summary = $("#disk-stat-grid");
  wrap.innerHTML = `<div class="skeleton" style="height:120px;margin-bottom:14px;"></div><div class="skeleton" style="height:120px;"></div>`;
  summary.innerHTML = `<div class="skeleton stat-card" style="height:100px;"></div><div class="skeleton stat-card" style="height:100px;"></div>`;

  const r = await apiGet("/api/disks");
  if (!r.ok || !r.data || r.data.length === 0) {
    wrap.innerHTML = `<div class="empty-state"><div class="icon">💽</div><b>未检测到磁盘</b><small>${r?.msg || "可能是权限不足"}</small></div>`;
    return;
  }
  const data = r.data;

  // 汇总
  const totalGB = data.reduce((s, d) => s + d.total_gb, 0);
  const usedGB  = data.reduce((s, d) => s + d.used_gb,  0);
  const freeGB  = data.reduce((s, d) => s + d.free_gb,  0);
  const usedPct = totalGB ? (usedGB / totalGB * 100) : 0;
  const dangerN = data.filter(d => d.status === "danger").length;
  const warnN   = data.filter(d => d.status === "warning").length;

  summary.innerHTML = `
    <div class="stat-card ${dangerN ? "danger" : warnN ? "warn" : "ok"}">
      <div class="lbl">总容量</div>
      <div class="val">${totalGB.toFixed(0)}<span style="font-size:18px;"> GB</span></div>
      <div class="sublabel">共 ${data.length} 个分区</div>
    </div>
    <div class="stat-card ${usedPct > 90 ? "danger" : usedPct > 75 ? "warn" : "info"}">
      <div class="lbl">整体使用率</div>
      <div class="val">${usedPct.toFixed(1)}<span style="font-size:18px;">%</span></div>
      <div class="sublabel">已用 ${usedGB.toFixed(0)} / ${totalGB.toFixed(0)} GB</div>
    </div>
    <div class="stat-card ${freeGB < 100 ? "warn" : "ok"}">
      <div class="lbl">剩余空间</div>
      <div class="val">${freeGB.toFixed(0)}<span style="font-size:18px;"> GB</span></div>
      <div class="sublabel">还有 ${data.filter(d => d.status !== "danger").length} 个健康分区</div>
    </div>
    <div class="stat-card ${dangerN ? "danger" : "info"}">
      <div class="lbl">告警数</div>
      <div class="val">${dangerN + warnN}<span style="font-size:18px;"> 个</span></div>
      <div class="sublabel">🔴${dangerN} 告急 · 🟡${warnN} 预警</div>
    </div>
  `;

  // 每个分区卡片
  wrap.innerHTML = data.map(d => {
    const statusMap = { danger: ["danger", "告急"], warning: ["warn", "预警"], normal: ["", "正常"] };
    const [cls, txt] = statusMap[d.status] || ["", d.status];
    return `
    <div class="disk-card">
      <div class="disk-head">
        <div class="disk-mount">
          <div class="disk-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M3 5v6c0 1.7 4 3 9 3s9-1.3 9-3V5"/>
              <path d="M3 11v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/>
            </svg>
          </div>
          <div class="disk-info">
            <div class="mp" title="${d.device}">${d.mountpoint}</div>
            <div class="fs">${d.device} · ${d.fstype}</div>
          </div>
        </div>
        <span class="disk-status ${cls}">${txt}</span>
      </div>
      <div class="disk-bar" title="${d.percent}%">
        <div class="disk-bar-fill ${cls}" style="width:${d.percent}%"></div>
      </div>
      <div class="disk-stats">
        <span>总量 <b>${d.total_gb.toFixed(1)} GB</b></span>
        <span>已用 <b>${d.used_gb.toFixed(1)} GB</b></span>
        <span>空闲 <b>${d.free_gb.toFixed(1)} GB</b></span>
        <span>${d.percent.toFixed(1)}%</span>
      </div>
    </div>`;
  }).join("");
}

// ---------------- 文件浏览 ----------------

let currentPath = "";

function renderCrumbs(path) {
  const el = $("#path-crumbs");
  if (!path) {
    el.innerHTML = `<span class="crumb">—</span>`;
    return;
  }
  const sep = path.includes("/") ? "/" : "\\";
  const parts = path.split(sep).filter(Boolean);
  // 处理 Windows 盘符 C:\ 这类情况
  let prefix = "";
  if (/^[A-Za-z]:$/.test(parts[0])) {
    prefix = parts.shift() + sep;
  } else if (path.startsWith(sep)) {
    prefix = sep;
  }
  let built = prefix;
  const html = [`<span class="crumb" data-path="${encodeURIComponent(prefix || sep)}">🏠 ${prefix || "根"}</span>`];
  parts.forEach((p, i) => {
    built += (i === 0 && !prefix ? "" : sep) + p;
    const isLast = i === parts.length - 1;
    html.push(`<span class="sep">›</span>`);
    html.push(`<span class="crumb ${isLast ? "current" : ""}" data-path="${encodeURIComponent(built)}">${escapeHtml(p)}</span>`);
  });
  el.innerHTML = html.join("");
  $$("#path-crumbs .crumb").forEach(c => {
    c.addEventListener("click", () => {
      const p = decodeURIComponent(c.dataset.path);
      $("#path-input").value = p;
      browse(p);
    });
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, ch =>
    ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[ch]));
}

async function browse(path) {
  const grid  = $("#file-grid");
  const count = $("#browser-count");
  grid.innerHTML = Array(8).fill(0).map(() => `<div class="skeleton" style="height:72px;border-radius:14px;"></div>`).join("");

  const includeDirSize = !!$("#chk-dirsize")?.checked;
  const r = await apiGet("/api/browse", {
    path: path || "",
    dirsize: includeDirSize ? "1" : "0",
  });
  if (!r.ok) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">😵</div><b>浏览失败</b><small>${escapeHtml(r.msg || "")}</small></div>`;
    return;
  }
  const data = r.data;
  currentPath = data.current_path;
  $("#path-input").value = currentPath;
  renderCrumbs(currentPath);

  if (data.error) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">🚫</div><b>无法访问</b><small>${escapeHtml(data.error)}</small></div>`;
    return;
  }

  count.textContent = `共 ${data.total_items} 项 · ${currentPath}`;

  const items = data.items;
  if (!items.length) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">📭</div><b>这里是空的</b><small>${escapeHtml(currentPath)}</small></div>`;
    return;
  }

  grid.innerHTML = items.map((it, idx) => {
    return `
      <div class="file-item" style="--fi-color:${it.color};--fi-bg:${it.bg};"
           data-idx="${idx}" data-path="${encodeURIComponent(it.path)}" data-dir="${it.is_dir ? 1 : 0}">
        <div class="fi-icon">${it.icon}</div>
        <div class="fi-body">
          <div class="fi-name" title="${escapeHtml(it.name)}">${escapeHtml(it.name)}</div>
          <div class="fi-meta">
            <span><b>${escapeHtml(it.category_label)}</b></span>
            <span>${it.is_dir && it.size_bytes === 0 ? "📁 目录" : it.size_human}</span>
          </div>
        </div>
        <div class="actions">
          <button class="icon-btn" data-act="open" title="在文件管理器打开">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/></svg>
          </button>
          ${it.is_dir ? "" : `
          <button class="icon-btn" data-act="reveal" title="定位到所在目录">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="5"/></svg>
          </button>`}
        </div>
      </div>`;
  }).join("");

  // 绑定事件
  $$("#file-grid .file-item").forEach(node => {
    const path = decodeURIComponent(node.dataset.path);
    const isDir = node.dataset.dir === "1";
    // 双击：目录进入；文件：打开
    node.addEventListener("dblclick", () => {
      if (isDir) {
        $("#path-input").value = path;
        browse(path);
      } else {
        openPath(path, false);
      }
    });
    // 单击空白也能进入
    node.addEventListener("click", (e) => {
      if (e.target.closest(".actions")) return;
    });
    $$(".actions .icon-btn", node).forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const act = btn.dataset.act;
        if (act === "open") {
          if (isDir) openPath(path, false);
          else openPath(path, false);
        } else if (act === "reveal") {
          openPath(path, true);
        }
      });
    });
  });
}

async function openPath(path, select = false) {
  const r = await apiPost("/api/open-path", { path, select, where: "file" });
  if (r.ok) toast("已打开 📂", r.msg, "ok");
  else toast("打开失败", r.msg || "", "error");
}

function bindDiskUI() {
  $("#btn-browse").addEventListener("click", () => {
    browse($("#path-input").value.trim());
  });
  $("#path-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") browse(e.target.value.trim());
  });
  $("#btn-home").addEventListener("click", () => { $("#path-input").value = ""; browse(""); });
  $("#btn-up").addEventListener("click", () => {
    // 回到上一级：用 browse API 返回的 parent 更好，这里模拟
    browse(currentPath + "/..");
  });
  $("#btn-refresh").addEventListener("click", () => browse(currentPath));
  $("#chk-dirsize").addEventListener("change", () => browse(currentPath));
}

// ================================================================
// 进程监控
// ================================================================

let allProcs = [];
let procFilter = "all";
let procSearch = "";
let procSortKey = "mem_rss_mb";
let procSortDesc = true;

async function loadProcesses() {
  const tbody = $("#proc-tbody");
  const count = $("#proc-count-sub");
  count.textContent = "扫描中…约 2 秒";
  tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="icon">🛰️</div><b>正在扫描进程…</b><small>首次采集 CPU 数据约需 2 秒</small></div></td></tr>`;

  const r = await apiGet("/api/processes", { sort: procSortDesc ? "mem" : "pid", cmdline: "1" });
  if (!r.ok) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="icon">❌</div><b>加载失败</b><small>${escapeHtml(r.msg || "")}</small></div></td></tr>`;
    return;
  }
  allProcs = r.data.list;
  window._procLoaded = true;
  renderProcOverview(r.data.summary);
  renderProcTable();
}

function renderProcOverview(s) {
  // stack bar
  const stack = $("#proc-stack");
  const total = Math.max(s.total_mem_mb, 1);
  const bPct = s.beneficial.mem_mb / total * 100;
  const uPct = s.unnecessary.mem_mb / total * 100;
  const kPct = s.unknown.mem_mb / total * 100;
  stack.innerHTML = `
    <span style="width:${bPct}%; background:${s.beneficial.color};"></span>
    <span style="width:${uPct}%; background:${s.unnecessary.color};"></span>
    <span style="width:${kPct}%; background:${s.unknown.color};"></span>
  `;

  const stats = $("#proc-stats");
  stats.innerHTML = `
    <div class="legend-row" style="--c:${s.beneficial.color};">
      <span>🟢 有益 <b>${s.beneficial.count}</b> 个</span>
      <span>${s.beneficial.mem_human} · ${s.beneficial.cpu.toFixed(1)}% CPU</span>
    </div>
    <div class="legend-row" style="--c:${s.unnecessary.color};">
      <span>🟠 无益/可疑 <b>${s.unnecessary.count}</b> 个</span>
      <span>${s.unnecessary.mem_human} · ${s.unnecessary.cpu.toFixed(1)}% CPU</span>
    </div>
    <div class="legend-row" style="--c:${s.unknown.color};">
      <span>⚪ 未知 <b>${s.unknown.count}</b> 个</span>
      <span>${s.unknown.mem_human} · ${s.unknown.cpu.toFixed(1)}% CPU</span>
    </div>
    <div class="legend-row" style="margin-top:6px; padding-top:8px; border-top:1px dashed rgba(255,255,255,0.06);">
      <span>📦 总计 <b style="color:var(--ink);">${s.total}</b> 个进程</span>
      <span>${s.total_mem_human} · ${s.total_cpu.toFixed(1)}% CPU</span>
    </div>
  `;

  // 4 个卡片
  const cards = $("#proc-card-grid");
  cards.innerHTML = `
    <div class="stat-card ok">
      <div class="lbl">✅ 有益进程</div>
      <div class="val">${s.beneficial.count}</div>
      <div class="sublabel">内存 ${s.beneficial.mem_human}</div>
    </div>
    <div class="stat-card ${s.unnecessary.count ? "danger" : "warn"}">
      <div class="lbl">⚠️ 无益 / 可疑</div>
      <div class="val">${s.unnecessary.count}</div>
      <div class="sublabel">内存 ${s.unnecessary.mem_human}</div>
    </div>
    <div class="stat-card info">
      <div class="lbl">❔ 未知分类</div>
      <div class="val">${s.unknown.count}</div>
      <div class="sublabel">内存 ${s.unknown.mem_human}</div>
    </div>
    <div class="stat-card info">
      <div class="lbl">🔥 总内存占用</div>
      <div class="val" style="font-size:28px;">${s.total_mem_human}</div>
      <div class="sublabel">合计 ${s.total} 个进程</div>
    </div>
  `;
}

function filteredProcs() {
  let list = allProcs;
  if (procFilter !== "all") list = list.filter(p => p.category === procFilter);
  if (procSearch) {
    const q = procSearch.toLowerCase();
    list = list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      String(p.pid).includes(q) ||
      (p.exe_path || "").toLowerCase().includes(q) ||
      (p.reason || "").toLowerCase().includes(q)
    );
  }
  list.sort((a, b) => {
    let va = a[procSortKey], vb = b[procSortKey];
    if (typeof va === "string") {
      va = va.toLowerCase(); vb = (vb || "").toLowerCase();
      return procSortDesc ? vb.localeCompare(va) : va.localeCompare(vb);
    }
    va = va || 0; vb = vb || 0;
    return procSortDesc ? vb - va : va - vb;
  });
  return list;
}

function renderProcTable() {
  const list = filteredProcs();
  $("#proc-count").textContent = `共 ${list.length} / ${allProcs.length} 条`;
  const maxMem = Math.max(allProcs.reduce((m, p) => Math.max(m, p.mem_rss_mb), 0), 1);
  const tbody = $("#proc-tbody");

  // 表头排序标记
  $$("#proc-table thead th").forEach(th => {
    th.classList.remove("asc", "desc");
    if (th.dataset.sort === procSortKey) {
      th.classList.add(procSortDesc ? "desc" : "asc");
    }
  });

  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="icon">🔍</div><b>没有匹配的进程</b><small>换个关键词或分类看看</small></div></td></tr>`;
    return;
  }

  // 控制渲染量避免卡顿
  const SHOW_N = 260;
  const view = list.slice(0, SHOW_N);

  tbody.innerHTML = view.map(p => {
    const color = p.color;
    const memPct = (p.mem_rss_mb / maxMem * 100).toFixed(1);
    return `
    <tr>
      <td>
        <div class="proc-name-cell">
          <span class="dot-cat" style="--c:${color};"></span>
          <div>
            <div class="pname">${escapeHtml(p.name)}</div>
            <div class="pid">${p.username || "—"}</div>
          </div>
        </div>
      </td>
      <td><span class="cat-chip" style="--bg:${p.bg}; --c:${color};">
        <span style="width:7px;height:7px;border-radius:50%;background:${color};"></span>
        ${p.category_label}
      </span></td>
      <td class="num"><b>${fmtMB(p.mem_rss_mb)}</b></td>
      <td><div class="bar" style="--c:${color};"><span style="width:${memPct}%;"></span></div></td>
      <td class="num">${p.cpu_percent.toFixed(1)}</td>
      <td><div class="reason" title="${escapeHtml(p.reason)}">${escapeHtml(p.reason)}</div></td>
      <td class="num pid" style="color:var(--ink-soft);">${p.pid}</td>
      <td>
        <div class="row-actions">
          <button class="icon-btn" title="定位路径" data-act="locate" data-pid="${p.pid}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          </button>
          <button class="icon-btn" title="终止进程" data-act="kill" data-pid="${p.pid}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
          </button>
        </div>
      </td>
    </tr>`;
  }).join("");

  if (list.length > SHOW_N) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="8" style="text-align:center;padding:14px;color:var(--ink-dim);font-family:var(--font-mono);font-size:12px;">
      只展示内存占用前 ${SHOW_N} 条，使用顶部 🔍 搜索以查看更多</td>`;
    tbody.appendChild(tr);
  }

  // 绑定行操作
  $$("#proc-tbody button[data-act]").forEach(btn => {
    btn.addEventListener("click", () => {
      const act = btn.dataset.act;
      const pid = parseInt(btn.dataset.pid, 10);
      if (act === "locate") locateProc(pid);
      if (act === "kill")   killProc(pid);
    });
  });
}

async function locateProc(pid) {
  toast("定位中…", `PID ${pid}`, "info", 1500);
  const r = await apiGet(`/api/process/${pid}/locate`);
  if (!r.ok) { toast("定位失败", r.msg || "", "error"); return; }
  const d = r;
  const lines = [
    `<div style="font-family:var(--font-mono); font-size:12px; line-height:1.7;">`,
    `📁 路径：<b style="color:var(--accent-gold)">${escapeHtml(d.exe_path || "未知")}</b><br>`,
    `📂 目录：${escapeHtml(d.exe_dir || "-")}<br>`,
    d.cwd ? `💻 工作：${escapeHtml(d.cwd)}<br>` : "",
    d.cmdline ? `🔧 命令：${escapeHtml(d.cmdline.length > 120 ? d.cmdline.slice(0,120)+"…" : d.cmdline)}` : "",
    `</div>`,
  ].join("");
  // toast 里显示简要信息
  toast(`📍 ${d.name || "进程"}`, `PID ${pid} · ${d.exe_path || "路径未知"}`, "ok", 5000);
  // 同时在文件管理器中打开 exe 所在目录
  if (d.exe_path) {
    const op = await apiPost("/api/open-path", { path: d.exe_dir || d.exe_path, select: !!d.exe_exists });
    if (op.ok) toast("已在文件管理器打开", op.msg, "ok", 3200);
  }
}

async function killProc(pid) {
  const confirmed = confirm(`确定要终止进程 PID ${pid} 吗？\n\n选「取消」再提示一次会强制杀进程。`);
  const force = confirmed === false ? false : confirm("使用「强制终止」（kill -9 / taskkill /F）？\n取消 = 温和终止；确定 = 强制终止");
  const r = await apiPost(`/api/process/${pid}/kill`, { force });
  if (r.ok) { toast("✅ 已发送终止信号", r.msg, "ok"); setTimeout(loadProcesses, 1000); }
  else toast("终止失败", r.msg || "", "error");
}

async function pushNotify() {
  toast("📤 正在调用桌面通知…", "如有可疑进程将直接弹出提醒", "info", 2000);
  const r = await apiPost("/api/process/notify", { top_n: 5 });
  if (r.ok) toast(r.notified ? `⚠️ 已通知 ${r.notified} 条可疑项` : "✅ 没有可疑进程", r.msg, r.notified ? "warn" : "ok");
  else toast("通知失败", r.msg || "", "error");
}

function bindProcUI() {
  $("#btn-refresh-proc").addEventListener("click", loadProcesses);
  $("#btn-notify").addEventListener("click", pushNotify);
  $("#btn-open-bad").addEventListener("click", () => {
    const chip = $$("#proc-chips .chip").find(c => c.dataset.cat === "unnecessary");
    if (chip) chip.click();
    document.getElementById("page-proc").scrollIntoView({ behavior: "smooth" });
  });
  $("#proc-search").addEventListener("input", (e) => {
    procSearch = e.target.value.trim();
    renderProcTable();
  });
  $$("#proc-chips .chip").forEach(c => {
    c.addEventListener("click", () => {
      $$("#proc-chips .chip").forEach(x => x.classList.remove("active"));
      c.classList.add("active");
      procFilter = c.dataset.cat;
      renderProcTable();
    });
  });
  // 表头排序
  $$("#proc-table thead th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (procSortKey === key) procSortDesc = !procSortDesc;
      else { procSortKey = key; procSortDesc = true; }
      renderProcTable();
    });
  });
}

// ================================================================
// 启动
// ================================================================

async function boot() {
  tickClock();
  setInterval(tickClock, 1000);
  bindDiskUI();
  bindProcUI();
  await loadCategories();
  await loadDisks();
  // 默认先渲染一次当前目录（主目录）
  browse("");
}

boot().catch(err => {
  console.error(err);
  toast("启动出错", String(err), "error", 8000);
});
