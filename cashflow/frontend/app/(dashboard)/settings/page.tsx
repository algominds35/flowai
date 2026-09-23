"use client";
import { useEffect, useState } from "react";
import {
  business as bizApi, cashAccounts as caApi, creditCards as ccApi,
  type Business, type CashAccount, type CreditCard,
} from "@/lib/api";
import { getBusinessId } from "@/lib/api";
import { fmt } from "@/lib/utils";
import { Save, Plus, CreditCard as CardIcon, Landmark } from "lucide-react";

export default function SettingsPage() {
  const [biz, setBiz] = useState<Business | null>(null);
  const [accounts, setAccounts] = useState<CashAccount[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [showAddCard, setShowAddCard] = useState(false);
  const [reserve, setReserve] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [accForm, setAccForm] = useState({ name: "", account_type: "checking", institution_name: "", current_balance: "" });
  const [cardForm, setCardForm] = useState({
    name: "", last_four: "", card_network: "visa", credit_limit: "",
    statement_closing_day: "25", payment_due_days: "21",
  });

  useEffect(() => { load(); }, []);

  async function load() {
    const id = getBusinessId();
    if (!id) return;
    const [bs, accs, ccs] = await Promise.all([
      bizApi.list().then(r => r[0]),
      caApi.list(),
      ccApi.list(),
    ]);
    setBiz(bs);
    setName(bs?.name || "");
    setIndustry(bs?.industry || "");
    setReserve(bs?.minimum_cash_reserve || "0");
    setAccounts(accs);
    setCards(ccs);
  }

  async function saveBusiness() {
    if (!biz) return;
    setSaving(true);
    try {
      const updated = await bizApi.update(biz.id, {
        name,
        industry: industry || undefined,
        minimum_cash_reserve: parseFloat(reserve),
      } as unknown as Parameters<typeof bizApi.update>[1]);
      setBiz(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  }

  async function addAccount(e: React.FormEvent) {
    e.preventDefault();
    await caApi.create({
      ...accForm,
      current_balance: parseFloat(accForm.current_balance),
    } as unknown as Parameters<typeof caApi.create>[0]);
    setShowAddAccount(false);
    setAccForm({ name: "", account_type: "checking", institution_name: "", current_balance: "" });
    const accs = await caApi.list();
    setAccounts(accs);
  }

  async function addCard(e: React.FormEvent) {
    e.preventDefault();
    await ccApi.create({
      ...cardForm,
      credit_limit: cardForm.credit_limit ? parseFloat(cardForm.credit_limit) : undefined,
      statement_closing_day: parseInt(cardForm.statement_closing_day),
      payment_due_days: parseInt(cardForm.payment_due_days),
    } as Parameters<typeof ccApi.create>[0]);
    setShowAddCard(false);
    const ccs = await ccApi.list();
    setCards(ccs);
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Business profile, accounts, and preferences</p>
      </div>

      {/* Business */}
      <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <h2 className="font-semibold text-gray-800">Business Profile</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Business Name</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Industry</label>
            <input className="input" value={industry} onChange={e => setIndustry(e.target.value)}
              placeholder="e.g. Retail, SaaS, Manufacturing" />
          </div>
          <div className="col-span-2">
            <label className="label">Minimum Cash Reserve ($)</label>
            <p className="text-xs text-gray-400 mb-1">
              Always keep at least this much cash in the bank. Affects Safe to Spend calculation.
            </p>
            <input className="input" type="number" step="100" value={reserve}
              onChange={e => setReserve(e.target.value)} />
          </div>
        </div>
        <button onClick={saveBusiness} disabled={saving}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            saved
              ? "bg-green-500 text-white"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}>
          <Save size={14} />
          {saved ? "Saved!" : saving ? "Saving..." : "Save Changes"}
        </button>
      </section>

      {/* Cash Accounts */}
      <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Cash Accounts</h2>
          <button onClick={() => setShowAddAccount(true)}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700">
            <Plus size={14} /> Add Account
          </button>
        </div>
        {accounts.length === 0 ? (
          <p className="text-sm text-gray-400">No accounts yet. Add your bank account to get started.</p>
        ) : (
          <div className="space-y-3">
            {accounts.map(acc => (
              <div key={acc.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Landmark size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{acc.name}</p>
                    <p className="text-xs text-gray-400 capitalize">
                      {acc.institution_name ? `${acc.institution_name} · ` : ""}{acc.account_type}
                    </p>
                  </div>
                </div>
                <p className="font-mono font-semibold text-gray-900">{fmt(acc.current_balance)}</p>
              </div>
            ))}
          </div>
        )}

        {showAddAccount && (
          <form onSubmit={addAccount} className="border border-blue-100 rounded-xl p-4 bg-blue-50 space-y-3">
            <p className="text-sm font-medium text-blue-800">New Cash Account</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Account Name</label>
                <input className="input" required value={accForm.name}
                  onChange={e => setAccForm(f => ({...f, name: e.target.value}))}
                  placeholder="e.g. Operating Checking" />
              </div>
              <div>
                <label className="label">Type</label>
                <select className="input" value={accForm.account_type}
                  onChange={e => setAccForm(f => ({...f, account_type: e.target.value}))}>
                  <option value="checking">Checking</option>
                  <option value="savings">Savings</option>
                  <option value="money_market">Money Market</option>
                  <option value="payroll">Payroll</option>
                </select>
              </div>
              <div>
                <label className="label">Bank / Institution</label>
                <input className="input" value={accForm.institution_name}
                  onChange={e => setAccForm(f => ({...f, institution_name: e.target.value}))} />
              </div>
              <div>
                <label className="label">Current Balance ($)</label>
                <input className="input" type="number" step="0.01" required value={accForm.current_balance}
                  onChange={e => setAccForm(f => ({...f, current_balance: e.target.value}))} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium">
                Add Account
              </button>
              <button type="button" onClick={() => setShowAddAccount(false)}
                className="flex-1 border border-gray-200 py-2 rounded-lg text-sm text-gray-700">
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>

      {/* Credit Cards */}
      <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-800">Credit Cards</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Bank cash only decreases when the card statement is paid, not on individual purchases
            </p>
          </div>
          <button onClick={() => setShowAddCard(true)}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700">
            <Plus size={14} /> Add Card
          </button>
        </div>
        {cards.length === 0 ? (
          <p className="text-sm text-gray-400">No credit cards yet.</p>
        ) : (
          <div className="space-y-3">
            {cards.map(card => (
              <div key={card.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <CardIcon size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{card.name}</p>
                    <p className="text-xs text-gray-400 capitalize">
                      {card.card_network} {card.last_four ? `···· ${card.last_four}` : ""}
                      {card.statement_closing_day ? ` · closes day ${card.statement_closing_day}` : ""}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-mono font-semibold text-gray-900">{fmt(card.current_balance)}</p>
                  {card.credit_limit && (
                    <p className="text-xs text-gray-400">of {fmt(card.credit_limit)} limit</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {showAddCard && (
          <form onSubmit={addCard} className="border border-blue-100 rounded-xl p-4 bg-blue-50 space-y-3">
            <p className="text-sm font-medium text-blue-800">New Credit Card</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Card Name</label>
                <input className="input" required value={cardForm.name}
                  onChange={e => setCardForm(f => ({...f, name: e.target.value}))}
                  placeholder="e.g. Chase Ink" />
              </div>
              <div>
                <label className="label">Network</label>
                <select className="input" value={cardForm.card_network}
                  onChange={e => setCardForm(f => ({...f, card_network: e.target.value}))}>
                  <option value="visa">Visa</option>
                  <option value="mastercard">Mastercard</option>
                  <option value="amex">Amex</option>
                  <option value="discover">Discover</option>
                </select>
              </div>
              <div>
                <label className="label">Last 4 digits</label>
                <input className="input" maxLength={4} value={cardForm.last_four}
                  onChange={e => setCardForm(f => ({...f, last_four: e.target.value}))} />
              </div>
              <div>
                <label className="label">Credit Limit ($)</label>
                <input className="input" type="number" step="100" value={cardForm.credit_limit}
                  onChange={e => setCardForm(f => ({...f, credit_limit: e.target.value}))} />
              </div>
              <div>
                <label className="label">Statement closes day</label>
                <input className="input" type="number" min={1} max={31} value={cardForm.statement_closing_day}
                  onChange={e => setCardForm(f => ({...f, statement_closing_day: e.target.value}))} />
              </div>
              <div>
                <label className="label">Payment due (days after close)</label>
                <input className="input" type="number" min={1} value={cardForm.payment_due_days}
                  onChange={e => setCardForm(f => ({...f, payment_due_days: e.target.value}))} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium">
                Add Card
              </button>
              <button type="button" onClick={() => setShowAddCard(false)}
                className="flex-1 border border-gray-200 py-2 rounded-lg text-sm text-gray-700">
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
