"use client";
import { useEffect, useState } from "react";
import { weeklyReview as api, type WeeklyReviewSession, type WeeklyReviewItem } from "@/lib/api";
import { fmt, fmtDate } from "@/lib/utils";
import { Play, CheckCircle, X, AlertTriangle, RotateCcw, Flag } from "lucide-react";

export default function WeeklyReviewPage() {
  const [session, setSession] = useState<WeeklyReviewSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [editItem, setEditItem] = useState<WeeklyReviewItem | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editDate, setEditDate] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const s = await api.current();
      setSession(s);
    } catch {
      setSession(null);
    } finally { setLoading(false); }
  }

  async function startSession() {
    setStarting(true);
    try {
      const s = await api.start();
      setSession(s);
    } finally { setStarting(false); }
  }

  async function takeAction(sessionId: string, itemId: string, action: string, data?: object) {
    const updated = await api.actionItem(sessionId, itemId, action, data);
    setSession(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.map(i => i.id === itemId ? updated : i),
      };
    });
    setEditItem(null);
  }

  async function completeSession() {
    if (!session) return;
    setCompleting(true);
    try {
      const s = await api.complete(session.id);
      setSession(s);
    } finally { setCompleting(false); }
  }

  const pending = session?.items.filter(i => i.status === "pending") || [];
  const actioned = session?.items.filter(i => i.status !== "pending") || [];
  const progress = session ? Math.round((actioned.length / session.items.length) * 100) : 0;

  const ACTION_COLOR: Record<string, string> = {
    confirmed: "bg-green-50 border-green-200",
    ignored: "bg-gray-50 border-gray-200 opacity-60",
    uncertain: "bg-yellow-50 border-yellow-200",
    amount_changed: "bg-blue-50 border-blue-200",
    date_changed: "bg-blue-50 border-blue-200",
  };

  if (loading) return (
    <div className="p-8 space-y-4 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-48" />
      <div className="h-32 bg-gray-200 rounded-xl" />
    </div>
  );

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Weekly Review</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Confirm, adjust, or flag uncertain cash flow items for this week
        </p>
      </div>

      {!session || session.status === "completed" ? (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center space-y-4">
          {session?.status === "completed" ? (
            <>
              <CheckCircle className="mx-auto text-green-500" size={48} />
              <p className="text-xl font-semibold text-gray-800">Review Complete!</p>
              <p className="text-sm text-gray-500">
                Week of {fmtDate(session.week_start)} – {fmtDate(session.week_end)}
              </p>
              <p className="text-sm text-gray-500">
                {actioned.length} items reviewed
              </p>
            </>
          ) : (
            <>
              <AlertTriangle className="mx-auto text-yellow-400" size={48} />
              <p className="text-xl font-semibold text-gray-800">No Active Review Session</p>
              <p className="text-sm text-gray-500">Start a new weekly review to surface uncertain items</p>
            </>
          )}
          <button onClick={startSession} disabled={starting}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">
            <Play size={16} />
            {starting ? "Starting..." : "Start New Review"}
          </button>
        </div>
      ) : (
        <>
          {/* Progress */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-700">
                Week of {fmtDate(session.week_start)} – {fmtDate(session.week_end)}
              </p>
              <p className="text-sm text-gray-500">{actioned.length}/{session.items.length} done</p>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            {pending.length === 0 && (
              <div className="mt-4 flex justify-end">
                <button onClick={completeSession} disabled={completing}
                  className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">
                  <CheckCircle size={14} />
                  {completing ? "Completing..." : "Complete Review"}
                </button>
              </div>
            )}
          </div>

          {/* Pending items */}
          {pending.length > 0 && (
            <div className="space-y-3">
              <h2 className="font-semibold text-gray-800">Needs Review ({pending.length})</h2>
              {pending.map((item) => (
                <div key={item.id} className="bg-white border border-yellow-200 rounded-xl p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
                        item.item_type === "uncertain_commitment" ? "bg-orange-100 text-orange-700" :
                        item.item_type === "uncertain_receivable" ? "bg-blue-100 text-blue-700" :
                        "bg-gray-100 text-gray-700"
                      }`}>{item.item_type.replace(/_/g, " ")}</span>
                      <p className="font-semibold text-gray-900 mt-2">{item.title}</p>
                      {item.description && <p className="text-sm text-gray-500 mt-0.5">{item.description}</p>}
                    </div>
                    <div className="text-right">
                      {item.original_amount && (
                        <p className="font-mono font-bold text-gray-900">{fmt(item.original_amount)}</p>
                      )}
                      {item.original_date && (
                        <p className="text-xs text-gray-400">{fmtDate(item.original_date)}</p>
                      )}
                    </div>
                  </div>

                  {/* Inline edit */}
                  {editItem?.id === item.id ? (
                    <div className="mt-4 bg-gray-50 rounded-lg p-3 space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="label">Confirmed Amount ($)</label>
                          <input className="input" type="number" step="0.01" value={editAmount}
                            onChange={e => setEditAmount(e.target.value)} />
                        </div>
                        <div>
                          <label className="label">Confirmed Date</label>
                          <input className="input" type="date" value={editDate}
                            onChange={e => setEditDate(e.target.value)} />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => takeAction(session.id, item.id, "amount_changed", {
                            confirmed_amount: parseFloat(editAmount),
                            confirmed_date: editDate || undefined,
                          })}
                          className="flex-1 bg-blue-600 text-white py-1.5 rounded-lg text-sm font-medium">
                          Save Changes
                        </button>
                        <button onClick={() => setEditItem(null)}
                          className="px-3 border border-gray-200 rounded-lg text-sm text-gray-600">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-2 mt-4 flex-wrap">
                      <button
                        onClick={() => takeAction(session.id, item.id, "confirmed")}
                        className="flex items-center gap-1.5 text-xs bg-green-50 text-green-700 border border-green-200 px-3 py-1.5 rounded-lg hover:bg-green-100">
                        <CheckCircle size={12} /> Confirm
                      </button>
                      <button
                        onClick={() => {
                          setEditItem(item);
                          setEditAmount(item.original_amount || "");
                          setEditDate(item.original_date || "");
                        }}
                        className="flex items-center gap-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-lg hover:bg-blue-100">
                        <RotateCcw size={12} /> Change Amount/Date
                      </button>
                      <button
                        onClick={() => takeAction(session.id, item.id, "mark_uncertain")}
                        className="flex items-center gap-1.5 text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-3 py-1.5 rounded-lg hover:bg-yellow-100">
                        <Flag size={12} /> Mark Uncertain
                      </button>
                      <button
                        onClick={() => takeAction(session.id, item.id, "ignore")}
                        className="flex items-center gap-1.5 text-xs bg-gray-50 text-gray-600 border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-100">
                        <X size={12} /> Ignore
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Actioned items */}
          {actioned.length > 0 && (
            <div className="space-y-2">
              <h2 className="font-semibold text-gray-600 text-sm">Completed ({actioned.length})</h2>
              {actioned.map((item) => (
                <div key={item.id}
                  className={`border rounded-xl p-4 text-sm ${ACTION_COLOR[item.action || ""] || "bg-gray-50 border-gray-200"}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-700">{item.title}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
                      item.action === "confirmed" ? "bg-green-100 text-green-700" :
                      item.action === "ignored" ? "bg-gray-100 text-gray-500" :
                      item.action === "uncertain" ? "bg-yellow-100 text-yellow-700" :
                      "bg-blue-100 text-blue-700"
                    }`}>{(item.action || "").replace(/_/g, " ")}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
