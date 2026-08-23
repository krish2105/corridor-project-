"use client";

/**
 * The readout that replaced the native `title` tooltip on every data grid here.
 *
 * It is deliberately a fixed panel under the grid rather than a floating tooltip: it
 * never covers the data it describes, it survives a tap on a phone, and it can hold a
 * pinned value while the reader looks away and back.
 *
 * It always shows something. An empty readout that appears on hover teaches the reader
 * nothing about what the grid contains, so when nothing is selected it shows the cell
 * worth looking at first — normally the worst one.
 */
export type Field = { k: string; v: string; tone?: "bad" | "ok" };

export default function Readout({
  title, fields, pinned, onClear, hint,
}: {
  title: string; fields: Field[]; pinned: boolean; onClear: () => void; hint: string;
}) {
  return (
    <div className={"readout" + (pinned ? " pinned" : "")} aria-live="polite">
      <div className="readout-head">
        <span className="readout-title">{title}</span>
        {pinned
          ? <button className="readout-clear" onClick={onClear}>pinned &middot; clear</button>
          : <span className="readout-hint">{hint}</span>}
      </div>
      <dl className="readout-fields">
        {fields.map((f) => (
          <div key={f.k}>
            <dt>{f.k}</dt>
            <dd className={f.tone ?? ""}>{f.v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
