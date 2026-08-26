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
 * Marker fill encodes how each position was established, and every one is now solid:
 * JDA supplied the six positions and the centreline as a KML. The dashed state is kept
 * rather than deleted because it is what the map showed while the positions were our own
 * inference, and that inference was wrong - our picks sat 269 to 950 m away, on a parallel
 * road. If a position is ever placed by us again, the map has to say so.
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
    // Repaint the basemap when the theme changes.
    //
    // The basemap colours are read from CSS custom properties, which only resolve once.
    // Without this the map keeps its light palette after a switch to dark and renders as
    // a bright grey rectangle on a near-black page. The old raster basemap had the same
    // problem and no way to fix it; owning the geometry is what makes this possible.
    //
    // Declared here rather than inside the fetch so the cleanup can remove the same
    // function reference it registered — passing a fresh arrow to removeEventListener
    // removes nothing and leaks a listener per mount.
    const repaint = () => {
      const m2 = map.current;
      if (!m2) return;
      const cs = getComputedStyle(document.documentElement);
      const get = (n: string, f: string) => cs.getPropertyValue(n).trim() || f;
      const sunk = get("--sunk", "#E9EBE6");
      const hard = get("--rule-hard", "#B4BBB4");
      const soft = get("--rule", "#D5D9D4");
      try {
        if (m2.getLayer("ground")) m2.setPaintProperty("ground", "background-color", sunk);
        if (m2.getLayer("base-structures"))
          m2.setPaintProperty("base-structures", "line-color", soft);
        if (m2.getLayer("base-carriageway"))
          m2.setPaintProperty("base-carriageway", "line-color", hard);
        if (m2.getLayer("base-median"))
          m2.setPaintProperty("base-median", "line-color", hard);
      } catch { /* map torn down mid-observation */ }
    };
    const themeWatch = new MutationObserver(repaint);
    themeWatch.observe(document.documentElement, {
      attributes: true, attributeFilter: ["data-theme"],
    });
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", repaint);

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
      // No position is confirmed, so no marker claims to be. The solid/dashed
      // split encoded a NAME match and was read as a POSITION match.
      const firm = j.location_confidence === "JDA KML";
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
      // JDA's OWN centreline, fetched as published geometry.
      //
      // We drew one before by joining our six pins, and it was wrong: it traced a
      // parallel road, 6,517 m against the 4,625 m JDA actually supplied. That line was
      // removed rather than corrected, because a line joining our own guesses asserts a
      // road we had inferred. This one is theirs, from the KML, so it can be drawn as
      // what it is.
      fetch("/centreline.geojson").then((r) => r.json()).then((data) => {
        if (!m.getSource("centreline")) {
          m.addSource("centreline", { type: "geojson", data });
          m.addLayer({ id: "centreline-halo", type: "line", source: "centreline",
            paint: { "line-color": "#FAFBF8", "line-width": 7, "line-opacity": .85 } });
          m.addLayer({ id: "centreline-line", type: "line", source: "centreline",
            paint: { "line-color": "#1B3A6B", "line-width": 2.6 } });
        }
      }).catch(() => { /* the map is still useful without it */ });

      //
      // A line joining the six junctions asserts which physical road they sit on. That
      // was our inference, JDA's reviewer disputed it, and drawing it is the same claim
      // as naming it - louder, if anything, because a line on a map reads as surveyed
      // fact rather than as a guess. The name was withdrawn from the text; leaving the
      // line would have withdrawn it in words and kept it in the picture.
      //
      // What stays is what the survey actually supports: six junction positions, and the
      // JDA drawing underneath them. A reader can see where the junctions are without
      // being told which road connects them. Restore this when JDA confirms the
      // alignment, from their centreline rather than by joining our own pins.

      // Surveyed basemap. Fetched after the corridor so the junctions paint first and
      // the map is useful before 408 KB of context has arrived.
      fetch("/basemap.geojson").then((r) => r.json()).then((base) => {
        if (!map.current || m.getSource("base")) return;
        m.addSource("base", { type: "geojson", data: base });
        const rule = tok("--rule-hard", "#B4BBB4");
        const faint = tok("--rule", "#D5D9D4");
        m.addLayer({ id: "base-structures", type: "line", source: "base",
          filter: ["==", ["get", "category"], "structures"],
          paint: { "line-color": faint, "line-width": .6, "line-opacity": .9 } });
        m.addLayer({ id: "base-carriageway", type: "line", source: "base",
          filter: ["==", ["get", "category"], "carriageway"],
          paint: { "line-color": rule, "line-width": 1.1 } });
        m.addLayer({ id: "base-median", type: "line", source: "base",
          filter: ["==", ["get", "category"], "median"],
          paint: { "line-color": rule, "line-width": .8, "line-dasharray": [3, 2] } });
        // The observer only fires on CHANGE, and the ground layer is created in the
        // constructor before any of this exists. Without one call here, a first load in
        // dark mode paints a light ground under dark linework.
        repaint();
      }).catch(() => { /* basemap is context; the junctions and corridor stand alone */ });

      m.fitBounds(bounds, { padding: 70, maxZoom: 14, duration: 0 });
    };
    if (m.isStyleLoaded()) build();
    else m.once("load", build);

    return () => {
      themeWatch.disconnect();
      mq.removeEventListener("change", repaint);
      m.remove();
      map.current = null;
    };
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
            paint: { "circle-color": def.colour, "circle-radius": 2.4, "circle-opacity": .8 } });
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
                 "circle-stroke-width": 1, "circle-stroke-color": "#fff" } });
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
        {/* The road name was our inference and it was challenged, so it is not
            asserted here. What the survey states is the two end points, and
            every junction carries them. */}
        <span className="tag">Mansarover Metro &ndash; Sanganer Stadium</span>
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
        <span style={{ color: "var(--accent)", fontWeight: 600 }}>
          Positions and centreline supplied by JDA</span>{" "}
        as a KML, and drawn as received. We had picked these ourselves before, from
        signal clusters in the CAD, and landed on a parallel road: our points sat 269 to
        950 m from where they belong, and the line we drew was 6,517 m against the actual
        4,625 m.{" "}
        <strong>Checked on receipt, not taken on trust:</strong> every supplied point
        falls 2 to 10 m off the supplied centreline, their order along it matches the
        placemark numbering, and the CAD drawing covers all fourteen vertices. Switch on{" "}
        <em>All 39 signal clusters</em> to see the candidates we were choosing between.
        The constraint layers are read directly from the JDA drawing.
      </div>
    </div>
  );
}
