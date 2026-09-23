"use client";
import { useEffect, useState } from "react";
import { receivables as api, type Receivable } from "@/lib/api";
import { fmt, fmtDate, daysUntil, STATUS_COLORS } from "@/lib/utils";
import { Plus, DollarSign, AlertCircle, CheckCircle } from "lucide-react";

export default function ReceivablesPage() {
  const [items, setItems] = useState<Receivable[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [showPayment, setShowPayment] = useState<string | null>(null);
  const [payAmount, setPayAmount] = useState("");
  const [payDate, setPayDate] = useState(new Date().toISOString().slice(0, 10));
  const [form, setForm] = useState({
    name: "", customer_name: "", invoice_number: "", receivable_type: "invoice",
    amount: "", expected_date: "", confidence_level: "high", notes: "",
  });

  useEffect(() => { load(); }, [filter]);

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string | boolean> = {};
      if (filter === "overdue") params.overdue_only = true;
      else if (filter !== "all") params.status = filter;
      setItems(await api.list(params as Parameters<typeof api.list>[0]));
    } finally { setLoading(false); }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await api.create({ ...form, amount: parseFloat(form.amount) } as unknown as Parameters<typeof api.create>[0]);
    setShowAdd(false);
    load();
  }

  async function handlePayment(id: string) {
    await api.recordPayment(id, parseFloat(payAmount), payDate);
    setShowPayment(null);
    load();
  }

  const totals = {
    expected: items.filter(i => ["expected", "partially_received"].includes(i.status))
      .reduce((s, i) => s + parseFloat(i.remaining_amount), 0),
    overdue: items.filter(i => i.status === "overdue")
      .reduce((s, i) => s + parseFloat(i.remaining_amount), 0),
    received: items.filter(i => i.status === "received")
      .reduce((s, i) => s + parseFloat(i.amount), 0),
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Receivables</h1>
          <p className="text-sm text-gray-500 mt-0.5">Invoices, payouts, and expected income</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          <Plus size={16} /> Add Receivable
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-red-200 rounded-xl p-4">
          <p className="text-xs text-red-500 font-medium uppercase">Overdue</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{fmt(totals.overdue)}</p>
        </div>
        <div className="bg-white border border-blue-200 rounded-xl p-4">
          <p className="text-xs text-blue-500 font-medium uppercase">Expected</p>
          <p className="text-2xl font-bold text-blue-700 mt-1">{fmt(totals.expected)}</p>
        </div>
        <div className="bg-white border border-green-200 rounded-xl p-4">
          <p className="text-xs text-green-500 font-medium uppercase">Received</p>
          <p className="text-2xl font-bold text-green-700 mt-1">{fmt(totals.received)}</p>
        </div>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {["all", "overdue", "expected", "partially_received", "received"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
              filter === f ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}>
            {f.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 animate-pulse">Loading...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-400">No receivables yet.</p>
            <button onClick={() => setShowAdd(true)} className="mt-3 text-blue-600 text-sm hover:underline">
              Add your first invoice
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Invoice / Source</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Customer</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Amount</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Expected</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Status</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => {
                const days = daysUntil(item.expected_date);
                const isOverdue = item.status === "overdue" || (days < 0 && item.status === "expected");
                const pct = parseFloat(item.amount) > 0
                  ? (parseFloat(item.amount_received) / parseFloat(item.amount)) * 100
                  : 0;
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{item.name}</p>
                      {item.invoice_number && <p className="text-xs text-gray-400">#{item.invoice_number}</p>}
                      {item.external_source && (
                        <span className="text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded capitalize">
                          {item.external_source.replace("_fixture", "")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.customer_name || "—"}</td>
                    <td className="px-4 py-3 text-right">
                      <p className="font-mono font-semibold text-gray-900">{fmt(item.amount)}</p>
                      {pct > 0 && pct < 100 && (
                        <div className="mt-1">
                          <div className="h-1.5 bg-gray-100 rounded-full w-16 ml-auto">
                            <div className="h-full bg-green-500 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <p className="text-xs text-gray-400">{fmt(item.remaining_amount)} left</p>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className={isOverdue ? "text-red-600 font-medium" : "text-gray-700"}>
                        {fmtDate(item.expected_date)}
                      </p>
                      <p className="text-xs text-gray-400">
                        {isOverdue ? `${Math.abs(days)}d overdue` : days === 0 ? "Today" : `in ${days}d`}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[item.status] || ""}`}>
                        {item.status === "received" && <CheckCircle size={10} />}
                        {(item.status === "overdue") && <AlertCircle size={10} />}
                        {item.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!["received", "written_off"].includes(item.status) && (
                        <button
                          onClick={() => { setShowPayment(item.id); setPayAmount(item.remaining_amount); }}
                          className="text-xs text-green-600 hover:text-green-700 font-medium border border-green-200 px-2 py-1 rounded hover:bg-green-50"
                        >
                          Record Payment
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

      {/* Record Payment Modal */}
      {showPayment && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Record Payment</h2>
            <div className="space-y-3">
              <div>
                <label className="label">Amount Received ($)</label>
                <input className="input" type="number" step="0.01" value={payAmount}
                  onChange={e => setPayAmount(e.target.value)} />
              </div>
              <div>
                <label className="label">Date Received</label>
                <input className="input" type="date" value={payDate}
                  onChange={e => setPayDate(e.target.value)} />
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => handlePayment(showPayment)}
                  className="flex-1 bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700">
                  Record
                </button>
                <button onClick={() => setShowPayment(null)}
                  className="flex-1 border border-gray-200 py-2 rounded-lg text-gray-700 hover:bg-gray-50">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Add Receivable</h2>
            <form onSubmit={handleAdd} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="label">Name / Description</label>
                  <input className="input" required value={form.name}
                    onChange={e => setForm(f => ({...f, name: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Type</label>
                  <select className="input" value={form.receivable_type}
                    onChange={e => setForm(f => ({...f, receivable_type: e.target.value}))}>
                    <option value="invoice">Invoice</option>
                    <option value="payout">Payout</option>
                    <option value="settlement">Settlement</option>
                    <option value="deposit">Deposit</option>
                    <option value="other">Other</option>
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
                  <label className="label">Customer</label>
                  <input className="input" value={form.customer_name}
                    onChange={e => setForm(f => ({...f, customer_name: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Invoice #</label>
                  <input className="input" value={form.invoice_number}
                    onChange={e => setForm(f => ({...f, invoice_number: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Amount ($)</label>
                  <input className="input" type="number" step="0.01" required value={form.amount}
                    onChange={e => setForm(f => ({...f, amount: e.target.value}))} />
                </div>
                <div>
                  <label className="label">Expected Date</label>
                  <input className="input" type="date" required value={form.expected_date}
                    onChange={e => setForm(f => ({...f, expected_date: e.target.value}))} />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit"
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">
                  Add Receivable
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
