"use client";
import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Junction } from "@/lib/types";

/**
 * The six junctions, the corridor, and the constraint atlas as toggleable layers.
 *
 * Layers load only when switched on. The atlas is 2.9 MB even after simplification, and
 * an officer opening this on a phone in a meeting should not wait for constraint data
 * they may never look at.
 *
 * Marker fill encodes how each position was established: solid where the survey's own
 * arm name matches JDA's scheme, dashed where it was placed by position in that sequence.
 * That distinction is the point - it lets the three inferred ones be challenged.
 */
type LayerDef = { id: string; label: string; colour: string; kind: "line" | "circle" };

const ATLAS_LAYERS: LayerDef[] = [
  { id: "structures", label: "Buildings", colour: "#9E2B25", kind: "line" },
  { id: "median", label: "Medians", colour: "#5C6663", kind: "line" },
  { id: "drainage", label: "Drainage", colour: "#1B6E8F", kind: "line" },
  { id: "electrical", label: "Electrical", colour: "#B08A00", kind: "circle" },
  { id: "telecom", label: "Telecom", colour: "#2C6249", kind: "circle" },
  { id: "vegetation", label: "Trees", colour: "#3E7A3E", kind: "circle" },
  { id: "gas", label: "Gas markers", colour: "#C8791A", kind: "circle" },
  { id: "religious", label: "Temples", colour: "#6B2D8C", kind: "circle" },
];

export default function CorridorMap({ junctions }: { junctions: Junction[] }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const atlas = useRef<unknown>(null);
  const [on, setOn] = useState<Record<string, boolean>>({});
  const [cands, setCands] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!box.current) return;
    // The basemap is the SURVEY DRAWING, not a tile service.
    //
    // This previously pulled raster tiles from tile.openstreetmap.org, which breaches
    // the OSM Tile Usage Policy for a commercial deliverable. The practical risk was
    // worse than the licensing one: OSM blocks abusive clients without warning, and a
    // basemap that can vanish mid-meeting is not a basemap.
    //
    // The drawing already carries the carriageway, the building footprints, the medians
    // and the alignment. Surveyed geometry is also the more defensible backdrop for a
    // survey deliverable than a generic tile layer. No third party, no key, nothing to
    // rate-limit, and the page makes zero cross-origin requests.
    const ink = getComputedStyle(document.documentElement);
    const tok = (n: string, f: string) => ink.getPropertyValue(n).trim() || f;
    const m = new maplibregl.Map({
      container: box.current,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "ground", type: "background",
                   paint: { "background-color": tok("--sunk", "#E9EBE6") } }],
      },
      center: [75.7635, 26.856], zoom: 12.6,
      attributionControl: false,
    });
    m.addControl(new maplibregl.AttributionControl({
      compact: true,
      customAttribution: "Basemap: JDA survey drawing (EPSG:32643)",
    }));
    map.current = m;
    m.addControl(new maplibregl.NavigationControl(), "top-right");
    m.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }));

    const ordered = [...junctions].sort((a, b) => b.lat - a.lat);
    const bounds = new maplibregl.LngLatBounds();
    ordered.forEach((j) => {
      bounds.extend([j.lon, j.lat]);
      const firm = j.location_confidence === "name match";
      const el = document.createElement("div");
      const d = 16 + Math.round((j.daily_veh / 160000) * 18);
      el.style.cssText =
        `width:${d}px;height:${d}px;border-radius:50%;cursor:pointer;z-index:5;` +
        `background:${firm ? "#1B3A6B" : "#9E2B25"};` +
        `border:2px ${firm ? "solid" : "dashed"} #fff;` +
        `box-shadow:0 1px 5px rgba(0,0,0,.45);display:flex;align-items:center;` +
        `justify-content:center;color:#fff;font:600 9px/1 "IBM Plex Mono",monospace`;
      el.textContent = j.code.replace("TMC-", "");
      new maplibregl.Marker({ element: el })
        .setLngLat([j.lon, j.lat])
        .setPopup(new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
          `<div style="font:12px/1.45 'IBM Plex Mono',monospace">
             <b>${j.code}</b> &middot; ${j.jda_name}<br>${j.arms[1]} / ${j.arms[3]}<br>
             ${j.daily_veh.toLocaleString("en-US")} veh/day &middot; peak ${j.peak_start}<br>
             through ${j.through_pct}%<br>
             <span style="color:#5C6663">${j.lat.toFixed(6)}, ${j.lon.toFixed(6)}<br>
             location: ${j.location_confidence}</span></div>`))
        .addTo(m);
    });

    // Attach-or-run rather than on("load") alone.
    //
    // Defensive, not a fix for an observed bug: an inline style with no remote sources
    // can finish loading before this line runs, and `once("load", ...)` would then never
    // fire. Cheap to guard against and impossible to notice if it ever happened.
    const build = () => {
      m.addSource("corridor", {
        type: "geojson",
        data: { type: "Feature", properties: {},
                geometry: { type: "LineString",
                            coordinates: ordered.map((j) => [j.lon, j.lat]) } },
      });
      m.addLayer({ id: "corridor-halo", type: "line", source: "corridor",
        paint: { "line-color": "#FAFBF8", "line-width": 7, "line-opacity": .85 } });
      m.addLayer({ id: "corridor-line", type: "line", source: "corridor",
        paint: { "line-color": "#1B3A6B", "line-width": 2.6 } });

      // Surveyed basemap. Fetched after the corridor so the junctions paint first and
      // the map is useful before 408 KB of context has arrived.
      fetch("/basemap.geojson").then((r) => r.json()).then((base) => {
        if (!map.current || m.getSource("base")) return;
        m.addSource("base", { type: "geojson", data: base });
        const rule = tok("--rule-hard", "#B4BBB4");
        const faint = tok("--rule", "#D5D9D4");
        m.addLayer({ id: "base-structures", type: "line", source: "base",
          filter: ["==", ["get", "category"], "structures"],
          paint: { "line-color": faint, "line-width": .6, "line-opacity": .9 } },
          "corridor-halo");
        m.addLayer({ id: "base-carriageway", type: "line", source: "base",
          filter: ["==", ["get", "category"], "carriageway"],
          paint: { "line-color": rule, "line-width": 1.1 } }, "corridor-halo");
        m.addLayer({ id: "base-median", type: "line", source: "base",
          filter: ["==", ["get", "category"], "median"],
          paint: { "line-color": rule, "line-width": .8, "line-dasharray": [3, 2] } },
          "corridor-halo");
      }).catch(() => { /* basemap is context; the junctions and corridor stand alone */ });
      m.fitBounds(bounds, { padding: 70, maxZoom: 14, duration: 0 });
    };
    if (m.isStyleLoaded()) build();
    else m.once("load", build);

    return () => { m.remove(); map.current = null; };
  }, [junctions]);

  async function toggleLayer(def: LayerDef) {
    const m = map.current;
    if (!m) return;
    const isOn = !!on[def.id];
    if (isOn) {
      if (m.getLayer(`atlas-${def.id}`)) m.removeLayer(`atlas-${def.id}`);
      setOn((s) => ({ ...s, [def.id]: false }));
      return;
    }
    setBusy(def.id);
    if (!atlas.current) {
      const r = await fetch("/atlas.geojson");
      atlas.current = await r.json();
      if (!m.getSource("atlas")) m.addSource("atlas", { type: "geojson", data: atlas.current as never });
    }
    if (!m.getLayer(`atlas-${def.id}`)) {
      m.addLayer(def.kind === "line"
        ? { id: `atlas-${def.id}`, type: "line", source: "atlas",
            filter: ["==", ["get", "category"], def.id],
            paint: { "line-color": def.colour, "line-width": 1.4, "line-opacity": .85 } }
        : { id: `atlas-${def.id}`, type: "circle", source: "atlas",
            filter: ["==", ["get", "category"], def.id],
            paint: { "circle-color": def.colour, "circle-radius": 2.4, "circle-opacity": .8 } },
        "corridor-halo");
    }
    setOn((s) => ({ ...s, [def.id]: true }));
    setBusy(null);
  }

  async function toggleCandidates() {
    const m = map.current;
    if (!m) return;
    if (cands) {
      if (m.getLayer("cand-c")) m.removeLayer("cand-c");
      if (m.getLayer("cand-l")) m.removeLayer("cand-l");
      setCands(false);
      return;
    }
    setBusy("cand");
    if (!m.getSource("cand")) {
      const r = await fetch("/junction_candidates.geojson");
      m.addSource("cand", { type: "geojson", data: await r.json() });
    }
    if (!m.getLayer("cand-c")) {
      m.addLayer({ id: "cand-c", type: "circle", source: "cand",
        paint: { "circle-radius": ["interpolate", ["linear"], ["get", "signal_heads"], 1, 3, 14, 9],
                 "circle-color": "#82600F", "circle-opacity": .55,
                 "circle-stroke-width": 1, "circle-stroke-color": "#fff" } }, "corridor-halo");
      m.addLayer({ id: "cand-l", type: "symbol", source: "cand",
        layout: { "text-field": ["get", "cluster"], "text-size": 9,
                  "text-offset": [0, 1.2], "text-allow-overlap": false },
        paint: { "text-color": "#5C6663", "text-halo-color": "#fff", "text-halo-width": 1 } });
    }
    setCands(true);
    setBusy(null);
  }

  return (
    <div className="card">
      <header>
        <h3>The six junctions, and what is around them</h3>
        <span className="tag">New Sanganer Road</span>
        <span className="tag">marker size = vehicles/day</span>
      </header>
      <div className="body" style={{ padding: 0 }}>
        <div ref={box} style={{ width: "100%", height: 480 }} />
      </div>
      <div style={{ padding: ".85rem 1.15rem", borderTop: "1px solid var(--rule)",
                    display: "flex", flexWrap: "wrap", gap: ".4rem", alignItems: "center" }}>
        <span style={{ fontSize: ".68rem", letterSpacing: ".1em", textTransform: "uppercase",
                       color: "var(--muted)", marginRight: ".3rem" }}>Layers</span>
        {ATLAS_LAYERS.map((d) => (
          <button key={d.id} className="lyr" aria-pressed={!!on[d.id]}
                  onClick={() => toggleLayer(d)} disabled={busy === d.id}>
            <i style={{ background: d.colour }} />
            {busy === d.id ? "loading" : d.label}
          </button>
        ))}
        <button className="lyr" aria-pressed={cands} onClick={toggleCandidates}
                disabled={busy === "cand"}>
          <i style={{ background: "#82600F" }} />
          {busy === "cand" ? "loading" : "All 39 signal clusters"}
        </button>
      </div>
      <div style={{ padding: ".8rem 1.15rem", borderTop: "1px solid var(--rule)",
                    fontSize: ".76rem", color: "var(--muted)" }}>
        <span style={{ color: "var(--accent)", fontWeight: 600 }}>Solid</span> — the
        survey&rsquo;s own arm name matches a junction JDA names in its signal-free scheme.{" "}
        <span style={{ color: "var(--defect)", fontWeight: 600 }}>Dashed</span> — placed by
        position in that sequence, not confirmed. Switch on <em>All 39 signal clusters</em>{" "}
        to see every candidate considered and judge the choice yourself. Constraint layers
        are read directly from the JDA survey drawing.
      </div>
    </div>
  );
}
