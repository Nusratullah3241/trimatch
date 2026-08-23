import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getDocument, getMatch, money, resolveException } from "../api/client";
import type { Document, MatchRun } from "../types";
import ReconciliationStrip from "../components/ReconciliationStrip";

const ACTIONS = [
  { key: "APPROVED", label: "Approve anyway" },
  { key: "REJECTED", label: "Reject" },
  { key: "CREDIT_NOTE_REQUESTED", label: "Request credit note" },
];

const TYPE_LABEL: Record<string, string> = {
  PRICE_VARIANCE: "Price above the agreed rate",
  QUANTITY_VARIANCE: "Billed for more than arrived",
  UNAUTHORIZED_ITEM: "Item was never ordered",
  MISSING_ON_INVOICE: "Received but not billed",
  DUPLICATE_INVOICE: "This invoice was already processed",
};

export default function MatchDetail() {
  const { id } = useParams();
  const [run, setRun] = useState<MatchRun | null>(null);
  const [docs, setDocs] = useState<{ po?: Document; grn?: Document; invoice?: Document }>({});
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getMatch(Number(id))
      .then(async (r) => {
        setRun(r);
        const [po, grn, invoice] = await Promise.all([
          getDocument(r.po_doc_id),
          getDocument(r.grn_doc_id),
          getDocument(r.invoice_doc_id),
        ]);
        setDocs({ po, grn, invoice });
      })
      .catch((e) => setError(String(e)));
  }, [id]);

  async function handleResolve(excId: number, resolution: string) {
    await resolveException(excId, resolution);
    const fresh = await getMatch(Number(id));
    setRun(fresh);
  }

  if (error) return <div className="text-sm text-breach">{error}</div>;
  if (!run) return <div className="text-muted text-sm">Loading...</div>;

  const cleared = run.status === "MATCHED";

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="eyebrow hover:text-ink">Back to ledger</Link>
          <h1 className="text-xl font-semibold mt-2">
            Run <span className="figure">#{run.id}</span>
          </h1>
          <p className="text-sm text-muted mt-1">
            {docs.invoice?.vendor_name}, processed in{" "}
            <span className="figure">{run.processing_ms} ms</span>
          </p>
        </div>

        <div
          className={`px-4 py-2 border text-sm ${
            cleared
              ? "text-matched border-matched/40 bg-matched/5"
              : "text-breach border-breach/40 bg-breach/5"
          }`}
        >
          {cleared ? "Cleared for payment" : `${run.exceptions.length} to review`}
          {!cleared && (
            <div className="figure text-lg mt-0.5">{money(run.total_variance)}</div>
          )}
        </div>
      </div>

      {docs.po && docs.grn && docs.invoice && (
        <section>
          <h2 className="eyebrow mb-3">Line by line</h2>
          <ReconciliationStrip po={docs.po} grn={docs.grn} invoice={docs.invoice} />
        </section>
      )}

      {run.exceptions.length > 0 && (
        <section>
          <h2 className="eyebrow mb-3">What needs a decision</h2>
          <div className="space-y-3">
            {run.exceptions.map((exc) => (
              <div key={exc.id} className="card p-5">
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs px-2 py-0.5 border ${
                      exc.severity === "HIGH"
                        ? "text-breach border-breach/40"
                        : exc.severity === "MEDIUM"
                        ? "text-variance border-variance/40"
                        : "text-muted border-rule"
                    }`}
                  >
                    {exc.severity}
                  </span>
                  <span className="text-sm font-medium">
                    {TYPE_LABEL[exc.exception_type] ?? exc.exception_type}
                  </span>
                </div>

                <div className="text-sm mt-2">{exc.line_description}</div>

                <div className="flex gap-8 mt-3">
                  <div>
                    <div className="eyebrow">Expected</div>
                    <div className="figure text-sm">{exc.expected_value}</div>
                  </div>
                  <div>
                    <div className="eyebrow">Actual</div>
                    <div className="figure text-sm text-breach">{exc.actual_value}</div>
                  </div>
                  <div>
                    <div className="eyebrow">At stake</div>
                    <div className="figure text-sm">
                      {money(exc.variance_amount)}
                      <span className="text-muted ml-1">({exc.variance_pct}%)</span>
                    </div>
                  </div>
                </div>

                {exc.ai_explanation && (
                  <p className="text-sm text-muted mt-3 border-l-2 border-rule pl-3">
                    {exc.ai_explanation}
                  </p>
                )}

                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-rule">
                  {exc.resolution === "PENDING" ? (
                    ACTIONS.map((a) => (
                      <button
                        key={a.key}
                        className="btn-ghost text-xs"
                        onClick={() => handleResolve(exc.id, a.key)}
                      >
                        {a.label}
                      </button>
                    ))
                  ) : (
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-matched">
                        {ACTIONS.find((a) => a.key === exc.resolution)?.label ?? exc.resolution}
                      </span>
                      <button
                        className="text-xs text-muted underline"
                        onClick={() => handleResolve(exc.id, "PENDING")}
                      >
                        undo
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
