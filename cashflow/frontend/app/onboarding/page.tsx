"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { business as bizApi, cashAccounts as caApi, setBusinessId } from "@/lib/api";

const INDUSTRIES = [
  "Retail", "E-commerce", "Restaurant / Food Service", "Professional Services",
  "Manufacturing", "Construction", "SaaS / Software", "Healthcare",
  "Real Estate", "Wholesale / Distribution", "Other",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [bizName, setBizName] = useState("");
  const [industry, setIndustry] = useState("");
  const [reserve, setReserve] = useState("10000");
  const [accName, setAccName] = useState("Operating Checking");
  const [accBalance, setAccBalance] = useState("");
  const [loading, setLoading] = useState(false);
  const [bizId, setBizId] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function createBusiness() {
    if (!bizName.trim()) { setError("Business name is required"); return; }
    setLoading(true);
    setError("");
    try {
      const biz = await bizApi.create({
        name: bizName,
        industry: industry || undefined,
        minimum_cash_reserve: parseFloat(reserve) || 0,
      });
      setBizId(biz.id);
      setBusinessId(biz.id);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create business");
    } finally { setLoading(false); }
  }

  async function addAccount() {
    if (!bizId || !accBalance) { setError("Enter your current balance"); return; }
    setLoading(true);
    setError("");
    try {
      await caApi.create({
        name: accName,
        account_type: "checking",
        current_balance: parseFloat(accBalance),
      } as unknown as Parameters<typeof caApi.create>[0]);
      router.replace("/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add account");
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex gap-2 mb-8">
          {[1, 2].map(s => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? "bg-white" : "bg-white/30"}`} />
          ))}
        </div>

        <div className="bg-white rounded-2xl p-8 shadow-xl">
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Set up your business</h2>
                <p className="text-gray-500 mt-1">Tell us about your business to personalize your cash flow dashboard.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
                <input type="text" value={bizName} onChange={e => setBizName(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Acme Trading Co." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                <select value={industry} onChange={e => setIndustry(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">Select an industry...</option>
                  {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Minimum Cash Reserve ($)
                </label>
                <p className="text-xs text-gray-400 mb-1">
                  The minimum amount you always want to keep in the bank. We&apos;ll warn you before you dip below this.
                </p>
                <input type="number" step="1000" value={reserve} onChange={e => setReserve(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. 25000" />
              </div>
              {error && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">{error}</div>}
              <button onClick={createBusiness} disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50">
                {loading ? "Creating..." : "Continue →"}
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Add your bank account</h2>
                <p className="text-gray-500 mt-1">Enter your current cash balance so we can calculate Safe to Spend.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Account Name</label>
                <input type="text" value={accName} onChange={e => setAccName(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Current Balance ($) *</label>
                <p className="text-xs text-gray-400 mb-1">What&apos;s in your bank account right now?</p>
                <input type="number" step="0.01" value={accBalance} onChange={e => setAccBalance(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. 85000" />
              </div>
              {error && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">{error}</div>}
              <button onClick={addAccount} disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50">
                {loading ? "Saving..." : "Go to Dashboard →"}
              </button>
              <button onClick={() => router.replace("/home")}
                className="w-full text-gray-500 text-sm hover:text-gray-700">
                Skip — I&apos;ll add an account later
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
