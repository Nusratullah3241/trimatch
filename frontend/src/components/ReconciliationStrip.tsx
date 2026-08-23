import type { Document, LineItem } from "../types";
import { money } from "../api/client";

interface Props {
  po: Document;
  grn: Document;
  invoice: Document;
}

interface Row {
  label: string;
  ordered: LineItem | null;
  received: LineItem | null;
  invoiced: LineItem | null;
}

function similar(a: string, b: string): boolean {
  const norm = (s: string) =>
    s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  const A = new Set(norm(a));
  const B = norm(b);
  if (!A.size || !B.length) return false;
  const hits = B.filter((w) => A.has(w)).length;
  return hits / Math.max(A.size, B.length) > 0.5;
}

function buildRows(po: Document, grn: Document, invoice: Document): Row[] {
  const rows: Row[] = [];
  const usedGrn = new Set<number>();
  const usedInv = new Set<number>();

  const find = (desc: string, lines: LineItem[], used: Set<number>) => {
    const idx = lines.findIndex((l, i) => !used.has(i) && similar(desc, l.description));
    if (idx === -1) return null;
    used.add(idx);
    return lines[idx];
  };

  for (const line of po.lines) {
    rows.push({
      label: line.description,
      ordered: line,
      received: find(line.description, grn.lines, usedGrn),
      invoiced: find(line.description, invoice.lines, usedInv),
    });
  }

  invoice.lines.forEach((l, i) => {
    if (usedInv.has(i)) return;
    rows.push({ label: l.description, ordered: null, received: null, invoiced: l });
  });

  return rows;
}

function Cell({
  primary,
  secondary,
  state,
}: {
  primary: string;
  secondary?: string;
  state: "ok" | "bad" | "absent";
}) {
  const tone = state === "bad" ? "text-breach" : state === "absent" ? "text-muted" : "text-ink";
  return (
    <div className="px-4 py-3">
      <div className={`figure text-sm ${tone} ${state === "bad" ? "font-semibold" : ""}`}>
        {primary}
      </div>
      {secondary && <div className="figure text-xs text-muted mt-0.5">{secondary}</div>}
    </div>
  );
}

export default function ReconciliationStrip({ po, grn, invoice }: Props) {
  const rows = buildRows(po, grn, invoice);

  return (
    <div className="card">
      <div className="grid grid-cols-[1fr_auto_auto_auto] border-b border-rule bg-rule/25">
        <div className="px-4 py-2 eyebrow">Line item</div>
        <div className="px-4 py-2 eyebrow text-right w-40">Ordered</div>
        <div className="px-4 py-2 eyebrow text-right w-40">Received</div>
        <div className="px-4 py-2 eyebrow text-right w-44">Invoiced</div>
      </div>

      {rows.map((row, i) => {
        const priceMismatch =
          !!row.ordered &&
          !!row.invoiced &&
          Number(row.ordered.unit_price) !== Number(row.invoiced.unit_price);

        const qtyMismatch =
          !!row.invoiced && Number(row.invoiced.quantity) > Number(row.received?.quantity ?? 0);

        const unauthorized = !row.ordered && !!row.invoiced;
        const unbilled = !!row.ordered && !row.invoiced;
        const broken = priceMismatch || qtyMismatch || unauthorized || unbilled;

        return (
          <div
            key={i}
            className={`grid grid-cols-[1fr_auto_auto_auto] items-stretch border-b border-rule last:border-b-0 ${
              broken ? "bg-breach/[0.03]" : ""
            }`}
          >
            <div className="px-4 py-3 flex items-center gap-3">
              <span
                aria-hidden
                className={`h-px w-6 shrink-0 ${broken ? "bg-breach opacity-40" : "bg-matched"}`}
              />
              <span className="text-sm leading-snug">{row.label}</span>
            </div>

            <div className="w-40 text-right border-l border-rule">
              {row.ordered ? (
                <Cell
                  primary={money(row.ordered.unit_price)}
                  secondary={`${row.ordered.quantity} units`}
                  state="ok"
                />
              ) : (
                <Cell primary="not ordered" state="absent" />
              )}
            </div>

            <div className="w-40 text-right border-l border-rule">
              {row.received ? (
                <Cell
                  primary={`${row.received.quantity}`}
                  secondary="units received"
                  state={qtyMismatch ? "bad" : "ok"}
                />
              ) : (
                <Cell primary="-" state="absent" />
              )}
            </div>

            <div className="w-44 text-right border-l border-rule">
              {row.invoiced ? (
                <>
                  <Cell
                    primary={money(row.invoiced.unit_price)}
                    secondary={`${row.invoiced.quantity} units`}
                    state={priceMismatch || unauthorized ? "bad" : "ok"}
                  />
                  {priceMismatch && row.ordered && (
                    <div className="px-4 pb-3 -mt-1">
                      <span className="figure text-xs text-breach">
                        +
                        {money(
                          (Number(row.invoiced.unit_price) - Number(row.ordered.unit_price)) *
                            Number(row.invoiced.quantity)
                        )}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <Cell primary="not billed" state="absent" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
