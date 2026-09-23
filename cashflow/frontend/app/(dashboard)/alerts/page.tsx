"use client";
import { useEffect, useState } from "react";
import { alerts as api, type Alert } from "@/lib/api";
import { fmt, fmtDate, SEVERITY_COLORS } from "@/lib/utils";
import { RefreshCw, CheckCircle, X, Bell, AlertTriangle, Info, AlertCircle } from "lucide-react";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  cash_shortfall: <AlertTriangle size={16} />,
  reserve_violation: <AlertTriangle size={16} />,
  cash_cliff: <AlertTriangle size={16} />,
  overdue_receivable: <AlertCircle size={16} />,
  upcoming_large_commitment: <Info size={16} />,
  credit_card_due: <Info size={16} />,
  missing_expected_receipt: <AlertCircle size={16} />,
  missing_expected_payout: <AlertCircle size={16} />,
  unverified_assumptions: <Info size={16} />,
  possible_duplicate: <Info size={16} />,
};

export default function AlertsPage() {
  const [items, setItems] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [filter, setFilter] = useState("all");

  useEffect(() => { load(); }, [filter]);

  async function load() {
    setLoading(true);
    try {
      const all = await api.list();
      setItems(all);
    } finally { setLoading(false); }
  }

  async function generate() {
    setGenerating(true);
    try {
      await api.generate();
      load();
    } finally { setGenerating(false); }
  }

  async function markRead(id: string) {
    await api.markRead(id);
    setItems(prev => prev.map(a => a.id === id ? { ...a, is_read: true } : a));
  }

  async function dismiss(id: string) {
    await api.dismiss(id);
    setItems(prev => prev.map(a => a.id === id ? { ...a, is_dismissed: true } : a));
  }

  const filtered = items.filter(a => {
    if (filter === "unread") return !a.is_read && !a.is_dismissed;
    if (filter === "active") return !a.is_dismissed;
    if (filter === "dismissed") return a.is_dismissed;
    return true;
  });

  const counts = {
    critical: items.filter(a => a.severity === "critical" && !a.is_dismissed).length,
    high: items.filter(a => a.severity === "high" && !a.is_dismissed).length,
    unread: items.filter(a => !a.is_read && !a.is_dismissed).length,
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {counts.unread > 0 ? `${counts.unread} unread` : "All caught up"}
          </p>
        </div>
        <button onClick={generate} disabled={generating}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          <RefreshCw size={14} className={generating ? "animate-spin" : ""} />
          {generating ? "Generating..." : "Refresh Alerts"}
        </button>
      </div>

      {/* Severity pills */}
      {(counts.critical > 0 || counts.high > 0) && (
        <div className="flex gap-3">
          {counts.critical > 0 && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <AlertTriangle size={14} className="text-red-500" />
              <span className="text-sm text-red-700 font-medium">{counts.critical} Critical</span>
            </div>
          )}
          {counts.high > 0 && (
            <div className="flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
              <AlertCircle size={14} className="text-orange-500" />
              <span className="text-sm text-orange-700 font-medium">{counts.high} High</span>
            </div>
          )}
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {["all", "unread", "active", "dismissed"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
              filter === f ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}>{f}</button>
        ))}
      </div>

      {/* Alert list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <Bell className="mx-auto text-gray-300 mb-3" size={40} />
          <p className="text-gray-500">No alerts in this category.</p>
          <button onClick={generate} className="mt-3 text-blue-600 text-sm hover:underline">
            Generate alerts
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <div key={alert.id}
              className={`border rounded-xl p-4 transition-opacity ${
                alert.is_dismissed ? "opacity-50" : ""
              } ${SEVERITY_COLORS[alert.severity] || "border-gray-200 bg-white"}`}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0">
                  {TYPE_ICONS[alert.alert_type] || <Bell size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-sm">{alert.title}</p>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full capitalize font-medium ${
                      alert.severity === "critical" ? "bg-red-100 text-red-700" :
                      alert.severity === "high" ? "bg-orange-100 text-orange-700" :
                      alert.severity === "medium" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>{alert.severity}</span>
                    {!alert.is_read && (
                      <span className="w-2 h-2 bg-blue-500 rounded-full" />
                    )}
                  </div>
                  <p className="text-sm mt-1 opacity-80">{alert.message}</p>
                  <div className="flex items-center gap-4 mt-2">
                    {alert.related_amount && (
                      <span className="text-xs font-mono font-medium">{fmt(alert.related_amount)}</span>
                    )}
                    {alert.related_date && (
                      <span className="text-xs opacity-60">{fmtDate(alert.related_date)}</span>
                    )}
                    <span className="text-xs opacity-50">{fmtDate(alert.fired_at.slice(0, 10))}</span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  {!alert.is_read && !alert.is_dismissed && (
                    <button onClick={() => markRead(alert.id)}
                      className="p-1.5 rounded-lg hover:bg-white/50 transition-colors"
                      title="Mark read">
                      <CheckCircle size={14} />
                    </button>
                  )}
                  {!alert.is_dismissed && (
                    <button onClick={() => dismiss(alert.id)}
                      className="p-1.5 rounded-lg hover:bg-white/50 transition-colors"
                      title="Dismiss">
                      <X size={14} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
