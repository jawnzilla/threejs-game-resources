#!/usr/bin/env python3
"""Build the Three.js Agent Skills Cheat Sheet.

Reads cheatsheet.json (curated digest of the open-source skill packs) and
renders cheatsheet.html — a decision-first reference page matching the
catalog's dark theme.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "cheatsheet.json"
OUT = ROOT / "cheatsheet.html"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

def main():
    data = load_json(DATA, {})
    decisions = data.get("decisions", [])
    packs = data.get("packs", [])
    skill_count = sum(len(g["skills"]) for p in packs for g in p.get("groups", []))
    print(f"Loaded {len(packs)} packs, {len(decisions)} decisions, {skill_count} distilled skills")

    payload = {"meta": data.get("meta", {}), "decisions": decisions, "packs": packs}
    html = render(json.dumps(payload, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html)/1024:.0f} KB)")

def render(data_json):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Three.js Agent Skills Cheat Sheet</title>
<style>
  :root {
    --bg: #0b0f17; --panel: #121826; --border: #1f2a3d;
    --text: #e6edf6; --muted: #8b98ab; --accent: #6ee7b7; --accent2: #38bdf8;
    --chip: #1a2436; --chip-hover: #22304a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif; line-height: 1.55;
  }
  .wrap { max-width: 1240px; margin: 0 auto; padding: 32px 20px 80px; }
  .nav { display: flex; gap: 16px; align-items: center; margin-bottom: 18px; font-size: .9rem; flex-wrap: wrap; }
  .nav a { color: var(--accent2); text-decoration: none; }
  .nav a:hover { text-decoration: underline; }
  .nav .spacer { flex: 1; }
  .nav .pill { color: var(--muted); border: 1px solid var(--border); padding: 4px 12px; border-radius: 999px; }
  header { margin-bottom: 26px; }
  header h1 {
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  header p.sub { color: var(--muted); margin-top: 6px; max-width: 820px; }
  .stats { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
  .stat { background: var(--panel); border: 1px solid var(--border); padding: 6px 14px; border-radius: 999px; font-size: .85rem; color: var(--muted); }
  .stat b { color: var(--text); }
  h2.section { font-size: 1.35rem; font-weight: 800; margin: 40px 0 14px; letter-spacing: -0.01em; }
  h2.section .k { color: var(--accent2); }
  table.decisions { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
  table.decisions th, table.decisions td { padding: 10px 14px; text-align: left; font-size: .88rem; border-bottom: 1px solid var(--border); vertical-align: top; }
  table.decisions th { background: #16203a; color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }
  table.decisions tr:last-child td { border-bottom: none; }
  table.decisions td.want { font-weight: 600; }
  table.decisions td.pack { color: var(--accent); white-space: nowrap; }
  table.decisions td.skill { color: var(--muted); }
  .pack { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 20px 22px; margin-top: 18px; }
  .pack-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .pack-head h3 { font-size: 1.2rem; font-weight: 800; }
  .pack-head h3 a { color: var(--text); text-decoration: none; }
  .pack-head h3 a:hover { color: var(--accent2); text-decoration: underline; }
  .stars { color: var(--accent2); font-size: .9rem; white-space: nowrap; }
  .pack-note { color: var(--muted); font-size: .9rem; margin-top: 8px; max-width: 960px; }
  .pack-install {
    margin-top: 10px; font-size: .8rem; color: var(--accent);
    background: #0e241e; border: 1px solid #1f5f52; border-radius: 8px;
    padding: 8px 12px; font-family: "Cascadia Code", Consolas, monospace; overflow-x: auto; white-space: nowrap;
  }
  .group-label { margin: 18px 0 8px; font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  .skills { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 10px; }
  .skill { background: #0f1520; border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; }
  .skill b { font-size: .9rem; color: var(--text); }
  .skill p { color: var(--muted); font-size: .82rem; margin-top: 4px; }
  footer { color: var(--muted); font-size: .8rem; margin-top: 44px; text-align: center; }
  @media (max-width: 720px) { .skills { grid-template-columns: 1fr; } table.decisions { font-size: .8rem; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="nav">
    <a href="index.html">← Full Catalog</a>
    <a href="assets.html">🖼️ Visual Assets</a>
    <span class="spacer"></span>
    <span class="pill">Cheat Sheet</span>
  </div>
  <header>
    <h1 id="title">Three.js Agent Skills Cheat Sheet</h1>
    <p class="sub" id="subtitle"></p>
    <div class="stats" id="stats"></div>
  </header>

  <h2 class="section">⚡ <span class="k">Pick a pack</span> — what do you want to build?</h2>
  <table class="decisions" id="decisions"></table>

  <h2 class="section">📦 <span class="k">The packs, distilled</span></h2>
  <div id="packs"></div>

  <footer>Distilled from each repo's SKILL.md contents · Star counts via GitHub API · Updated <span id="updated"></span></footer>
</div>
<script id="cs-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('cs-data').textContent);
const { decisions, packs, meta } = DATA;
const fmt = n => n >= 1000 ? (n/1000).toFixed(1) + 'k' : String(n);
const $ = sel => document.querySelector(sel);

function init() {
  $('#title').textContent = meta.title;
  $('#subtitle').textContent = meta.subtitle;
  $('#updated').textContent = meta.updated;
  const skills = packs.reduce((n, p) => n + p.groups.reduce((m, g) => m + g.skills.length, 0), 0);
  $('#stats').innerHTML =
    `<span class="stat"><b>${packs.length}</b> skill packs</span>` +
    `<span class="stat"><b>${skills}</b> distilled skills</span>` +
    `<span class="stat"><b>${decisions.length}</b> quick picks</span>`;

  $('#decisions').innerHTML =
    `<thead><tr><th>You want…</th><th>Pack</th><th>Use</th></tr></thead><tbody>` +
    decisions.map(d => `<tr><td class="want">${d.want}</td><td class="pack">${d.pack}</td><td class="skill">${d.skill}</td></tr>`).join('') +
    `</tbody>`;

  $('#packs').innerHTML = packs.map(p => {
    const groups = p.groups.map(g => `
      <div class="group-label">${g.label}</div>
      <div class="skills">${g.skills.map(s =>
        `<div class="skill"><b>${s.name}</b><p>${s.teach}</p></div>`).join('')}
      </div>`).join('');
    return `<div class="pack">
      <div class="pack-head"><h3><a href="${p.url}" target="_blank" rel="noopener">${p.name}</a></h3>
        <span class="stars">★ ${fmt(p.stars)}</span></div>
      <div class="pack-install">${p.install}</div>
      <div class="pack-note">${p.note}</div>
      ${groups}
    </div>`;
  }).join('');
}
init();
</script>
</body>
</html>
""".replace("__DATA__", data_json)

if __name__ == "__main__":
    main()
