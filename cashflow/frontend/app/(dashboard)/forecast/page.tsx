"use client";
import { useEffect, useState } from "react";
import { forecast as api, type ForecastSnapshot } from "@/lib/api";
import { fmt, fmtDate, fmtShortDate } from "@/lib/utils";
import { RefreshCw, TrendingDown, TrendingUp, AlertTriangle } from "lucide-react";

export default function ForecastPage() {
  const [snapshot, setSnapshot] = useState<ForecastSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [horizonWeeks, setHorizonWeeks] = useState(13);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      setSnapshot(await api.current());
    } finally { setLoading(false); }
  }

  async function recompute() {
    setComputing(true);
    try {
      setSnapshot(await api.compute(horizonWeeks));
    } finally { setComputing(false); }
  }

  if (loading) return <div className="p-8 animate-pulse space-y-4">
    <div className="h-8 bg-gray-200 rounded w-48" />
    {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-gray-200 rounded-xl" />)}
  </div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cash Forecast</h1>
          {snapshot && (
            <p className="text-sm text-gray-500 mt-0.5">
              Last computed {fmtDate(snapshot.computed_at.slice(0, 10))} · {snapshot.horizon_weeks} weeks
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {[8, 13].map(w => (
              <button key={w} onClick={() => setHorizonWeeks(w)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  horizonWeeks === w ? "bg-white shadow text-gray-900" : "text-gray-500"
                }`}>{w}wk</button>
            ))}
          </div>
          <button onClick={recompute} disabled={computing}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
            <RefreshCw size={14} className={computing ? "animate-spin" : ""} />
            {computing ? "Computing..." : "Recompute"}
          </button>
        </div>
      </div>

      {snapshot ? (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-gray-500 font-medium uppercase">Safe to Spend</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{fmt(snapshot.safe_to_spend)}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-gray-500 font-medium uppercase">Opening Cash</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{fmt(snapshot.opening_cash)}</p>
            </div>
            <div className={`bg-white border rounded-xl p-5 ${
              parseFloat(snapshot.lowest_projected_cash) < parseFloat(snapshot.minimum_cash_reserve)
                ? "border-red-300 bg-red-50"
                : "border-gray-200"
            }`}>
              <p className="text-xs text-gray-500 font-medium uppercase flex items-center gap-1">
                <TrendingDown size={12} /> Lowest Cash
              </p>
              <p className={`text-2xl font-bold mt-1 ${
                parseFloat(snapshot.lowest_projected_cash) < parseFloat(snapshot.minimum_cash_reserve)
                  ? "text-red-600" : "text-gray-900"
              }`}>{fmt(snapshot.lowest_projected_cash)}</p>
              {snapshot.lowest_cash_week && (
                <p className="text-xs text-gray-400 mt-1">Week of {fmtShortDate(snapshot.lowest_cash_week)}</p>
              )}
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-gray-500 font-medium uppercase">Min Reserve</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{fmt(snapshot.minimum_cash_reserve)}</p>
            </div>
          </div>

          {/* Cash cliff alert */}
          {snapshot.has_cash_cliff && (
            <div className="bg-red-50 border border-red-300 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="text-red-500 mt-0.5" size={20} />
              <div>
                <p className="font-semibold text-red-800">Cash Cliff Detected</p>
                <p className="text-sm text-red-700">
                  Cash drops {fmt(snapshot.cash_cliff_amount)} below your reserve around {fmtDate(snapshot.cash_cliff_date)}.
                </p>
              </div>
            </div>
          )}

          {/* Weekly breakdown */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Week-by-Week Breakdown</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="text-left px-4 py-3 text-gray-500 font-medium">Week</th>
                    <th className="text-right px-4 py-3 text-gray-500 font-medium">Opening</th>
                    <th className="text-right px-4 py-3 text-green-600 font-medium">+ Inflows</th>
                    <th className="text-right px-4 py-3 text-red-600 font-medium">− Outflows</th>
                    <th className="text-right px-4 py-3 text-gray-500 font-medium">Closing</th>
                    <th className="text-right px-4 py-3 text-gray-500 font-medium">vs Reserve</th>
                    {snapshot.weeks.some(w => w.actual_closing_cash) && (
                      <>
                        <th className="text-right px-4 py-3 text-gray-500 font-medium">Actual</th>
                        <th className="text-right px-4 py-3 text-gray-500 font-medium">Variance</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {snapshot.weeks.map((week) => {
                    const closing = parseFloat(week.closing_cash);
                    const res = parseFloat(week.reserve_threshold);
                    const diff = closing - res;
                    const hasActual = !!week.actual_closing_cash;
                    return (
                      <tr key={week.id} className={`hover:bg-gray-50 ${week.below_reserve ? "bg-red-50" : ""}`}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-800">Week {week.week_number}</p>
                          <p className="text-xs text-gray-400">
                            {fmtShortDate(week.week_start)} – {fmtShortDate(week.week_end)}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-gray-700">{fmt(week.opening_cash)}</td>
                        <td className="px-4 py-3 text-right font-mono text-green-600">
                          {parseFloat(week.expected_inflows) > 0 ? `+${fmt(week.expected_inflows)}` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-red-600">
                          {parseFloat(week.expected_outflows) > 0 ? `−${fmt(week.expected_outflows)}` : "—"}
                        </td>
                        <td className={`px-4 py-3 text-right font-mono font-semibold ${
                          closing < 0 ? "text-red-600" : "text-gray-900"
                        }`}>{fmt(week.closing_cash)}</td>
                        <td className={`px-4 py-3 text-right text-xs font-medium ${
                          diff < 0 ? "text-red-600" : "text-green-600"
                        }`}>
                          {diff >= 0 ? "+" : ""}{fmt(diff)}
                        </td>
                        {snapshot.weeks.some(w => w.actual_closing_cash) && (
                          <>
                            <td className="px-4 py-3 text-right font-mono text-gray-600">
                              {hasActual ? fmt(week.actual_closing_cash) : "—"}
                            </td>
                            <td className={`px-4 py-3 text-right font-mono text-xs ${
                              week.cash_variance
                                ? parseFloat(week.cash_variance) >= 0 ? "text-green-600" : "text-red-600"
                                : "text-gray-300"
                            }`}>
                              {week.cash_variance
                                ? `${parseFloat(week.cash_variance) >= 0 ? "+" : ""}${fmt(week.cash_variance)}`
                                : "—"}
                            </td>
                          </>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <p className="text-gray-500 mb-4">No forecast computed yet.</p>
          <button onClick={recompute}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">
            Compute First Forecast
          </button>
        </div>
      )}
    </div>
  );
}
