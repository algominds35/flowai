"use client";
import { useEffect, useState } from "react";
import { creditCards as api, type CreditCard } from "@/lib/api";
import { fmt, fmtDate, fmtShortDate } from "@/lib/utils";
import { CreditCard as CardIcon, Plus, AlertCircle, Info, Calendar } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cashflow_token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string>),
    },
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

interface CCTransaction {
  id: string;
  credit_card_id: string;
  description: string;
  merchant: string | null;
  amount: string;
  transaction_date: string;
  category: string | null;
  is_reconciled: boolean;
  statement_id: string | null;
}

interface CCStatement {
  id: string;
  credit_card_id: string;
  statement_date: string;
  payment_due_date: string;
  balance: string;
  minimum_payment: string | null;
  is_paid: boolean;
  paid_date: string | null;
  paid_amount: string | null;
}

export default function CreditCardsPage() {
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [selectedCard, setSelectedCard] = useState<CreditCard | null>(null);
  const [transactions, setTransactions] = useState<CCTransaction[]>([]);
  const [statements, setStatements] = useState<CCStatement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddTx, setShowAddTx] = useState(false);
  const [txForm, setTxForm] = useState({
    description: "", merchant: "", amount: "",
    transaction_date: new Date().toISOString().slice(0, 10), category: "",
  });

  useEffect(() => { loadCards(); }, []);
  useEffect(() => { if (selectedCard) loadCardDetail(selectedCard.id); }, [selectedCard]);

  async function loadCards() {
    setLoading(true);
    try {
      const list = await api.list();
      setCards(list);
      if (list.length > 0 && !selectedCard) setSelectedCard(list[0]);
    } finally { setLoading(false); }
  }

  async function loadCardDetail(cardId: string) {
    try {
      const [txs, stmts] = await Promise.all([
        apiFetch<CCTransaction[]>(`/api/v1/credit-cards/${cardId}/transactions`).catch(() => []),
        apiFetch<CCStatement[]>(`/api/v1/credit-cards/${cardId}/statements`).catch(() => []),
      ]);
      setTransactions(txs);
      setStatements(stmts);
    } catch { /* endpoints may return empty */ }
  }

  async function addTransaction(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedCard) return;
    await apiFetch(`/api/v1/credit-cards/${selectedCard.id}/transactions`, {
      method: "POST",
      body: JSON.stringify({
        ...txForm,
        amount: parseFloat(txForm.amount),
      }),
    });
    setShowAddTx(false);
    setTxForm({ description: "", merchant: "", amount: "", transaction_date: new Date().toISOString().slice(0, 10), category: "" });
    loadCardDetail(selectedCard.id);
    loadCards();
  }

  async function closeStatement(cardId: string) {
    await apiFetch(`/api/v1/credit-cards/${cardId}/close-statement`, { method: "POST" }).catch(() => null);
    loadCardDetail(cardId);
    loadCards();
  }

  const utilization = selectedCard && selectedCard.credit_limit
    ? (parseFloat(selectedCard.current_balance) / parseFloat(selectedCard.credit_limit)) * 100
    : null;

  // Next statement/payment dates
  const nextStatement = selectedCard?.statement_closing_day
    ? (() => {
        const today = new Date();
        const closing = new Date(today.getFullYear(), today.getMonth(), selectedCard.statement_closing_day);
        if (closing <= today) closing.setMonth(closing.getMonth() + 1);
        return closing.toISOString().slice(0, 10);
      })()
    : null;

  const nextPayment = nextStatement && selectedCard
    ? (() => {
        const d = new Date(nextStatement);
        d.setDate(d.getDate() + selectedCard.payment_due_days);
        return d.toISOString().slice(0, 10);
      })()
    : null;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Credit Cards</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Card purchases don&apos;t affect your bank cash — only statement payments do
        </p>
      </div>

      {/* How it works */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
        <Info size={16} className="text-blue-500 mt-0.5 shrink-0" />
        <div className="text-sm text-blue-800">
          <strong>How credit cards work in CashFlow:</strong> When you make a purchase, your bank balance doesn&apos;t change — the card balance increases. Your bank cash only decreases when you <em>pay the statement</em>. Each upcoming statement payment is automatically added as a commitment in your forecast.
        </div>
      </div>

      {loading ? (
        <div className="h-48 bg-gray-200 rounded-xl animate-pulse" />
      ) : cards.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <CardIcon className="mx-auto text-gray-300 mb-3" size={48} />
          <p className="text-gray-500 mb-1">No credit cards set up.</p>
          <p className="text-sm text-gray-400 mb-4">Add your cards in Settings to start tracking purchases.</p>
          <a href="/settings"
            className="inline-block bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
            Go to Settings
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Card selector */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Your Cards</h2>
            {cards.map(card => (
              <button
                key={card.id}
                onClick={() => setSelectedCard(card)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  selectedCard?.id === card.id
                    ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                    : "border-gray-200 bg-white hover:border-blue-200"
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <CardIcon size={18} className="text-gray-400" />
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">{card.name}</p>
                    <p className="text-xs text-gray-400 capitalize">
                      {card.card_network}{card.last_four ? ` ···· ${card.last_four}` : ""}
                    </p>
                  </div>
                </div>
                <p className="text-xl font-bold text-gray-900">{fmt(card.current_balance)}</p>
                {card.credit_limit && (
                  <>
                    <div className="mt-2 h-1.5 bg-gray-100 rounded-full">
                      <div
                        className={`h-full rounded-full transition-all ${
                          parseFloat(card.current_balance) / parseFloat(card.credit_limit) > 0.8
                            ? "bg-red-500" : "bg-blue-500"
                        }`}
                        style={{
                          width: `${Math.min(
                            (parseFloat(card.current_balance) / parseFloat(card.credit_limit)) * 100,
                            100
                          )}%`
                        }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {fmt(card.current_balance)} of {fmt(card.credit_limit)} limit
                    </p>
                  </>
                )}
              </button>
            ))}
          </div>

          {/* Card detail */}
          {selectedCard && (
            <div className="lg:col-span-2 space-y-5">

              {/* Card stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500 font-medium uppercase">Current Balance</p>
                  <p className="text-xl font-bold text-gray-900 mt-1">{fmt(selectedCard.current_balance)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">Unpaid purchases</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500 font-medium uppercase">Statement Closes</p>
                  <p className="text-xl font-bold text-gray-900 mt-1">
                    {selectedCard.statement_closing_day ? `Day ${selectedCard.statement_closing_day}` : "—"}
                  </p>
                  {nextStatement && (
                    <p className="text-xs text-gray-400 mt-0.5">Next: {fmtShortDate(nextStatement)}</p>
                  )}
                </div>
                <div className={`bg-white border rounded-xl p-4 ${
                  nextPayment && new Date(nextPayment) < new Date(Date.now() + 7 * 86400000)
                    ? "border-orange-300 bg-orange-50"
                    : "border-gray-200"
                }`}>
                  <p className="text-xs text-gray-500 font-medium uppercase flex items-center gap-1">
                    <Calendar size={11} /> Payment Due
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-1">
                    {nextPayment ? fmtShortDate(nextPayment) : "—"}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {selectedCard.payment_due_days}d after close
                  </p>
                </div>
              </div>

              {/* Statements */}
              {statements.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                    <h3 className="font-semibold text-gray-800 text-sm">Recent Statements</h3>
                    <p className="text-xs text-gray-400">Statement payment = bank cash outflow</p>
                  </div>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left px-5 py-2 text-gray-500 font-medium text-xs">Statement Date</th>
                        <th className="text-left px-5 py-2 text-gray-500 font-medium text-xs">Payment Due</th>
                        <th className="text-right px-5 py-2 text-gray-500 font-medium text-xs">Balance</th>
                        <th className="text-left px-5 py-2 text-gray-500 font-medium text-xs">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {statements.map(stmt => (
                        <tr key={stmt.id} className="hover:bg-gray-50">
                          <td className="px-5 py-3 text-gray-700">{fmtDate(stmt.statement_date)}</td>
                          <td className="px-5 py-3">
                            <span className={
                              !stmt.is_paid && new Date(stmt.payment_due_date) < new Date()
                                ? "text-red-600 font-medium"
                                : "text-gray-700"
                            }>
                              {fmtDate(stmt.payment_due_date)}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-right font-mono font-semibold text-gray-900">
                            {fmt(stmt.balance)}
                          </td>
                          <td className="px-5 py-3">
                            {stmt.is_paid ? (
                              <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full">
                                Paid {stmt.paid_date ? fmtShortDate(stmt.paid_date) : ""}
                              </span>
                            ) : (
                              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                                new Date(stmt.payment_due_date) < new Date()
                                  ? "text-red-600 bg-red-50"
                                  : "text-orange-600 bg-orange-50"
                              }`}>
                                {new Date(stmt.payment_due_date) < new Date() ? "Overdue" : "Pending"}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Transactions */}
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-800 text-sm">Transactions</h3>
                    <p className="text-xs text-gray-400">These do NOT reduce bank cash — only statement payments do</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => closeStatement(selectedCard.id)}
                      className="text-xs border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50"
                    >
                      Close Statement
                    </button>
                    <button
                      onClick={() => setShowAddTx(true)}
                      className="flex items-center gap-1.5 text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700"
                    >
                      <Plus size={12} /> Add Purchase
                    </button>
                  </div>
                </div>

                {transactions.length === 0 ? (
                  <div className="p-8 text-center">
                    <p className="text-gray-400 text-sm">No transactions yet.</p>
                    <button onClick={() => setShowAddTx(true)}
                      className="mt-2 text-blue-600 text-sm hover:underline">
                      Log a purchase
                    </button>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-100">
                      <tr>
                        <th className="text-left px-5 py-2.5 text-gray-500 font-medium text-xs">Description</th>
                        <th className="text-left px-5 py-2.5 text-gray-500 font-medium text-xs">Date</th>
                        <th className="text-left px-5 py-2.5 text-gray-500 font-medium text-xs">Category</th>
                        <th className="text-right px-5 py-2.5 text-gray-500 font-medium text-xs">Amount</th>
                        <th className="text-left px-5 py-2.5 text-gray-500 font-medium text-xs">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {transactions.map(tx => (
                        <tr key={tx.id} className="hover:bg-gray-50">
                          <td className="px-5 py-3">
                            <p className="font-medium text-gray-900">{tx.description}</p>
                            {tx.merchant && <p className="text-xs text-gray-400">{tx.merchant}</p>}
                          </td>
                          <td className="px-5 py-3 text-gray-600">{fmtDate(tx.transaction_date)}</td>
                          <td className="px-5 py-3 text-xs text-gray-500 capitalize">
                            {tx.category || "—"}
                          </td>
                          <td className="px-5 py-3 text-right font-mono font-semibold text-gray-900">
                            {fmt(tx.amount)}
                          </td>
                          <td className="px-5 py-3">
                            {tx.is_reconciled ? (
                              <span className="text-xs text-green-600 font-medium">Reconciled</span>
                            ) : tx.statement_id ? (
                              <span className="text-xs text-blue-600 font-medium">On statement</span>
                            ) : (
                              <span className="text-xs text-gray-400">Open</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Transaction Modal */}
      {showAddTx && selectedCard && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-lg font-bold text-gray-900 mb-1">Log Card Purchase</h2>
            <p className="text-sm text-gray-400 mb-4">
              This will increase your card balance but <strong>not</strong> reduce bank cash.
              Bank cash only decreases when you pay the statement.
            </p>
            <form onSubmit={addTransaction} className="space-y-3">
              <div>
                <label className="label">Description *</label>
                <input className="input" required value={txForm.description}
                  onChange={e => setTxForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="e.g. Office supplies — Staples" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Amount ($) *</label>
                  <input className="input" type="number" step="0.01" required value={txForm.amount}
                    onChange={e => setTxForm(f => ({ ...f, amount: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Date</label>
                  <input className="input" type="date" value={txForm.transaction_date}
                    onChange={e => setTxForm(f => ({ ...f, transaction_date: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Merchant</label>
                  <input className="input" value={txForm.merchant}
                    onChange={e => setTxForm(f => ({ ...f, merchant: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Category</label>
                  <input className="input" value={txForm.category}
                    placeholder="e.g. supplies, travel"
                    onChange={e => setTxForm(f => ({ ...f, category: e.target.value }))} />
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle size={14} className="text-blue-500 mt-0.5 shrink-0" />
                <p className="text-xs text-blue-700">
                  Card: <strong>{selectedCard.name}</strong> · Current balance: <strong>{fmt(selectedCard.current_balance)}</strong> → will become <strong>{fmt((parseFloat(selectedCard.current_balance) + (parseFloat(txForm.amount) || 0)).toString())}</strong>
                </p>
              </div>
              <div className="flex gap-3 pt-1">
                <button type="submit"
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-semibold hover:bg-blue-700">
                  Log Purchase
                </button>
                <button type="button" onClick={() => setShowAddTx(false)}
                  className="flex-1 border border-gray-200 py-2.5 rounded-xl text-gray-700 hover:bg-gray-50">
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
