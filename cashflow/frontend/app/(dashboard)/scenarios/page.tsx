"use client";
import { useEffect, useState } from "react";
import { scenarios as api, type Scenario } from "@/lib/api";
import { fmt, fmtDate, fmtShortDate } from "@/lib/utils";
import { Plus, CheckCircle, XCircle, GitBranch, TrendingDown } from "lucide-react";

const SCENARIO_TYPES = [
  { value: "one_time_purchase", label: "One-Time Purchase" },
  { value: "recurring_expense", label: "New Recurring Expense" },
  { value: "new_hire", label: "New Hire" },
  { value: "inventory_purchase", label: "Inventory Purchase" },
  { value: "marketing_campaign", label: "Marketing Campaign" },
  { value: "equipment", label: "Vehicle / Equipment" },
  { value: "owner_distribution", label: "Owner Distribution" },
];

const FREQUENCIES = ["weekly", "biweekly", "monthly", "quarterly", "annually"];

export default function ScenariosPage() {
  const [items, setItems] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [form, setForm] = useState({
    name: "", description: "", scenario_type: "one_time_purchase",
    amount: "", start_date: new Date().toISOString().slice(0, 10),
    end_date: "", frequency: "",
  });

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setItems(await api.list()); }
    finally { setLoading(false); }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const s = await api.create({
      ...form,
      amount: parseFloat(form.amount),
      end_date: form.end_date || undefined,
      frequency: form.frequency || undefined,
    } as unknown as Parameters<typeof api.create>[0]);
    setShowAdd(false);
    setSelected(s);
    load();
  }

  async function handleDelete(id: string) {
    await api.delete(id);
    if (selected?.id === id) setSelected(null);
    load();
  }

  const isRecurring = (t: string) =>
    ["new_hire", "recurring_expense"].includes(t);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scenarios</h1>
          <p className="text-sm text-gray-500 mt-0.5">Can I Afford This? — see the impact on your cash before you commit</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          <Plus size={16} /> New Scenario
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenario list */}
        <div className="space-y-3">
          {loading ? (
            [...Array(3)].map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-xl animate-pulse" />)
          ) : items.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
              <GitBranch className="mx-auto text-gray-300 mb-2" size={32} />
              <p className="text-gray-400 text-sm">No scenarios yet.</p>
              <button onClick={() => setShowAdd(true)} className="mt-2 text-blue-600 text-sm hover:underline">
                Create one
              </button>
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id}
                onClick={() => setSelected(item)}
                className={`bg-white border rounded-xl p-4 cursor-pointer transition-all hover:shadow-sm ${
                  selected?.id === item.id ? "border-blue-500 ring-1 ring-blue-500" : "border-gray-200"
                }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{item.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5 capitalize">
                      {item.scenario_type.replace(/_/g, " ")}
                    </p>
                  </div>
                  {item.can_afford === true && (
                    <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                      <CheckCircle size={12} /> Yes
                    </span>
                  )}
                  {item.can_afford === false && (
                    <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
                      <XCircle size={12} /> No
                    </span>
                  )}
                </div>
                <p className="text-lg font-bold text-gray-900 mt-2">{fmt(item.amount)}</p>
                <p className="text-xs text-gray-400">{fmtDate(item.start_date)}</p>
              </div>
            ))
          )}
        </div>

        {/* Scenario detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selected.name}</h2>
                  {selected.description && <p className="text-sm text-gray-500 mt-1">{selected.description}</p>}
                </div>
                <button onClick={() => handleDelete(selected.id)}
                  className="text-xs text-red-500 hover:text-red-600 border border-red-200 px-2 py-1 rounded hover:bg-red-50">
                  Delete
                </button>
              </div>

              {/* Verdict */}
              {selected.can_afford !== null && (
                <div className={`rounded-xl p-4 ${
                  selected.can_afford
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}>
                  <div className="flex items-center gap-2">
                    {selected.can_afford
                      ? <CheckCircle className="text-green-600" size={20} />
                      : <XCircle className="text-red-600" size={20} />}
                    <p className={`font-bold ${selected.can_afford ? "text-green-800" : "text-red-800"}`}>
                      {selected.can_afford ? "You can afford this" : "You cannot afford this"}
                    </p>
                  </div>
                  {selected.verdict_message && (
                    <p className="text-sm mt-2 text-gray-700">{selected.verdict_message}</p>
                  )}
                </div>
              )}

              {/* Before/After */}
              {selected.baseline_safe_to_spend && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium">Before</p>
                    <p className="text-xs text-gray-400 mt-1">Safe to Spend</p>
                    <p className="text-xl font-bold text-gray-900 mt-0.5">{fmt(selected.baseline_safe_to_spend)}</p>
                    <p className="text-xs text-gray-400 mt-2">Lowest Cash</p>
                    <p className="text-lg font-semibold text-gray-800">{fmt(selected.baseline_lowest_cash)}</p>
                  </div>
                  <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                    <p className="text-xs text-blue-600 uppercase font-medium">After This Scenario</p>
                    <p className="text-xs text-gray-400 mt-1">Safe to Spend</p>
                    <p className={`text-xl font-bold mt-0.5 ${
                      selected.can_afford ? "text-green-700" : "text-red-600"
                    }`}>{fmt(selected.projected_safe_to_spend)}</p>
                    <p className="text-xs text-gray-400 mt-2">Lowest Cash</p>
                    <p className={`text-lg font-semibold ${
                      selected.can_afford ? "text-gray-800" : "text-red-600"
                    }`}>{fmt(selected.projected_lowest_cash)}</p>
                  </div>
                </div>
              )}

              {/* Affected weeks */}
              {selected.items && selected.items.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <TrendingDown size={16} className="text-red-500" />
                    Affected Weeks
                  </h3>
                  <div className="space-y-2">
                    {selected.items.map((item, i) => {
                      const diff = parseFloat(item.scenario_closing_cash) - parseFloat(item.baseline_closing_cash);
                      return (
                        <div key={i} className="flex items-center justify-between text-sm border-b border-gray-50 pb-2">
                          <span className="text-gray-600">Wk {fmtShortDate(item.week_start)}</span>
                          <span className="text-gray-600 font-mono">{fmt(item.baseline_closing_cash)}</span>
                          <span className="text-gray-400">→</span>
                          <span className={`font-mono font-semibold ${diff < 0 ? "text-red-600" : "text-green-600"}`}>
                            {fmt(item.scenario_closing_cash)}
                          </span>
                          <span className={`text-xs font-medium ${diff < 0 ? "text-red-600" : "text-green-600"}`}>
                            ({diff >= 0 ? "+" : ""}{fmt(diff)})
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
              <GitBranch className="mx-auto text-gray-300 mb-3" size={40} />
              <p className="text-gray-500">Select a scenario to see its impact</p>
            </div>
          )}
        </div>
      </div>

      {/* Add Scenario Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Can I Afford This?</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="label">Name</label>
                <input className="input" required placeholder="e.g. New hire — operations manager"
                  value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Type</label>
                  <select className="input" value={form.scenario_type}
                    onChange={e => setForm(f => ({...f, scenario_type: e.target.value}))}>
                    {SCENARIO_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Amount ($)</label>
                  <input className="input" type="number" step="0.01" required
                    placeholder={isRecurring(form.scenario_type) ? "Per period" : "Total"}
                    value={form.amount} onChange={e => setForm(f => ({...f, amount: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Start Date</label>
                  <input className="input" type="date" required value={form.start_date}
                    onChange={e => setForm(f => ({...f, start_date: e.target.value}))} />
                </div>
                {isRecurring(form.scenario_type) ? (
                  <div>
                    <label className="label">Frequency</label>
                    <select className="input" value={form.frequency}
                      onChange={e => setForm(f => ({...f, frequency: e.target.value}))}>
                      <option value="">Select...</option>
                      {FREQUENCIES.map(fr => <option key={fr} value={fr} className="capitalize">{fr}</option>)}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="label">End Date (optional)</label>
                    <input className="input" type="date" value={form.end_date}
                      onChange={e => setForm(f => ({...f, end_date: e.target.value}))} />
                  </div>
                )}
              </div>
              <div>
                <label className="label">Description (optional)</label>
                <textarea className="input resize-none" rows={2} value={form.description}
                  onChange={e => setForm(f => ({...f, description: e.target.value}))} />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit"
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">
                  Run Scenario
                </button>
                <button type="button" onClick={() => setShowAdd(false)}
                  className="flex-1 border border-gray-200 py-2 rounded-lg text-gray-700">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
