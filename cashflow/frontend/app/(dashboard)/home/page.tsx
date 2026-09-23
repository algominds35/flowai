"use client";
import { useEffect, useState } from "react";
import { dashboard, alerts, type SafeToSpendData, type Alert } from "@/lib/api";
import { fmt, fmtDate, fmtShortDate, SEVERITY_COLORS } from "@/lib/utils";
import { AlertTriangle, TrendingDown, Shield, ArrowDown, ArrowUp, Info, ChevronDown, ChevronRight } from "lucide-react";

export default function HomePage() {
  const [s2s, setS2s] = useState<SafeToSpendData | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [horizonWeeks, setHorizonWeeks] = useState(8);
  const [showBreakdown, setShowBreakdown] = useState(false);

  useEffect(() => {
    load();
  }, [horizonWeeks]);

  async function load() {
    setLoading(true);
    try {
      const [s2sData, alertData] = await Promise.all([
        dashboard.safeToSpend(horizonWeeks),
        alerts.list().catch(() => []),
      ]);
      setS2s(s2sData);
      setActiveAlerts(alertData.filter((a) => !a.is_dismissed).slice(0, 5));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <PageSkeleton />;
  if (!s2s) return <div className="p-8 text-gray-500">No data yet. Add a cash account to get started.</div>;

  const s2sAmount = parseFloat(s2s.safe_to_spend);
  const currentCash = parseFloat(s2s.current_cash);
  const reserve = parseFloat(s2s.minimum_reserve);
  const outflows = parseFloat(s2s.total_scheduled_outflows);
  const inflows = parseFloat(s2s.total_expected_inflows);
  const lowestCash = parseFloat(s2s.lowest_projected_cash);

  const s2sColor = s2sAmount <= 0
    ? "text-red-600"
    : s2sAmount < reserve
    ? "text-yellow-600"
    : "text-green-600";

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cash Position</h1>
          <p className="text-sm text-gray-500 mt-0.5">As of {fmtDate(s2s.as_of_date)}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Horizon:</span>
          {[8, 13].map((w) => (
            <button
              key={w}
              onClick={() => setHorizonWeeks(w)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                horizonWeeks === w
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300"
              }`}
            >
              {w}wk
            </button>
          ))}
        </div>
      </div>

      {/* Cash Cliff Banner */}
      {s2s.has_cash_cliff && (
        <div className="bg-red-50 border border-red-300 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="text-red-500 mt-0.5 shrink-0" size={20} />
          <div>
            <p className="font-semibold text-red-800">Cash Cliff Detected</p>
            <p className="text-sm text-red-700 mt-0.5">
              Cash drops {fmt(s2s.cash_cliff_amount)} below your reserve around{" "}
              {fmtDate(s2s.cash_cliff_date)}. Take action now.
            </p>
          </div>
        </div>
      )}

      {/* Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-2">
          {activeAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg px-4 py-3 flex items-start gap-3 ${SEVERITY_COLORS[alert.severity] || "border-gray-200 bg-white"}`}
            >
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{alert.title}</p>
                <p className="text-xs mt-0.5 opacity-80">{alert.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Primary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* SAFE TO SPEND — primary number */}
        <div className="md:col-span-1 bg-white rounded-2xl border border-gray-200 p-8 flex flex-col items-center text-center shadow-sm">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Safe to Spend</p>
          <p className={`text-5xl font-bold mt-3 ${s2sColor}`}>
            {fmt(s2s.safe_to_spend)}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Over next {horizonWeeks} weeks
          </p>
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="mt-4 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
          >
            How is this calculated?
            {showBreakdown ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        </div>

        {/* Supporting numbers */}
        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          <KpiCard
            label="Current Cash"
            value={fmt(s2s.current_cash)}
            sub="In bank accounts"
            icon={<ArrowUp className="text-green-500" size={16} />}
            color="border-green-200"
          />
          <KpiCard
            label="Min. Reserve"
            value={fmt(s2s.minimum_reserve)}
            sub="Always keep this buffer"
            icon={<Shield className="text-blue-500" size={16} />}
            color="border-blue-200"
          />
          <KpiCard
            label="Scheduled Outflows"
            value={fmt(s2s.total_scheduled_outflows)}
            sub={`Due in ${horizonWeeks} weeks`}
            icon={<ArrowDown className="text-red-500" size={16} />}
            color="border-red-200"
          />
          <KpiCard
            label="Lowest Cash Point"
            value={fmt(s2s.lowest_projected_cash)}
            sub={s2s.lowest_cash_week ? `Week of ${fmtShortDate(s2s.lowest_cash_week)}` : "Not yet reached"}
            icon={<TrendingDown className="text-orange-500" size={16} />}
            color={lowestCash < reserve ? "border-red-300 bg-red-50" : "border-orange-200"}
          />
        </div>
      </div>

      {/* S2S Breakdown */}
      {showBreakdown && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-3">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Info size={16} className="text-blue-500" />
            How Safe to Spend is Calculated
          </h3>
          <div className="space-y-2">
            {s2s.components.map((c, i) => {
              const isTotal = c.label === "Safe to Spend";
              const amount = parseFloat(c.amount);
              return (
                <div
                  key={i}
                  className={`flex items-center justify-between py-2 ${
                    isTotal
                      ? "border-t-2 border-gray-800 pt-3 font-bold"
                      : "border-b border-gray-100"
                  }`}
                >
                  <div>
                    <p className={`text-sm ${isTotal ? "text-gray-900 text-base" : "text-gray-700"}`}>
                      {c.label}
                    </p>
                    <p className="text-xs text-gray-400">{c.description}</p>
                  </div>
                  <span
                    className={`font-mono font-semibold ${
                      isTotal
                        ? s2sColor + " text-lg"
                        : amount < 0
                        ? "text-red-600"
                        : "text-gray-800"
                    }`}
                  >
                    {amount >= 0 ? "" : "−"}{fmt(Math.abs(amount))}
                  </span>
                </div>
              );
            })}
          </div>
          {s2s.total_expected_inflows !== "0.00" && (
            <p className="text-xs text-gray-400 mt-2">
              * Expected inflows of {fmt(s2s.total_expected_inflows)} are shown for context only — they are NOT counted in Safe to Spend since they aren&apos;t guaranteed.
            </p>
          )}
        </div>
      )}

      {/* Weekly Forecast Chart */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h3 className="font-semibold text-gray-800 mb-4">{horizonWeeks}-Week Cash Forecast</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left py-2 text-gray-500 font-medium">Week</th>
                <th className="text-right py-2 text-gray-500 font-medium">Opening</th>
                <th className="text-right py-2 text-gray-500 font-medium text-green-600">+Inflows</th>
                <th className="text-right py-2 text-gray-500 font-medium text-red-600">−Outflows</th>
                <th className="text-right py-2 text-gray-500 font-medium">Closing</th>
                <th className="text-right py-2 text-gray-500 font-medium">vs Reserve</th>
              </tr>
            </thead>
            <tbody>
              {s2s.weeks.map((week) => {
                const closing = parseFloat(week.closing_cash);
                const res = parseFloat(week.reserve_threshold);
                const diff = closing - res;
                return (
                  <tr
                    key={week.week_number}
                    className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                      week.below_reserve ? "bg-red-50" : ""
                    }`}
                  >
                    <td className="py-2.5 text-gray-600">
                      <span className="font-medium">Wk {week.week_number}</span>
                      <span className="text-xs text-gray-400 ml-1">
                        {fmtShortDate(week.week_start)}
                      </span>
                    </td>
                    <td className="py-2.5 text-right font-mono text-gray-700">
                      {fmt(week.opening_cash)}
                    </td>
                    <td className="py-2.5 text-right font-mono text-green-600">
                      {parseFloat(week.expected_inflows) > 0 ? `+${fmt(week.expected_inflows)}` : "—"}
                    </td>
                    <td className="py-2.5 text-right font-mono text-red-600">
                      {parseFloat(week.expected_outflows) > 0 ? `−${fmt(week.expected_outflows)}` : "—"}
                    </td>
                    <td className={`py-2.5 text-right font-mono font-semibold ${
                      closing < 0 ? "text-red-600" : "text-gray-900"
                    }`}>
                      {fmt(week.closing_cash)}
                    </td>
                    <td className={`py-2.5 text-right text-xs font-medium ${
                      diff < 0 ? "text-red-600" : "text-green-600"
                    }`}>
                      {diff >= 0 ? "+" : ""}{fmt(diff)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Expected Inflows (context) */}
      {inflows > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="font-semibold text-gray-800 mb-1">Expected Inflows (Context Only)</h3>
          <p className="text-xs text-gray-400 mb-4">Not counted in Safe to Spend — shown for planning</p>
          <div className="space-y-2">
            {s2s.weeks.flatMap((w) => w.inflow_items).map((item, i) => (
              <div key={i} className="flex items-center justify-between text-sm border-b border-gray-50 pb-2">
                <span className="text-gray-700">{item.name}</span>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-400">{fmtShortDate(item.date)}</span>
                  <span className="font-mono font-medium text-green-600">+{fmt(item.amount)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, sub, icon, color }: {
  label: string; value: string; sub: string; icon: React.ReactNode; color?: string;
}) {
  return (
    <div className={`bg-white rounded-xl border p-5 ${color || "border-gray-200"}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="p-8 space-y-6 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-48" />
      <div className="grid grid-cols-3 gap-6">
        <div className="h-48 bg-gray-200 rounded-2xl" />
        <div className="col-span-2 grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-xl" />)}
        </div>
      </div>
      <div className="h-64 bg-gray-200 rounded-xl" />
    </div>
  );
}
