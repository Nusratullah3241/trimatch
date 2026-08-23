import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStats, listMatches, money } from "../api/client";
import type { MatchRun, Stats } from "../types";

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="card p-5">
      <div className="eyebrow">{label}</div>
      <div className="figure text-2xl mt-2">{value}</div>
      {note && <div className="text-xs text-muted mt-1">{note}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<MatchRun[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getStats(), listMatches()])
      .then(([s, r]) => {
        setStats(s);
        setRuns(r);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-breach font-medium">Cannot reach the API</div>
        <p className="text-sm text-muted mt-2">
          Start the backend with uvicorn app.main:app --reload --port 8000, then reload this page.
        </p>
      </div>
    );
  }

  if (!stats) return <div className="text-muted text-sm">Loading...</div>;

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile
          label="Documents read"
          value={String(stats.total_documents)}
          note={`${stats.total_match_runs} matches run`}
        />
        <Tile
          label="Cleared without review"
          value={`${stats.auto_approval_rate}%`}
          note={`${stats.auto_approved} of ${stats.total_match_runs}`}
        />
        <Tile
          label="Variance caught"
          value={money(stats.total_variance_caught)}
          note="PKR, across all runs"
        />
        <Tile
          label="Time saved"
          value={`${stats.estimated_minutes_saved} min`}
          note={`vs ${stats.avg_processing_ms} ms per run`}
        />
      </div>

      <section>
        <h2 className="eyebrow mb-3">Recent runs</h2>

        {runs.length === 0 ? (
          <div className="card p-8 text-center">
            <p className="text-sm text-muted">
              Nothing processed yet. Drop a PO, GRN and invoice into the inbox folder, or start one here.
            </p>
            <Link to="/new" className="btn-primary inline-block mt-4">Start a match</Link>
          </div>
        ) : (
          <div className="card divide-y divide-rule">
            {runs.map((r) => (
              <Link
                key={r.id}
                to={`/match/${r.id}`}
                className="flex items-center gap-6 px-5 py-4 hover:bg-rule/20"
              >
                <span className="figure text-sm text-muted w-12">#{r.id}</span>
                <span
                  className={`text-xs px-2 py-1 border ${
                    r.status === "MATCHED"
                      ? "text-matched border-matched/40 bg-matched/5"
                      : "text-breach border-breach/40 bg-breach/5"
                  }`}
                >
                  {r.status === "MATCHED" ? "Cleared" : "Needs review"}
                </span>
                <span className="text-sm text-muted flex-1">
                  {r.exceptions.length === 0
                    ? "No discrepancies"
                    : `${r.exceptions.length} discrepanc${r.exceptions.length === 1 ? "y" : "ies"}`}
                </span>
                <span className="figure text-sm">
                  {r.total_variance ? money(r.total_variance) : "-"}
                </span>
                <span className="figure text-xs text-muted w-16 text-right">
                  {r.processing_ms} ms
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
