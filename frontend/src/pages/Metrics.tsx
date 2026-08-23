import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getStats, money } from "../api/client";
import type { Stats } from "../types";

const TYPE_LABEL: Record<string, string> = {
  PRICE_VARIANCE: "Price above rate",
  QUANTITY_VARIANCE: "Over-billed qty",
  UNAUTHORIZED_ITEM: "Never ordered",
  MISSING_ON_INVOICE: "Not billed",
  DUPLICATE_INVOICE: "Duplicate",
};

const COLORS = ["#A32E27", "#B87503", "#2F6F4E", "#6B7280", "#14181F"];

export default function Metrics() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(null));
  }, []);

  if (!stats) return <div className="text-muted text-sm">Loading...</div>;

  const data = Object.entries(stats.exceptions_by_type).map(([k, v]) => ({
    name: TYPE_LABEL[k] ?? k,
    count: v,
  }));

  const manualMinutes = stats.total_match_runs * 12;
  const systemMinutes = (stats.total_match_runs * stats.avg_processing_ms) / 60000;

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-xl font-semibold">Where the time and money went</h1>
        <p className="text-sm text-muted mt-1">Figures update as more sets are processed.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-5">
          <div className="eyebrow">Manual estimate</div>
          <div className="figure text-2xl mt-2">{manualMinutes.toFixed(0)} min</div>
          <div className="text-xs text-muted mt-1">at 12 min per set</div>
        </div>
        <div className="card p-5">
          <div className="eyebrow">This system</div>
          <div className="figure text-2xl mt-2">{systemMinutes.toFixed(1)} min</div>
          <div className="text-xs text-muted mt-1">{stats.avg_processing_ms} ms average</div>
        </div>
        <div className="card p-5">
          <div className="eyebrow">Still awaiting a decision</div>
          <div className="figure text-2xl mt-2">{stats.pending_review}</div>
          <div className="text-xs text-muted mt-1">of {stats.total_match_runs} runs</div>
        </div>
      </div>

      <section>
        <h2 className="eyebrow mb-4">Discrepancies by kind</h2>
        {data.length === 0 ? (
          <div className="card p-8 text-sm text-muted text-center">
            No discrepancies recorded yet.
          </div>
        ) : (
          <div className="card p-5">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid stroke="#DDD9CE" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  axisLine={{ stroke: "#DDD9CE" }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "#DDD9CE33" }}
                  contentStyle={{ border: "1px solid #DDD9CE", borderRadius: 0, fontSize: 12 }}
                />
                <Bar dataKey="count">
                  {data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="card p-5">
        <div className="eyebrow">Total variance caught</div>
        <div className="figure text-3xl mt-2">{money(stats.total_variance_caught)}</div>
        <p className="text-sm text-muted mt-2 max-w-xl">
          Money that would have been paid out had these sets been approved without checking.
        </p>
      </section>
    </div>
  );
}
