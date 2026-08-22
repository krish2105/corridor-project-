"use client";
import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Junction } from "@/lib/types";

/**
 * The six junctions on their real positions. Marker fill encodes how the location
 * was established: a name match against the JDA scheme is firm, the rest are placed
 * by position in the sequence and are labelled as inferred rather than presented as
 * equally certain.
 */
export default function CorridorMap({ junctions }: { junctions: Junction[] }) {
  const box = useRef<HTMLDivElement>(null);

  // No "already created" guard here. React StrictMode mounts effects twice in dev;
  // a guard lets the first mount's cleanup destroy the map while blocking the second
  // from rebuilding it, and you get an empty container. Create, and let cleanup remove.
  useEffect(() => {
    if (!box.current) return;

    const map = new maplibregl.Map({
      container: box.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [75.7635, 26.856],
      zoom: 12.6,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }));

    const ordered = [...junctions].sort((a, b) => b.lat - a.lat);

    const bounds = new maplibregl.LngLatBounds();
    ordered.forEach((j) => {
      bounds.extend([j.lon, j.lat]);
      const firm = j.location_confidence === "name match";
      const el = document.createElement("div");
      const d = 16 + Math.round((j.daily_veh / 160000) * 18);
      el.style.cssText =
        `width:${d}px;height:${d}px;border-radius:50%;cursor:pointer;` +
        `background:${firm ? "#1B3A6B" : "#9E2B25"};` +
        `border:2px ${firm ? "solid" : "dashed"} #fff;` +
        `box-shadow:0 1px 5px rgba(0,0,0,.45);display:flex;align-items:center;` +
        `justify-content:center;color:#fff;font:600 9px/1 "IBM Plex Mono",monospace`;
      el.textContent = j.code.replace("TMC-", "");
      new maplibregl.Marker({ element: el })
        .setLngLat([j.lon, j.lat])
        .setPopup(new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
          `<div style="font:12px/1.45 'IBM Plex Mono',monospace">
             <b>${j.code}</b> &middot; ${j.jda_name}<br>
             ${j.arms[1]} / ${j.arms[3]}<br>
             ${j.daily_veh.toLocaleString("en-US")} veh/day &middot; peak ${j.peak_start}<br>
             through ${j.through_pct}%<br>
             <span style="color:#5C6663">${j.lat.toFixed(6)}, ${j.lon.toFixed(6)}<br>
             location: ${j.location_confidence}</span>
           </div>`))
        .addTo(map);
    });
    map.fitBounds(bounds, { padding: 70, maxZoom: 14, duration: 0 });

    map.on("load", () => {
      // corridor line through the six, north to south
      map.addSource("corridor", {
        type: "geojson",
        data: {
          type: "Feature", properties: {},
          geometry: { type: "LineString", coordinates: ordered.map((j) => [j.lon, j.lat]) },
        },
      });
      map.addLayer({
        id: "corridor-halo", type: "line", source: "corridor",
        paint: { "line-color": "#FAFBF8", "line-width": 7, "line-opacity": .85 },
      });
      map.addLayer({
        id: "corridor-line", type: "line", source: "corridor",
        paint: { "line-color": "#1B3A6B", "line-width": 2.6 },
      });

    });

    return () => map.remove();
  }, [junctions]);

  return (
    <div className="card">
      <header>
        <h3>The six junctions</h3>
        <span className="tag">New Sanganer Road</span>
        <span className="tag">marker size = vehicles/day</span>
      </header>
      <div className="body" style={{ padding: 0 }}>
        <div ref={box} style={{ width: "100%", height: 460 }} />
      </div>
      <div style={{ padding: ".8rem 1.15rem", borderTop: "1px solid var(--rule)",
                    fontSize: ".76rem", color: "var(--muted)" }}>
        <span style={{ color: "var(--accent)", fontWeight: 600 }}>Solid</span> — the
        survey&rsquo;s own arm name matches the junction JDA names in its signal-free
        scheme. <span style={{ color: "var(--defect)", fontWeight: 600 }}>Dashed</span> —
        placed by position in that sequence, not confirmed. The survey contractor&rsquo;s
        location schedule would settle the dashed ones.
      </div>
    </div>
  );
}
