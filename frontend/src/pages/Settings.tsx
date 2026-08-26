import { useEffect, useState } from "react";
import {
  getTolerances,
  resetTolerances,
  updateTolerances,
} from "../api/client";
import type { Tolerances } from "../types";

type FieldKey =
  | "price_tolerance_pct"
  | "absolute_tolerance_amount"
  | "quantity_tolerance_pct";

interface Field {
  key: FieldKey;
  label: string;
  suffix: string;
  min: number;
  max: number;
  step: number;
  help: string;
}

const FIELDS: Field[] = [
  {
    key: "price_tolerance_pct",
    label: "Price drift",
    suffix: "%",
    min: 0,
    max: 50,
    step: 0.1,
    help: "An invoiced rate above the ordered rate by more than this is flagged. Capped at 50% - a higher value would effectively switch the price check off.",
  },
  {
    key: "absolute_tolerance_amount",
    label: "Minimum amount",
    suffix: "PKR",
    min: 0,
    max: 100000,
    step: 100,
    help: "Drifts below this figure are ignored even when the percentage looks large. A 5% rise on a 100-rupee item is 5 rupees.",
  },
  {
    key: "quantity_tolerance_pct",
    label: "Quantity drift",
    suffix: "%",
    min: 0,
    max: 20,
    step: 0.5,
    help: "Normally zero. Being billed for goods that did not arrive is not a rounding error.",
  },
];

type Draft = Record<FieldKey, number>;

function draftFrom(t: Tolerances): Draft {
  return {
    price_tolerance_pct: t.price_tolerance_pct,
    absolute_tolerance_amount: t.absolute_tolerance_amount,
    quantity_tolerance_pct: t.quantity_tolerance_pct,
  };
}

export default function Settings() {
  const [saved, setSaved] = useState<Tolerances | null>(null);
  const [draft, setDraft] = useState<Draft>({
    price_tolerance_pct: 0,
    absolute_tolerance_amount: 0,
    quantity_tolerance_pct: 0,
  });
  const [status, setStatus] = useState<"idle" | "saving" | "done">("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    getTolerances()
      .then((t) => {
        setSaved(t);
        setDraft(draftFrom(t));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const dirty =
    saved !== null &&
    FIELDS.some((f) => Number(draft[f.key]) !== Number(saved[f.key]));

  async function handleSave() {
    setStatus("saving");
    setError("");
    try {
      const updated = await updateTolerances({
        price_tolerance_pct: Number(draft.price_tolerance_pct),
        absolute_tolerance_amount: Number(draft.absolute_tolerance_amount),
        quantity_tolerance_pct: Number(draft.quantity_tolerance_pct),
      });
      setSaved(updated);
      setDraft(draftFrom(updated));
      setStatus("done");
      setTimeout(() => setStatus("idle"), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("idle");
    }
  }

  async function handleReset() {
    setError("");
    try {
      const t = await resetTolerances();
      setSaved(t);
      setDraft(draftFrom(t));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function discard() {
    if (saved) setDraft(draftFrom(saved));
  }

  function setField(key: FieldKey, value: number) {
    setDraft((d) => ({ ...d, [key]: Number.isNaN(value) ? 0 : value }));
  }

  if (error && !saved) {
    return <div className="text-sm text-breach">{error}</div>;
  }

  if (!saved) return <div className="text-muted text-sm">Loading...</div>;

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold">Tolerances</h1>
        <p className="text-sm text-muted mt-1">
          How far a figure can drift before someone needs to look at it.
        </p>
      </div>

      <div className="card divide-y divide-rule">
        {FIELDS.map((f) => (
          <div key={f.key} className="p-5">
            <div className="flex items-baseline justify-between gap-6">
              <div className="text-sm font-medium">{f.label}</div>
              <div className="flex items-baseline gap-2">
                <input
                  type="number"
                  className="figure text-lg w-28 text-right border border-rule px-2 py-1 focus:outline-none focus:border-ink bg-paper"
                  value={draft[f.key]}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  onChange={(e) => setField(f.key, e.target.valueAsNumber)}
                />
                <span className="text-sm text-muted w-10">{f.suffix}</span>
              </div>
            </div>

            <input
              type="range"
              className="w-full mt-3 accent-ink"
              value={draft[f.key]}
              min={f.min}
              max={f.max}
              step={f.step}
              onChange={(e) => setField(f.key, e.target.valueAsNumber)}
            />

            <p className="text-xs text-muted mt-2 leading-relaxed">{f.help}</p>
          </div>
        ))}
      </div>

      {error && <div className="text-sm text-breach">{error}</div>}

      <div className="flex items-center gap-3">
        <button
          className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={!dirty || status === "saving"}
          onClick={handleSave}
        >
          {status === "saving" ? "Saving..." : "Save changes"}
        </button>

        {dirty && (
          <button className="btn-ghost" onClick={discard}>
            Discard
          </button>
        )}

        {status === "done" && <span className="text-sm text-matched">Saved.</span>}

        <button
          className="text-xs text-muted underline ml-auto"
          onClick={handleReset}
        >
          reset to defaults
        </button>
      </div>

      <div className="card p-5 bg-rule/20">
        <div className="eyebrow">What changing these does</div>
        <p className="text-sm mt-2 leading-relaxed">
          New thresholds apply to the next match only. Past runs are not
          re-evaluated - each one records the tolerances it was judged under, so
          a decision made last month stays explainable after a policy change.
        </p>
        <p className="text-sm mt-3 leading-relaxed">
          Both the percentage and the minimum amount must be breached together
          before a price exception is raised. A large percentage on a trivial
          amount is not worth a reviewer's attention.
        </p>
        <p className="text-xs text-muted mt-3">
          Last changed{" "}
          <span className="figure">
            {new Date(saved.updated_at).toLocaleString()}
          </span>{" "}
          by {saved.updated_by}.
        </p>
      </div>
    </div>
  );
}