"use client";
import { useId, useState } from "react";

/**
 * The numbers behind a prose finding, on demand.
 *
 * Sixteen of the thirty-four cards on this page were prose and nothing else: a claim,
 * stated well, with no way to reach what it rests on. That is the shape of every traffic
 * report this audit exists to object to — a conclusion a reader must take on trust.
 *
 * Collapsed by default, because the claim is the point and the arithmetic is the backing.
 * A real <button> with aria-expanded, so it works on a phone and under a screen reader,
 * and the panel stays in the DOM so browser find-in-page still reaches it.
 */
export type Row = { k: string; v: string; note?: string; tone?: "bad" | "ok" };

export default function Evidence({
  label = "How this number was reached", rows, source,
}: { label?: string; rows: Row[]; source?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className={"evid" + (open ? " open" : "")}>
      <button className="evid-toggle" aria-expanded={open} aria-controls={id}
              onClick={() => setOpen((o) => !o)}>
        <span className="evid-caret" aria-hidden>{open ? "−" : "+"}</span>
        {label}
      </button>
      <div className="evid-body" id={id} hidden={!open}>
        <dl className="evid-rows">
          {rows.map((r) => (
            <div key={r.k}>
              <dt>{r.k}</dt>
              <dd className={r.tone ?? ""}>
                {r.v}
                {r.note && <em>{r.note}</em>}
              </dd>
            </div>
          ))}
        </dl>
        {source && <p className="evid-src">{source}</p>}
      </div>
    </div>
  );
}
