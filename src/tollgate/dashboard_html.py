"""Control Room WebUI — radical simple ops pane (not a config cemetery).

Screens: Overview · Agents · Providers · Prove · Audit
Question: Is my AI safe, does it work, what must I do?
"""

from __future__ import annotations

# Single-page app (no build). Fetches /v1/control, /v1/audit, /v1/certificate, chaos.

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tollgate — Control Room</title>
<style>
  :root {
    --bg:#0c0e12; --panel:#141820; --line:#252b36; --fg:#e8eaed;
    --muted:#8b93a7; --ok:#3dd68c; --warn:#f5a524; --bad:#f31260;
    --acc:#6c8cff; --chip:#1c2230;
  }
  * { box-sizing:border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
    background:var(--bg); color:var(--fg); min-height:100vh; }
  a { color:var(--acc); text-decoration:none; }
  button { font:inherit; cursor:pointer; border:0; border-radius:8px;
    background:var(--acc); color:#fff; padding:.5rem 1rem; font-weight:600; }
  button.ghost { background:transparent; border:1px solid var(--line); color:var(--fg); }
  button:disabled { opacity:.5; cursor:wait; }
  header {
    display:flex; align-items:center; justify-content:space-between; gap:1rem;
    padding:.9rem 1.25rem; border-bottom:1px solid var(--line);
    position:sticky; top:0; background:rgba(12,14,18,.92); backdrop-filter:blur(8px); z-index:10;
  }
  .brand { font-weight:700; letter-spacing:.04em; font-size:1rem; }
  .brand span { color:var(--muted); font-weight:500; margin-left:.5rem; font-size:.85rem; }
  .badge {
    display:inline-flex; align-items:center; gap:.4rem;
    padding:.28rem .7rem; border-radius:999px; font-size:.75rem; font-weight:700;
    letter-spacing:.04em; background:var(--chip); border:1px solid var(--line);
  }
  .badge.ok { color:var(--ok); border-color:#245c42; }
  .badge.warn { color:var(--warn); border-color:#6a4a12; }
  .badge.bad, .badge.frozen { color:var(--bad); border-color:#6a1a35; }
  .dot { width:8px; height:8px; border-radius:50%; background:currentColor; }
  nav { display:flex; gap:.15rem; flex-wrap:wrap; padding:.5rem 1.25rem; border-bottom:1px solid var(--line); }
  nav a {
    color:var(--muted); padding:.45rem .8rem; border-radius:8px; font-size:.9rem; font-weight:600;
  }
  nav a:hover { color:var(--fg); background:var(--chip); }
  nav a.active { color:var(--fg); background:var(--panel); border:1px solid var(--line); }
  main { max-width:980px; margin:0 auto; padding:1.25rem 1.25rem 3rem; }
  .view { display:none; }
  .view.active { display:block; }
  h2 { font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:1.4rem 0 .6rem; }
  h1.page { font-size:1.35rem; margin:0 0 .35rem; }
  .sub { color:var(--muted); margin:0 0 1.2rem; font-size:.95rem; }
  .card {
    background:var(--panel); border:1px solid var(--line); border-radius:14px;
    padding:1.1rem 1.2rem; margin-bottom:.85rem;
  }
  .hero {
    display:grid; grid-template-columns:160px 1fr; gap:1.25rem; align-items:center;
  }
  @media (max-width:700px){ .hero { grid-template-columns:1fr; } nav{overflow-x:auto;} }
  .ring-box { position:relative; width:130px; height:130px; margin:0 auto; }
  .ring {
    --p:0; width:130px; height:130px; border-radius:50%;
    background: conic-gradient(var(--acc) calc(var(--p) * 1%), var(--line) 0);
    display:grid; place-items:center;
  }
  .ring::before { content:""; width:96px; height:96px; border-radius:50%; background:var(--panel); }
  .ring-box .val { position:absolute; inset:0; display:grid; place-items:center; font-size:1.7rem; font-weight:800; }
  .ring-label { text-align:center; margin-top:.4rem; font-size:.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
  .grade { font-weight:700; font-size:.95rem; margin-top:.2rem; text-align:center; }
  .stats { display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; }
  @media (max-width:560px){ .stats { grid-template-columns:1fr; } }
  .stat b { display:block; font-size:1.2rem; }
  .stat span { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; }
  .row {
    display:flex; justify-content:space-between; align-items:center; gap:1rem;
    padding:.7rem 0; border-bottom:1px solid var(--line); font-size:.95rem;
  }
  .row:last-child { border-bottom:0; }
  .muted { color:var(--muted); }
  .ok { color:var(--ok); } .warn { color:var(--warn); } .bad { color:var(--bad); }
  .pill { display:inline-block; padding:.1rem .45rem; border-radius:999px; font-size:.72rem; background:var(--chip); }
  table { width:100%; border-collapse:collapse; font-size:.9rem; }
  th, td { text-align:left; padding:.55rem .35rem; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; }
  tr:last-child td { border-bottom:0; }
  tr.click { cursor:pointer; }
  tr.click:hover td { background:rgba(108,140,255,.06); }
  .detail { display:none; margin-top:.5rem; padding:.85rem; background:#0f1218; border-radius:10px; border:1px solid var(--line); }
  .detail.open { display:block; }
  .kv { display:grid; grid-template-columns:1fr 1fr; gap:.35rem .75rem; font-size:.9rem; }
  .kv b { color:var(--muted); font-weight:500; }
  .actions { display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.85rem; }
  .reco { border-left:3px solid var(--warn); padding-left:.85rem; margin:.55rem 0; }
  .reco.ok { border-color:var(--ok); }
  .reco.bad { border-color:var(--bad); }
  footer { margin-top:2rem; color:var(--muted); font-size:.8rem; }
  code { background:#0f1218; padding:.1rem .35rem; border-radius:4px; font-size:.82rem; }
  .empty { color:var(--muted); padding:.5rem 0; }
  .bar { height:6px; background:var(--line); border-radius:3px; overflow:hidden; margin-top:.35rem; }
  .bar i { display:block; height:100%; background:var(--acc); }
  .bar.warn i { background:var(--warn); }
  .bar.bad i { background:var(--bad); }
  .auth-bar { font-size:.8rem; color:var(--muted); }
  .auth-bar input { background:#0f1218; border:1px solid var(--line); color:var(--fg);
    border-radius:6px; padding:.25rem .5rem; width:11rem; }
  /* Onboarding */
  #onboard {
    display:none; position:fixed; inset:0; z-index:50;
    background:rgba(8,10,14,.92); backdrop-filter:blur(10px);
    align-items:center; justify-content:center; padding:1.25rem;
  }
  #onboard.open { display:flex; }
  .ob-card {
    width:min(440px,100%); background:var(--panel); border:1px solid var(--line);
    border-radius:16px; padding:1.4rem 1.5rem 1.35rem;
  }
  .ob-steps { display:flex; gap:.4rem; margin:0 0 1.1rem; }
  .ob-steps i {
    flex:1; height:4px; border-radius:2px; background:var(--line);
  }
  .ob-steps i.on { background:var(--acc); }
  .ob-card h1 { font-size:1.25rem; margin:0 0 .4rem; }
  .ob-card .sub { margin-bottom:1rem; }
  .field { margin:0 0 .85rem; }
  .field label { display:block; font-size:.78rem; color:var(--muted); text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:.3rem; }
  .field input, .field select {
    width:100%; background:#0f1218; border:1px solid var(--line); color:var(--fg);
    border-radius:8px; padding:.55rem .7rem; font:inherit;
  }
  .field-row { display:grid; grid-template-columns:1fr 1fr; gap:.65rem; }
  .ob-actions { display:flex; gap:.5rem; justify-content:space-between; margin-top:1.1rem; flex-wrap:wrap; }
  .ob-check { margin:.4rem 0; font-size:.95rem; }
  .ob-check.ok { color:var(--ok); }
  #blockModal {
    display:none; position:fixed; inset:0; z-index:60; background:rgba(8,10,14,.88);
    align-items:center; justify-content:center; padding:1rem;
  }
  #blockModal.open { display:flex; }
  #blockModal .card { max-width:420px; width:100%; white-space:pre-wrap; font-family:ui-monospace,monospace; font-size:.88rem; }
</style>
</head>
<body>
<!-- First-run: protect your first agent -->
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
  <div class="brand">TOLLGATE <span id="dayLabel"></span></div>
  <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;">
    <button type="button" class="ghost" id="btnSetup" style="padding:.28rem .65rem;font-size:.75rem">Setup</button>
    <div class="auth-bar" title="Open mode: any label. Auth mode: id:secret">
      key <input id="apiKey" placeholder="desk" value="desk"/>
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
  <!-- OVERVIEW -->
  <section class="view active" id="view-overview">
    <h1 class="page">Control Room</h1>
    <p class="sub">Is your AI safe, does it work, and what must you do?</p>
    <div class="card hero">
      <div>
        <div class="ring-box">
          <div class="ring" id="ring" style="--p:0"></div>
          <div class="val" id="ringVal">—</div>
        </div>
        <div class="ring-label">AI Reliability</div>
        <div class="grade" id="grade">—</div>
      </div>
      <div>
        <div class="stats" id="stats"></div>
        <p class="muted" style="margin:.9rem 0 0;font-size:.9rem" id="headline"></p>
      </div>
    </div>
    <h2>Needs attention</h2>
    <div class="card" id="attention"><div class="empty">Loading…</div></div>
    <h2>Recommendations</h2>
    <div class="card" id="reco"><div class="empty">Loading…</div></div>
    <h2>Where money goes</h2>
    <div class="card" id="costSplit"><div class="empty">Loading…</div></div>
    <h2>Providers at a glance</h2>
    <div class="card" id="provGlance"><div class="empty">Loading…</div></div>
    <div class="actions">
      <button type="button" class="ghost" id="btnLoopTest">Test tool-loop block</button>
      <button type="button" class="ghost" id="btnUnfreeze" style="display:none">Unfreeze admission</button>
    </div>
  </section>

  <div id="blockModal"><div class="card" id="blockModalBody"></div></div>

  <!-- AGENTS -->
  <section class="view" id="view-agents">
    <h1 class="page">Agents</h1>
    <p class="sub">Who is protected, who burns $, who is about to break limits.</p>
    <div id="agentsList"><div class="card empty">Loading…</div></div>
  </section>

  <!-- PROVIDERS -->
  <section class="view" id="view-providers">
    <h1 class="page">Providers</h1>
    <p class="sub">Which provider works best right now — not a config cemetery.</p>
    <div class="card">
      <table>
        <thead><tr><th>Provider</th><th>Health</th><th>Success</th><th>Latency</th><th>Cost day</th><th>Circuit</th></tr></thead>
        <tbody id="provTable"></tbody>
      </table>
    </div>
    <div id="provDetail"></div>
  </section>

  <!-- PROVE -->
  <section class="view" id="view-prove">
    <h1 class="page">Prove</h1>
    <p class="sub">Is your AI infrastructure actually resilient — or only configured?</p>
    <div class="card" id="proveScore"></div>
    <div class="card">
      <h2 style="margin-top:0">Provider failover test</h2>
      <p class="muted" id="proveLast">Last test: —</p>
      <div class="actions">
        <label class="muted">Provider
          <input id="chaosProvider" value="opencode_zen" style="margin-left:.35rem;background:#0f1218;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:.3rem .5rem"/>
        </label>
        <button id="btnChaos">Run test</button>
        <button class="ghost" id="btnCert">Refresh certificate</button>
      </div>
      <pre id="proveOut" class="muted" style="margin-top:1rem;white-space:pre-wrap;font-size:.85rem"></pre>
    </div>
    <div class="card" id="certCard"></div>
  </section>

  <!-- AUDIT -->
  <section class="view" id="view-audit">
    <h1 class="page">Audit</h1>
    <p class="sub">What did Tollgate allow, block, or fail over — ops only, no secrets.</p>
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
    <a href="https://github.com/landjunge/tollgate/blob/main/docs/HILFE.md" target="_blank" rel="noopener">Hilfe</a> ·
    <a href="https://github.com/landjunge/tollgate/blob/main/docs/USER_GUIDE.md" target="_blank" rel="noopener">User Guide</a> ·
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
  s = (s||'').toLowerCase();
  if (['ok','healthy','pass','protected','closed'].includes(s)) return 'ok';
  if (['warn','likely_over','degraded','half_open','approaching','ready','not_run'].includes(s)) return 'warn';
  return 'bad';
}
function money(n) { return '$' + (Number(n||0)).toFixed(2); }
function money4(n) { return '$' + (Number(n||0)).toFixed(4); }
function pct(n) { return n==null ? '—' : (Number(n)*100).toFixed(1)+'%'; }
function when(ts) {
  if (ts==null || ts==='') return '—';
  try {
    const t = Number(ts) > 1e12 ? Number(ts) : Number(ts)*1000;
    return new Date(t).toLocaleString();
  } catch { return String(ts); }
}
function grade(score) {
  if (score==null) return '—';
  if (score >= 85) return {t:'GOOD', c:'ok'};
  if (score >= 65) return {t:'FAIR', c:'warn'};
  return {t:'WEAK', c:'bad'};
}

let CTRL = null;
let CERT = null;

async function api(path, opts={}) {
  const r = await fetch(path, { ...opts, headers: { ...headers(), ...(opts.headers||{}) } });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(r.status + ' ' + t.slice(0,180));
  }
  const ct = r.headers.get('content-type')||'';
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
  $('ring').style.setProperty('--p', score==null ? 0 : Math.max(0, Math.min(100, score)));
  $('ringVal').textContent = score==null ? '—' : Math.round(score);
  $('grade').innerHTML = `<span class="${g.c}">${g.t}</span>`;
  $('dayLabel').textContent = ctrl.day ? '· ' + ctrl.day : '';
  $('headline').textContent = ctrl.headline || '';
  $('stats').innerHTML = [
    ['Spent today', money(s.usd)],
    ['Requests', String(s.calls ?? 0)],
    ['Success', s.errors!=null && s.calls ? pct(1 - (s.errors/(s.calls||1))) : '—'],
    ['Agent stops', String(s.agent_protection_blocks ?? 0)],
    ['Circuits open', String(s.circuits_open ?? 0)],
    ['Agents protected', String(s.consumers_protected ?? 0)],
  ].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');

  const att = ctrl.attention || [];
  if (!att.length) {
    $('attention').innerHTML = `<div class="ok">✓ Nothing urgent — agents under control</div>`;
  } else {
    $('attention').innerHTML = `<div class="muted" style="margin-bottom:.5rem">${att.length} thing(s) need attention</div>` +
      att.map(a => {
        const c = a.level==='ok'?'ok':(a.level==='error'?'bad':'warn');
        const mark = a.level==='ok'?'✓':(a.level==='error'?'⛔':'⚠');
        return `<div class="row"><span class="${c}">${mark} ${a.message||''}</span><span class="muted">${a.code||''}</span></div>`;
      }).join('');
  }

  // Recommendations (actionable)
  const recos = [];
  if (ctrl.freeze && ctrl.freeze.frozen) {
    recos.push({level:'bad', text:'Admission is frozen — no billable traffic.', action:'tollgate unfreeze'});
  }
  const consumers = ctrl.consumers || [];
  consumers.filter(c => !c.protected && c.consumer).forEach(c => {
    recos.push({level:'warn', text:`Agent «${c.consumer}» has weak or no spend/loop limits.`, action:`tollgate consumer-budget ${c.consumer} --max-usd-day 2 --max-tool-calls 20`});
  });
  consumers.filter(c => c.status==='warn' || c.status==='likely_over' || c.status==='over_budget').forEach(c => {
    recos.push({level: c.status==='over_budget'?'bad':'warn', text:`«${c.consumer}» spend ${money4(c.usd)}` + (c.max_usd_day?` / ${money(c.max_usd_day)}`:'') + ` (${c.status})`, action:'#agents'});
  });
  const last = (ctrl.chaos||{}).last_report;
  if (!last) {
    recos.push({level:'warn', text:'Failover has never been tested (Prove).', action:'#prove'});
  } else if (last.survived === false) {
    recos.push({level:'bad', text:`Last DR test failed for ${last.chaos_provider}.`, action:'#prove'});
  }
  if (!recos.length) {
    recos.push({level:'ok', text:'Settings look reasonable for a protected desk.', action:''});
  }
  $('reco').innerHTML = recos.map(r =>
    `<div class="reco ${r.level}">${r.text}${r.action && r.action.startsWith('#') ? ` <a href="${r.action}">Open →</a>` : (r.action ? `<div class="muted" style="margin-top:.25rem"><code>${r.action}</code></div>` : '')}</div>`
  ).join('');

  // Cost split (where money goes)
  const byAgent = (consumers||[]).filter(c => Number(c.usd||0) > 0).slice(0,8);
  const byProv = (ctrl.providers||[]).filter(p => Number(p.usd||0) > 0).slice(0,8);
  const totalUsd = Number(s.usd||0);
  if (!byAgent.length && !byProv.length) {
    $('costSplit').innerHTML = `<div class="empty">No spend yet today — good. Traffic will show by agent & provider.</div>`;
  } else {
    let html = `<div class="muted" style="margin-bottom:.5rem">Today ${money(totalUsd)}</div>`;
    if (byAgent.length) {
      html += `<div class="muted" style="font-size:.72rem;text-transform:uppercase;margin:.4rem 0">By agent</div>`;
      html += byAgent.map(c => {
        const share = totalUsd > 0 ? Math.round(100*Number(c.usd)/totalUsd) : 0;
        return `<div class="row"><span>${c.consumer}</span><span>${money4(c.usd)} <span class="muted">(${share}%)</span></span></div>`;
      }).join('');
    }
    if (byProv.length) {
      html += `<div class="muted" style="font-size:.72rem;text-transform:uppercase;margin:.6rem 0 .4rem">By provider</div>`;
      html += byProv.map(p => {
        const share = totalUsd > 0 ? Math.round(100*Number(p.usd)/totalUsd) : 0;
        return `<div class="row"><span>${p.provider}</span><span>${money4(p.usd)} <span class="muted">(${share}%)</span></span></div>`;
      }).join('');
    }
    $('costSplit').innerHTML = html;
  }

  const provs = (ctrl.providers||[]).filter(p => p.enabled !== false).slice(0,6);
  if (!provs.length) {
    $('provGlance').innerHTML = `<div class="empty">No provider traffic yet</div>`;
  } else {
    $('provGlance').innerHTML = provs.map(p =>
      `<div class="row">
        <span><b>${p.provider}</b> <span class="pill ${cls(p.status)}">${p.status}</span></span>
        <span class="muted">${pct(p.success_rate)} · ${p.latency_ms_avg!=null?Math.round(p.latency_ms_avg)+'ms':'—'} · ${money4(p.usd)}</span>
      </div>`
    ).join('');
  }

  // Unfreeze button
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
  $('agentsList').innerHTML = list.map((c,i) => {
    const max = c.max_usd_day;
    const used = Number(c.usd||0);
    const ratio = max ? Math.min(100, (used/max)*100) : 0;
    const barC = c.status==='over_budget'||c.status==='blocked'?'bad':(c.status==='warn'||c.status==='likely_over'?'warn':'');
    const st = c.protected
      ? (c.status==='ok' ? 'Protected' : c.status)
      : 'Unprotected';
    const stc = c.protected && c.status==='ok' ? 'ok' : cls(c.status);
    return `<div class="card">
      <div class="row" style="border:0;padding:0">
        <div>
          <b style="font-size:1.05rem">${c.consumer}</b>
          <div class="${stc}" style="margin-top:.25rem">● ${st}</div>
        </div>
        <div style="display:flex;gap:.4rem">
          <button class="ghost" data-loop="${c.consumer}">Test loop</button>
          <button class="ghost" data-agent="${i}">View</button>
        </div>
      </div>
      <div style="margin-top:.75rem">
        ${max ? `${money4(used)} / ${money(max)} budget` : `${money4(used)} spent (no day $ cap)`}
        ${max ? `<div class="bar ${barC}"><i style="width:${ratio}%"></i></div>` : ''}
        <div class="muted" style="margin-top:.4rem;font-size:.85rem">${c.calls||0} requests · ${c.tokens||0} tokens · projected EOD ${money4(c.projected_usd_eod)}</div>
      </div>
      <div class="detail" id="agent-d-${i}">
        <h2 style="margin-top:0">Edit protection</h2>
        <div class="field-row">
          <div class="field"><label>Daily budget $</label>
            <input id="ed-day-${i}" type="number" step="0.5" value="${c.max_usd_day??''}"/></div>
          <div class="field"><label>Max $ / task</label>
            <input id="ed-req-${i}" type="number" step="0.1" value="${c.max_usd_request??''}"/></div>
        </div>
        <div class="field-row">
          <div class="field"><label>Max tool calls</label>
            <input id="ed-tools-${i}" type="number" step="1" value="${c.max_tool_calls??''}"/></div>
          <div class="field"><label>Max req/min</label>
            <input id="ed-rpm-${i}" type="number" step="1" value="${c.max_requests_minute??''}"/></div>
        </div>
        <div class="actions">
          <button type="button" data-save="${i}" data-name="${c.consumer}">Save</button>
          <button type="button" class="ghost" data-loop="${c.consumer}">Test tool-loop block</button>
        </div>
        <h2>Scopes</h2>
        <div class="muted" style="font-size:.9rem">
          Allowed providers: ${(c.allowed_providers||[]).length ? c.allowed_providers.join(', ') : 'any'}<br/>
          Blocked: ${(c.blocked_providers||[]).length ? c.blocked_providers.join(', ') : '—'}<br/>
          Intents: ${(c.allowed_intents||[]).length ? c.allowed_intents.join(', ') : 'any'} ·
          Ops: ${(c.allowed_ops||[]).length ? c.allowed_ops.join(', ') : 'any'}
        </div>
        <p id="ed-msg-${i}" class="muted" style="margin:.6rem 0 0;font-size:.85rem"></p>
      </div>
    </div>`;
  }).join('');
  document.querySelectorAll('[data-agent]').forEach(btn => {
    btn.onclick = () => {
      const el = $('agent-d-' + btn.dataset.agent);
      el.classList.toggle('open');
      btn.textContent = el.classList.contains('open') ? 'Hide' : 'View';
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
  $('provTable').innerHTML = rows.map((p,i) =>
    `<tr class="click" data-prov="${i}">
      <td><b>${p.provider}</b>${p.enabled===false?' <span class="muted">(off)</span>':''}</td>
      <td class="${cls(p.status)}">${p.status}</td>
      <td>${pct(p.success_rate)}</td>
      <td>${p.latency_ms_avg!=null?Math.round(p.latency_ms_avg)+' ms':'—'}</td>
      <td>${money4(p.usd)}</td>
      <td><span class="pill">${p.circuit||'closed'}</span></td>
    </tr>`
  ).join('');
  document.querySelectorAll('[data-prov]').forEach(tr => {
    tr.onclick = () => {
      const p = rows[Number(tr.dataset.prov)];
      $('provDetail').innerHTML = `<div class="card">
        <b style="font-size:1.1rem">${p.provider}</b>
        <div class="kv" style="margin-top:.75rem">
          <div><b>Health score</b><br/>${p.score??'—'}</div>
          <div><b>Status</b><br/><span class="${cls(p.status)}">${p.status}</span></div>
          <div><b>Requests today</b><br/>${p.calls??0}</div>
          <div><b>Errors</b><br/>${p.errors??0}</div>
          <div><b>Success</b><br/>${pct(p.success_rate)}</div>
          <div><b>Avg latency</b><br/>${p.latency_ms_avg!=null?Math.round(p.latency_ms_avg)+' ms':'—'}</div>
          <div><b>USD today</b><br/>${money4(p.usd)}</div>
          <div><b>Circuit</b><br/>${p.circuit}</div>
        </div>
        <p class="muted" style="margin:.85rem 0 0;font-size:.85rem">
          Reset circuit: <code>tollgate circuits reset ${p.provider}</code>
        </p>
      </div>`;
    };
  });
}

function renderProve(ctrl, cert) {
  const res = ctrl.resilience || {};
  const last = (ctrl.chaos||{}).last_report;
  const score = res.score;
  $('proveScore').innerHTML = `
    <div class="stats">
      <div class="stat"><b>${score!=null?Math.round(score):'—'}</b><span>Resilience</span></div>
      <div class="stat"><b>${res.policy_compliant===true?'OK':(res.policy_compliant===false?'⚠':'—')}</b><span>Policy</span></div>
      <div class="stat"><b>${(ctrl.chaos&&ctrl.chaos.history||[]).length}</b><span>DR history</span></div>
    </div>
    <p class="muted" style="margin:.75rem 0 0">${res.summary || ctrl.promise || ''}</p>`;
  if (!last) {
    $('proveLast').innerHTML = `Last test: <span class="warn">Never — run a failover test</span>`;
  } else {
    const ok = last.survived;
    $('proveLast').innerHTML = `Last test: <span class="${ok?'ok':'bad'}">${ok?'✓ PASSED':'✗ FAILED'}</span>
      · ${last.chaos_provider} · ${last.successful||0}/${last.requests_tested||0} routes · recovery ${last.recovery_time_ms_best??'—'} ms
      <div style="margin-top:.35rem">${last.message||''}</div>`;
  }
  if (cert) {
    const checks = (cert.checks||[]).map(ch =>
      `<div class="row"><span>${ch.label}</span><span class="${cls(ch.status)}">${ch.status}</span></div>`
    ).join('');
    $('certCard').innerHTML = `<h2 style="margin-top:0">AI Reliability Report</h2>
      <div class="muted">${cert.application||''} · ${cert.period||''} · overall <b class="${cls(cert.overall)}">${cert.overall}</b></div>
      ${checks}
      <div style="margin-top:.75rem">Resilience <b>${cert.resilience_score??'—'}</b>/100</div>`;
  }
}

function renderAudit(events) {
  if (!events || !events.length) {
    $('auditTable').innerHTML = `<tr><td colspan="5" class="muted">No audit rows yet — denials and usage appear after traffic</td></tr>`;
    return;
  }
  $('auditTable').innerHTML = events.map(e => {
    const ev = e.event || '—';
    const detail = (e.error || e.reason || (e.extra && JSON.stringify(e.extra)) || '—');
    const short = String(detail).slice(0, 80);
    return `<tr>
      <td class="muted">${when(e.ts)}</td>
      <td>${e.consumer||'—'}</td>
      <td class="${ev==='admit_deny'?'bad':''}">${ev}</td>
      <td>${e.provider||'—'}</td>
      <td class="muted" title="${String(detail).replace(/"/g,'&quot;')}">${short}</td>
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
  const h = (location.hash || '#overview').replace('#','') || 'overview';
  showView(h);
}

document.querySelectorAll('nav a').forEach(a => {
  a.addEventListener('click', (e) => {
    /* hash navigation */
  });
});
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
      rep.survived ? '\nYour agent survived.' : '',
    ];
    $('proveOut').textContent = lines.join('\n');
    await loadAll();
    showView('prove');
  } catch (e) {
    $('proveOut').textContent = 'Test failed to start: ' + e.message +
      '\n\nOpen mode: use any key. Auth mode: need admin consumer.';
  } finally {
    btn.disabled = false;
  }
};

// Persist API key label
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
    const header = d.ok === false
      ? 'Aha — Protect works\n\n'
      : 'Unexpected allow (raise max_tool_calls / set protection)\n\n';
    showBlockModal(header + msg);
    await loadAll();
  } catch (e) {
    showBlockModal('Test failed: ' + e.message);
  }
}

async function saveAgentProtection(i, name) {
  const msg = $('ed-msg-' + i);
  try {
    const day = Number($('ed-day-' + i).value);
    const req = Number($('ed-req-' + i).value);
    const tools = parseInt($('ed-tools-' + i).value, 10);
    const rpm = parseInt($('ed-rpm-' + i).value, 10);
    const env = {};
    if (!Number.isNaN(day) && day >= 0) env.max_usd_day = day;
    if (!Number.isNaN(req) && req >= 0) env.max_usd_request = req;
    if (!Number.isNaN(tools) && tools >= 0) env.max_tool_calls = tools;
    if (!Number.isNaN(rpm) && rpm >= 0) env.max_requests_minute = rpm;
    await api('/v1/config', {
      method: 'POST',
      body: JSON.stringify({ consumer_envelopes: { [name]: env } }),
    });
    if (msg) { msg.textContent = 'Saved.'; msg.className = 'ok'; }
    await loadAll();
  } catch (e) {
    if (msg) { msg.textContent = e.message; msg.className = 'bad'; }
  }
}

$('btnLoopTest').onclick = () => {
  const list = (CTRL && CTRL.consumers) || [];
  const c = list.find(x => x.protected) || list[0];
  const name = c ? c.consumer : (OB.name || 'support-agent');
  simulateLoopBlock(name);
};
$('btnUnfreeze').onclick = async () => {
  try {
    await api('/v1/freeze', { method: 'POST', body: JSON.stringify({ frozen: false }) });
    await loadAll();
  } catch (e) {
    alert('Unfreeze failed: ' + e.message);
  }
};

// ── Onboarding: protect first agent in 4 steps ──────────────────────
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
  const anyProt = list.some(c => c.protected);
  // also check summary consumers_protected (default envelope may count)
  return !anyProt;
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
      <p class="sub">Let's protect your first AI agent — not configure 50 gateways.</p>
      <div class="ob-check ok">✓ Safety layer between agents and the internet</div>
      <div class="ob-check">1 · Name the agent</div>
      <div class="ob-check">2 · Set protection (budget + tool loops)</div>
      <div class="ob-check">3 · Prove it works</div>
      <p class="muted" style="margin-top:1rem;font-size:.85rem">
        API keys stay in <code>Key.txt</code> (optional for the loop-block test).
      </p>`;
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
      <p class="sub">Hard stops before the invoice. You can tighten later.</p>
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
      <p class="sub">Lane <b id="obFinalName">${OB.name}</b> will get hard limits.</p>
      <div class="ob-check ok">✓ Budget configured</div>
      <div class="ob-check ok">✓ Tool-loop limit enabled</div>
      <div class="ob-check ok">✓ Rate limit enabled</div>
      <p class="muted" style="margin-top:.85rem;font-size:.9rem">
        After Finish you can <b>Test tool-loop block</b> on Overview — the Protect Aha, no API keys needed.
        Then open <b>Prove</b> for failover.
      </p>`;
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
  // Keep free_llm + chat usable for desk demos
  env.allowed_intents = ['free_llm', 'llm'];
  env.allowed_ops = ['chat', 'status', 'search'];
  await api('/v1/config', {
    method: 'POST',
    body: JSON.stringify({ consumer_envelopes: { [OB.name]: env } }),
  });
}

$('obSkip').onclick = () => {
  setObDone();
  showOnboard(false);
};
$('obBack').onclick = () => {
  if (OB.step > 0) { OB.step -= 1; renderObSteps(); }
};
$('obNext').onclick = async () => {
  try {
    readObFields();
  } catch (e) {
    $('obErr').style.display = '';
    $('obErr').textContent = e.message;
    return;
  }
  if (OB.step < 3) {
    OB.step += 1;
    renderObSteps();
    return;
  }
  // Finish: write protection
  $('obNext').disabled = true;
  try {
    await applyProtection();
    setObDone();
    showOnboard(false);
    await loadAll();
    location.hash = '#agents';
    onHash();
    // Immediate Aha — tool loop block for the new lane
    setTimeout(() => simulateLoopBlock(OB.name), 400);
  } catch (e) {
    $('obErr').style.display = '';
    $('obErr').textContent = 'Could not save protection: ' + e.message;
  } finally {
    $('obNext').disabled = false;
  }
};
$('btnSetup').onclick = () => {
  OB.step = 0;
  renderObSteps();
  showOnboard(true);
};

const _loadAllOrig = loadAll;
loadAll = async function() {
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
