"use client";
import { useEffect, useState } from "react";
import { commitments as api, type Commitment } from "@/lib/api";
import { fmt, fmtDate, daysUntil, CATEGORY_LABELS, STATUS_COLORS } from "@/lib/utils";
import { Plus, CheckCircle, Clock, AlertCircle, Filter } from "lucide-react";

const CATEGORIES = [
  "payroll", "rent", "tax", "insurance", "loan", "subscription",
  "credit_card_payment", "inventory_po", "vendor_bill", "recurring_expense", "manual",
];

export default function CommitmentsPage() {
  const [items, setItems] = useState<Commitment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    name: "", category: "manual", amount: "", due_date: "", vendor_name: "",
    is_recurring: false, recurring_frequency: "", confidence_level: "high", notes: "",
  });

  useEffect(() => { load(); }, [filter]);

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string | boolean> = {};
      if (filter === "overdue") params.overdue_only = true;
      else if (filter !== "all") params.status = filter;
      setItems(await api.list(params as Parameters<typeof api.list>[0]));
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await api.create({
      ...form,
      amount: parseFloat(form.amount),
      recurring_frequency: form.is_recurring ? form.recurring_frequency || undefined : undefined,
    } as unknown as Parameters<typeof api.create>[0]);
    setShowAdd(false);
    setForm({ name: "", category: "manual", amount: "", due_date: "", vendor_name: "", is_recurring: false, recurring_frequency: "", confidence_level: "high", notes: "" });
    load();
  }

  async function markPaid(id: string) {
    await api.markPaid(id);
    load();
  }

  const totals = {
    scheduled: items.filter(i => i.status === "scheduled").reduce((s, i) => s + parseFloat(i.remaining_amount), 0),
    overdue: items.filter(i => i.status === "overdue").reduce((s, i) => s + parseFloat(i.remaining_amount), 0),
    paid: items.filter(i => i.status === "paid").reduce((s, i) => s + parseFloat(i.amount), 0),
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Commitments</h1>
          <p className="text-sm text-gray-500 mt-0.5">Bills, payroll, taxes, and all scheduled outflows</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={16} /> Add Commitment
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-red-200 rounded-xl p-4">
          <p className="text-xs text-red-500 font-medium uppercase">Overdue</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{fmt(totals.overdue)}</p>
        </div>
        <div className="bg-white border border-blue-200 rounded-xl p-4">
          <p className="text-xs text-blue-500 font-medium uppercase">Scheduled</p>
          <p className="text-2xl font-bold text-blue-700 mt-1">{fmt(totals.scheduled)}</p>
        </div>
        <div className="bg-white border border-green-200 rounded-xl p-4">
          <p className="text-xs text-green-500 font-medium uppercase">Paid (shown)</p>
          <p className="text-2xl font-bold text-green-700 mt-1">{fmt(totals.paid)}</p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {["all", "overdue", "scheduled", "paid"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
              filter === f ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 animate-pulse">Loading...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-400">No commitments found.</p>
            <button onClick={() => setShowAdd(true)} className="mt-3 text-blue-600 text-sm hover:underline">
              Add your first commitment
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Name</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Category</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Amount</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Due</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Status</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => {
                const days = daysUntil(item.due_date);
                const isOverdue = item.status === "overdue";
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{item.name}</p>
                      {item.vendor_name && <p className="text-xs text-gray-400">{item.vendor_name}</p>}
                      {item.is_recurring && (
                        <span className="text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">
                          ↻ {item.recurring_frequency}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {CATEGORY_LABELS[item.category] || item.category}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900">
                      {fmt(item.remaining_amount)}
                      {item.amount_paid !== "0.00" && (
                        <p className="text-xs text-gray-400">{fmt(item.amount_paid)} paid</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className={isOverdue ? "text-red-600 font-medium" : "text-gray-700"}>
                        {fmtDate(item.due_date)}
                      </p>
                      <p className="text-xs text-gray-400">
                        {isOverdue ? `${Math.abs(days)}d overdue` : days === 0 ? "Today" : `in ${days}d`}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[item.status] || ""}`}>
                        {item.status === "paid" && <CheckCircle size={10} />}
                        {item.status === "overdue" && <AlertCircle size={10} />}
                        {item.status === "scheduled" && <Clock size={10} />}
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {item.status !== "paid" && item.status !== "cancelled" && (
                        <button
                          onClick={() => markPaid(item.id)}
                          className="text-xs text-green-600 hover:text-green-700 font-medium border border-green-200 px-2 py-1 rounded hover:bg-green-50"
                        >
                          Mark Paid
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Add Commitment</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="label">Name</label>
                  <input className="input" required value={form.name}
                    onChange={e => setForm(f => ({...f, name: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Category</label>
                  <select className="input" value={form.category}
                    onChange={e => setForm(f => ({...f, category: e.target.value}))}>
                    {CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Confidence</label>
                  <select className="input" value={form.confidence_level}
                    onChange={e => setForm(f => ({...f, confidence_level: e.target.value}))}>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="uncertain">Uncertain</option>
                  </select>
                </div>
                <div>
                  <label className="label">Amount ($)</label>
                  <input className="input" type="number" step="0.01" required value={form.amount}
                    onChange={e => setForm(f => ({...f, amount: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Due Date</label>
                  <input className="input" type="date" required value={form.due_date}
                    onChange={e => setForm(f => ({...f, due_date: e.target.value}))} />
                </div>
                <div className="col-span-2">
                  <label className="label">Vendor / Payee (optional)</label>
                  <input className="input" value={form.vendor_name}
                    onChange={e => setForm(f => ({...f, vendor_name: e.target.value}))} />
                </div>
                <div className="col-span-2 flex items-center gap-2">
                  <input type="checkbox" id="recurring" checked={form.is_recurring}
                    onChange={e => setForm(f => ({...f, is_recurring: e.target.checked}))} />
                  <label htmlFor="recurring" className="text-sm text-gray-700">Recurring</label>
                </div>
                {form.is_recurring && (
                  <div>
                    <label className="label">Frequency</label>
                    <select className="input" value={form.recurring_frequency}
                      onChange={e => setForm(f => ({...f, recurring_frequency: e.target.value}))}>
                      <option value="weekly">Weekly</option>
                      <option value="biweekly">Biweekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="annually">Annually</option>
                    </select>
                  </div>
                )}
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">
                  Add Commitment
                </button>
                <button type="button" onClick={() => setShowAdd(false)}
                  className="flex-1 border border-gray-200 py-2 rounded-lg text-gray-700 hover:bg-gray-50">
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
