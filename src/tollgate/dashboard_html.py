"""Minimal control-plane HTML — Protect · Route · Prove."""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tollgate — Protect · Route · Prove</title>
<style>
  :root { --bg:#0f1115; --card:#1a1d24; --fg:#e8eaed; --muted:#9aa0a6; --ok:#3dd68c; --warn:#f5a524; --bad:#f31260; --acc:#6c8cff; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--fg); }
  header { padding:1.25rem 1.5rem; border-bottom:1px solid #2a2f3a; }
  header h1 { margin:0; font-size:1.25rem; letter-spacing:.02em; }
  header p { margin:.35rem 0 0; color:var(--muted); font-size:.9rem; max-width:52rem; }
  main { padding:1.25rem 1.5rem 3rem; max-width:1100px; margin:0 auto; }
  .headline { background:linear-gradient(135deg,#1e2430,#151922); border:1px solid #2a2f3a; border-radius:12px; padding:1.1rem 1.25rem; font-size:1.05rem; margin-bottom:1rem; font-weight:600; }
  .promise { color:var(--muted); font-size:.9rem; margin:-.4rem 0 1.25rem; }
  .top { display:grid; grid-template-columns: 160px 1fr; gap:1rem; margin-bottom:1.25rem; align-items:center; }
  @media (max-width:700px){ .top { grid-template-columns:1fr; } }
  .ring-wrap { background:var(--card); border:1px solid #2a2f3a; border-radius:12px; padding:1rem; text-align:center; }
  .ring {
    --p: 0;
    width:120px; height:120px; border-radius:50%; margin:0 auto .5rem;
    background: conic-gradient(var(--acc) calc(var(--p) * 1%), #2a2f3a 0);
    display:grid; place-items:center;
  }
  .ring::before {
    content:""; width:88px; height:88px; border-radius:50%; background:var(--card);
  }
  .ring-label { position:absolute; font-size:1.4rem; font-weight:700; }
  .ring-box { position:relative; display:inline-grid; place-items:center; }
  .ring-box .ring { grid-area:1/1; }
  .ring-box .val { grid-area:1/1; font-size:1.35rem; font-weight:700; z-index:1; }
  .ring-sub { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:.75rem; }
  .stat { background:var(--card); border-radius:10px; padding:.85rem 1rem; border:1px solid #2a2f3a; }
  .stat b { display:block; font-size:1.25rem; }
  .stat span { color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.04em; }
  h2 { font-size:.95rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin:1.5rem 0 .6rem; }
  .attn, .dr { background:var(--card); border:1px solid #2a2f3a; border-radius:10px; padding:.5rem 0; margin-bottom:1rem; }
  .attn div, .dr div { padding:.45rem 1rem; border-bottom:1px solid #2a2f3a; font-size:.9rem; }
  .attn div:last-child, .dr div:last-child { border-bottom:none; }
  .dims { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:.5rem; margin:.75rem 0; }
  .dim { background:#12151c; border-radius:8px; padding:.5rem .7rem; font-size:.85rem; }
  .dim b { float:right; }
  .bar { height:4px; background:#2a2f3a; border-radius:2px; margin-top:.35rem; overflow:hidden; }
  .bar i { display:block; height:100%; background:var(--acc); }
  table { width:100%; border-collapse:collapse; background:var(--card); border-radius:10px; overflow:hidden; border:1px solid #2a2f3a; }
  th, td { text-align:left; padding:.55rem .75rem; border-bottom:1px solid #2a2f3a; font-size:.9rem; }
  th { color:var(--muted); font-weight:600; font-size:.75rem; text-transform:uppercase; }
  tr:last-child td { border-bottom:none; }
  .pill { display:inline-block; padding:.12rem .45rem; border-radius:999px; font-size:.75rem; background:#2a2f3a; }
  .ok { color:var(--ok); } .warn { color:var(--warn); } .bad,.error { color:var(--bad); }
  footer { margin-top:2rem; color:var(--muted); font-size:.8rem; }
  a { color:var(--acc); }
  button { background:var(--acc); color:#fff; border:0; border-radius:8px; padding:.45rem .9rem; cursor:pointer; font-weight:600; }
  code { background:#12151c; padding:.1rem .35rem; border-radius:4px; font-size:.8rem; }
</style>
</head>
<body>
<header>
  <h1>Tollgate</h1>
  <p id="promise">Protect · Route · Prove — AI reliability &amp; control plane</p>
</header>
<main>
  <div class="headline" id="headline">Loading…</div>
  <div class="attn" id="freezeBanner" style="display:none;border-color:var(--bad);margin-bottom:1rem"></div>
  <p class="promise" id="tagline"></p>
  <div class="top">
    <div class="ring-wrap">
      <div class="ring-box">
        <div class="ring" id="ring" style="--p:0"></div>
        <div class="val" id="ringVal">—</div>
      </div>
      <div class="ring-sub">AI Resilience</div>
      <div id="avail" class="ring-sub" style="margin-top:.35rem"></div>
    </div>
    <div class="grid" id="stats"></div>
  </div>
  <div class="dims" id="dims"></div>
  <h2>Disaster recovery (Prove)</h2>
  <div class="dr" id="dr"><div>—</div></div>
  <h2>Needs attention</h2>
  <div class="attn" id="attention"><div>—</div></div>
  <h2>Recent denies (Protect)</h2>
  <table><thead><tr><th>When</th><th>Agent</th><th>Provider</th><th>Why</th></tr></thead>
  <tbody id="denies"></tbody></table>
  <h2>Chaos test history</h2>
  <table><thead><tr><th>When</th><th>Provider</th><th>Result</th><th>OK / Fail</th></tr></thead>
  <tbody id="history"></tbody></table>
  <h2>Agents / consumers</h2>
  <table><thead><tr><th>Agent</th><th>USD today</th><th>Projected EOD</th><th>Budget</th><th>Status</th></tr></thead>
  <tbody id="consumers"></tbody></table>
  <h2>Provider health</h2>
  <table><thead><tr><th>Provider</th><th>Status</th><th>Success</th><th>Latency</th><th>USD day</th><th>Score</th><th>Circuit</th></tr></thead>
  <tbody id="providers"></tbody></table>
  <footer id="foot"></footer>
  <p style="margin-top:1rem">
    <button onclick="load()">Refresh</button>
    · <a href="/docs">API</a>
    · <a href="/v1/control">JSON</a>
    · <a href="/v1/report?format=md">Report</a>
    · <a href="/v1/resilience">Resilience</a>
    · <a href="/v1/chaos">Chaos</a>
  </p>
  <p class="promise">CLI: <code>tollgate report</code> · <code>tollgate audit --event admit_deny</code> · <code>tollgate chaos test opencode_zen</code></p>
</main>
<script>
function cls(s){ if(!s) return ''; if(['healthy','ok','idle'].includes(s)) return 'ok'; if(['warn','likely_over','degraded','half_open'].includes(s)) return 'warn'; return 'bad'; }
function when(ts){ if(!ts) return '—'; try { return new Date(ts*1000).toLocaleString(); } catch(e){ return String(ts); } }
async function load(){
  const r = await fetch('/v1/control');
  const d = await r.json();
  document.getElementById('headline').textContent = d.headline || '—';
  document.getElementById('tagline').textContent = d.tagline || d.promise || '';
  if (d.promise) document.getElementById('promise').textContent = d.promise;
  const fb = document.getElementById('freezeBanner');
  if (d.freeze && d.freeze.frozen) {
    fb.style.display = 'block';
    fb.innerHTML = `<div class="error">⛔ ADMISSION FROZEN — ${d.freeze.reason||'kill switch'} · <code>tollgate unfreeze</code> or POST /v1/freeze</div>`;
  } else {
    fb.style.display = 'none';
    fb.innerHTML = '';
  }
  const s = d.summary || {};
  const res = d.resilience || {};
  const score = res.score!=null ? Number(res.score) : null;
  const ring = document.getElementById('ring');
  if (score!=null) {
    ring.style.setProperty('--p', Math.max(0, Math.min(100, score)));
    document.getElementById('ringVal').textContent = score.toFixed(0);
  } else {
    document.getElementById('ringVal').textContent = '—';
  }
  document.getElementById('avail').textContent =
    res.availability_estimate_pct!=null ? ('~'+res.availability_estimate_pct+'% est.') : '';
  document.getElementById('stats').innerHTML = [
    ['Spent today', '$'+(s.usd||0).toFixed(2)],
    ['Agent stops', s.agent_protection_blocks ?? 0],
    ['Provider errors', s.errors ?? 0],
    ['Agents protected', s.consumers_protected ?? 0],
    ['Calls', s.calls ?? 0],
    ['Policy', res.policy_compliant===true?'OK':(res.policy_compliant===false?'⚠':'—')]
  ].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  const dims = res.dimensions || {};
  document.getElementById('dims').innerHTML = Object.keys(dims).map(k => {
    const v = Number(dims[k])||0;
    return `<div class="dim">${k.replace(/_/g,' ')} <b>${v.toFixed(0)}</b><div class="bar"><i style="width:${Math.min(100,v)}%"></i></div></div>`;
  }).join('');
  // DR panel
  const last = res.last_chaos_report || (d.chaos&&d.chaos.last_report) || null;
  const active = (res.active_chaos||[]).concat((d.chaos&&d.chaos.active)||[]);
  const recovering = res.recovering || (d.chaos&&d.chaos.recovering) || [];
  let dr = [];
  if (last) {
    dr.push(`<div class="${last.survived?'ok':'bad'}">${last.survived?'✓':'⛔'} Last DR: <b>${last.chaos_provider||'?'}</b> — ${last.message|| (last.survived?'survived':'failed')} · ${last.successful||0}/${last.requests_tested||0} routes · recovery ${last.recovery_time_ms_best??'—'}ms</div>`);
  } else {
    dr.push(`<div class="warn">⚠ No chaos test yet — run <code>tollgate chaos test &lt;provider&gt;</code></div>`);
  }
  if (active.length) active.forEach(a => dr.push(`<div class="warn">⚠ Chaos ACTIVE on <b>${a.provider}</b></div>`));
  if (recovering.length) recovering.forEach(a => dr.push(`<div class="warn">↻ Gradual recovery: <b>${a.provider}</b> (${a.duration_s}s ramp)</div>`));
  if (res.policy) {
    const p = res.policy;
    dr.push(`<div>Policy: fallbacks≥${p.required_fallbacks} · max failover ${p.max_failover_time_s}s · recovery ramp ${p.gradual_recovery_s}s · target ${p.availability_target}%</div>`);
  }
  document.getElementById('dr').innerHTML = dr.join('');
  const att = d.attention || [];
  document.getElementById('attention').innerHTML = att.length
    ? att.map(a => `<div class="${a.level||''}">${a.level==='ok'?'✓':(a.level==='error'?'⛔':'⚠')} ${a.message||''}</div>`).join('')
    : '<div class="ok">✓ Nothing urgent — agents under control</div>';
  const denies = d.recent_denies || [];
  document.getElementById('denies').innerHTML = denies.length
    ? denies.map(x => `
      <tr>
        <td>${when(x.ts)}</td>
        <td>${x.consumer||'—'}</td>
        <td>${x.provider||'—'}</td>
        <td class="warn">${(x.protection ? ('['+x.protection+'] ') : '') + (x.error||x.reason||'deny')}</td>
      </tr>`).join('')
    : '<tr><td colspan="4" class="ok">No admit denies in recent audit — gate is quiet</td></tr>';
  const hist = (d.chaos && d.chaos.history) || [];
  document.getElementById('history').innerHTML = hist.length
    ? hist.slice().reverse().map(h => `
      <tr>
        <td>${when(h.finished_at)}</td>
        <td>${h.chaos_provider||'—'}</td>
        <td class="${h.survived?'ok':'bad'}">${h.survived?'survived':'failed'}</td>
        <td>${h.successful??'—'}/${(h.successful||0)+(h.failed||0) || '—'}</td>
      </tr>`).join('')
    : '<tr><td colspan="4">No tests yet</td></tr>';
  document.getElementById('consumers').innerHTML = (d.consumers||[]).map(c => `
    <tr>
      <td>${c.consumer}</td>
      <td>$${(c.usd||0).toFixed(4)}</td>
      <td>$${(c.projected_usd_eod||0).toFixed(4)}</td>
      <td>${c.max_usd_day!=null ? '$'+c.max_usd_day : (c.max_calls_day!=null ? c.max_calls_day+' calls' : '—')}</td>
      <td class="${cls(c.status)}">${c.status}</td>
    </tr>`).join('') || '<tr><td colspan="5">No agent traffic yet</td></tr>';
  document.getElementById('providers').innerHTML = (d.providers||[]).map(p => `
    <tr>
      <td>${p.provider}</td>
      <td class="${cls(p.status)}">${p.status}</td>
      <td>${p.success_rate==null ? '—' : (p.success_rate*100).toFixed(1)+'%'}</td>
      <td>${p.latency_ms_avg==null ? '—' : p.latency_ms_avg.toFixed(0)+' ms'}</td>
      <td>$${(p.usd||0).toFixed(4)}</td>
      <td>${p.score}</td>
      <td><span class="pill">${p.circuit}</span></td>
    </tr>`).join('') || '<tr><td colspan="7">No provider traffic yet</td></tr>';
  document.getElementById('foot').textContent = 'Day '+(d.day||'')+' · '+((d.pillars||[]).join(' · '));
}
load(); setInterval(load, 15000);
</script>
</body>
</html>
"""
