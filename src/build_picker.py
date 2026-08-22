"""
build_picker.py — an interactive map for assigning TMC-01..06 to junction candidates.

The workbooks carry no coordinates, so the six surveyed junctions cannot be matched
to the drawing automatically. This renders the 39 traffic-signal clusters on a real
basemap and lets a human click the six, then emits the assignment as text.

Runs locally rather than as a published artifact: map tiles come from an external
host, which the artifact CSP blocks.

Run:  uv run python src/build_picker.py
Then: cd out && python3 -m http.server 8899   ->  http://localhost:8899/pick_junctions.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTIONS, OUT, OUT_DATA

SRC = OUT_DATA / "junction_candidates.geojson"

TPL = """<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pick the six junctions</title>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{--paper:#F1F2EF;--surface:#FAFBF8;--sunk:#E9EBE6;--ink:#14181A;--muted:#5C6663;
  --faint:#8B938E;--rule:#D5D9D4;--accent:#1B3A6B;--defect:#9E2B25;--ok:#2C6249}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--paper);color:var(--ink);
  font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:13px}
#app{display:grid;grid-template-columns:1fr 22rem;height:100%}
@media(max-width:860px){#app{grid-template-columns:1fr;grid-template-rows:60vh 1fr}}
#map{width:100%;height:100%}
aside{border-left:1px solid var(--rule);background:var(--surface);overflow-y:auto;
  padding:1rem;display:flex;flex-direction:column;gap:.9rem}
h1{font-family:Archivo,sans-serif;font-size:1.05rem;margin:0;letter-spacing:-.01em}
p{margin:0;color:var(--muted);line-height:1.5}
.slot{display:flex;align-items:center;gap:.5rem;padding:.4rem .55rem;border-radius:3px;
  border:1px solid var(--rule);background:var(--paper)}
.slot.filled{border-color:var(--accent);background:#E2E8F1}
.slot b{width:4.2rem;flex:none}
.slot span{color:var(--muted);font-size:11px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.slot button{margin-left:auto;border:0;background:none;color:var(--defect);cursor:pointer;
  font-family:inherit;font-size:15px;line-height:1;padding:0 .2rem}
textarea{width:100%;height:8.5rem;font-family:inherit;font-size:11.5px;padding:.5rem;
  border:1px solid var(--rule);border-radius:3px;background:var(--paper);color:var(--ink);
  resize:vertical}
.row{display:flex;gap:.5rem}
button.act{flex:1;padding:.5rem;border:1px solid var(--rule);border-radius:3px;
  background:var(--paper);color:var(--ink);cursor:pointer;font-family:inherit;font-size:11.5px;
  text-transform:uppercase;letter-spacing:.07em}
button.act:hover{border-color:var(--accent);color:var(--accent)}
button.act.primary{background:var(--accent);color:var(--surface);border-color:var(--accent)}
.legend{font-size:11px;color:var(--faint);line-height:1.6}
.maplibregl-popup-content{font-family:"IBM Plex Mono",monospace;font-size:11.5px;padding:.5rem .7rem}
</style>
</head>
<body>
<div id="app">
  <div id="map"></div>
  <aside>
    <h1>Pick the six junctions</h1>
    <p>Each circle is a cluster of traffic signals from the JDA survey drawing, sized by
    how many signal heads it holds. Click one to assign it to the next empty TMC slot.
    Click it again, or the &times;, to clear.</p>
    <div id="slots"></div>
    <div class="row">
      <button class="act" id="reset">Reset</button>
      <button class="act primary" id="copy">Copy</button>
    </div>
    <textarea id="out" readonly></textarea>
    <p class="legend">
      <b>Sizing:</b> a 4-arm signalised junction typically carries 8&ndash;16 heads, so the
      larger circles are the real junctions.<br><br>
      <b>Cross-streets to look for:</b><br>__ARMS__
    </p>
    <p class="legend">Basemap &copy; OpenStreetMap contributors.</p>
  </aside>
</div>
<script>
var DATA = __DATA__;
var CODES = __CODES__;
var picks = {};
CODES.forEach(function(c){ picks[c] = null; });

var map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                      tileSize: 256, attribution: '&copy; OpenStreetMap contributors' } },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
  },
  center: [75.7679, 26.8536], zoom: 12.4
});
map.addControl(new maplibregl.NavigationControl(), 'top-left');
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }));

function codeFor(id){
  for (var i = 0; i < CODES.length; i++) if (picks[CODES[i]] === id) return CODES[i];
  return null;
}
function nextFree(){
  for (var i = 0; i < CODES.length; i++) if (!picks[CODES[i]]) return CODES[i];
  return null;
}

var markers = {};
DATA.features.forEach(function(f){
  var p = f.properties, id = p.cluster;
  var n = p.signal_heads;
  var d = Math.max(14, Math.min(34, 10 + n * 1.6));
  var el = document.createElement('div');
  el.style.cssText = 'width:' + d + 'px;height:' + d + 'px;border-radius:50%;cursor:pointer;' +
    'display:flex;align-items:center;justify-content:center;font:600 10px/1 "IBM Plex Mono",monospace;' +
    'border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)';
  el.title = id + ' — ' + n + ' signal heads' + (p.nearest_label ? ' — ' + p.nearest_label : '');
  el.addEventListener('click', function(ev){
    ev.stopPropagation();
    var cur = codeFor(id);
    if (cur) { picks[cur] = null; }
    else { var slot = nextFree(); if (!slot) { alert('All six slots are filled. Clear one first.'); return; } picks[slot] = id; }
    render();
  });
  var m = new maplibregl.Marker({ element: el })
    .setLngLat(f.geometry.coordinates)
    .setPopup(new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
      '<b>' + id + '</b> &middot; ' + n + ' heads<br>' +
      f.geometry.coordinates[1].toFixed(6) + ', ' + f.geometry.coordinates[0].toFixed(6) +
      (p.nearest_label ? '<br><i>' + p.nearest_label + '</i>' : '')))
    .addTo(map);
  markers[id] = { el: el, feature: f };
});

function render(){
  Object.keys(markers).forEach(function(id){
    var c = codeFor(id), el = markers[id].el;
    el.style.background = c ? '#1B3A6B' : 'rgba(158,43,37,.82)';
    el.style.color = '#fff';
    el.textContent = c ? c.replace('TMC-', '') : '';
  });
  var html = '';
  CODES.forEach(function(c){
    var id = picks[c];
    var f = id ? markers[id].feature : null;
    var label = f ? (f.geometry.coordinates[1].toFixed(6) + ', ' + f.geometry.coordinates[0].toFixed(6)) : 'not set';
    html += '<div class="slot' + (id ? ' filled' : '') + '"><b>' + c + '</b><span>' +
      (id ? id + ' — ' + label : label) + '</span>' +
      (id ? '<button data-c="' + c + '">&times;</button>' : '') + '</div>';
  });
  document.getElementById('slots').innerHTML = html;
  Array.prototype.forEach.call(document.querySelectorAll('.slot button'), function(b){
    b.addEventListener('click', function(){ picks[b.getAttribute('data-c')] = null; render(); });
  });
  var lines = [];
  CODES.forEach(function(c){
    var id = picks[c];
    if (!id) return;
    var f = markers[id].feature;
    lines.push(c + ': ' + f.geometry.coordinates[1].toFixed(6) + ', ' +
               f.geometry.coordinates[0].toFixed(6) + '   # ' + id + ', ' +
               f.properties.signal_heads + ' heads' +
               (f.properties.nearest_label ? ', near ' + f.properties.nearest_label : ''));
  });
  document.getElementById('out').value = lines.length
    ? lines.join('\\n')
    : 'Pick junctions on the map. The six lines to paste back will appear here.';
}

document.getElementById('reset').addEventListener('click', function(){
  CODES.forEach(function(c){ picks[c] = null; }); render();
});
document.getElementById('copy').addEventListener('click', function(){
  var t = document.getElementById('out');
  t.select(); document.execCommand('copy');
  var b = document.getElementById('copy'); b.textContent = 'Copied';
  setTimeout(function(){ b.textContent = 'Copy'; }, 1200);
});
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if not SRC.exists():
        raise SystemExit(f"Not found: {SRC} — run src/dxf_inventory.py first.")
    data = json.loads(SRC.read_text())
    arms = "<br>".join(f"{c} &middot; {a[1]} / {a[3]}" for c, a in JUNCTIONS.items())
    html = (TPL.replace("__DATA__", json.dumps(data, separators=(",", ":")))
               .replace("__CODES__", json.dumps(list(JUNCTIONS)))
               .replace("__ARMS__", arms))
    out = OUT / "pick_junctions.html"
    out.write_text(html)
    print(f"written: {out}  ({len(html)/1024:,.0f} KB, {len(data['features'])} candidates)")
    print("\nserve it (tiles need http, not file://):")
    print("  cd out && python3 -m http.server 8899")
    print("  open http://localhost:8899/pick_junctions.html")
