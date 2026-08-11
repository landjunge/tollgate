"""Minimal control-plane HTML — feelable product, no SPA build."""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tollgate — Agent control plane</title>
<style>
  :root { --bg:#0f1115; --card:#1a1d24; --fg:#e8eaed; --muted:#9aa0a6; --ok:#3dd68c; --warn:#f5a524; --bad:#f31260; --acc:#6c8cff; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--fg); }
  header { padding:1.25rem 1.5rem; border-bottom:1px solid #2a2f3a; }
  header h1 { margin:0; font-size:1.25rem; letter-spacing:.02em; }
  header p { margin:.35rem 0 0; color:var(--muted); font-size:.9rem; max-width:52rem; }
  main { padding:1.25rem 1.5rem 3rem; max-width:1100px; margin:0 auto; }
  .headline { background:linear-gradient(135deg,#1e2430,#151922); border:1px solid #2a2f3a; border-radius:12px; padding:1.1rem 1.25rem; font-size:1.1rem; margin-bottom:1rem; font-weight:600; }
  .promise { color:var(--muted); font-size:.9rem; margin:-.4rem 0 1.25rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:.75rem; margin-bottom:1.5rem; }
  .stat { background:var(--card); border-radius:10px; padding:.85rem 1rem; border:1px solid #2a2f3a; }
  .stat b { display:block; font-size:1.35rem; }
  .stat span { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
  h2 { font-size:.95rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin:1.5rem 0 .6rem; }
  .attn { background:var(--card); border:1px solid #2a2f3a; border-radius:10px; padding:.5rem 0; margin-bottom:1rem; }
  .attn div { padding:.45rem 1rem; border-bottom:1px solid #2a2f3a; font-size:.9rem; }
  .attn div:last-child { border-bottom:none; }
  table { width:100%; border-collapse:collapse; background:var(--card); border-radius:10px; overflow:hidden; border:1px solid #2a2f3a; }
  th, td { text-align:left; padding:.55rem .75rem; border-bottom:1px solid #2a2f3a; font-size:.9rem; }
  th { color:var(--muted); font-weight:600; font-size:.75rem; text-transform:uppercase; }
  tr:last-child td { border-bottom:none; }
  .pill { display:inline-block; padding:.12rem .45rem; border-radius:999px; font-size:.75rem; background:#2a2f3a; }
  .ok { color:var(--ok); } .warn { color:var(--warn); } .bad { color:var(--bad); } .error { color:var(--bad); }
  footer { margin-top:2rem; color:var(--muted); font-size:.8rem; }
  a { color:var(--acc); }
  button { background:var(--acc); color:#fff; border:0; border-radius:8px; padding:.45rem .9rem; cursor:pointer; font-weight:600; }
</style>
</head>
<body>
<header>
  <h1>Tollgate</h1>
  <p id="promise">Safety &amp; control layer for AI agents — not another LLM gateway.</p>
</header>
<main>
  <div class="headline" id="headline">Loading…</div>
  <p class="promise" id="tagline"></p>
  <div class="grid" id="stats"></div>
  <h2>Needs attention</h2>
  <div class="attn" id="attention"><div class="muted">—</div></div>
  <h2>Agents / consumers</h2>
  <table><thead><tr><th>Agent</th><th>USD today</th><th>Projected EOD</th><th>Budget</th><th>Status</th></tr></thead>
  <tbody id="consumers"></tbody></table>
  <h2>Provider health</h2>
  <table><thead><tr><th>Provider</th><th>Status</th><th>Success</th><th>Latency</th><th>USD day</th><th>Score</th><th>Circuit</th></tr></thead>
  <tbody id="providers"></tbody></table>
  <footer id="foot"></footer>
  <p style="margin-top:1rem"><button onclick="load()">Refresh</button>
  · <a href="/docs">API</a> · <a href="/v1/control">JSON</a></p>
</main>
<script>
function cls(s){ if(!s) return ''; if(['healthy','ok','idle'].includes(s)) return 'ok'; if(['warn','likely_over','degraded','half_open'].includes(s)) return 'warn'; return 'bad'; }
async function load(){
  const r = await fetch('/v1/control');
  const d = await r.json();
  document.getElementById('headline').textContent = d.headline || '—';
  document.getElementById('tagline').textContent = d.tagline || d.promise || '';
  if (d.promise) document.getElementById('promise').textContent = d.promise;
  const s = d.summary || {};
  const res = d.resilience || {};
  document.getElementById('stats').innerHTML = [
    ['Resilience', (res.score!=null?res.score:'—')+'/100'],
    ['Spent today', '$'+(s.usd||0).toFixed(2)],
    ['Agent stops', s.agent_protection_blocks ?? 0],
    ['Provider errors', s.errors ?? 0],
    ['Agents protected', s.consumers_protected ?? 0],
    ['Calls', s.calls ?? 0]
  ].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  const att = d.attention || [];
  document.getElementById('attention').innerHTML = att.length
    ? att.map(a => `<div class="${a.level||''}">${a.level==='ok'?'✓':(a.level==='error'?'⛔':'⚠')} ${a.message||''}</div>`).join('')
    : '<div class="ok">✓ Nothing urgent — agents under control</div>';
  document.getElementById('consumers').innerHTML = (d.consumers||[]).map(c => `
    <tr>
      <td>${c.consumer}</td>
      <td>$${(c.usd||0).toFixed(4)}</td>
      <td>$${(c.projected_usd_eod||0).toFixed(4)}</td>
      <td>${c.max_usd_day!=null ? '$'+c.max_usd_day : (c.max_calls_day!=null ? c.max_calls_day+' calls' : '—')}</td>
      <td class="${cls(c.status)}">${c.status}</td>
    </tr>`).join('') || '<tr><td colspan="5">No agent traffic yet — set consumer-budget and send a request</td></tr>';
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
