import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { runMatch, uploadDocument } from "../api/client";
import type { Document } from "../types";

type Slot = "PO" | "GRN" | "INVOICE";

const SLOTS: { key: Slot; title: string; hint: string }[] = [
  { key: "PO", title: "Purchase order", hint: "What was ordered" },
  { key: "GRN", title: "Goods received note", hint: "What actually arrived" },
  { key: "INVOICE", title: "Invoice", hint: "What is being charged" },
];

interface SlotState {
  status: "empty" | "reading" | "done" | "error";
  doc?: Document;
  message?: string;
}

export default function NewMatch() {
  const navigate = useNavigate();
  const [slots, setSlots] = useState<Record<Slot, SlotState>>({
    PO: { status: "empty" },
    GRN: { status: "empty" },
    INVOICE: { status: "empty" },
  });
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(slot: Slot, file: File) {
    setSlots((s) => ({ ...s, [slot]: { status: "reading" } }));
    try {
      const doc = await uploadDocument(file, slot);
      setSlots((s) => ({ ...s, [slot]: { status: "done", doc } }));
    } catch (e) {
      setSlots((s) => ({ ...s, [slot]: { status: "error", message: String(e) } }));
    }
  }

  const ready =
    slots.PO.status === "done" &&
    slots.GRN.status === "done" &&
    slots.INVOICE.status === "done";

  async function handleRun() {
    if (!ready) return;
    setRunning(true);
    setError("");
    try {
      const run = await runMatch(slots.PO.doc!.id, slots.GRN.doc!.id, slots.INVOICE.doc!.id);
      navigate(`/match/${run.id}`);
    } catch (e) {
      setError(String(e));
      setRunning(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold">Match a set by hand</h1>
        <p className="text-sm text-muted mt-1">
          Documents dropped into the inbox folder are matched automatically. Use this when you want to run one directly.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {SLOTS.map(({ key, title, hint }) => {
          const state = slots[key];
          return (
            <div key={key} className="card p-5">
              <div className="eyebrow">{title}</div>
              <div className="text-xs text-muted mt-1">{hint}</div>

              <div className="mt-4">
                {state.status === "empty" && (
                  <label className="block border border-dashed border-rule px-4 py-8 text-center cursor-pointer hover:border-ink transition-colors">
                    <span className="text-sm text-muted">Choose a PDF</span>
                    <input
                      type="file"
                      accept=".pdf"
                      className="sr-only"
                      onChange={(e) => e.target.files?.[0] && handleFile(key, e.target.files[0])}
                    />
                  </label>
                )}

                {state.status === "reading" && (
                  <div className="px-4 py-8 text-center text-sm text-muted">Reading document...</div>
                )}

                {state.status === "done" && state.doc && (
                  <div className="space-y-1">
                    <div className="figure text-sm">
                      {state.doc.document_number || state.doc.filename}
                    </div>
                    <div className="text-xs text-muted">{state.doc.vendor_name}</div>
                    <div className="text-xs text-muted">
                      {state.doc.lines.length} lines, confidence{" "}
                      <span className="figure">
                        {(state.doc.extraction_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                )}

                {state.status === "error" && (
                  <div className="text-xs text-breach">
                    Could not read that file. {state.message?.slice(0, 90)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && <div className="text-sm text-breach">{error}</div>}

      <button
        className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
        disabled={!ready || running}
        onClick={handleRun}
      >
        {running ? "Comparing..." : "Compare the three"}
      </button>
    </div>
  );
}
