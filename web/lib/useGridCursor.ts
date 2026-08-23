"use client";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Keyboard- and touch-capable cursor over a 2-D grid of cells.
 *
 * Every data grid on this page used to carry its readout in a native `title` attribute.
 * That was wrong three times over: a title tooltip does not fire on touch at all, and a
 * JDA officer opens this on a phone in a meeting — which is the whole stated reason the
 * dashboard exists; it is not reachable by keyboard; and it cannot be pinned, so a
 * reader cannot hold one cell while reading the number.
 *
 * So: click to pin, hover to preview, and the readout renders as real markup below the
 * grid rather than as a floating tooltip. `pinned ?? hover` means a phone (no hover)
 * still gets the full behaviour from taps alone.
 *
 * Keyboard follows the ARIA grid pattern with a ROVING TAB STOP. Making 576 cells each
 * a tab stop would bury the rest of the page behind them; instead the grid is one stop
 * and the arrow keys move inside it.
 */
export type Cursor = { r: number; c: number };
const same = (a: Cursor | null, b: Cursor | null) => !!a && !!b && a.r === b.r && a.c === b.c;

export function useGridCursor(rows: number, cols: number) {
  const [pinned, setPinned] = useState<Cursor | null>(null);
  const [hover, setHover] = useState<Cursor | null>(null);
  // where the roving tab stop sits; starts top-left so the first Tab lands somewhere sane
  const [cursor, setCursor] = useState<Cursor>({ r: 0, c: 0 });
  const ref = useRef<HTMLTableSectionElement | null>(null);

  const active = pinned ?? hover;

  const focusCell = useCallback((n: Cursor) => {
    const el = ref.current?.querySelector<HTMLElement>(`[data-r="${n.r}"][data-c="${n.c}"]`);
    el?.focus();
  }, []);

  const onKeyDown = useCallback((e: React.KeyboardEvent, at: Cursor) => {
    const D: Record<string, [number, number]> = {
      ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1],
    };
    if (e.key in D) {
      const [dr, dc] = D[e.key];
      const n = {
        r: Math.min(rows - 1, Math.max(0, at.r + dr)),
        c: Math.min(cols - 1, Math.max(0, at.c + dc)),
      };
      if (same(n, at)) return;
      e.preventDefault();
      setCursor(n); setHover(n); focusCell(n);
      return;
    }
    if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const n = { r: at.r, c: e.key === "Home" ? 0 : cols - 1 };
      setCursor(n); setHover(n); focusCell(n);
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setPinned((p) => (same(p, at) ? null : at));
      return;
    }
    if (e.key === "Escape" && pinned) { e.preventDefault(); setPinned(null); }
  }, [rows, cols, pinned, focusCell]);

  // Escape clears the pin even when focus has moved off the grid
  useEffect(() => {
    if (!pinned) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") setPinned(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [pinned]);

  /** Props for one cell. Spread onto the <td>. */
  const cellProps = (r: number, c: number) => ({
    "data-r": r, "data-c": c,
    role: "gridcell" as const,
    tabIndex: cursor.r === r && cursor.c === c ? 0 : -1,
    "aria-selected": same(pinned, { r, c }),
    onMouseEnter: () => setHover({ r, c }),
    onFocus: () => setHover({ r, c }),
    onClick: () => { setCursor({ r, c }); setPinned((p) => (same(p, { r, c }) ? null : { r, c })); },
    onKeyDown: (e: React.KeyboardEvent) => onKeyDown(e, { r, c }),
  });

  const bodyProps = { ref, onMouseLeave: () => setHover(null) };

  return { active, pinned, hover, cellProps, bodyProps, clear: () => setPinned(null), same };
}
