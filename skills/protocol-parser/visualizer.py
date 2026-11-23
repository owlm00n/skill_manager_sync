#!/usr/bin/env python3
"""
Protocol Parser Visualizer v1.0 — HTML Visualization Generator
===============================================================
Layer 2 of the protocol-parser 3-layer architecture.

Takes structured extraction JSON (from smart_extractor.extract_structured())
and generates a self-contained HTML report with:

  - Dual-column Lecroy-style view: TCPM State Machine | PD Protocol Messages
  - Hard reset phase highlighting
  - Negotiation round grouping
  - PD header decode tooltips
  - Interactive event filtering
  - Anomaly summary
  - Dark theme matching Lecroy protocol analyzer aesthetic

Usage:
  from visualizer import generate_html, save_report

  result = extract_structured("hardreset_ok.txt")
  html = generate_html(result)
  save_report(html, "report.html")
"""

from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime
from typing import Any


def generate_html(extraction_result: dict, title: str | None = None,
                  hub_url: str = "http://127.0.0.1:8777") -> str:
    """Generate a self-contained HTML report from extraction result.

    Args:
        extraction_result: Dict from smart_extractor.extract_structured()
        title: Optional report title override

    Returns:
        Complete HTML document as a string
    """
    data_json = json.dumps(extraction_result, ensure_ascii=False, default=str)

    meta = extraction_result.get("metadata", {})
    source = meta.get("source_file", "unknown")
    if not title:
        title = os.path.basename(source) if source else "PD Protocol Analysis"

    timeline_count = meta.get("extracted_event_count", len(extraction_result.get("timeline", [])))
    platform = meta.get("platform", "sprd").upper()
    chip = meta.get("chip", "")

    # URL-encode source path for file:// link (handles Chinese characters)
    source_url = urllib.parse.quote(source.replace("\\", "/"), safe="/:")

    html = _HTML_TEMPLATE.format(
        title=title,
        source=source_url,
        platform=platform,
        chip=chip,
        timeline_count=timeline_count,
        gen_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hub_url=hub_url,
    )
    html = html.replace("__DATA_JSON_PLACEHOLDER__", data_json)
    html = html.replace("__SOURCE_PATH_PLACEHOLDER__", json.dumps(source))
    return html


def save_report(html: str, output_path: str) -> str:
    """Save HTML report to file and return absolute path."""
    path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


# ============================================================
# HTML/CSS/JS Template
# ============================================================

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — PD Protocol Analysis</title>
<style>
/* ============================================================
   Lecroy-style Dark Theme
   ============================================================ */
:root {{
    --bg: #0a0e14;
    --surface: #131820;
    --surface2: #1a2030;
    --border: #2a3548;
    --border-bright: #3d4f6b;
    --text: #cdd6e0;
    --text-dim: #6b7d95;
    --text-bright: #e8edf3;

    /* Message direction colors (Lecroy-inspired) */
    --tx: #36b0e0;
    --tx-bg: rgba(54, 176, 224, 0.08);
    --tx-border: rgba(54, 176, 224, 0.35);
    --rx: #b088f0;
    --rx-bg: rgba(176, 136, 240, 0.08);
    --rx-border: rgba(176, 136, 240, 0.35);

    /* Status colors */
    --ok: #44c868;
    --warn: #e8b830;
    --error: #e84855;
    --info: #5090d0;

    /* Phase colors */
    --hr-bg: rgba(232, 72, 85, 0.06);
    --hr-border: rgba(232, 72, 85, 0.3);
    --neg-bg: rgba(68, 200, 104, 0.04);
    --neg-border: rgba(68, 200, 104, 0.25);

    /* State machine */
    --state-active: #5090d0;
    --state-transition: #8ab4e0;
    --state-hr: #e84855;
    --state-idle: #3d4f6b;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', 'Menlo', monospace;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    line-height: 1.5;
    overflow-x: hidden;
}}

/* ============================================================
   Top Bar
   ============================================================ */
.topbar {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(8px);
}}
.topbar-title {{
    font-size: 15px;
    font-weight: 700;
    color: var(--text-bright);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 500px;
}}
.topbar-badge {{
    font-size: 10px;
    padding: 2px 10px;
    border-radius: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.topbar-badge.pd {{ background: rgba(54,176,224,0.18); color: var(--tx); }}
.topbar-badge.sprd {{ background: rgba(80,144,208,0.18); color: var(--info); }}
.topbar-meta {{
    font-size: 11px;
    color: var(--text-dim);
}}
.topbar-source-btn {{
    font-size: 11px;
    color: var(--tx);
    background: rgba(54,176,224,0.12);
    border: 1px solid rgba(54,176,224,0.25);
    border-radius: 4px;
    padding: 4px 12px;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
    transition: all 0.2s;
}}
.topbar-source-btn:hover {{
    background: rgba(54,176,224,0.25);
    border-color: rgba(54,176,224,0.5);
    color: #fff;
}}
.topbar-copy-btn {{
    font-size: 11px;
    color: var(--text-dim);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 10px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s;
}}
.topbar-copy-btn:hover {{
    background: var(--surface2);
    color: var(--text-bright);
    border-color: var(--tx-dim);
}}
.topbar-copy-btn.copied {{
    background: rgba(80,200,120,0.18);
    border-color: rgba(80,200,120,0.4);
    color: #50c878;
}}
.topbar-parse-btn {{
    font-size: 11px;
    color: var(--tx);
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 5px 14px;
    border-radius: 6px;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 6px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.2s;
}}
.topbar-parse-btn:hover {{
    background: rgba(102,126,234,0.25);
    border-color: rgba(102,126,234,0.5);
    color: #fff;
}}

/* ============================================================
   Summary Cards Row
   ============================================================ */
.summary-row {{
    display: flex;
    gap: 10px;
    padding: 14px 24px;
    flex-wrap: wrap;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
}}
.card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 16px;
    min-width: 120px;
    flex: 1;
    max-width: 200px;
}}
.card-label {{
    font-size: 9px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 4px;
}}
.card-value {{
    font-size: 20px;
    font-weight: 700;
}}
.card-value.ok {{ color: var(--ok); }}
.card-value.warn {{ color: var(--warn); }}
.card-value.err {{ color: var(--error); }}
.card-value.info {{ color: var(--tx); }}
.card-sub {{
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 2px;
}}

/* ============================================================
   Main Dual-Column Layout
   ============================================================ */
.main {{
    display: flex;
    height: calc(100vh - 120px);
    overflow: hidden;
}}

/* === Left Column: State Machine === */
.col-left {{
    width: 340px;
    min-width: 280px;
    border-right: 1px solid var(--border);
    background: var(--surface);
    overflow-y: auto;
    padding: 16px;
}}
.col-left h3 {{
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}}

/* State machine node */
.sm-node {{
    position: relative;
    padding: 6px 12px;
    margin: 2px 0;
    border-left: 3px solid var(--state-idle);
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s;
    border-radius: 0 4px 4px 0;
}}
.sm-node:hover {{ background: var(--surface2); }}
.sm-node.active {{ border-left-color: var(--state-active); background: rgba(80,144,208,0.06); }}
.sm-node.hr {{ border-left-color: var(--state-hr); background: var(--hr-bg); }}
.sm-node.delayed {{ border-left-style: dashed; }}
.sm-node .sm-name {{
    font-weight: 600;
    color: var(--text-bright);
}}
.sm-node .sm-arrow {{
    color: var(--text-dim);
    margin: 0 4px;
    font-size: 9px;
}}
.sm-node .sm-delay {{
    font-size: 10px;
    color: var(--warn);
    margin-left: 6px;
}}
.sm-node .sm-event {{
    font-size: 9px;
    color: var(--text-dim);
    display: block;
}}

/* State machine phase divider */
.sm-phase-divider {{
    padding: 4px 12px;
    margin: 8px 0 4px;
    font-size: 10px;
    font-weight: 700;
    color: var(--error);
    background: var(--hr-bg);
    border: 1px solid var(--hr-border);
    border-radius: 4px;
    text-align: center;
    letter-spacing: 1px;
}}
.sm-phase-divider.negotiate {{
    color: var(--ok);
    background: var(--neg-bg);
    border-color: var(--neg-border);
}}

/* === Right Column: PD Messages Timeline === */
.col-right {{
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
}}

/* Phase grouping bracket */
.phase-bracket {{
    margin: 8px 0 16px;
    border-left: 2px solid var(--border-bright);
    padding-left: 12px;
}}
.phase-bracket.hard-reset {{
    border-left-color: var(--error);
    background: var(--hr-bg);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
}}
.phase-label {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
}}
.phase-label.hr {{ color: var(--error); }}
.phase-label.negotiate {{ color: var(--ok); }}
.phase-label.transition {{ color: var(--info); }}

/* Individual PD message row */
.msg-row {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 5px 8px;
    margin: 1px 0;
    border-left: 2px solid transparent;
    border-radius: 0 4px 4px 0;
    cursor: pointer;
    transition: background 0.1s;
    font-size: 11px;
}}
.msg-row:hover {{ background: var(--surface2); }}
.msg-row.tx {{ border-left-color: var(--tx); }}
.msg-row.rx {{ border-left-color: var(--rx); }}
.msg-row.state {{ border-left-color: var(--info); }}
.msg-row.warn {{ border-left-color: var(--warn); background: rgba(232,184,48,0.04); }}
.msg-row.error {{ border-left-color: var(--error); background: var(--hr-bg); }}
.msg-row.hr {{ background: var(--hr-bg); }}
.msg-row.negotiate {{ background: var(--neg-bg); }}

.msg-idx {{
    color: var(--text-dim);
    font-size: 9px;
    min-width: 32px;
    text-align: right;
}}
.msg-ts {{
    color: var(--text-dim);
    font-size: 10px;
    min-width: 72px;
    white-space: nowrap;
}}
.msg-dir {{
    font-size: 9px;
    font-weight: 700;
    min-width: 24px;
    text-align: center;
    padding: 1px 4px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.msg-dir.tx {{ color: var(--tx); background: var(--tx-bg); }}
.msg-dir.rx {{ color: var(--rx); background: var(--rx-bg); }}
.msg-dir.info {{ color: var(--info); background: rgba(80,144,208,0.12); }}
.msg-type {{
    font-weight: 600;
    min-width: 80px;
    white-space: nowrap;
}}
.msg-type.tx {{ color: var(--tx); }}
.msg-type.rx {{ color: var(--rx); }}
.msg-type.warn {{ color: var(--warn); }}
.msg-type.error {{ color: var(--error); }}
.msg-content {{
    color: var(--text-dim);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.msg-content:hover {{
    overflow: visible;
    white-space: normal;
    word-break: break-all;
}}
.msg-tags {{
    display: flex;
    gap: 3px;
    flex-wrap: wrap;
}}
.msg-tag {{
    font-size: 8px;
    padding: 1px 5px;
    border-radius: 3px;
    background: var(--surface2);
    color: var(--text-dim);
    border: 1px solid var(--border);
    white-space: nowrap;
}}
.msg-tag.hr {{ color: var(--error); border-color: rgba(232,72,85,0.3); }}
.msg-tag.negotiate {{ color: var(--ok); border-color: rgba(68,200,104,0.3); }}

/* Tooltip */
.msg-tooltip {{
    display: none;
    position: fixed;
    z-index: 200;
    background: var(--surface);
    border: 1px solid var(--border-bright);
    border-radius: 8px;
    padding: 12px 16px;
    max-width: 420px;
    font-size: 11px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    pointer-events: none;
}}
.msg-tooltip.active {{ display: block; }}
.msg-tooltip h4 {{
    font-size: 11px;
    color: var(--text-bright);
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}}
.msg-tooltip table {{
    width: 100%;
    border-collapse: collapse;
}}
.msg-tooltip td {{
    padding: 2px 8px 2px 0;
    font-size: 10px;
}}
.msg-tooltip td:first-child {{
    color: var(--text-dim);
    white-space: nowrap;
}}
.msg-tooltip td:last-child {{
    color: var(--text-bright);
    font-weight: 600;
}}
.msg-tooltip .raw-hex {{
    font-family: 'SF Mono', 'Consolas', monospace;
    color: var(--tx);
    font-size: 10px;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid var(--border);
}}

/* ============================================================
   Bottom / Tab panels
   ============================================================ */
.tabs {{
    display: flex;
    gap: 0;
    padding: 0 24px;
    background: var(--surface);
    border-top: 1px solid var(--border);
}}
.tab-btn {{
    padding: 6px 16px;
    font-size: 11px;
    color: var(--text-dim);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
}}
.tab-btn:hover {{ color: var(--text); }}
.tab-btn.active {{ color: var(--tx); border-bottom-color: var(--tx); }}
.tab-panel {{
    display: none;
    padding: 14px 24px;
    background: var(--bg);
    max-height: 300px;
    overflow-y: auto;
    border-top: 1px solid var(--border);
}}
.tab-panel.active {{ display: block; }}

/* Anomaly item */
.anomaly-item {{
    padding: 6px 12px;
    margin: 3px 0;
    border-left: 3px solid var(--warn);
    font-size: 11px;
    background: var(--surface);
    border-radius: 0 4px 4px 0;
}}
.anomaly-item .anomaly-desc {{
    color: var(--text-bright);
}}
.anomaly-item .anomaly-detail {{
    color: var(--text-dim);
    font-size: 10px;
    margin-top: 2px;
}}

/* Negotiation summary card */
.neg-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    margin: 6px 0;
}}
.neg-card h4 {{
    font-size: 11px;
    color: var(--ok);
    margin-bottom: 6px;
}}
.neg-card .neg-flow {{
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    font-size: 10px;
}}
.neg-card .neg-step {{
    padding: 2px 8px;
    border-radius: 3px;
    background: var(--surface2);
    border: 1px solid var(--border);
}}
.neg-card .neg-step.tx {{ border-color: var(--tx-border); color: var(--tx); }}
.neg-card .neg-step.rx {{ border-color: var(--rx-border); color: var(--rx); }}
.neg-card .neg-arrow {{ color: var(--text-dim); }}

/* Checkbox filter row */
.filter-row {{
    display: flex;
    gap: 6px;
    padding: 8px 24px;
    flex-wrap: wrap;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    align-items: center;
}}
.filter-row label {{
    font-size: 10px;
    color: var(--text-dim);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    border-radius: 3px;
    border: 1px solid transparent;
    user-select: none;
}}
.filter-row label.checked {{
    border-color: var(--border-bright);
    color: var(--text);
}}
.filter-row input {{ display: none; }}
.filter-label {{
    font-size: 9px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-right: 8px;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--border-bright); }}

/* Responsive */
@media (max-width: 900px) {{
    .main {{ flex-direction: column; }}
    .col-left {{ width: 100%; min-width: auto; max-height: 250px; }}
}}
</style>
</head>
<body>

<!-- Top Bar -->
<div class="topbar">
    <span class="topbar-title">{title}</span>
    <span class="topbar-badge pd">PD</span>
    <span class="topbar-badge sprd">{platform}</span>
    <span class="topbar-meta">{chip} &middot; {timeline_count} events &middot; Generated {gen_time}</span>
    <span style="flex:1"></span>
    <a class="topbar-source-btn" href="file:///{source}" title="Open source log file">📂 Open Source Log</a>
    <button class="topbar-copy-btn" onclick="copySourcePath()" title="Copy source path">📋 Copy Path</button>
    <a class="topbar-parse-btn" href="{hub_url}/pages/protocol-parser.html" target="_blank" title="Open bug-hub Dashboard to analyze a different log file">🔄 Parse Another Log</a>
</div>

<!-- Summary Cards -->
<div class="summary-row" id="summary-row"></div>

<!-- Main Dual-Column View -->
<div class="main">
    <div class="col-left" id="col-state">
        <h3>TCPM State Machine</h3>
        <div id="state-machine"></div>
    </div>
    <div class="col-right" id="col-msgs">
        <div id="msg-timeline"></div>
    </div>
</div>

<!-- Filter Row -->
<div class="filter-row" id="filter-row"></div>

<!-- Bottom Tabs -->
<div class="tabs">
    <button class="tab-btn active" data-tab="negotiations">Negotiations</button>
    <button class="tab-btn" data-tab="anomalies">Anomalies</button>
    <button class="tab-btn" data-tab="raw">Raw Events</button>
</div>
<div class="tab-panel active" id="tab-negotiations"></div>
<div class="tab-panel" id="tab-anomalies"></div>
<div class="tab-panel" id="tab-raw"></div>

<!-- Tooltip -->
<div class="msg-tooltip" id="tooltip"></div>

<script>
// ============================================================
// Data
// ============================================================
const DATA = __DATA_JSON_PLACEHOLDER__;
const SOURCE_PATH = __SOURCE_PATH_PLACEHOLDER__;

// ============================================================
// Helpers
// ============================================================
const BASE_TS = DATA.timeline.length > 0 ? DATA.timeline[0].kernel_ts : 0;

function copySourcePath() {{
    navigator.clipboard.writeText(SOURCE_PATH).then(() => {{
        const btn = document.querySelector('.topbar-copy-btn');
        btn.textContent = '✓ Copied!';
        btn.classList.add('copied');
        setTimeout(() => {{
            btn.textContent = '📋 Copy Path';
            btn.classList.remove('copied');
        }}, 2000);
    }}).catch(() => {{
        // Fallback for older browsers
        const ta = document.createElement('textarea');
        ta.value = SOURCE_PATH;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        const btn = document.querySelector('.topbar-copy-btn');
        btn.textContent = '✓ Copied!';
        btn.classList.add('copied');
        setTimeout(() => {{
            btn.textContent = '📋 Copy Path';
            btn.classList.remove('copied');
        }}, 2000);
    }});
}}

// ============================================================
// Helpers
// ============================================================
const BASE_TS = DATA.timeline.length > 0 ? DATA.timeline[0].kernel_ts : 0;

function relTs(ts) {{
    return ((ts - BASE_TS) * 1000).toFixed(1);
}}

function absTs(ts) {{
    const d = new Date((ts - BASE_TS) * 1000);
    const m = String(d.getUTCMinutes()).padStart(2, '0');
    const s = String(d.getUTCSeconds()).padStart(2, '0');
    const ms = String(d.getUTCMilliseconds()).padStart(3, '0');
    return m + ':' + s + '.' + ms;
}}

function fmtVoltage(mv) {{ return mv ? (mv / 1000).toFixed(1) + 'V' : '-'; }}
function fmtCurrent(ma) {{ return ma ? (ma / 1000).toFixed(2) + 'A' : '-'; }}

function getDir(e) {{
    const t = e.event_type;
    if (t === 'pd_rx' || t === 'pd_rx_data' || t === 'pd_rx_fifo') return 'rx';
    if (t === 'pd_tx' || t === 'pd_tx_cfg' || t === 'pd_tx_end' || t === 'pd_tx_complete') return 'tx';
    if (t.startsWith('state_') || t.startsWith('pd_engine_')) return 'info';
    if (t === 'vbus_event' || t === 'disconnect' || t === 'plug_out') return 'warn';
    const dec = e.decoded || {{}};
    if (dec.msg_role === 'host') return 'tx';
    if (dec.msg_role === 'device') return 'rx';
    return 'info';
}}

function getTypeLabel(e) {{
    const t = e.event_type;
    const dec = e.decoded || {{}};
    if (dec.pd_header_decoded) return dec.pd_header_decoded.message_type;
    if (t === 'state_change') return (e.state_from || '?') + ' -> ' + (e.state_to || '?');
    if (t === 'delayed_state_change') return 'DELAYED: ' + (e.state_from || '?') + ' -> ' + (e.state_to || '?');
    if (t === 'pending_state_change') return 'PENDING: ' + (e.state_from || '?') + ' -> ' + (e.state_to || '?');
    const labels = {{
        'state_change': 'State',
        'delayed_state_change': 'Delayed',
        'pending_state_change': 'Pending',
        'pd_tx': 'TX', 'pd_rx': 'RX',
        'pd_tx_cfg': 'TX Config', 'pd_tx_end': 'TX End',
        'pd_tx_complete': 'TX Done', 'pd_rx_data': 'RX Data',
        'pd_rx_fifo': 'RX FIFO', 'pd_irq': 'PD IRQ',
        'pd_reset': 'PD Reset', 'pd_rx_flush': 'RX Flush',
        'pd_ps_rdy': 'PS_RDY', 'pd_snk_negotiate': 'Snk Negotiate',
        'pd_init': 'PD Init', 'pd_engine_state': 'PD Engine',
        'vbus_event': 'VBUS', 'cc_change': 'CC Change',
        'cc_polarity': 'CC Polarity', 'cc_vbus_state': 'CC/VBUS',
        'pdo_entry': 'PDO', 'pdo_request': 'Req PDO',
        'caps_update': 'Caps Update', 'rp_change': 'RP Change',
        'rp_limit': 'RP Limit', 'power_role': 'Power Role',
        'typec_connect': 'Connect', 'typec_interrupt': 'TypeC IRQ',
        'typec_config': 'TypeC Cfg', 'typec_timing': 'TypeC Timing',
        'tcpm_config': 'TCPM Cfg',
        'plug_out': 'Plug Out', 'disconnect': 'Disconnect',
        'charger_info': 'Chg Info', 'charger_limit': 'Chg Limit',
        'charger_state': 'Chg State', 'charger_vote': 'Chg Vote',
        'charger_jeita': 'JEITA', 'charger_monitor': 'Chg Mon',
        'charger_fchg': 'Fast Chg', 'charger_target': 'Chg Target',
        'charger_config': 'Chg Config', 'charger_ic_irq': 'Chg IC IRQ',
        'charger_otg': 'OTG', 'charger_bc1p2': 'BC1.2',
        'musb_state': 'MUSB State', 'musb_resume': 'MUSB Resume',
        'musb_extcon': 'MUSB Extcon', 'musb_gadget': 'MUSB Gadget',
        'usb_pullup': 'USB Pullup', 'musb_chg_detect': 'MUSB ChgDet',
        'bc1p2': 'BC1.2', 'reset_port': 'Reset Port',
        'toggling': 'Toggling',
    }};
    return labels[t] || t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}}

function getMsgContent(e) {{
    const dec = e.decoded || {{}};
    const hd = dec.pd_header_decoded;
    if (hd) {{
        let s = hd.message_type + ' | msg_id=' + hd.message_id;
        if (dec.pdos && dec.pdos.length) {{
            const pdoDescs = dec.pdos.map(p => {{
                if (p.type === 'pps') return 'PPS ' + p.voltage_mv + 'mV';
                return p.voltage_mv + 'mV';
            }});
            s += ' | PDOs: ' + pdoDescs.join(', ');
        }}
        if (dec.rdo) {{
            s += ' | RDO: pos=' + dec.rdo.object_position + ' ' + dec.rdo.operating_current_ma + 'mA';
        }}
        return s;
    }}
    if (e.current_ma !== undefined && e.voltage_mv !== undefined) {{
        return fmtVoltage(e.voltage_mv) + ' / ' + fmtCurrent(e.current_ma);
    }}
    if (e.current_ma !== undefined) return fmtCurrent(e.current_ma);
    if (e.voltage_mv !== undefined) return fmtVoltage(e.voltage_mv);
    const ci = e.charger_info;
    if (ci) {{
        return 'adapter=' + fmtVoltage(ci.adapter_chg_volt_mv) + ' max_chg=' + fmtCurrent(ci.max_chg_lmt_cur_ua / 1000);
    }}
    return e.content_raw ? (e.content_raw.length > 80 ? e.content_raw.substring(0, 80) + '...' : e.content_raw) : '';
}}

function getTags(e) {{
    const tags = [];
    if (e.flags) {{
        e.flags.forEach(f => {{
            if (f === 'HARD_RESET') tags.push({{cls: 'hr', text: 'HR'}});
            if (f === 'FIRST_NEGOTIATE') tags.push({{cls: 'negotiate', text: '1st Neg'}});
            if (f === 'PPS_NEGOTIATE') tags.push({{cls: 'negotiate', text: 'PPS'}});
            if (f === 'DISCONNECT') tags.push({{cls: 'hr', text: 'DC'}});
            if (f === 'KEY_EVENT') tags.push({{cls: '', text: 'KEY'}});
        }});
    }}
    return tags;
}}

// ============================================================
// State Machine Rendering
// ============================================================
function renderStateMachine() {{
    const sm = DATA.state_machine_summary || {{}};
    const transitions = sm.transitions || [];
    const nego = DATA.pd_negotiations || [];
    const hrp = DATA.hard_reset_phases || [];

    // Build a map: event_id -> state transition info
    const evtToTrans = {{}};
    transitions.forEach(t => {{ evtToTrans[t.event_id] = t; }});

    // Build negotiation event-id ranges
    const negRanges = nego.map(n => ({{
        start: n.event_ids[0], end: n.event_ids[n.event_ids.length - 1],
        label: n.label, cycle: n.cycle
    }}));

    // Build hard-reset event-id ranges
    const hrRanges = hrp.map(h => ({{
        start: h.event_ids[0], end: h.event_ids[h.event_ids.length - 1],
        label: h.phase_name
    }}));

    let html = '';
    let prevPhase = '';

    transitions.forEach((t, i) => {{
        // Check phase boundaries
        const eid = t.event_id;
        let phaseDivider = '';

        // Check hard reset boundary
        for (const hr of hrRanges) {{
            if (eid >= hr.start && eid <= hr.end && prevPhase !== 'hr') {{
                phaseDivider = '<div class="sm-phase-divider">HARD RESET</div>';
                prevPhase = 'hr';
                break;
            }}
        }}

        // Check negotiation boundary
        if (!phaseDivider) {{
            for (const n of negRanges) {{
                if (eid >= n.start && eid <= n.end && prevPhase !== 'neg_' + n.cycle) {{
                    phaseDivider = '<div class="sm-phase-divider negotiate">Negotiation #' + n.cycle + '</div>';
                    prevPhase = 'neg_' + n.cycle;
                    break;
                }}
            }}
        }}

        if (phaseDivider) html += phaseDivider;

        const isHr = t.from.includes('HARD_RESET') || t.to.includes('HARD_RESET');
        const isDelayed = t.is_delayed || t.delay_ms > 0;
        let cls = 'sm-node active';
        if (isHr) cls = 'sm-node hr';
        if (isDelayed) cls += ' delayed';

        html += '<div class="' + cls + '" onclick="scrollToEvent(' + eid + ')">';
        html += '<span class="sm-name">' + t.from + '</span>';
        html += '<span class="sm-arrow">-></span>';
        html += '<span class="sm-name">' + t.to + '</span>';
        if (isDelayed) html += '<span class="sm-delay">' + t.delay_ms + 'ms</span>';
        html += '<span class="sm-event">#' + eid + ' @ ' + relTs(t.ts) + 'ms</span>';
        html += '</div>';
    }});

    document.getElementById('state-machine').innerHTML = html || '<div style="color:var(--text-dim);font-size:11px">No state transitions detected</div>';
}}

// ============================================================
// Message Timeline Rendering
// ============================================================
let FILTER_HIDDEN = new Set();

function renderMessageTimeline() {{
    const timeline = DATA.timeline || [];
    const nego = DATA.pd_negotiations || [];
    const hrp = DATA.hard_reset_phases || [];

    // Build lookup: event_id -> negotiation cycle
    const evtToNeg = {{}};
    nego.forEach(n => {{
        n.event_ids.forEach(eid => {{ evtToNeg[eid] = n; }});
    }});

    // Build lookup: event_id -> hard reset phase
    const evtToHr = {{}};
    hrp.forEach(h => {{
        h.event_ids.forEach(eid => {{ evtToHr[eid] = h; }});
    }});

    // Build phase groups
    let html = '';
    let currentPhase = null;
    let phaseEvents = [];

    function flushPhase() {{
        if (!phaseEvents.length) return;
        let phaseCls = '';
        let phaseLabel = '';
        let phaseLabelCls = '';

        if (currentPhase === 'hr') {{
            phaseCls = ' hard-reset';
            phaseLabel = 'HARD RESET PHASE';
            phaseLabelCls = ' hr';
        }} else if (currentPhase && currentPhase.startsWith('neg_')) {{
            phaseCls = '';
            phaseLabel = currentPhase;
            phaseLabelCls = ' negotiate';
        }}

        html += '<div class="phase-bracket' + phaseCls + '">';
        if (phaseLabel) {{
            html += '<div class="phase-label' + phaseLabelCls + '">' + phaseLabel + '</div>';
        }}

        phaseEvents.forEach(e => {{
            if (FILTER_HIDDEN.has(e.event_type)) return;

            const dir = getDir(e);
            const typeLabel = getTypeLabel(e);
            const content = getMsgContent(e);
            const tags = getTags(e);
            const isHr = evtToHr[e.id] !== undefined;
            const isNeg = evtToNeg[e.id] !== undefined;

            let rowCls = 'msg-row ' + dir;
            if (isHr) rowCls += ' hr';
            if (isNeg) rowCls += ' negotiate';

            const tsRel = relTs(e.kernel_ts);

            html += '<div class="' + rowCls + '" data-eid="' + e.id + '" ';
            html += 'onmouseenter="showTooltip(event, ' + e.id + ')" ';
            html += 'onmouseleave="hideTooltip()" ';
            html += 'onclick="scrollToEvent(' + e.id + ')">';
            html += '<span class="msg-idx">#' + e.id + '</span>';
            html += '<span class="msg-ts">' + tsRel + 'ms</span>';
            html += '<span class="msg-dir ' + dir + '">' + (dir === 'tx' ? 'TX' : dir === 'rx' ? 'RX' : dir === 'info' ? '--' : '!!') + '</span>';
            html += '<span class="msg-type ' + dir + '">' + typeLabel + '</span>';
            html += '<span class="msg-content">' + escapeHtml(content) + '</span>';
            if (tags.length) {{
                html += '<span class="msg-tags">';
                tags.forEach(tag => {{
                    html += '<span class="msg-tag ' + tag.cls + '">' + tag.text + '</span>';
                }});
                html += '</span>';
            }}
            html += '</div>';
        }});

        html += '</div>';
        phaseEvents = [];
    }}

    // Walk through timeline, grouping into phases
    timeline.forEach(e => {{
        let phase = 'other';
        if (evtToHr[e.id]) phase = 'hr';
        else if (evtToNeg[e.id]) {{
            const n = evtToNeg[e.id];
            phase = 'neg_' + n.cycle + ': ' + (n.label || 'Negotiation');
        }}

        if (phase !== currentPhase) {{
            flushPhase();
            currentPhase = phase;
        }}

        phaseEvents.push(e);
    }});
    flushPhase();

    document.getElementById('msg-timeline').innerHTML = html || '<div style="color:var(--text-dim)">No events</div>';
}}

function escapeHtml(str) {{
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}}

// ============================================================
// Tooltip
// ============================================================
const EVT_MAP = {{}};
(DATA.timeline || []).forEach(e => {{ EVT_MAP[e.id] = e; }});

function showTooltip(evt, eid) {{
    const e = EVT_MAP[eid];
    if (!e) return;

    const tooltip = document.getElementById('tooltip');
    const dec = e.decoded || {{}};
    const hd = dec.pd_header_decoded;

    let html = '<h4>#' + e.id + ' &middot; ' + getTypeLabel(e) + ' &middot; ' + relTs(e.kernel_ts) + 'ms</h4>';

    if (hd) {{
        html += '<table>';
        html += '<tr><td>Message Type</td><td>' + hd.message_type + '</td></tr>';
        html += '<tr><td>Spec Revision</td><td>' + hd.spec_revision + '</td></tr>';
        html += '<tr><td>Power Role</td><td>' + hd.port_power_role + '</td></tr>';
        html += '<tr><td>Data Role</td><td>' + hd.port_data_role + '</td></tr>';
        html += '<tr><td>Message ID</td><td>' + hd.message_id + '</td></tr>';
        html += '<tr><td>Data Objects</td><td>' + hd.number_of_data_objects + '</td></tr>';
        if (hd.extended) html += '<tr><td>Extended</td><td>true</td></tr>';
        html += '</table>';
        html += '<div class="raw-hex">Header: ' + hd.raw_hex + '</div>';
    }}

    if (dec.pdos && dec.pdos.length) {{
        html += '<table style="margin-top:6px">';
        html += '<tr><td colspan="2" style="color:var(--text-dim);font-size:9px">PDOs</td></tr>';
        dec.pdos.forEach((p, i) => {{
            html += '<tr><td>PDO[' + i + ']</td><td>' + p.type.toUpperCase() + ' ' + p.voltage_mv + 'mV ' + p.current_ma + 'mA</td></tr>';
        }});
        html += '</table>';
    }}

    if (dec.rdo) {{
        html += '<table style="margin-top:6px">';
        html += '<tr><td colspan="2" style="color:var(--text-dim);font-size:9px">RDO</td></tr>';
        html += '<tr><td>Position</td><td>PDO #' + dec.rdo.object_position + '</td></tr>';
        html += '<tr><td>Op Current</td><td>' + dec.rdo.operating_current_ma + 'mA</td></tr>';
        if (dec.rdo.max_current_ma) html += '<tr><td>Max Current</td><td>' + dec.rdo.max_current_ma + 'mA</td></tr>';
        html += '</table>';
    }}

    if (dec.tx_status !== undefined) {{
        html += '<table><tr><td>TX Status</td><td>' + (dec.tx_status === 0 ? 'OK' : 'FAIL(' + dec.tx_status + ')') + '</td></tr></table>';
    }}

    if (e.content_raw) {{
        html += '<div class="raw-hex">' + escapeHtml(e.content_raw.length > 120 ? e.content_raw.substring(0, 120) + '...' : e.content_raw) + '</div>';
    }}

    tooltip.innerHTML = html;
    tooltip.classList.add('active');

    // Position tooltip near cursor
    const x = evt.clientX + 16;
    const y = evt.clientY - 10;
    tooltip.style.left = Math.min(x, window.innerWidth - 440) + 'px';
    tooltip.style.top = Math.min(y, window.innerHeight - 300) + 'px';
}}

function hideTooltip() {{
    document.getElementById('tooltip').classList.remove('active');
}}

// ============================================================
// Summary Cards
// ============================================================
function renderSummary() {{
    const meta = DATA.metadata || {{}};
    const timeline = DATA.timeline || [];
    const nego = DATA.pd_negotiations || [];
    const anomalies = DATA.anomalies || [];
    const sm = DATA.state_machine_summary || {{}};
    const transitions = sm.transitions || [];

    // Count hard resets
    const hrCount = timeline.filter(e => e.flags && e.flags.includes('HARD_RESET')).length;

    // Last negotiation result
    const lastNeg = nego.length > 0 ? nego[nego.length - 1] : null;
    const negResult = lastNeg && lastNeg.result;

    // Count message directions
    const txCount = timeline.filter(e => getDir(e) === 'tx').length;
    const rxCount = timeline.filter(e => getDir(e) === 'rx').length;

    let cards = '';

    // Negotiation result
    if (negResult) {{
        cards += '<div class="card">';
        cards += '<div class="card-label">Negotiation</div>';
        cards += '<div class="card-value ' + (negResult.success ? 'ok' : 'err') + '">' + (negResult.success ? 'SUCCESS' : 'FAILED') + '</div>';
        cards += '<div class="card-sub">' + fmtVoltage(negResult.voltage_mv) + ' / ' + fmtCurrent(negResult.current_ma) + '</div>';
        cards += '</div>';
    }}

    // Negotiation cycles
    cards += '<div class="card">';
    cards += '<div class="card-label">Cycles</div>';
    cards += '<div class="card-value info">' + nego.length + '</div>';
    cards += '<div class="card-sub">PD negotiations</div>';
    cards += '</div>';

    // Hard resets
    cards += '<div class="card">';
    cards += '<div class="card-label">Hard Resets</div>';
    cards += '<div class="card-value ' + (hrCount > 0 ? 'warn' : 'ok') + '">' + hrCount + '</div>';
    cards += '<div class="card-sub">' + (DATA.hard_reset_phases || []).length + ' phases</div>';
    cards += '</div>';

    // State transitions
    cards += '<div class="card">';
    cards += '<div class="card-label">State Transitions</div>';
    cards += '<div class="card-value info">' + transitions.length + '</div>';
    cards += '<div class="card-sub">' + (sm.states_visited || []).length + ' states visited</div>';
    cards += '</div>';

    // Anomalies
    cards += '<div class="card">';
    cards += '<div class="card-label">Anomalies</div>';
    cards += '<div class="card-value ' + (anomalies.length > 0 ? 'warn' : 'ok') + '">' + anomalies.length + '</div>';
    cards += '<div class="card-sub">' + anomalies.filter(a => a.severity === 'critical' || a.severity === 'error').length + ' critical</div>';
    cards += '</div>';

    // Messages
    cards += '<div class="card">';
    cards += '<div class="card-label">Messages</div>';
    cards += '<div class="card-value">' + (txCount + rxCount) + '</div>';
    cards += '<div class="card-sub">' + txCount + ' TX / ' + rxCount + ' RX</div>';
    cards += '</div>';

    // Time range
    const tr = meta.time_range || {{}};
    if (tr.start_kernel_ts && tr.end_kernel_ts) {{
        const duration = ((tr.end_kernel_ts - tr.start_kernel_ts) * 1000).toFixed(0);
        cards += '<div class="card">';
        cards += '<div class="card-label">Duration</div>';
        cards += '<div class="card-value info">' + duration + 'ms</div>';
        cards += '<div class="card-sub">' + (duration / 1000).toFixed(1) + 's total</div>';
        cards += '</div>';
    }}

    document.getElementById('summary-row').innerHTML = cards;
}}

// ============================================================
// Negotiations Tab
// ============================================================
function renderNegotiations() {{
    const nego = DATA.pd_negotiations || [];
    let html = '';

    nego.forEach(n => {{
        const r = n.result || {{}};
        html += '<div class="neg-card">';
        html += '<h4>Cycle #' + n.cycle + ': ' + (n.label || 'Negotiation') + '</h4>';

        // Message flow
        html += '<div class="neg-flow">';
        const msgs = [];
        if (n.source_cap) msgs.push({{label: 'Source Caps', cls: 'rx', id: n.source_cap.event_id}});
        if (n.request) msgs.push({{label: 'Request', cls: 'tx', id: n.request.event_id}});
        if (n.accept) msgs.push({{label: 'Accept', cls: 'rx', id: n.accept.event_id}});
        if (n.ps_rdy) msgs.push({{label: 'PS_RDY', cls: 'rx', id: n.ps_rdy.event_id}});

        msgs.forEach((m, i) => {{
            if (i > 0) html += '<span class="neg-arrow">-></span>';
            html += '<span class="neg-step ' + m.cls + '">' + m.label + ' #' + m.id + '</span>';
        }});

        html += '<span class="neg-arrow">=</span>';
        html += '<span class="neg-step" style="border-color:rgba(68,200,104,0.35);color:var(--ok)">';
        html += fmtVoltage(r.voltage_mv) + ' / ' + fmtCurrent(r.current_ma);
        if (r.final_state) html += ' (' + r.final_state + ')';
        html += '</span>';

        html += '<span style="margin-left:auto;font-size:10px;color:var(--text-dim)">';
        html += relTs(n.start_ts) + 'ms - ' + relTs(n.end_ts) + 'ms';
        html += ' (' + n.event_ids.length + ' events)';
        html += '</span>';
        html += '</div>';

        // PDOs if available
        const sc = n.source_cap || {{}};
        const pdos = sc.pdos || [];
        if (pdos.length) {{
            html += '<div style="margin-top:6px;font-size:10px;color:var(--text-dim)">';
            pdos.forEach(p => {{
                html += '<span style="margin-right:8px;padding:1px 6px;background:var(--surface2);border-radius:3px">';
                html += p.type.toUpperCase() + ' ' + p.voltage_mv + 'mV/' + p.current_ma + 'mA';
                html += '</span>';
            }});
            html += '</div>';
        }}

        html += '</div>';
    }});

    document.getElementById('tab-negotiations').innerHTML = html || '<div style="color:var(--text-dim)">No negotiations detected</div>';
}}

// ============================================================
// Anomalies Tab
// ============================================================
function renderAnomalies() {{
    const anomalies = DATA.anomalies || [];
    let html = '';

    anomalies.forEach(a => {{
        const sev = a.severity || 'info';
        html += '<div class="anomaly-item" onclick="scrollToEvent(' + a.event_id + ')" style="cursor:pointer">';
        html += '<span class="anomaly-desc">[' + a.type.toUpperCase() + '] ' + (a.description || '') + '</span>';
        if (a.detail) html += '<div class="anomaly-detail">' + a.detail + ' (event #' + a.event_id + ')</div>';
        html += '</div>';
    }});

    document.getElementById('tab-anomalies').innerHTML = html || '<div style="color:var(--ok)">No anomalies detected</div>';
}}

// ============================================================
// Raw Events Tab
// ============================================================
function renderRawEvents() {{
    const timeline = DATA.timeline || [];
    let html = '<table class="hex-table" style="width:100%;border-collapse:collapse;font-size:10px">';
    html += '<thead><tr style="color:var(--text-dim);text-align:left">';
    html += '<th style="padding:4px 8px">#</th>';
    html += '<th style="padding:4px 8px">Time</th>';
    html += '<th style="padding:4px 8px">Dir</th>';
    html += '<th style="padding:4px 8px">Type</th>';
    html += '<th style="padding:4px 8px">Content</th>';
    html += '</tr></thead><tbody>';

    timeline.forEach(e => {{
        if (FILTER_HIDDEN.has(e.event_type)) return;
        const dir = getDir(e);
        html += '<tr class="msg-row ' + dir + '" style="display:table-row;cursor:pointer" ';
        html += 'onmouseenter="showTooltip(event, ' + e.id + ')" onmouseleave="hideTooltip()">';
        html += '<td style="padding:2px 8px;color:var(--text-dim)">' + e.id + '</td>';
        html += '<td style="padding:2px 8px;color:var(--text-dim)">' + relTs(e.kernel_ts) + 'ms</td>';
        html += '<td style="padding:2px 8px;text-align:center;color:' + (dir === 'tx' ? 'var(--tx)' : dir === 'rx' ? 'var(--rx)' : 'var(--text-dim)') + '">' + dir.toUpperCase() + '</td>';
        html += '<td style="padding:2px 8px">' + getTypeLabel(e) + '</td>';
        html += '<td style="padding:2px 8px;color:var(--text-dim);max-width:500px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + escapeHtml(e.content_raw || '') + '</td>';
        html += '</tr>';
    }});
    html += '</tbody></table>';

    document.getElementById('tab-raw').innerHTML = html;
}}

// ============================================================
// Event Type Filter
// ============================================================
function renderFilter() {{
    // Gather all unique event types
    const types = new Set();
    (DATA.timeline || []).forEach(e => types.add(e.event_type));
    const sorted = Array.from(types).sort();

    // Group by category
    const groups = {{
        'STATE': [], 'PD': [], 'CC': [], 'CHARGER': [], 'MUSB': [], 'TYPEC': [], 'OTHER': []
    }};

    sorted.forEach(t => {{
        if (t.startsWith('state_') || t.startsWith('pd_engine_')) groups['STATE'].push(t);
        else if (t.startsWith('pd_')) groups['PD'].push(t);
        else if (t.startsWith('cc_')) groups['CC'].push(t);
        else if (t.startsWith('charger_')) groups['CHARGER'].push(t);
        else if (t.startsWith('musb_') || t.startsWith('usb_')) groups['MUSB'].push(t);
        else if (t.startsWith('typec_') || t.startsWith('tcpm_')) groups['TYPEC'].push(t);
        else groups['OTHER'].push(t);
    }});

    let html = '<span class="filter-label">Filter:</span>';

    Object.entries(groups).forEach(([group, items]) => {{
        if (!items.length) return;
        html += '<span style="font-size:9px;color:var(--text-dim);margin:0 4px">' + group + '</span>';
        items.forEach(t => {{
            html += '<label class="checked" data-type="' + t + '">';
            html += '<input type="checkbox" checked onchange="toggleFilter(this, \'' + t + '\')">';
            html += t.replace(/_/g, ' ');
            html += '</label>';
        }});
    }});

    html += '<button onclick="selectAll()" style="font-size:9px;color:var(--tx);background:none;border:1px solid var(--border);padding:2px 6px;border-radius:3px;cursor:pointer;margin-left:8px;font-family:inherit">All</button>';
    html += '<button onclick="deselectAll()" style="font-size:9px;color:var(--text-dim);background:none;border:1px solid var(--border);padding:2px 6px;border-radius:3px;cursor:pointer;font-family:inherit">None</button>';

    document.getElementById('filter-row').innerHTML = html;
}}

function toggleFilter(cb, eventType) {{
    const label = cb.parentElement;
    if (cb.checked) {{
        FILTER_HIDDEN.delete(eventType);
        label.classList.add('checked');
    }} else {{
        FILTER_HIDDEN.add(eventType);
        label.classList.remove('checked');
    }}
    renderMessageTimeline();
    renderRawEvents();
}}

function selectAll() {{
    FILTER_HIDDEN.clear();
    document.querySelectorAll('#filter-row input').forEach(cb => {{
        cb.checked = true;
        cb.parentElement.classList.add('checked');
    }});
    renderMessageTimeline();
    renderRawEvents();
}}

function deselectAll() {{
    document.querySelectorAll('#filter-row input').forEach(cb => {{
        cb.checked = false;
        FILTER_HIDDEN.add(cb.parentElement.dataset.type);
        cb.parentElement.classList.remove('checked');
    }});
    renderMessageTimeline();
    renderRawEvents();
}}

// ============================================================
// Scroll to event (highlight in right column)
// ============================================================
function scrollToEvent(eid) {{
    const el = document.querySelector('.msg-row[data-eid="' + eid + '"]');
    if (el) {{
        el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        el.style.background = 'rgba(54,176,224,0.15)';
        setTimeout(() => {{ el.style.background = ''; }}, 1500);
    }}
}}

// ============================================================
// Tab switching
// ============================================================
document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    }});
}});

// ============================================================
// Init
// ============================================================
renderSummary();
renderStateMachine();
renderMessageTimeline();
renderNegotiations();
renderAnomalies();
renderRawEvents();
renderFilter();
</script>
</body>
</html>"""


# ============================================================
# CLI entry point
# ============================================================
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Generate HTML visualization from protocol extraction JSON")
    ap.add_argument("input", help="Extraction JSON file (from smart_extractor output)")
    ap.add_argument("-o", "--output", default=None, help="Output HTML file path (default: input.html)")
    ap.add_argument("-t", "--title", default=None, help="Report title")

    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = generate_html(data, title=args.title)

    out_path = args.output or (os.path.splitext(args.input)[0] + ".html")
    saved = save_report(html, out_path)
    print(f"Report saved: {saved}")