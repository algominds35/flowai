"use client";
import { useEffect, useState } from "react";
import { purchaseOrders as api, scenarios as scenarioApi, type PurchaseOrder, type Scenario } from "@/lib/api";
import { fmt, fmtDate, fmtShortDate } from "@/lib/utils";
import { Plus, Package, CheckCircle, Clock, AlertCircle, ChevronDown, ChevronRight, GitBranch } from "lucide-react";

const INSTALLMENT_LABELS: Record<string, string> = {
  deposit: "Deposit",
  production: "Production Payment",
  freight: "Freight / Shipping",
  duties: "Duties / Customs",
  final: "Final Payment",
  other: "Other",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  confirmed: "bg-blue-100 text-blue-700",
  in_production: "bg-yellow-100 text-yellow-700",
  shipped: "bg-purple-100 text-purple-700",
  delivered: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-600",
};

export default function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [affordResult, setAffordResult] = useState<Record<string, Scenario>>({});
  const [runningAfford, setRunningAfford] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    supplier_name: "",
    description: "",
    po_number: "",
    total_amount: "",
    order_date: new Date().toISOString().slice(0, 10),
    expected_delivery_date: "",
    currency: "USD",
  });

  // Installment rows
  const [installments, setInstallments] = useState([
    { installment_type: "deposit", label: "Deposit", amount: "", due_date: "" },
  ]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setOrders(await api.list()); }
    finally { setLoading(false); }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const validInstallments = installments.filter(i => i.amount && i.due_date);
    await api.create({
      ...form,
      total_amount: parseFloat(form.total_amount),
      installments: validInstallments.map(i => ({
        ...i,
        amount: parseFloat(i.amount),
      })),
    } as unknown as Parameters<typeof api.create>[0]);
    setShowAdd(false);
    setForm({
      supplier_name: "", description: "", po_number: "",
      total_amount: "", order_date: new Date().toISOString().slice(0, 10),
      expected_delivery_date: "", currency: "USD",
    });
    setInstallments([{ installment_type: "deposit", label: "Deposit", amount: "", due_date: "" }]);
    load();
  }

  async function runAffordability(po: PurchaseOrder) {
    setRunningAfford(po.id);
    try {
      // Create a scenario for the total PO amount
      const s = await scenarioApi.create({
        name: `PO: ${po.supplier_name}`,
        description: `Can I afford this purchase order? Total: ${fmt(po.total_amount)}`,
        scenario_type: "inventory_purchase",
        amount: parseFloat(po.total_amount),
        start_date: po.order_date || new Date().toISOString().slice(0, 10),
      } as unknown as Parameters<typeof scenarioApi.create>[0]);
      setAffordResult(prev => ({ ...prev, [po.id]: s }));
    } finally { setRunningAfford(null); }
  }

  function addInstallmentRow() {
    setInstallments(prev => [
      ...prev,
      { installment_type: "other", label: "", amount: "", due_date: "" },
    ]);
  }

  function removeInstallmentRow(idx: number) {
    setInstallments(prev => prev.filter((_, i) => i !== idx));
  }

  const totalInstallmentAmount = installments
    .reduce((s, i) => s + (parseFloat(i.amount) || 0), 0);

  const summaryTotals = {
    committed: orders
      .filter(o => !["cancelled", "delivered"].includes(o.status))
      .reduce((s, o) => s + parseFloat(o.remaining_amount), 0),
    paid: orders.reduce((s, o) => s + parseFloat(o.amount_paid), 0),
    orders: orders.length,
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Purchase Orders</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Supplier POs with installment payments — each cash event forecasted separately
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={16} /> New Purchase Order
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-blue-200 rounded-xl p-5">
          <p className="text-xs font-medium text-blue-500 uppercase">Outstanding</p>
          <p className="text-2xl font-bold text-blue-700 mt-1">{fmt(summaryTotals.committed)}</p>
          <p className="text-xs text-gray-400 mt-1">Still owed to suppliers</p>
        </div>
        <div className="bg-white border border-green-200 rounded-xl p-5">
          <p className="text-xs font-medium text-green-500 uppercase">Paid to Date</p>
          <p className="text-2xl font-bold text-green-700 mt-1">{fmt(summaryTotals.paid)}</p>
          <p className="text-xs text-gray-400 mt-1">Across all POs</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase">Total POs</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{summaryTotals.orders}</p>
          <p className="text-xs text-gray-400 mt-1">All time</p>
        </div>
      </div>

      {/* PO List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : orders.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <Package className="mx-auto text-gray-300 mb-3" size={48} />
          <p className="text-gray-500 mb-1">No purchase orders yet.</p>
          <p className="text-sm text-gray-400 mb-4">
            Add a PO to forecast each installment (deposit, production, freight, duties, final) separately.
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Create First PO
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((po) => {
            const isExpanded = expanded === po.id;
            const afford = affordResult[po.id];
            const paidPct = parseFloat(po.total_amount) > 0
              ? (parseFloat(po.amount_paid) / parseFloat(po.total_amount)) * 100
              : 0;

            return (
              <div key={po.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                {/* PO Header row */}
                <div
                  className="flex items-center gap-4 p-5 cursor-pointer hover:bg-gray-50"
                  onClick={() => setExpanded(isExpanded ? null : po.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <p className="font-semibold text-gray-900">{po.supplier_name}</p>
                      {po.po_number && (
                        <span className="text-xs text-gray-400">PO #{po.po_number}</span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLORS[po.status] || "bg-gray-100 text-gray-600"}`}>
                        {po.status.replace("_", " ")}
                      </span>
                    </div>
                    {po.description && (
                      <p className="text-sm text-gray-500 mt-0.5 truncate">{po.description}</p>
                    )}
                    {/* Progress bar */}
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-gray-100 rounded-full">
                        <div
                          className="h-full bg-green-500 rounded-full transition-all"
                          style={{ width: `${Math.min(paidPct, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 whitespace-nowrap">
                        {fmt(po.amount_paid)} of {fmt(po.total_amount)} paid
                      </span>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <p className="font-mono font-bold text-gray-900 text-lg">{fmt(po.total_amount)}</p>
                    <p className="text-xs text-red-600 font-medium">{fmt(po.remaining_amount)} remaining</p>
                    {po.expected_delivery_date && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Delivery: {fmtShortDate(po.expected_delivery_date)}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 text-gray-400">
                    {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  </div>
                </div>

                {/* Expanded: installments + affordability */}
                {isExpanded && (
                  <div className="border-t border-gray-100 p-5 bg-gray-50 space-y-5">

                    {/* Installments table */}
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-3">
                        Payment Schedule — each installment is a separate commitment in your forecast
                      </h3>
                      {po.installments && po.installments.length > 0 ? (
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-2 text-gray-500 font-medium">Payment Type</th>
                              <th className="text-right py-2 text-gray-500 font-medium">Amount</th>
                              <th className="text-left py-2 text-gray-500 font-medium">Due Date</th>
                              <th className="text-left py-2 text-gray-500 font-medium">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {po.installments.map((inst) => (
                              <tr key={inst.id} className="hover:bg-white">
                                <td className="py-2.5">
                                  <p className="font-medium text-gray-800">
                                    {INSTALLMENT_LABELS[inst.installment_type] || inst.label}
                                  </p>
                                  {inst.label !== INSTALLMENT_LABELS[inst.installment_type] && (
                                    <p className="text-xs text-gray-400">{inst.label}</p>
                                  )}
                                </td>
                                <td className="py-2.5 text-right font-mono font-semibold text-gray-900">
                                  {fmt(inst.amount)}
                                </td>
                                <td className="py-2.5 text-gray-600">
                                  {fmtDate(inst.due_date)}
                                </td>
                                <td className="py-2.5">
                                  {inst.is_paid ? (
                                    <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                                      <CheckCircle size={12} /> Paid
                                      {inst.paid_date && <span className="text-gray-400">{fmtShortDate(inst.paid_date)}</span>}
                                    </span>
                                  ) : (
                                    <span className="flex items-center gap-1 text-xs text-blue-600 font-medium">
                                      <Clock size={12} /> Scheduled
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="border-t-2 border-gray-300">
                            <tr>
                              <td className="py-2 font-semibold text-gray-800">Total</td>
                              <td className="py-2 text-right font-mono font-bold text-gray-900">
                                {fmt(po.total_amount)}
                              </td>
                              <td colSpan={2} />
                            </tr>
                          </tfoot>
                        </table>
                      ) : (
                        <p className="text-sm text-gray-400">No installment schedule — single payment PO.</p>
                      )}
                    </div>

                    {/* Can I Afford This? */}
                    <div className="border-t border-gray-200 pt-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                          <GitBranch size={14} className="text-blue-500" />
                          Can I Afford This PO?
                        </h3>
                        <button
                          onClick={() => runAffordability(po)}
                          disabled={runningAfford === po.id}
                          className="flex items-center gap-1.5 text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        >
                          <GitBranch size={12} />
                          {runningAfford === po.id ? "Analyzing..." : "Run Analysis"}
                        </button>
                      </div>

                      {afford ? (
                        <div className={`rounded-xl p-4 ${
                          afford.can_afford
                            ? "bg-green-50 border border-green-200"
                            : "bg-red-50 border border-red-200"
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            {afford.can_afford
                              ? <CheckCircle className="text-green-600" size={18} />
                              : <AlertCircle className="text-red-600" size={18} />}
                            <p className={`font-bold ${afford.can_afford ? "text-green-800" : "text-red-800"}`}>
                              {afford.can_afford ? "Yes, you can afford this PO" : "You cannot afford this PO right now"}
                            </p>
                          </div>
                          {afford.verdict_message && (
                            <p className="text-sm text-gray-700 mb-3">{afford.verdict_message}</p>
                          )}
                          <div className="grid grid-cols-2 gap-3 mt-3">
                            <div className="bg-white/60 rounded-lg p-3">
                              <p className="text-xs text-gray-500">Safe to Spend — Before</p>
                              <p className="text-lg font-bold text-gray-900 mt-0.5">
                                {fmt(afford.baseline_safe_to_spend)}
                              </p>
                            </div>
                            <div className="bg-white/60 rounded-lg p-3">
                              <p className="text-xs text-gray-500">Safe to Spend — After PO</p>
                              <p className={`text-lg font-bold mt-0.5 ${
                                afford.can_afford ? "text-gray-900" : "text-red-600"
                              }`}>
                                {fmt(afford.projected_safe_to_spend)}
                              </p>
                            </div>
                            <div className="bg-white/60 rounded-lg p-3">
                              <p className="text-xs text-gray-500">Lowest Cash — Before</p>
                              <p className="text-lg font-bold text-gray-900 mt-0.5">
                                {fmt(afford.baseline_lowest_cash)}
                              </p>
                            </div>
                            <div className="bg-white/60 rounded-lg p-3">
                              <p className="text-xs text-gray-500">Lowest Cash — After PO</p>
                              <p className={`text-lg font-bold mt-0.5 ${
                                afford.can_afford ? "text-gray-900" : "text-red-600"
                              }`}>
                                {fmt(afford.projected_lowest_cash)}
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400">
                          Click "Run Analysis" to see if your cash flow can support this PO without going below your reserve.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add PO Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl p-6 w-full max-w-2xl shadow-2xl my-8">
            <h2 className="text-lg font-bold text-gray-900 mb-5">New Purchase Order</h2>
            <form onSubmit={handleAdd} className="space-y-5">

              {/* Basic info */}
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="label">Supplier Name *</label>
                  <input className="input" required value={form.supplier_name}
                    onChange={e => setForm(f => ({ ...f, supplier_name: e.target.value }))}
                    placeholder="e.g. Guangzhou Manufacturing Co." />
                </div>
                <div>
                  <label className="label">PO Number</label>
                  <input className="input" value={form.po_number}
                    onChange={e => setForm(f => ({ ...f, po_number: e.target.value }))}
                    placeholder="e.g. PO-2026-001" />
                </div>
                <div>
                  <label className="label">Total PO Amount ($) *</label>
                  <input className="input" type="number" step="0.01" required value={form.total_amount}
                    onChange={e => setForm(f => ({ ...f, total_amount: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Order Date</label>
                  <input className="input" type="date" value={form.order_date}
                    onChange={e => setForm(f => ({ ...f, order_date: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Expected Delivery</label>
                  <input className="input" type="date" value={form.expected_delivery_date}
                    onChange={e => setForm(f => ({ ...f, expected_delivery_date: e.target.value }))} />
                </div>
                <div className="col-span-2">
                  <label className="label">Description (optional)</label>
                  <input className="input" value={form.description}
                    onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                    placeholder="e.g. Winter inventory — 500 units fleece jackets" />
                </div>
              </div>

              {/* Payment schedule */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <label className="label mb-0">Payment Schedule</label>
                    <p className="text-xs text-gray-400">
                      Each row becomes a separate commitment in your forecast
                    </p>
                  </div>
                  <button type="button" onClick={addInstallmentRow}
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                    + Add row
                  </button>
                </div>

                <div className="space-y-2">
                  {installments.map((inst, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                      <div className="col-span-3">
                        {idx === 0 && <label className="label">Type</label>}
                        <select className="input" value={inst.installment_type}
                          onChange={e => setInstallments(prev =>
                            prev.map((r, i) => i === idx
                              ? { ...r, installment_type: e.target.value, label: INSTALLMENT_LABELS[e.target.value] || r.label }
                              : r
                            )
                          )}>
                          {Object.entries(INSTALLMENT_LABELS).map(([v, l]) => (
                            <option key={v} value={v}>{l}</option>
                          ))}
                        </select>
                      </div>
                      <div className="col-span-3">
                        {idx === 0 && <label className="label">Label</label>}
                        <input className="input" placeholder="e.g. 30% deposit" value={inst.label}
                          onChange={e => setInstallments(prev =>
                            prev.map((r, i) => i === idx ? { ...r, label: e.target.value } : r)
                          )} />
                      </div>
                      <div className="col-span-3">
                        {idx === 0 && <label className="label">Amount ($)</label>}
                        <input className="input" type="number" step="0.01" placeholder="0.00" value={inst.amount}
                          onChange={e => setInstallments(prev =>
                            prev.map((r, i) => i === idx ? { ...r, amount: e.target.value } : r)
                          )} />
                      </div>
                      <div className="col-span-2">
                        {idx === 0 && <label className="label">Due Date</label>}
                        <input className="input" type="date" value={inst.due_date}
                          onChange={e => setInstallments(prev =>
                            prev.map((r, i) => i === idx ? { ...r, due_date: e.target.value } : r)
                          )} />
                      </div>
                      <div className="col-span-1 flex justify-center pb-0.5">
                        {installments.length > 1 && (
                          <button type="button" onClick={() => removeInstallmentRow(idx)}
                            className="text-red-400 hover:text-red-600 text-lg font-bold leading-none">×</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Running total vs PO total */}
                <div className="mt-3 flex items-center justify-between text-sm border-t border-gray-100 pt-2">
                  <span className="text-gray-500">Total of installments</span>
                  <span className={`font-mono font-bold ${
                    form.total_amount && Math.abs(totalInstallmentAmount - parseFloat(form.total_amount)) > 0.01
                      ? "text-red-600"
                      : "text-green-600"
                  }`}>
                    {fmt(totalInstallmentAmount)}
                    {form.total_amount && Math.abs(totalInstallmentAmount - parseFloat(form.total_amount)) > 0.01 && (
                      <span className="text-xs font-normal text-red-500 ml-2">
                        (PO total is {fmt(form.total_amount)})
                      </span>
                    )}
                  </span>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="submit"
                  className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700">
                  Create Purchase Order
                </button>
                <button type="button" onClick={() => setShowAdd(false)}
                  className="flex-1 border border-gray-200 py-3 rounded-xl text-gray-700 hover:bg-gray-50">
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
