#!/usr/bin/env python3
"""Build the Visual Asset Browser.

Reads assets.json, fetches an og:image thumbnail for each site (cached in
thumbs.json), and renders assets.html — a thumbnail-first, filterable grid
for visually browsing 3D models, textures, HDRIs, characters, 2D art and tools.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets.json"
THUMBS = ROOT / "thumbs.json"
OUT = ROOT / "assets.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

META_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
    re.compile(r'<link[^>]+rel=["\']apple-touch-icon["\'][^>]+href=["\']([^"\']+)["\']', re.I),
]

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

def fetch_thumb(url):
    """Fetch an og:image (or fallback icon) URL for a site. Returns str or None."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            if resp.status != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
                return None
            html = resp.read(200_000).decode("utf-8", errors="ignore")
        for pattern in META_PATTERNS:
            m = pattern.search(html)
            if m:
                candidate = urljoin(url, m.group(1).strip())
                if candidate.startswith("http"):
                    return candidate
    except Exception as e:  # noqa: BLE001
        print(f"  ! fetch failed for {url}: {type(e).__name__}")
    return None

def main():
    data = load_json(ASSETS, {})
    items = data.get("items", [])
    catalog = load_json(ROOT / "catalog.json", {})
    catalog_count = len(catalog.get("items", []))
    print(f"Loaded {len(items)} visual asset sources (main catalog: {catalog_count} items)")

    cache = load_json(THUMBS, {})
    found = 0
    for it in items:
        site = it.get("site")
        if not site:
            continue
        if site in cache:
            if cache[site]:
                found += 1
            continue
        thumb = fetch_thumb(site)
        if not thumb:
            # Last-resort fallback: favicon service so every card has a visual.
            domain = urlparse(site).netloc
            thumb = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
        cache[site] = thumb
        if thumb:
            found += 1
            print(f"  ✓ {site} -> {thumb[:90]}")
        else:
            print(f"  · {site} -> no og:image (placeholder fallback)")
    with open(THUMBS, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    print(f"Thumbnails resolved: {found}/{len(items)}")

    for it in items:
        it["thumb"] = cache.get(it.get("site")) or None

    payload = {"meta": data.get("meta", {}), "types": data.get("types", []),
               "licenses": data.get("licenses", []), "items": items}
    html = render(json.dumps(payload, ensure_ascii=False), catalog_count)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html)/1024:.0f} KB)")

def render(data_json, catalog_count):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Visual Asset Browser — Three.js</title>
<style>
  :root {
    --bg: #0b0f17; --panel: #121826; --border: #1f2a3d;
    --text: #e6edf6; --muted: #8b98ab; --accent: #6ee7b7; --accent2: #38bdf8;
    --chip: #1a2436; --chip-hover: #22304a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif; line-height: 1.5;
  }
  .wrap { max-width: 1320px; margin: 0 auto; padding: 32px 20px 80px; }
  .nav { display: flex; gap: 16px; align-items: center; margin-bottom: 18px; font-size: .9rem; }
  .nav a { color: var(--accent2); text-decoration: none; }
  .nav a:hover { text-decoration: underline; }
  .nav .spacer { flex: 1; }
  .nav .pill { color: var(--muted); border: 1px solid var(--border); padding: 4px 12px; border-radius: 999px; }
  header { margin-bottom: 24px; }
  header h1 {
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  header p.sub { color: var(--muted); margin-top: 6px; max-width: 760px; }
  .stats { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
  .stat { background: var(--panel); border: 1px solid var(--border); padding: 6px 14px; border-radius: 999px; font-size: .85rem; color: var(--muted); }
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
  .chip.active { background: var(--accent); border-color: var(--accent); color: #06281c; font-weight: 600; }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px; margin-top: 24px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
    overflow: hidden; display: flex; flex-direction: column;
    transition: transform .12s ease, border-color .12s ease;
  }
  .card:hover { transform: translateY(-3px); border-color: var(--accent2); }
  .thumb { aspect-ratio: 16 / 10; background: #1a2436; position: relative; overflow: hidden; }
  .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .thumb .ph {
    width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
    font-size: 3rem; font-weight: 800; color: rgba(230, 237, 246, .28);
    background: linear-gradient(135deg, #182236, #101a2b);
  }
  .body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .body .top { display: flex; align-items: center; gap: 6px; }
  .body .icon { font-size: 1.1rem; }
  .body h3 { font-size: 1rem; font-weight: 700; }
  .body h3 a { color: var(--text); text-decoration: none; }
  .body h3 a:hover { color: var(--accent2); text-decoration: underline; }
  .lic { margin-left: auto; font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
  .body .desc { color: var(--muted); font-size: .86rem; flex: 1; }
  .empty { color: var(--muted); text-align: center; padding: 60px 0; display: none; }
  footer { color: var(--muted); font-size: .8rem; margin-top: 40px; text-align: center; }
  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="nav">
    <a href="index.html">← Full Catalog (all __CATALOG_COUNT__ resources)</a>
    <span class="spacer"></span>
    <span class="pill">Visual Assets</span>
  </div>
  <header>
    <h1 id="title">Visual Asset Browser</h1>
    <p class="sub" id="subtitle"></p>
    <div class="stats" id="stats"></div>
  </header>
  <div class="controls">
    <input id="search" type="search" placeholder="Search visual assets — e.g. characters, textures, voxel...">
    <div class="chips" id="chips"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty">No sources match. Try a different filter.</div>
  <footer>Curated for Three.js game dev · Updated <span id="updated"></span> · Thumbnails pulled from each site's og:image · License labels are the sites' default terms — always verify before shipping</footer>
</div>
<script id="asset-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('asset-data').textContent);
const { items, types, licenses, meta } = DATA;
const state = { type: 'all', lic: 'all', q: '' };
const $ = sel => document.querySelector(sel);

function init() {
  $('#title').textContent = meta.title;
  $('#subtitle').textContent = meta.subtitle;
  $('#updated').textContent = meta.updated;
  const cc0 = items.filter(i => i.license === 'cc0').length;
  const withThumb = items.filter(i => i.thumb).length;
  $('#stats').innerHTML =
    `<span class="stat"><b>${items.length}</b> sources</span>` +
    `<span class="stat"><b>${types.length}</b> types</span>` +
    `<span class="stat"><b>${cc0}</b> CC0</span>` +
    `<span class="stat"><b>${withThumb}/${items.length}</b> with thumbnails</span>`;

  const typeChips = `<div class="chip active" data-type="all">All types</div>` +
    types.map(t => `<div class="chip" data-type="${t.id}">${t.icon} ${t.label}</div>`).join('');
  const licChips = `<div class="chip active" data-lic="all">Any license</div>` +
    licenses.map(l => `<div class="chip" data-lic="${l.id}" style="--lc:${l.color}">${l.label}</div>`).join('');
  $('#chips').innerHTML = typeChips + licChips;

  document.querySelectorAll('[data-type]').forEach(chip =>
    chip.addEventListener('click', () => {
      document.querySelectorAll('[data-type]').forEach(c => c.classList.remove('active'));
      chip.classList.add('active'); state.type = chip.dataset.type; render();
    }));
  document.querySelectorAll('[data-lic]').forEach(chip =>
    chip.addEventListener('click', () => {
      document.querySelectorAll('[data-lic]').forEach(c => c.classList.remove('active'));
      chip.classList.add('active'); state.lic = chip.dataset.lic; render();
    }));
  $('#search').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
  render();
}

function matches(it) {
  if (state.type !== 'all' && it.type !== state.type) return false;
  if (state.lic !== 'all' && it.license !== state.lic) return false;
  if (!state.q) return true;
  return [it.name, it.desc, it.type].join(' ').toLowerCase().includes(state.q);
}

function render() {
  const visible = items.filter(matches);
  const lic = l => licenses.find(x => x.id === l);
  $('#grid').innerHTML = visible.map(it => {
    const t = types.find(x => x.id === it.type);
    const l = lic(it.license);
    const thumb = it.thumb
      ? `<img src="${it.thumb}" alt="${it.name}" loading="lazy" onerror="this.outerHTML='<div class=\\'ph\\'>${it.name[0]}</div>'">`
      : `<div class="ph">${it.name[0]}</div>`;
    return `<div class="card">
      <div class="thumb">${thumb}</div>
      <div class="body">
        <div class="top"><span class="icon">${t.icon}</span>
          <h3><a href="${it.url}" target="_blank" rel="noopener">${it.name}</a></h3>
          <span class="lic" style="background:${l.color}22;color:${l.color}">${l.label}</span>
        </div>
        <div class="desc">${it.desc}</div>
      </div>
    </div>`;
  }).join('');
  $('#empty').style.display = visible.length ? 'none' : 'block';
  document.title = `${meta.title} — ${visible.length} results`;
}

init();
</script>
</body>
</html>
""".replace("__DATA__", data_json).replace("__CATALOG_COUNT__", str(catalog_count))

if __name__ == "__main__":
    main()
