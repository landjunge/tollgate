"""Control Room WebUI — Protect · Route · Prove.

Designed for operators: see agents, set $ limits, prove failover.
"""

from __future__ import annotations

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tollgate · Control Room</title>
<style>
  :root {
    /* Gnom-Hub-V1 desk chrome (shared). */
    --bg: #121316;
    --bg2: #1a1b1f;
    --panel: #1e1f24;
    --panel2: #24262d;
    --line: #2e3138;
    --line2: #3a3e46;
    --fg: #e2e4e9;
    --muted: #8b909a;
    --muted2: #6b7280;
    --ok: #3d9b6a;
    --ok-dim: rgba(61,155,106,.12);
    --warn: #c9a227;
    --warn-dim: rgba(201,162,39,.12);
    --bad: #c45c5c;
    --bad-dim: rgba(196,92,92,.12);
    --acc: #a1a8b3;
    --acc2: #6b7280;
    --acc-dim: rgba(161,168,179,.12);
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 4px 18px rgba(0, 0, 0, 0.28);
    --font: system-ui, -apple-system, "Segoe UI", sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    min-height: 100vh;
    font-family: var(--font);
    background: var(--bg);
    color: var(--fg);
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
  }
  a { color: var(--acc); text-decoration: none; }
  a:hover { text-decoration: underline; }
  button {
    font: inherit; cursor: pointer; border: 0; border-radius: 10px;
    background: linear-gradient(180deg, var(--acc) 0%, var(--acc2) 100%);
    color: #fff; padding: .55rem 1.05rem; font-weight: 600;
    box-shadow: 0 1px 0 rgba(255,255,255,.12) inset, 0 4px 14px rgba(91,124,250,.25);
    transition: transform .12s ease, filter .12s ease, opacity .12s;
  }
  button:hover { filter: brightness(1.06); }
  button:active { transform: translateY(1px); }
  button:disabled { opacity: .5; cursor: wait; filter: none; }
  button.ghost {
    background: transparent; color: var(--fg);
    border: 1px solid var(--line2);
    box-shadow: none;
  }
  button.ghost:hover { background: var(--panel2); border-color: var(--muted2); filter: none; }
  button.sm { padding: .35rem .7rem; font-size: .82rem; border-radius: 8px; }

  /* Header */
  header {
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    padding: .85rem 1.5rem;
    border-bottom: 1px solid var(--line);
    background: rgba(9,11,16,.82);
    backdrop-filter: blur(16px) saturate(1.2);
    position: sticky; top: 0; z-index: 20;
  }
  .brand {
    display: flex; align-items: baseline; gap: .55rem;
    font-weight: 750; letter-spacing: .06em; font-size: .95rem;
  }
  .brand em { font-style: normal; color: var(--muted); font-weight: 500; letter-spacing: 0; font-size: .82rem; }
  .header-right { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; }
  .auth-bar {
    display: flex; align-items: center; gap: .4rem;
    font-size: .78rem; color: var(--muted);
    background: var(--panel); border: 1px solid var(--line); border-radius: 999px;
    padding: .25rem .55rem .25rem .75rem;
  }
  .auth-bar input {
    background: transparent; border: 0; color: var(--fg);
    width: 7.5rem; font: inherit; outline: none;
  }
  .badge {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: .32rem .75rem; border-radius: 999px;
    font-size: .72rem; font-weight: 700; letter-spacing: .05em;
    background: var(--panel); border: 1px solid var(--line); color: var(--muted);
  }
  .badge.ok { color: var(--ok); border-color: rgba(52,211,153,.35); background: var(--ok-dim); }
  .badge.warn { color: var(--warn); border-color: rgba(251,191,36,.35); background: var(--warn-dim); }
  .badge.bad, .badge.frozen { color: var(--bad); border-color: rgba(244,63,94,.4); background: var(--bad-dim); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; }

  nav {
    display: flex; gap: .2rem; flex-wrap: wrap;
    padding: .45rem 1.5rem;
    border-bottom: 1px solid var(--line);
    background: rgba(14,17,24,.6);
  }
  nav a {
    color: var(--muted); padding: .5rem .95rem; border-radius: 9px;
    font-size: .88rem; font-weight: 600; text-decoration: none;
  }
  nav a:hover { color: var(--fg); background: var(--panel); text-decoration: none; }
  nav a.active {
    color: var(--fg); background: var(--panel);
    border: 1px solid var(--line2);
    box-shadow: var(--shadow);
  }

  main { max-width: 1040px; margin: 0 auto; padding: 1.5rem 1.5rem 4rem; }
  .view { display: none; animation: fade .25s ease; }
  .view.active { display: block; }
  @keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

  h1.page { font-size: 1.55rem; font-weight: 750; margin: 0 0 .35rem; letter-spacing: -.02em; }
  .sub { color: var(--muted); margin: 0 0 1.35rem; font-size: .95rem; max-width: 42rem; }
  h2.sec {
    font-size: .72rem; text-transform: uppercase; letter-spacing: .1em;
    color: var(--muted2); margin: 1.6rem 0 .65rem; font-weight: 700;
  }

  .card {
    background: linear-gradient(180deg, var(--panel) 0%, var(--bg2) 100%);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 1.15rem 1.25rem;
    margin-bottom: .9rem;
    box-shadow: var(--shadow);
  }
  .card.flat { background: var(--panel); box-shadow: none; }

  .hero {
    display: grid; grid-template-columns: 150px 1fr; gap: 1.5rem; align-items: center;
  }
  @media (max-width:720px) {
    .hero { grid-template-columns: 1fr; }
    nav { overflow-x: auto; flex-wrap: nowrap; }
  }

  .ring-box { position: relative; width: 128px; height: 128px; margin: 0 auto; }
  .ring {
    --p: 0; width: 128px; height: 128px; border-radius: 50%;
    background: conic-gradient(var(--acc) calc(var(--p) * 1%), var(--line) 0);
    display: grid; place-items: center;
  }
  .ring::before {
    content: ""; width: 94px; height: 94px; border-radius: 50%;
    background: var(--panel); border: 1px solid var(--line);
  }
  .ring-box .val {
    position: absolute; inset: 0; display: grid; place-items: center;
    font-size: 1.75rem; font-weight: 800; letter-spacing: -.03em;
  }
  .ring-label {
    text-align: center; margin-top: .45rem;
    font-size: .7rem; color: var(--muted2); text-transform: uppercase; letter-spacing: .08em;
  }
  .grade { text-align: center; font-weight: 700; font-size: .9rem; margin-top: .15rem; }

  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .65rem; }
  @media (max-width:560px) { .stats { grid-template-columns: 1fr 1fr; } }
  .stat {
    background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-sm);
    padding: .7rem .8rem;
  }
  .stat b { display: block; font-size: 1.15rem; font-weight: 750; font-variant-numeric: tabular-nums; }
  .stat span {
    color: var(--muted2); font-size: .68rem; text-transform: uppercase;
    letter-spacing: .06em; font-weight: 600;
  }

  .muted { color: var(--muted); }
  .ok { color: var(--ok); } .warn { color: var(--warn); } .bad { color: var(--bad); }

  .row {
    display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    padding: .65rem 0; border-bottom: 1px solid var(--line); font-size: .92rem;
  }
  .row:last-child { border-bottom: 0; }

  .pill {
    display: inline-flex; align-items: center; gap: .25rem;
    padding: .18rem .5rem; border-radius: 999px;
    font-size: .72rem; font-weight: 650;
    background: var(--bg); border: 1px solid var(--line); color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .pill.ok { color: var(--ok); border-color: rgba(52,211,153,.3); background: var(--ok-dim); }
  .pill.warn { color: var(--warn); border-color: rgba(251,191,36,.3); background: var(--warn-dim); }
  .pill.bad { color: var(--bad); border-color: rgba(244,63,94,.35); background: var(--bad-dim); }
  .pill.acc { color: var(--acc); border-color: rgba(124,156,255,.35); background: var(--acc-dim); }

  .bar {
    height: 6px; background: var(--line); border-radius: 99px; overflow: hidden; margin-top: .5rem;
  }
  .bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--acc2), var(--acc)); border-radius: 99px; }
  .bar.warn i { background: linear-gradient(90deg, #d97706, var(--warn)); }
  .bar.bad i { background: linear-gradient(90deg, #e11d48, var(--bad)); }

  /* Agent cards */
  .agent-grid { display: grid; gap: .85rem; }
  .agent-card {
    background: linear-gradient(165deg, var(--panel) 0%, var(--bg2) 100%);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 1.15rem 1.25rem;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
  }
  .agent-card::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--line2);
  }
  .agent-card.is-ok::before { background: var(--ok); }
  .agent-card.is-warn::before { background: var(--warn); }
  .agent-card.is-bad::before { background: var(--bad); }
  .agent-top {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
  }
  .agent-name { font-size: 1.12rem; font-weight: 750; letter-spacing: -.01em; }
  .agent-meta { margin-top: .3rem; font-size: .84rem; }
  .agent-spend {
    text-align: right; font-variant-numeric: tabular-nums;
  }
  .agent-spend .big {
    font-size: 1.35rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.1;
  }
  .agent-spend .cap { font-size: .8rem; color: var(--muted); margin-top: .15rem; }
  .limit-row {
    display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .75rem;
  }
  .agent-foot {
    display: flex; justify-content: space-between; align-items: center;
    gap: .75rem; margin-top: .85rem; flex-wrap: wrap;
  }
  .agent-foot .muted { font-size: .82rem; }

  .editor {
    display: none;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
  }
  .editor.open { display: block; }
  .editor h3 {
    margin: 0 0 .75rem; font-size: .8rem; text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted2); font-weight: 700;
  }
  .fields {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: .65rem;
  }
  @media (max-width:700px) { .fields { grid-template-columns: 1fr 1fr; } }
  @media (max-width:480px) { .fields { grid-template-columns: 1fr; } }
  .field { margin: 0; }
  .field label {
    display: block; font-size: .7rem; color: var(--muted2);
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: .3rem; font-weight: 650;
  }
  .field input, .field select {
    width: 100%; background: var(--panel); border: 1px solid var(--line2);
    color: var(--fg); border-radius: 9px; padding: .55rem .7rem; font: inherit;
    font-variant-numeric: tabular-nums;
  }
  .field input:focus, .field select:focus {
    outline: none; border-color: var(--acc); box-shadow: 0 0 0 3px var(--acc-dim);
  }
  .field hint { display: block; margin-top: .25rem; font-size: .72rem; color: var(--muted2); }
  .editor .actions { margin-top: .9rem; display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }

  .overview-agents {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: .75rem;
  }
  .mini-agent {
    background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-sm);
    padding: .85rem .95rem; cursor: pointer; transition: border-color .15s, background .15s;
  }
  .mini-agent:hover { border-color: var(--line2); background: var(--panel2); }
  .mini-agent .n { font-weight: 700; font-size: .95rem; }
  .mini-agent .s { font-size: 1.05rem; font-weight: 750; margin: .35rem 0 .2rem; font-variant-numeric: tabular-nums; }
  .mini-agent .l { font-size: .78rem; color: var(--muted); }

  table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  th, td { text-align: left; padding: .6rem .4rem; border-bottom: 1px solid var(--line); }
  th { color: var(--muted2); font-size: .68rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }
  tr:last-child td { border-bottom: 0; }
  tr.click { cursor: pointer; }
  tr.click:hover td { background: rgba(124,156,255,.05); }

  .kv { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem .85rem; font-size: .9rem; }
  .kv b { color: var(--muted); font-weight: 500; font-size: .78rem; display: block; margin-bottom: .15rem; }

  .reco {
    border-left: 3px solid var(--warn); padding: .15rem 0 .15rem .9rem; margin: .55rem 0;
    font-size: .92rem;
  }
  .reco.ok { border-color: var(--ok); }
  .reco.bad { border-color: var(--bad); }

  .actions { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: .85rem; }
  .empty { color: var(--muted); padding: .4rem 0; font-size: .92rem; }
  code {
    font-family: var(--mono); background: var(--bg); padding: .12rem .35rem;
    border-radius: 5px; font-size: .8rem; border: 1px solid var(--line);
  }
  footer {
    margin-top: 2.5rem; padding-top: 1.25rem; border-top: 1px solid var(--line);
    color: var(--muted2); font-size: .78rem; line-height: 1.7;
  }

  /* Onboarding + modal */
  #onboard {
    display: none; position: fixed; inset: 0; z-index: 50;
    background: rgba(5,7,12,.9); backdrop-filter: blur(12px);
    align-items: center; justify-content: center; padding: 1.25rem;
  }
  #onboard.open { display: flex; }
  .ob-card {
    width: min(440px, 100%); background: var(--panel); border: 1px solid var(--line);
    border-radius: 18px; padding: 1.5rem; box-shadow: var(--shadow);
  }
  .ob-steps { display: flex; gap: .4rem; margin: 0 0 1.1rem; }
  .ob-steps i { flex: 1; height: 4px; border-radius: 2px; background: var(--line); }
  .ob-steps i.on { background: var(--acc); }
  .ob-card h1 { font-size: 1.25rem; margin: 0 0 .4rem; }
  .ob-actions { display: flex; gap: .5rem; justify-content: space-between; margin-top: 1.1rem; flex-wrap: wrap; }
  .ob-check { margin: .4rem 0; font-size: .95rem; }
  .ob-check.ok { color: var(--ok); }
  .field-row { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; }
  #blockModal {
    display: none; position: fixed; inset: 0; z-index: 60;
    background: rgba(5,7,12,.88); align-items: center; justify-content: center; padding: 1rem;
  }
  #blockModal.open { display: flex; }
  #blockModal .card {
    max-width: 440px; width: 100%; white-space: pre-wrap;
    font-family: var(--mono); font-size: .85rem;
  }
  #secBanner {
    display: none; margin: 0; padding: .55rem 1.5rem; font-size: .85rem;
    background: #2a1c0c; color: #f5c48a; border-bottom: 1px solid #6a4a12;
  }
  #secBanner.show { display: block; }
  #secBanner.bad { background: #2a1018; color: #f5a0b0; border-color: #6a1a35; }
</style>
</head>
<body>
<div id="secBanner" role="status"></div>
<div id="onboard" role="dialog" aria-label="Setup">
  <div class="ob-card">
    <div class="ob-steps" id="obSteps"><i class="on"></i><i></i><i></i><i></i></div>
    <div id="obBody"></div>
    <div class="ob-actions">
      <button type="button" class="ghost" id="obSkip">Skip</button>
      <div style="display:flex;gap:.5rem">
        <button type="button" class="ghost" id="obBack" style="display:none">Back</button>
        <button type="button" id="obNext">Continue</button>
      </div>
    </div>
    <p class="muted" id="obErr" style="margin:.75rem 0 0;font-size:.85rem;display:none"></p>
  </div>
</div>

<header>
  <div class="brand">TOLLGATE <em id="dayLabel"></em></div>
  <div class="header-right">
    <button type="button" class="ghost sm" id="btnSetup">Setup</button>
    <div class="auth-bar" title="Open mode: any label · Auth mode: id:secret">
      <span>key</span>
      <input id="apiKey" placeholder="desk" value="desk" autocomplete="off"/>
    </div>
    <div class="badge ok" id="statusBadge"><span class="dot"></span><span id="statusText">…</span></div>
  </div>
</header>

<nav>
  <a href="#overview" data-view="overview" class="active">Overview</a>
  <a href="#agents" data-view="agents">Agents</a>
  <a href="#providers" data-view="providers">Providers</a>
  <a href="#prove" data-view="prove">Prove</a>
  <a href="#audit" data-view="audit">Audit</a>
</nav>

<main>
  <section class="view active" id="view-overview">
    <h1 class="page">Control Room</h1>
    <p class="sub">Is your AI safe, does it work, and what must you do next?</p>

    <div class="card hero">
      <div>
        <div class="ring-box">
          <div class="ring" id="ring" style="--p:0"></div>
          <div class="val" id="ringVal">—</div>
        </div>
        <div class="ring-label">Reliability</div>
        <div class="grade" id="grade">—</div>
      </div>
      <div>
        <div class="stats" id="stats"></div>
        <p class="muted" style="margin:.9rem 0 0;font-size:.9rem" id="headline"></p>
      </div>
    </div>

    <h2 class="sec">Agents · spend &amp; limits</h2>
    <div class="card flat">
      <div class="overview-agents" id="costSplit"><div class="empty">Loading…</div></div>
      <div class="actions" style="margin-top:.85rem">
        <a href="#agents" class="ghost" style="display:inline-flex;padding:.45rem .9rem;border-radius:10px;border:1px solid var(--line2);font-weight:600;color:var(--fg);text-decoration:none">Manage limits →</a>
      </div>
    </div>

    <h2 class="sec">Needs attention</h2>
    <div class="card" id="attention"><div class="empty">Loading…</div></div>

    <h2 class="sec">Recommendations</h2>
    <div class="card" id="reco"><div class="empty">Loading…</div></div>

    <h2 class="sec">Providers</h2>
    <div class="card" id="provGlance"><div class="empty">Loading…</div></div>

    <div class="actions">
      <button type="button" class="ghost" id="btnLoopTest">Test tool-loop block</button>
      <button type="button" class="ghost" id="btnUnfreeze" style="display:none">Unfreeze admission</button>
    </div>
  </section>

  <div id="blockModal"><div class="card" id="blockModalBody"></div></div>

  <section class="view" id="view-agents">
    <h1 class="page">Agents</h1>
    <p class="sub">Each lane (agent / app) has its own hard limits. Open <b>Edit limits</b> to change day, hour, and per-request budgets.</p>
    <div class="agent-grid" id="agentsList"><div class="card empty">Loading…</div></div>
  </section>

  <section class="view" id="view-providers">
    <h1 class="page">Providers</h1>
    <p class="sub">Which provider works best right now — health, not a config dump.</p>
    <div class="card">
      <table>
        <thead><tr><th>Provider</th><th>Health</th><th>Success</th><th>Latency</th><th>Cost day</th><th>Circuit</th></tr></thead>
        <tbody id="provTable"></tbody>
      </table>
    </div>
    <div id="provDetail"></div>
  </section>

  <section class="view" id="view-prove">
    <h1 class="page">Prove</h1>
    <p class="sub">Is failover real — or only configured?</p>
    <div class="card" id="proveScore"></div>
    <div class="card">
      <h2 class="sec" style="margin-top:0">Provider failover test</h2>
      <p class="muted" id="proveLast">Last test: —</p>
      <div class="actions">
        <label class="muted" style="display:flex;align-items:center;gap:.4rem">Provider
          <input id="chaosProvider" value="opencode_zen"
            style="background:var(--bg);border:1px solid var(--line2);color:var(--fg);border-radius:8px;padding:.4rem .55rem"/>
        </label>
        <button id="btnChaos">Run test</button>
        <button class="ghost" id="btnCert">Refresh certificate</button>
      </div>
      <pre id="proveOut" class="muted" style="margin-top:1rem;white-space:pre-wrap;font-size:.85rem;font-family:var(--mono)"></pre>
    </div>
    <div class="card" id="certCard"></div>
  </section>

  <section class="view" id="view-audit">
    <h1 class="page">Audit</h1>
    <p class="sub">What Tollgate allowed, blocked, or failed over — ops only, no secrets.</p>
    <div class="actions" style="margin-bottom:.75rem">
      <button class="ghost" id="btnAudit">Refresh</button>
      <button class="ghost" id="btnAuditDenies">Denies only</button>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>When</th><th>Agent</th><th>Event</th><th>Provider</th><th>Detail</th></tr></thead>
        <tbody id="auditTable"></tbody>
      </table>
    </div>
  </section>

  <footer>
    Safety layer for AI agents · not a gateway catalog ·
    <a href="/docs">API</a> ·
    <a href="https://landjunge.github.io/tollgate/" target="_blank" rel="noopener">Website</a> ·
    <a href="https://github.com/landjunge/tollgate">GitHub</a> ·
    <code>tollgate help</code>
  </footer>
</main>

<script>
const $ = (id) => document.getElementById(id);
function key() { return ($('apiKey').value || 'desk').trim(); }
function headers() {
  const k = key();
  return {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Consumer-Key': k,
    'Authorization': 'Bearer ' + k,
  };
}
function cls(s) {
  s = (s || '').toLowerCase();
  if (['ok','healthy','pass','protected','closed'].includes(s)) return 'ok';
  if (['warn','likely_over','degraded','half_open','approaching','ready','not_run'].includes(s)) return 'warn';
  return 'bad';
}
function money(n) {
  const v = Number(n || 0);
  return '$' + (Math.abs(v) >= 10 ? v.toFixed(2) : v.toFixed(2));
}
function money4(n) { return '$' + Number(n || 0).toFixed(4); }
function pct(n) { return n == null ? '—' : (Number(n) * 100).toFixed(1) + '%'; }
function when(ts) {
  if (ts == null || ts === '') return '—';
  try {
    const t = Number(ts) > 1e12 ? Number(ts) : Number(ts) * 1000;
    return new Date(t).toLocaleString();
  } catch { return String(ts); }
}
function grade(score) {
  if (score == null) return { t: '—', c: 'muted' };
  if (score >= 85) return { t: 'GOOD', c: 'ok' };
  if (score >= 65) return { t: 'FAIR', c: 'warn' };
  return { t: 'WEAK', c: 'bad' };
}
function cardTone(c) {
  if (!c.protected) return 'is-warn';
  if (c.status === 'over_budget' || c.status === 'blocked') return 'is-bad';
  if (c.status === 'warn' || c.status === 'likely_over') return 'is-warn';
  return 'is-ok';
}
function limitPills(c) {
  const pills = [];
  if (c.max_usd_day) pills.push(`<span class="pill acc" title="Tagesbudget">Day ${money(c.max_usd_day)}</span>`);
  if (c.max_usd_hour) pills.push(`<span class="pill warn" title="Stundenbudget — oft der „$2“-Wert">Hour ${money(c.max_usd_hour)}</span>`);
  if (c.max_usd_request) pills.push(`<span class="pill" title="Pro Request">Req ${money4(c.max_usd_request)}</span>`);
  if (c.max_tool_calls) pills.push(`<span class="pill" title="Tool-Loop-Stop">Tools ${c.max_tool_calls}</span>`);
  if (c.max_requests_minute) pills.push(`<span class="pill">${c.max_requests_minute}/min</span>`);
  if (!pills.length) pills.push(`<span class="pill bad">No hard limits</span>`);
  return pills.join('');
}

let CTRL = null;
let CERT = null;

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(r.status + ' ' + t.slice(0, 180));
  }
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('json')) return r.json();
  return r.text();
}

function setStatus(ctrl) {
  const fr = ctrl.freeze || {};
  const att = ctrl.attention || [];
  const urgent = att.filter(a => a.level === 'error' || a.level === 'warn');
  const badge = $('statusBadge');
  const text = $('statusText');
  badge.className = 'badge';
  if (fr.frozen) {
    badge.classList.add('frozen');
    text.textContent = 'FROZEN';
  } else if (urgent.some(a => a.level === 'error')) {
    badge.classList.add('bad');
    text.textContent = 'ATTENTION';
  } else if (urgent.length) {
    badge.classList.add('warn');
    text.textContent = 'ATTENTION';
  } else {
    badge.classList.add('ok');
    text.textContent = 'PROTECTED';
  }
}

function renderOverview(ctrl, cert) {
  const s = ctrl.summary || {};
  const res = ctrl.resilience || {};
  const score = res.score != null ? Number(res.score) : null;
  const g = grade(score);
  $('ring').style.setProperty('--p', score == null ? 0 : Math.max(0, Math.min(100, score)));
  $('ringVal').textContent = score == null ? '—' : Math.round(score);
  $('grade').innerHTML = `<span class="${g.c}">${g.t}</span>`;
  $('dayLabel').textContent = ctrl.day ? '· ' + ctrl.day : '';
  $('headline').textContent = ctrl.headline || '';
  $('stats').innerHTML = [
    ['Spent today', money(s.usd)],
    ['Requests', String(s.calls ?? 0)],
    ['Success', s.errors != null && s.calls ? pct(1 - (s.errors / (s.calls || 1))) : '—'],
    ['Agent stops', String(s.agent_protection_blocks ?? 0)],
    ['Circuits open', String(s.circuits_open ?? 0)],
    ['Agents protected', String(s.consumers_protected ?? 0)],
  ].map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');

  const consumers = ctrl.consumers || [];
  if (!consumers.length) {
    $('costSplit').innerHTML = `<div class="empty">No agents yet — send traffic, then set limits under Agents.</div>`;
  } else {
    $('costSplit').innerHTML = consumers.slice(0, 12).map(c => {
      const day = c.max_usd_day ? money(c.max_usd_day) + '/day' : 'no day cap';
      const hour = c.max_usd_hour ? ' · ' + money(c.max_usd_hour) + '/hour' : '';
      return `<div class="mini-agent" data-goto-agent="${c.consumer}">
        <div class="n">${c.consumer}</div>
        <div class="s">${money4(c.usd)}</div>
        <div class="l">${day}${hour} · ${c.calls || 0} req</div>
      </div>`;
    }).join('');
    document.querySelectorAll('[data-goto-agent]').forEach(el => {
      el.onclick = () => {
        location.hash = '#agents';
        onHash();
        setTimeout(() => {
          const name = el.getAttribute('data-goto-agent');
          const cards = document.querySelectorAll('.agent-card');
          cards.forEach(card => {
            if (card.dataset.name === name) {
              const ed = card.querySelector('.editor');
              if (ed) {
                ed.classList.add('open');
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
            }
          });
        }, 80);
      };
    });
  }

  const att = ctrl.attention || [];
  if (!att.length) {
    $('attention').innerHTML = `<div class="ok">✓ Nothing urgent — agents under control</div>`;
  } else {
    $('attention').innerHTML = `<div class="muted" style="margin-bottom:.5rem">${att.length} item(s)</div>` +
      att.map(a => {
        const c = a.level === 'ok' ? 'ok' : (a.level === 'error' ? 'bad' : 'warn');
        const mark = a.level === 'ok' ? '✓' : (a.level === 'error' ? '⛔' : '⚠');
        return `<div class="row"><span class="${c}">${mark} ${a.message || ''}</span><span class="muted">${a.code || ''}</span></div>`;
      }).join('');
  }

  const recos = [];
  if (ctrl.freeze && ctrl.freeze.frozen) {
    recos.push({ level: 'bad', text: 'Admission is frozen — no billable traffic.', href: null });
  }
  consumers.filter(c => !c.protected && c.consumer).forEach(c => {
    recos.push({ level: 'warn', text: `«${c.consumer}» has weak limits — set day/hour budgets under Agents.`, href: '#agents' });
  });
  consumers.filter(c => ['warn', 'likely_over', 'over_budget'].includes(c.status)).forEach(c => {
    recos.push({
      level: c.status === 'over_budget' ? 'bad' : 'warn',
      text: `«${c.consumer}» ${money4(c.usd)}` + (c.max_usd_day ? ` / ${money(c.max_usd_day)} day` : '') + ` (${c.status})`,
      href: '#agents',
    });
  });
  const last = (ctrl.chaos || {}).last_report;
  if (!last) {
    recos.push({ level: 'warn', text: 'Prove pending: no failover test yet. Needs ≥2 providers + keys.', href: '#prove' });
  } else if (last.survived === false) {
    recos.push({ level: 'bad', text: `Last DR test failed for ${last.chaos_provider}.`, href: '#prove' });
  }
  if (!recos.length) recos.push({ level: 'ok', text: 'Desk looks protected. Keep using real traffic.', href: null });
  $('reco').innerHTML = recos.map(r =>
    `<div class="reco ${r.level}">${r.text}${r.href ? ` <a href="${r.href}">Open →</a>` : ''}</div>`
  ).join('');

  const provs = (ctrl.providers || []).filter(p => p.enabled !== false).slice(0, 6);
  if (!provs.length) {
    $('provGlance').innerHTML = `<div class="empty">No provider traffic yet</div>`;
  } else {
    $('provGlance').innerHTML = provs.map(p =>
      `<div class="row">
        <span><b>${p.provider}</b> <span class="pill ${cls(p.status)}">${p.status}</span></span>
        <span class="muted">${pct(p.success_rate)} · ${p.latency_ms_avg != null ? Math.round(p.latency_ms_avg) + 'ms' : '—'} · ${money4(p.usd)}</span>
      </div>`
    ).join('');
  }

  const uf = $('btnUnfreeze');
  if (uf) uf.style.display = (ctrl.freeze && ctrl.freeze.frozen) ? '' : 'none';
}

function renderAgents(ctrl) {
  const list = ctrl.consumers || [];
  if (!list.length) {
    $('agentsList').innerHTML = `<div class="card empty">No agents yet.
      <div class="actions"><button type="button" id="btnSetupAgents">Protect first agent</button></div></div>`;
    const b = $('btnSetupAgents');
    if (b) b.onclick = () => { OB.step = 0; renderObSteps(); showOnboard(true); };
    return;
  }
  $('agentsList').innerHTML = list.map((c, i) => {
    const max = Number(c.max_usd_day || 0);
    const used = Number(c.usd || 0);
    const rem = max > 0 ? Math.max(0, (c.remaining_usd != null ? Number(c.remaining_usd) : max - used)) : null;
    const ratio = max > 0 ? Math.min(100, (used / max) * 100) : 0;
    const barC = (c.status === 'over_budget' || c.status === 'blocked') ? 'bad'
      : (c.status === 'warn' || c.status === 'likely_over') ? 'warn' : '';
    const st = c.protected ? (c.status === 'ok' ? 'Protected' : c.status) : 'Unprotected';
    const stc = c.protected && c.status === 'ok' ? 'ok' : cls(c.status);
    return `<div class="agent-card ${cardTone(c)}" data-name="${c.consumer}" id="agent-card-${i}">
      <div class="agent-top">
        <div>
          <div class="agent-name">${c.consumer}</div>
          <div class="agent-meta ${stc}">● ${st}${c.uses_default_only ? ' · default policy' : ''}</div>
        </div>
        <div class="agent-spend">
          <div class="big">${money4(used)}</div>
          <div class="cap">${max > 0 ? 'of ' + money(max) + ' / day' : 'spent today'}${rem != null && max > 0 ? ' · ' + money4(rem) + ' left' : ''}</div>
        </div>
      </div>
      ${max > 0 ? `<div class="bar ${barC}"><i style="width:${ratio}%"></i></div>` : ''}
      <div class="limit-row">${limitPills(c)}</div>
      <div class="agent-foot">
        <span class="muted">${c.calls || 0} requests · ${c.tokens || 0} tokens · EOD ~ ${money4(c.projected_usd_eod)}</span>
        <div style="display:flex;gap:.4rem">
          <button type="button" class="ghost sm" data-edit="${i}">Edit limits</button>
          <button type="button" class="ghost sm" data-loop="${c.consumer}">Test loop</button>
        </div>
      </div>
      <div class="editor" id="agent-d-${i}">
        <h3>Limits for «${c.consumer}»</h3>
        <div class="fields">
          <div class="field">
            <label>Day budget ($)</label>
            <input id="ed-day-${i}" type="number" min="0" step="0.5" value="${c.max_usd_day ?? ''}" placeholder="e.g. 5"/>
            <span class="hint">Hard stop for the calendar day</span>
          </div>
          <div class="field">
            <label>Hour budget ($)</label>
            <input id="ed-hour-${i}" type="number" min="0" step="0.25" value="${c.max_usd_hour ?? ''}" placeholder="e.g. 2"/>
            <span class="hint">Often the “$2” default — separate from day</span>
          </div>
          <div class="field">
            <label>Max $ / request</label>
            <input id="ed-req-${i}" type="number" min="0" step="0.05" value="${c.max_usd_request ?? ''}" placeholder="e.g. 0.50"/>
            <span class="hint">Blocks oversized single calls</span>
          </div>
          <div class="field">
            <label>Max tool-calls</label>
            <input id="ed-tools-${i}" type="number" min="0" step="1" value="${c.max_tool_calls ?? ''}" placeholder="e.g. 20"/>
            <span class="hint">Stops runaway agent loops</span>
          </div>
          <div class="field">
            <label>Max req / minute</label>
            <input id="ed-rpm-${i}" type="number" min="0" step="1" value="${c.max_requests_minute ?? ''}" placeholder="e.g. 40"/>
            <span class="hint">Rate limit per lane</span>
          </div>
        </div>
        <div class="actions">
          <button type="button" data-save="${i}" data-name="${c.consumer}">Save limits</button>
          <button type="button" class="ghost" data-edit-close="${i}">Cancel</button>
          <span id="ed-msg-${i}" class="muted" style="font-size:.85rem"></span>
        </div>
      </div>
    </div>`;
  }).join('');

  document.querySelectorAll('[data-edit]').forEach(btn => {
    btn.onclick = () => {
      const i = btn.getAttribute('data-edit');
      const ed = $('agent-d-' + i);
      const open = !ed.classList.contains('open');
      document.querySelectorAll('.editor').forEach(e => e.classList.remove('open'));
      document.querySelectorAll('[data-edit]').forEach(b => { b.textContent = 'Edit limits'; });
      if (open) {
        ed.classList.add('open');
        btn.textContent = 'Hide';
      }
    };
  });
  document.querySelectorAll('[data-edit-close]').forEach(btn => {
    btn.onclick = () => {
      const i = btn.getAttribute('data-edit-close');
      $('agent-d-' + i).classList.remove('open');
      const t = document.querySelector('[data-edit="'+i+'"]');
      if (t) t.textContent = 'Edit limits';
    };
  });
  document.querySelectorAll('[data-loop]').forEach(btn => {
    btn.onclick = () => simulateLoopBlock(btn.dataset.loop);
  });
  document.querySelectorAll('[data-save]').forEach(btn => {
    btn.onclick = () => saveAgentProtection(Number(btn.dataset.save), btn.dataset.name);
  });
}

function renderProviders(ctrl) {
  const rows = ctrl.providers || [];
  if (!rows.length) {
    $('provTable').innerHTML = `<tr><td colspan="6" class="muted">No provider data yet</td></tr>`;
    return;
  }
  $('provTable').innerHTML = rows.map((p, i) =>
    `<tr class="click" data-prov="${i}">
      <td><b>${p.provider}</b>${p.enabled === false ? ' <span class="muted">(off)</span>' : ''}</td>
      <td class="${cls(p.status)}">${p.status}</td>
      <td>${pct(p.success_rate)}</td>
      <td>${p.latency_ms_avg != null ? Math.round(p.latency_ms_avg) + ' ms' : '—'}</td>
      <td>${money4(p.usd)}</td>
      <td><span class="pill">${p.circuit || 'closed'}</span></td>
    </tr>`
  ).join('');
  document.querySelectorAll('[data-prov]').forEach(tr => {
    tr.onclick = () => {
      const p = rows[Number(tr.dataset.prov)];
      $('provDetail').innerHTML = `<div class="card">
        <b style="font-size:1.1rem">${p.provider}</b>
        <div class="kv" style="margin-top:.75rem">
          <div><b>Health score</b>${p.score ?? '—'}</div>
          <div><b>Status</b><span class="${cls(p.status)}">${p.status}</span></div>
          <div><b>Requests today</b>${p.calls ?? 0}</div>
          <div><b>Errors</b>${p.errors ?? 0}</div>
          <div><b>Success</b>${pct(p.success_rate)}</div>
          <div><b>Avg latency</b>${p.latency_ms_avg != null ? Math.round(p.latency_ms_avg) + ' ms' : '—'}</div>
          <div><b>USD today</b>${money4(p.usd)}</div>
          <div><b>Circuit</b>${p.circuit}</div>
        </div>
      </div>`;
    };
  });
}

function renderProve(ctrl, cert) {
  const res = ctrl.resilience || {};
  const last = (ctrl.chaos || {}).last_report;
  const score = res.score;
  $('proveScore').innerHTML = `
    <div class="stats">
      <div class="stat"><b>${score != null ? Math.round(score) : '—'}</b><span>Resilience</span></div>
      <div class="stat"><b>${res.policy_compliant === true ? 'OK' : (res.policy_compliant === false ? '⚠' : '—')}</b><span>Policy</span></div>
      <div class="stat"><b>${(ctrl.chaos && ctrl.chaos.history || []).length}</b><span>DR history</span></div>
    </div>
    <p class="muted" style="margin:.75rem 0 0">${res.summary || ctrl.promise || ''}</p>`;
  if (!last) {
    $('proveLast').innerHTML = `
      <div style="margin-bottom:.5rem">Last test: <span class="warn">Never run</span></div>
      <div class="muted" style="font-size:.9rem;line-height:1.5">
        Needs ≥2 providers in free_llm + keys, then run the test below.
      </div>`;
  } else {
    const ok = last.survived;
    $('proveLast').innerHTML = `Last test: <span class="${ok ? 'ok' : 'bad'}">${ok ? '✓ PASSED' : '✗ FAILED'}</span>
      · ${last.chaos_provider} · ${last.successful || 0}/${last.requests_tested || 0} · recovery ${last.recovery_time_ms_best ?? '—'} ms
      <div style="margin-top:.35rem">${last.message || ''}</div>`;
  }
  if (cert) {
    const checks = (cert.checks || []).map(ch =>
      `<div class="row"><span>${ch.label}</span><span class="${cls(ch.status)}">${ch.status}</span></div>
       ${ch.detail ? `<div class="muted" style="font-size:.8rem;margin:-.2rem 0 .45rem">${ch.detail}</div>` : ''}`
    ).join('');
    $('certCard').innerHTML = `<h2 class="sec" style="margin-top:0">AI Reliability Report</h2>
      <div class="muted">${cert.application || ''} · overall <b class="${cls(cert.overall)}">${cert.overall}</b></div>
      ${checks}
      <div style="margin-top:.75rem">Resilience <b>${cert.resilience_score ?? '—'}</b>/100</div>`;
  }
}

function renderAudit(events) {
  if (!events || !events.length) {
    $('auditTable').innerHTML = `<tr><td colspan="5" class="muted">No audit rows yet</td></tr>`;
    return;
  }
  $('auditTable').innerHTML = events.map(e => {
    const ev = e.event || '—';
    const detail = (e.error || e.reason || (e.extra && JSON.stringify(e.extra)) || '—');
    const short = String(detail).slice(0, 90);
    return `<tr>
      <td class="muted">${when(e.ts)}</td>
      <td>${e.consumer || '—'}</td>
      <td class="${ev === 'admit_deny' ? 'bad' : ''}">${ev}</td>
      <td>${e.provider || '—'}</td>
      <td class="muted" title="${String(detail).replace(/"/g, '&quot;')}">${short}</td>
    </tr>`;
  }).join('');
}

async function loadAll() {
  try {
    CTRL = await api('/v1/control');
    setStatus(CTRL);
    try { CERT = await api('/v1/certificate'); } catch { CERT = null; }
    renderOverview(CTRL, CERT);
    renderAgents(CTRL);
    renderProviders(CTRL);
    renderProve(CTRL, CERT);
  } catch (e) {
    $('headline').textContent = 'Failed to load control plane: ' + e.message;
  }
}

async function loadAudit(deniesOnly) {
  try {
    const q = deniesOnly ? '?event=admit_deny&limit=40' : '?limit=40';
    const d = await api('/v1/audit' + q);
    renderAudit(d.events || []);
  } catch (e) {
    $('auditTable').innerHTML = `<tr><td colspan="5" class="bad">${e.message}</td></tr>`;
  }
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
  const el = $('view-' + name);
  if (el) el.classList.add('active');
  const link = document.querySelector(`nav a[data-view="${name}"]`);
  if (link) link.classList.add('active');
  if (name === 'audit') loadAudit(false);
  if (name === 'prove' && CTRL) renderProve(CTRL, CERT);
}

function onHash() {
  const h = (location.hash || '#overview').replace('#', '') || 'overview';
  showView(h);
}

window.addEventListener('hashchange', onHash);
$('apiKey').addEventListener('change', loadAll);
$('btnAudit').onclick = () => loadAudit(false);
$('btnAuditDenies').onclick = () => loadAudit(true);
$('btnCert').onclick = async () => {
  try {
    CERT = await api('/v1/certificate');
    if (CTRL) renderProve(CTRL, CERT);
    $('proveOut').textContent = 'Certificate refreshed.';
  } catch (e) { $('proveOut').textContent = e.message; }
};
$('btnChaos').onclick = async () => {
  const btn = $('btnChaos');
  btn.disabled = true;
  $('proveOut').textContent = 'Running failover test…';
  try {
    const provider = $('chaosProvider').value.trim() || 'opencode_zen';
    const rep = await api('/v1/chaos/test', {
      method: 'POST',
      body: JSON.stringify({ provider, requests: 8, intent: 'free_llm' }),
    });
    const lines = [
      rep.survived ? '✓ TEST PASSED' : '✗ TEST FAILED',
      '',
      `Provider:     ${rep.chaos_provider}`,
      `Requests:     ${rep.requests_tested}`,
      `Successful:   ${rep.successful}`,
      `Failed:       ${rep.failed}`,
      `Failover %:   ${rep.automatic_failover_pct}`,
      `Recovery ms:  ${rep.recovery_time_ms_best}`,
      '',
      rep.message || '',
    ];
    $('proveOut').textContent = lines.join('\n');
    await loadAll();
    showView('prove');
  } catch (e) {
    $('proveOut').textContent = 'Test failed to start: ' + e.message;
  } finally {
    btn.disabled = false;
  }
};

try {
  const saved = localStorage.getItem('tollgate_api_key');
  if (saved) $('apiKey').value = saved;
} catch {}
$('apiKey').addEventListener('change', () => {
  try { localStorage.setItem('tollgate_api_key', key()); } catch {}
});

function showBlockModal(text) {
  $('blockModalBody').textContent = text;
  $('blockModal').classList.add('open');
}
$('blockModal').onclick = (e) => {
  if (e.target.id === 'blockModal') $('blockModal').classList.remove('open');
};

async function simulateLoopBlock(consumer) {
  const name = (consumer || '').trim() || 'support-agent';
  showBlockModal('Testing tool-loop protection for ' + name + '…');
  try {
    const r = await fetch('/v1/invoke', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Consumer-Key': name,
        'Authorization': 'Bearer ' + name,
      },
      body: JSON.stringify({
        provider: 'opencode_zen',
        op: 'chat',
        tool_calls_est: 999,
        tokens_est: 10,
        arguments: { message: 'ui loop test' },
        agent_id: name,
        request_class: 'interactive',
      }),
    });
    const d = await r.json();
    const msg = (d.blocked && d.blocked.message) || d.message || d.error || JSON.stringify(d, null, 2);
    const header = d.ok === false ? 'Aha — Protect works\n\n' : 'Unexpected allow\n\n';
    showBlockModal(header + msg);
    await loadAll();
  } catch (e) {
    showBlockModal('Test failed: ' + e.message);
  }
}

function numField(id) {
  const el = $(id);
  if (!el) return 0;
  const raw = el.value;
  if (raw === '' || raw == null) return 0;
  const n = Number(raw);
  return Number.isNaN(n) ? NaN : n;
}

async function saveAgentProtection(i, name) {
  const msg = $('ed-msg-' + i);
  try {
    const day = numField('ed-day-' + i);
    const hour = numField('ed-hour-' + i);
    const req = numField('ed-req-' + i);
    const tools = numField('ed-tools-' + i);
    const rpm = numField('ed-rpm-' + i);
    if ([day, hour, req, tools, rpm].some(n => Number.isNaN(n) || n < 0)) {
      throw new Error('Use numbers ≥ 0 (empty = unlimited)');
    }
    const env = {
      max_usd_day: day,
      max_usd_hour: hour,
      max_usd_request: req,
      max_tool_calls: Math.floor(tools),
      max_requests_minute: Math.floor(rpm),
    };
    if (msg) { msg.textContent = 'Saving…'; msg.className = 'muted'; }
    await api('/v1/config', {
      method: 'POST',
      body: JSON.stringify({ consumer_envelopes: { [name]: env } }),
    });
    if (msg) { msg.textContent = 'Saved.'; msg.className = 'ok'; }
    await loadAll();
    const ed = $('agent-d-' + i);
    if (ed) ed.classList.add('open');
    const t = document.querySelector('[data-edit="'+i+'"]');
    if (t) t.textContent = 'Hide';
  } catch (e) {
    if (msg) { msg.textContent = e.message; msg.className = 'bad'; }
  }
}

$('btnLoopTest').onclick = () => {
  const list = (CTRL && CTRL.consumers) || [];
  const c = list.find(x => x.protected) || list[0];
  simulateLoopBlock(c ? c.consumer : (OB.name || 'support-agent'));
};
$('btnUnfreeze').onclick = async () => {
  try {
    await api('/v1/freeze', { method: 'POST', body: JSON.stringify({ frozen: false }) });
    await loadAll();
  } catch (e) {
    alert('Unfreeze failed: ' + e.message);
  }
};

const OB = {
  step: 0,
  name: 'support-agent',
  maxUsdDay: 20,
  maxUsdReq: 2,
  maxToolCalls: 20,
  maxRpm: 50,
};

function obDone() {
  try { return localStorage.getItem('tollgate_onboarded') === '1'; } catch { return false; }
}
function setObDone() {
  try { localStorage.setItem('tollgate_onboarded', '1'); } catch {}
}
function needsOnboarding(ctrl) {
  if (obDone()) return false;
  const list = (ctrl && ctrl.consumers) || [];
  return !list.some(c => c.protected);
}
function showOnboard(show) {
  $('onboard').classList.toggle('open', !!show);
}
function renderObSteps() {
  const dots = $('obSteps').querySelectorAll('i');
  dots.forEach((d, i) => d.classList.toggle('on', i <= OB.step));
  $('obBack').style.display = OB.step > 0 ? '' : 'none';
  const next = $('obNext');
  next.textContent = OB.step === 0 ? 'Get started' : (OB.step === 3 ? 'Finish' : 'Continue');
  const body = $('obBody');
  $('obErr').style.display = 'none';

  if (OB.step === 0) {
    body.innerHTML = `
      <h1>Welcome to Tollgate</h1>
      <p class="sub">Protect your first AI agent — not configure 50 gateways.</p>
      <div class="ob-check ok">✓ Safety layer between agents and providers</div>
      <div class="ob-check">1 · Name the agent</div>
      <div class="ob-check">2 · Set protection (budget + tool loops)</div>
      <div class="ob-check">3 · Prove it works</div>`;
  } else if (OB.step === 1) {
    body.innerHTML = `
      <h1>Who are we protecting?</h1>
      <p class="sub">Application / agent lane name (consumer id).</p>
      <div class="field">
        <label>Application name</label>
        <input id="obName" value="${OB.name}" placeholder="support-agent"/>
      </div>`;
  } else if (OB.step === 2) {
    body.innerHTML = `
      <h1>Set protection</h1>
      <p class="sub">Hard stops before the invoice. You can tighten later under Agents.</p>
      <div class="field-row">
        <div class="field"><label>Daily budget ($)</label>
          <input id="obDay" type="number" min="0" step="0.5" value="${OB.maxUsdDay}"/></div>
        <div class="field"><label>Max $ / task</label>
          <input id="obReq" type="number" min="0" step="0.1" value="${OB.maxUsdReq}"/></div>
      </div>
      <div class="field-row">
        <div class="field"><label>Max tool calls</label>
          <input id="obTools" type="number" min="1" step="1" value="${OB.maxToolCalls}"/></div>
        <div class="field"><label>Max requests / min</label>
          <input id="obRpm" type="number" min="1" step="1" value="${OB.maxRpm}"/></div>
      </div>`;
  } else {
    body.innerHTML = `
      <h1>You're protected</h1>
      <p class="sub">Lane <b>${OB.name}</b> will get hard limits.</p>
      <div class="ob-check ok">✓ Budget configured</div>
      <div class="ob-check ok">✓ Tool-loop limit enabled</div>
      <div class="ob-check ok">✓ Rate limit enabled</div>`;
  }
}

function readObFields() {
  if (OB.step === 1) {
    const n = ($('obName') && $('obName').value || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-');
    if (!n) throw new Error('Enter an application name');
    OB.name = n.slice(0, 64);
  }
  if (OB.step === 2) {
    OB.maxUsdDay = Math.max(0, Number($('obDay').value) || 0);
    OB.maxUsdReq = Math.max(0, Number($('obReq').value) || 0);
    OB.maxToolCalls = Math.max(0, parseInt($('obTools').value, 10) || 0);
    OB.maxRpm = Math.max(0, parseInt($('obRpm').value, 10) || 0);
    if (!OB.maxUsdDay && !OB.maxToolCalls) {
      throw new Error('Set at least a daily budget or max tool calls');
    }
  }
}

async function applyProtection() {
  const env = {};
  if (OB.maxUsdDay > 0) env.max_usd_day = OB.maxUsdDay;
  if (OB.maxUsdReq > 0) env.max_usd_request = OB.maxUsdReq;
  if (OB.maxToolCalls > 0) env.max_tool_calls = OB.maxToolCalls;
  if (OB.maxRpm > 0) env.max_requests_minute = OB.maxRpm;
  env.allowed_intents = ['free_llm', 'llm'];
  env.allowed_ops = ['chat', 'status', 'search'];
  await api('/v1/config', {
    method: 'POST',
    body: JSON.stringify({ consumer_envelopes: { [OB.name]: env } }),
  });
}

$('obSkip').onclick = () => { setObDone(); showOnboard(false); };
$('obBack').onclick = () => { if (OB.step > 0) { OB.step -= 1; renderObSteps(); } };
$('obNext').onclick = async () => {
  try { readObFields(); }
  catch (e) { $('obErr').style.display = ''; $('obErr').textContent = e.message; return; }
  if (OB.step < 3) { OB.step += 1; renderObSteps(); return; }
  $('obNext').disabled = true;
  try {
    await applyProtection();
    setObDone();
    showOnboard(false);
    await loadAll();
    location.hash = '#agents';
    onHash();
    setTimeout(() => simulateLoopBlock(OB.name), 400);
  } catch (e) {
    $('obErr').style.display = '';
    $('obErr').textContent = 'Could not save protection: ' + e.message;
  } finally {
    $('obNext').disabled = false;
  }
};
$('btnSetup').onclick = () => { OB.step = 0; renderObSteps(); showOnboard(true); };

const _loadAllOrig = loadAll;
loadAll = async function () {
  await _loadAllOrig();
  if (CTRL && needsOnboarding(CTRL)) {
    OB.step = 0;
    renderObSteps();
    showOnboard(true);
  }
};

loadAll();
onHash();
setInterval(loadAll, 15000);
</script>
</body>
</html>
"""
