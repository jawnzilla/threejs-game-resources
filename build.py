#!/usr/bin/env python3
"""Build the Three.js Game Dev Resource Catalog.

Reads catalog.json, fetches GitHub star counts for repos (via `gh api`,
cached in stars.json), and renders index.html — a self-contained, searchable,
category-filterable catalog that works from any static host (GitHub Pages).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "catalog.json"
STARS = ROOT / "stars.json"
OUT = ROOT / "index.html"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

def star_count(repo, cache):
    """Return star count for owner/repo, using gh api, cached in stars.json."""
    if repo in cache:
        return cache[repo]
    count = None
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}", "--jq", ".stargazers_count"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip().isdigit():
            count = int(proc.stdout.strip())
        else:
            print(f"  ! star fetch failed for {repo}: {proc.stderr.strip()[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"  ! star fetch error for {repo}: {e}")
    cache[repo] = count
    return count

def fmt_stars(n):
    if n is None:
        return None
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def main():
    catalog = load_json(CATALOG, {})
    items = catalog.get("items", [])
    categories = catalog.get("categories", [])
    print(f"Loaded {len(items)} items across {len(categories)} categories")

    cache = load_json(STARS, {})
    repos = sorted({it["github"] for it in items if it.get("github")})
    print(f"Fetching stars for {len(repos)} GitHub repos...")
    for repo in repos:
        star_count(repo, cache)
    with open(STARS, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    ok = sum(1 for v in cache.values() if v is not None)
    print(f"Stars resolved for {ok}/{len(repos)} repos")

    # Enrich items with star counts
    for it in items:
        gh = it.get("github")
        if gh and cache.get(gh) is not None:
            it["stars"] = cache[gh]

    cat_count = {c["id"]: 0 for c in categories}
    for it in items:
        cat_count[it["category"]] = cat_count.get(it["category"], 0) + 1

    data = {
        "meta": catalog.get("meta", {}),
        "categories": categories,
        "catCount": cat_count,
        "items": items,
    }
    data_json = json.dumps(data, ensure_ascii=False)

    html = render(data_json)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html)/1024:.0f} KB)")

def render(data_json):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Three.js Game Dev Resource Catalog</title>
<style>
  :root {
    --bg: #0b0f17; --panel: #121826; --panel2: #0f1520; --border: #1f2a3d;
    --text: #e6edf6; --muted: #8b98ab; --accent: #6ee7b7; --accent2: #38bdf8;
    --chip: #1a2436; --chip-hover: #22304a; --star: #fbbf24;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    line-height: 1.5;
  }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 32px 20px 80px; }
  header { margin-bottom: 28px; }
  header h1 {
    font-size: 2.1rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  header p.sub { color: var(--muted); margin-top: 6px; max-width: 720px; }
  .stats { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
  .stat {
    background: var(--panel); border: 1px solid var(--border);
    padding: 6px 14px; border-radius: 999px; font-size: .85rem; color: var(--muted);
  }
  .stat b { color: var(--text); }
  .controls { position: sticky; top: 0; z-index: 10; padding: 12px 0; background: var(--bg); }
  #search {
    width: 100%; padding: 12px 16px; border-radius: 12px;
    background: var(--panel); border: 1px solid var(--border); color: var(--text);
    font-size: 1rem; outline: none;
  }
  #search:focus { border-color: var(--accent2); }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
  .chip {
    background: var(--chip); border: 1px solid var(--border); color: var(--muted);
    padding: 6px 12px; border-radius: 999px; cursor: pointer; font-size: .82rem;
    user-select: none; transition: all .12s ease;
  }
  .chip:hover { background: var(--chip-hover); color: var(--text); }
  .chip.active {
    background: var(--accent); border-color: var(--accent); color: #06281c; font-weight: 600;
  }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 14px; margin-top: 24px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
    padding: 16px 18px; display: flex; flex-direction: column; gap: 8px;
    transition: transform .12s ease, border-color .12s ease;
  }
  .card:hover { transform: translateY(-2px); border-color: var(--accent2); }
  .card .top { display: flex; align-items: center; gap: 8px; }
  .card .icon { font-size: 1.15rem; }
  .card h3 { font-size: 1rem; font-weight: 700; }
  .card h3 a { color: var(--text); text-decoration: none; }
  .card h3 a:hover { color: var(--accent2); text-decoration: underline; }
  .stars {
    margin-left: auto; font-size: .8rem; color: var(--star); white-space: nowrap;
    display: inline-flex; align-items: center; gap: 3px;
  }
  .card .desc { color: var(--muted); font-size: .88rem; flex: 1; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    font-size: .72rem; padding: 2px 8px; border-radius: 999px;
    background: var(--chip); color: var(--muted);
  }
  .tag.free { color: var(--accent); }
  .empty { color: var(--muted); text-align: center; padding: 60px 0; display: none; }
  footer { color: var(--muted); font-size: .8rem; margin-top: 40px; text-align: center; }
  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1 id="title">Three.js Game Dev Resource Catalog</h1>
    <p class="sub" id="subtitle"></p>
    <div class="stats" id="stats"></div>
  </header>
  <div class="controls">
    <input id="search" type="search" placeholder="Search resources — e.g. physics, multiplayer, text, particles...">
    <div class="chips" id="chips"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty">No resources match your filter. Try another search.</div>
  <footer>Curated for game development with Three.js · Updated <span id="updated"></span> · Star counts via GitHub API</footer>
</div>
<script id="catalog-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('catalog-data').textContent);
const { items, categories, catCount, meta } = DATA;
const state = { cat: 'all', q: '' };

const fmt = n => n >= 1000 ? (n/1000).toFixed(1) + 'k' : String(n);
const $ = sel => document.querySelector(sel);

function init() {
  $('#title').textContent = meta.title;
  $('#subtitle').textContent = meta.subtitle;
  $('#updated').textContent = meta.updated;
  const total = items.length;
  const gh = items.filter(i => i.stars != null).length;
  const games = items.filter(i => (i.tags||[]).includes('game')).length;
  $('#stats').innerHTML =
    `<span class="stat"><b>${total}</b> resources</span>` +
    `<span class="stat"><b>${categories.length}</b> categories</span>` +
    `<span class="stat"><b>${games}</b> playable showcases</span>` +
    `<span class="stat"><b>${gh}</b> GitHub repos w/ stars</span>`;
  $('#chips').innerHTML =
    `<div class="chip active" data-cat="all">All (${total})</div>` +
    categories.map(c =>
      `<div class="chip" data-cat="${c.id}">${c.icon} ${c.label} (${catCount[c.id]||0})</div>`
    ).join('');
  document.querySelectorAll('.chip').forEach(chip =>
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.cat = chip.dataset.cat;
      render();
    })
  );
  $('#search').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
  render();
}

function matches(item) {
  if (state.cat !== 'all' && item.category !== state.cat) return false;
  if (!state.q) return true;
  const hay = [item.name, item.desc, (item.tags||[]).join(' '), item.url].join(' ').toLowerCase();
  return state.q.split(/\s+/).every(term => hay.includes(term));
}

function render() {
  const cat = categories.find(c => c.id === state.cat);
  const visible = items.filter(matches);
  const sortItems = [...visible].sort((a,b) => (b.stars||0) - (a.stars||0));
  $('#grid').innerHTML = sortItems.map(item => {
    const c = categories.find(c => c.id === item.category);
    const tags = (item.tags||[]).map(t =>
      `<span class="tag ${t === 'free' ? 'free' : ''}">${t}</span>`).join('');
    const stars = item.stars != null
      ? `<span class="stars">★ ${fmt(item.stars)}</span>` : '';
    return `<div class="card">
      <div class="top"><span class="icon">${c.icon}</span>
        <h3><a href="${item.url}" target="_blank" rel="noopener">${item.name}</a></h3>${stars}
      </div>
      <div class="desc">${item.desc}</div>
      <div class="tags">${tags}</div>
    </div>`;
  }).join('');
  $('#empty').style.display = visible.length ? 'none' : 'block';
  document.title = `${meta.title} — ${visible.length} results`;
}

init();
</script>
</body>
</html>
""".replace("__DATA__", data_json)

if __name__ == "__main__":
    main()
