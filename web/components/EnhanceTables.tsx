"use client";
import { useEffect } from "react";

/**
 * Progressive enhancement for the static findings tables.
 *
 * Eleven of the fourteen tables on this page were rendered server-side and left inert:
 * no sorting, no row selection, no way to pull one junction out of a wall of numbers.
 * On a phone, in a meeting, that is a screenshot rather than a tool.
 *
 * WHY A DOM ENHANCER AND NOT ELEVEN COMPONENT REWRITES. These tables are built inline in
 * a server component, each with a different column shape. Rewriting them all as one
 * generic <DataTable> would mean touching every call site and inventing a schema that
 * fits all of them. This attaches to what is already there, so the markup, the numbers
 * and their provenance stay exactly as the pipeline emitted them.
 *
 * It is safe here specifically because these subtrees never re-render: the page is
 * statically prerendered and the tables hold no React state. Anything already
 * interactive - the LOS grid, the flow raster, the conflict rows - declares
 * role="grid" or .grow and is skipped, so the two systems never fight.
 */
const NUM = /^[-+₹]?[\d,]+(\.\d+)?%?$/;

function cellValue(td: HTMLElement): number | string {
  const raw = (td.textContent ?? "").trim();
  if (NUM.test(raw)) {
    const n = parseFloat(raw.replace(/[,₹%+]/g, ""));
    if (!Number.isNaN(n)) return n;
  }
  return raw.toLowerCase();
}

export default function EnhanceTables() {
  useEffect(() => {
    const cleanups: (() => void)[] = [];

    function enhance() {
    const tables = [...document.querySelectorAll<HTMLTableElement>(".card table")]
      .filter((t) => t.getAttribute("role") !== "grid"
                  && !t.querySelector("tr.grow")
                  && !t.dataset.enhanced);

    for (const table of tables) {
      const head = table.tHead?.rows[0];
      const body = table.tBodies[0];
      if (!head || !body || body.rows.length < 2) continue;
      table.dataset.enhanced = "1";
      table.classList.add("enh");

      // --- sortable headers ------------------------------------------------
      const dirs: (1 | -1)[] = [...head.cells].map(() => 1);
      [...head.cells].forEach((th, col) => {
        th.classList.add("enh-th");
        th.tabIndex = 0;
        th.setAttribute("role", "columnheader");
        th.setAttribute("aria-sort", "none");
        const sort = () => {
          const rows = [...body.rows];
          const dir = dirs[col];
          rows.sort((a, b) => {
            const x = cellValue(a.cells[col] as HTMLElement);
            const y = cellValue(b.cells[col] as HTMLElement);
            if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
            return String(x).localeCompare(String(y)) * dir;
          });
          rows.forEach((r) => body.appendChild(r));
          [...head.cells].forEach((o, i) => o.setAttribute(
            "aria-sort", i === col ? (dir === 1 ? "ascending" : "descending") : "none"));
          dirs[col] = (dir === 1 ? -1 : 1) as 1 | -1;
        };
        const onKey = (e: KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); }
        };
        th.addEventListener("click", sort);
        th.addEventListener("keydown", onKey);
        cleanups.push(() => {
          th.removeEventListener("click", sort);
          th.removeEventListener("keydown", onKey);
        });
      });

      // --- selectable rows -------------------------------------------------
      // One row at a time, so a reader can hold a junction while reading the prose
      // underneath. Escape clears, which matters when the selection is off-screen.
      const pick = (tr: HTMLTableRowElement) => {
        const on = tr.getAttribute("aria-selected") === "true";
        [...body.rows].forEach((r) => r.setAttribute("aria-selected", "false"));
        tr.setAttribute("aria-selected", on ? "false" : "true");
      };
      [...body.rows].forEach((tr) => {
        tr.classList.add("enh-row");
        tr.tabIndex = 0;
        tr.setAttribute("aria-selected", "false");
        const onClick = () => pick(tr);
        const onKey = (e: KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(tr); }
          if (e.key === "Escape") {
            [...body.rows].forEach((r) => r.setAttribute("aria-selected", "false"));
          }
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            const rows = [...body.rows];
            const i = rows.indexOf(tr);
            const n = rows[Math.min(rows.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
            n?.focus();
          }
        };
        tr.addEventListener("click", onClick);
        tr.addEventListener("keydown", onKey);
        cleanups.push(() => {
          tr.removeEventListener("click", onClick);
          tr.removeEventListener("keydown", onKey);
        });
      });

      // tell the reader it does something; a control nobody knows about is not a control
      const cap = table.querySelector("caption");
      const hint = document.createElement("span");
      hint.className = "enh-hint";
      hint.textContent = " Click a column to sort, a row to hold it.";
      if (cap) cap.appendChild(hint);
    }
    }

    // The heavy sections - LOS, cumulative queue, flow raster, continuity - are fetched
    // after mount to keep corridor.json small, so their tables did not exist when this
    // effect first ran and were left inert. Watch for them rather than assuming the page
    // is finished when React says it is.
    enhance();
    const mo = new MutationObserver(() => enhance());
    mo.observe(document.body, { childList: true, subtree: true });
    return () => {
      mo.disconnect();
      cleanups.forEach((f) => f());
    };
  }, []);

  return null;
}
