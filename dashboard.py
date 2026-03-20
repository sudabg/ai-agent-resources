#!/usr/bin/env python3
"""Awesome Miner Dashboard - Real-time resource curation"""
import json
import os
import time
import threading
import subprocess
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

DATA_DIR = Path("/root/clawd/awesome-miner/data")
DATA_DIR.mkdir(exist_ok=True)

STATUS_FILE = DATA_DIR / "status.json"
RESOURCES_FILE = DATA_DIR / "resources.json"
LOG_FILE = DATA_DIR / "scan.log"

def get_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {
        "phase": "initializing",
        "total_links": 700,
        "scanned": 0,
        "relevant": 0,
        "categories": {},
        "last_update": datetime.now().isoformat(),
        "log": []
    }

def get_resources():
    if RESOURCES_FILE.exists():
        return json.loads(RESOURCES_FILE.read_text())
    return {"immediate": [], "longterm": [], "archive": []}

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(get_status(), ensure_ascii=False).encode())
        elif self.path == "/api/resources":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(get_resources(), ensure_ascii=False).encode())
        elif self.path == "/api/log":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            log_lines = []
            if LOG_FILE.exists():
                log_lines = LOG_FILE.read_text().strip().split("\n")[-100:]
            self.wfile.write(json.dumps({"lines": log_lines}).encode())
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress access logs

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Awesome Miner | 艾瑞的资源挖掘站</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0a0f; color:#e0e0e0; font-family:'SF Mono','Fira Code','Cascadia Code',monospace; min-height:100vh; }
.container { max-width:1400px; margin:0 auto; padding:20px; }

/* Header */
.header { text-align:center; padding:40px 0 20px; }
.header h1 { font-size:2.5em; background:linear-gradient(135deg,#ff6b6b,#feca57,#48dbfb,#ff9ff3); -webkit-background-clip:text; -webkit-text-fill-color:transparent; letter-spacing:2px; }
.header .subtitle { color:#666; font-size:0.9em; margin-top:8px; }
.header .node-id { color:#48dbfb; font-size:0.75em; margin-top:4px; opacity:0.7; }

/* Stats Grid */
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin:30px 0; }
.stat-card { background:linear-gradient(135deg,#1a1a2e,#16213e); border:1px solid #333; border-radius:12px; padding:20px; text-align:center; transition:all 0.3s; }
.stat-card:hover { border-color:#48dbfb; transform:translateY(-2px); box-shadow:0 8px 32px rgba(72,219,251,0.1); }
.stat-value { font-size:2.2em; font-weight:700; }
.stat-label { color:#888; font-size:0.8em; margin-top:4px; text-transform:uppercase; letter-spacing:1px; }
.c1 .stat-value { color:#ff6b6b; }
.c2 .stat-value { color:#feca57; }
.c3 .stat-value { color:#48dbfb; }
.c4 .stat-value { color:#ff9ff3; }
.c5 .stat-value { color:#55efc4; }

/* Progress Bar */
.progress-wrap { margin:20px 0; }
.progress-bar { height:8px; background:#1a1a2e; border-radius:4px; overflow:hidden; }
.progress-fill { height:100%; border-radius:4px; transition:width 0.5s ease; background:linear-gradient(90deg,#ff6b6b,#feca57,#48dbfb); }
.progress-text { display:flex; justify-content:space-between; margin-top:6px; font-size:0.75em; color:#666; }

/* Phase indicator */
.phase { text-align:center; margin:20px 0; }
.phase-badge { display:inline-block; padding:8px 24px; border-radius:20px; font-size:0.85em; font-weight:600; }
.phase-scanning { background:rgba(255,107,107,0.15); color:#ff6b6b; border:1px solid rgba(255,107,107,0.3); animation:pulse 2s infinite; }
.phase-analyzing { background:rgba(254,202,87,0.15); color:#feca57; border:1px solid rgba(254,202,87,0.3); animation:pulse 2s infinite; }
.phase-done { background:rgba(85,239,196,0.15); color:#55efc4; border:1px solid rgba(85,239,196,0.3); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }

/* Categories */
.categories { margin:30px 0; }
.categories h2 { color:#48dbfb; margin-bottom:16px; font-size:1.2em; }
.cat-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:12px; }
.cat-item { background:#12121a; border:1px solid #222; border-radius:8px; padding:16px; transition:all 0.3s; }
.cat-item:hover { border-color:#feca57; }
.cat-name { font-weight:600; color:#feca57; margin-bottom:6px; }
.cat-count { font-size:2em; font-weight:700; color:#48dbfb; }
.cat-desc { color:#666; font-size:0.75em; margin-top:4px; }

/* Log Stream */
.log-panel { margin:30px 0; background:#0d0d14; border:1px solid #222; border-radius:12px; overflow:hidden; }
.log-header { background:#1a1a2e; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; }
.log-header h3 { color:#48dbfb; font-size:0.9em; }
.log-body { height:300px; overflow-y:auto; padding:12px 20px; font-size:0.8em; line-height:1.6; }
.log-line { padding:2px 0; border-bottom:1px solid #111; }
.log-line:hover { background:rgba(72,219,251,0.03); }
.log-time { color:#555; }
.log-ok { color:#55efc4; }
.log-warn { color:#feca57; }
.log-err { color:#ff6b6b; }
.log-info { color:#48dbfb; }

/* Resource Cards */
.resources { margin:30px 0; }
.resources h2 { color:#ff9ff3; margin-bottom:16px; font-size:1.2em; }
.res-tabs { display:flex; gap:8px; margin-bottom:16px; }
.res-tab { padding:8px 20px; border-radius:8px; border:1px solid #333; background:transparent; color:#888; cursor:pointer; font-family:inherit; transition:all 0.3s; }
.res-tab.active { background:rgba(255,159,243,0.1); border-color:#ff9ff3; color:#ff9ff3; }
.res-list { display:grid; gap:8px; }
.res-item { background:#12121a; border:1px solid #222; border-radius:8px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; transition:all 0.3s; }
.res-item:hover { border-color:#48dbfb; transform:translateX(4px); }
.res-name { font-weight:600; color:#e0e0e0; }
.res-name a { color:#48dbfb; text-decoration:none; }
.res-name a:hover { text-decoration:underline; }
.res-tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.7em; margin-left:8px; }
.tag-immediate { background:rgba(255,107,107,0.15); color:#ff6b6b; }
.tag-longterm { background:rgba(254,202,87,0.15); color:#feca57; }
.tag-ai { background:rgba(72,219,251,0.15); color:#48dbfb; }
.tag-dev { background:rgba(85,239,196,0.15); color:#55efc4; }
.res-reason { color:#666; font-size:0.75em; max-width:500px; text-align:right; }

/* Footer */
.footer { text-align:center; padding:40px 0 20px; color:#333; font-size:0.7em; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⛏ AWESOME MINER</h1>
    <div class="subtitle">Recursive Resource Curation from 700+ Awesome Lists</div>
    <div class="node-id">Powered by 艾瑞 · node_97df6f90cdcf8360 · EvoMap</div>
  </div>

  <div class="stats">
    <div class="stat-card c1"><div class="stat-value" id="s-total">700</div><div class="stat-label">Total Links</div></div>
    <div class="stat-card c2"><div class="stat-value" id="s-scanned">0</div><div class="stat-label">Scanned</div></div>
    <div class="stat-card c3"><div class="stat-value" id="s-relevant">0</div><div class="stat-label">Relevant</div></div>
    <div class="stat-card c4"><div class="stat-value" id="s-immediate">0</div><div class="stat-label">Immediate</div></div>
    <div class="stat-card c5"><div class="stat-value" id="s-longterm">0</div><div class="stat-label">Long-term</div></div>
  </div>

  <div class="progress-wrap">
    <div class="progress-bar"><div class="progress-fill" id="p-fill" style="width:0%"></div></div>
    <div class="progress-text"><span id="p-pct">0%</span><span id="p-detail">Waiting to start...</span></div>
  </div>

  <div class="phase"><span class="phase-badge phase-scanning" id="phase-badge">INITIALIZING</span></div>

  <div class="categories">
    <h2>📊 Category Breakdown</h2>
    <div class="cat-grid" id="cat-grid"></div>
  </div>

  <div class="log-panel">
    <div class="log-header"><h3>📡 Live Scan Log</h3><span id="log-count" style="color:#555;font-size:0.75em">0 lines</span></div>
    <div class="log-body" id="log-body"></div>
  </div>

  <div class="resources">
    <h2>💎 Curated Resources</h2>
    <div class="res-tabs">
      <button class="res-tab active" onclick="switchTab('immediate')">⚡ Immediate Action</button>
      <button class="res-tab" onclick="switchTab('longterm')">🏗 Long-term Maintain</button>
      <button class="res-tab" onclick="switchTab('archive')">📦 Archive</button>
    </div>
    <div class="res-list" id="res-list"></div>
  </div>

  <div class="footer">艾瑞 Awesome Miner · Real-time Dashboard · Cloudflare Tunnel Active</div>
</div>

<script>
let currentTab = 'immediate';
let logLines = [];

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.res-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  fetchResources();
}

async function fetchStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('s-total').textContent = d.total_links || 700;
    document.getElementById('s-scanned').textContent = d.scanned || 0;
    document.getElementById('s-relevant').textContent = d.relevant || 0;
    document.getElementById('s-immediate').textContent = d.immediate || 0;
    document.getElementById('s-longterm').textContent = d.longterm || 0;
    
    const pct = d.total_links ? Math.round((d.scanned / d.total_links) * 100) : 0;
    document.getElementById('p-fill').style.width = pct + '%';
    document.getElementById('p-pct').textContent = pct + '%';
    document.getElementById('p-detail').textContent = d.phase_detail || '';
    
    const badge = document.getElementById('phase-badge');
    badge.textContent = (d.phase || 'UNKNOWN').toUpperCase();
    badge.className = 'phase-badge phase-' + (d.phase || 'scanning');
    
    // Categories
    if (d.categories) {
      const grid = document.getElementById('cat-grid');
      grid.innerHTML = '';
      for (const [name, info] of Object.entries(d.categories)) {
        grid.innerHTML += `<div class="cat-item"><div class="cat-name">${name}</div><div class="cat-count">${info.count || 0}</div><div class="cat-desc">${info.desc || ''}</div></div>`;
      }
    }
  } catch(e) {}
}

async function fetchLog() {
  try {
    const r = await fetch('/api/log');
    const d = await r.json();
    const body = document.getElementById('log-body');
    body.innerHTML = '';
    (d.lines || []).forEach(line => {
      let cls = 'log-line';
      if (line.includes('✅') || line.includes('FOUND')) cls += ' log-ok';
      else if (line.includes('⚠') || line.includes('SKIP')) cls += ' log-warn';
      else if (line.includes('❌') || line.includes('ERROR')) cls += ' log-err';
      else if (line.includes('🔍') || line.includes('SCANNING')) cls += ' log-info';
      body.innerHTML += `<div class="${cls}">${line}</div>`;
    });
    body.scrollTop = body.scrollHeight;
    document.getElementById('log-count').textContent = (d.lines || []).length + ' lines';
  } catch(e) {}
}

async function fetchResources() {
  try {
    const r = await fetch('/api/resources');
    const d = await r.json();
    const items = d[currentTab] || [];
    const list = document.getElementById('res-list');
    list.innerHTML = '';
    items.forEach(item => {
      const tagClass = currentTab === 'immediate' ? 'tag-immediate' : 'tag-longterm';
      const tags = (item.tags || []).map(t => `<span class="res-tag tag-${t}">${t}</span>`).join('');
      list.innerHTML += `<div class="res-item"><div class="res-name"><a href="${item.url || '#'}" target="_blank">${item.name || 'Unknown'}</a>${tags}</div><div class="res-reason">${item.reason || ''}</div></div>`;
    });
  } catch(e) {}
}

setInterval(fetchStatus, 3000);
setInterval(fetchLog, 5000);
setInterval(fetchResources, 8000);
fetchStatus(); fetchLog(); fetchResources();
</script>
</body>
</html>'''

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9888), DashboardHandler)
    print(f"Dashboard running on http://0.0.0.0:9888")
    server.serve_forever()
