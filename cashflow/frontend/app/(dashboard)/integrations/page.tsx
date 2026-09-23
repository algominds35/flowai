"use client";
import { useEffect, useState } from "react";
import { integrations as api, type IntegrationStatus } from "@/lib/api";
import { RefreshCw, CheckCircle, XCircle, AlertTriangle, ExternalLink } from "lucide-react";

export default function IntegrationsPage() {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [shopDomain, setShopDomain] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setStatus(await api.status()); }
    finally { setLoading(false); }
  }

  async function syncProvider(name: string, fn: () => Promise<unknown>) {
    setSyncing(name);
    try {
      await fn();
      await load();
    } catch (e) {
      alert(`Sync error: ${e}`);
    } finally { setSyncing(null); }
  }

  if (loading) return (
    <div className="p-8 space-y-4 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-48" />
      {[...Array(4)].map((_, i) => <div key={i} className="h-40 bg-gray-200 rounded-xl" />)}
    </div>
  );

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-sm text-gray-500 mt-0.5">Connect your bank, accounting, and ecommerce platforms</p>
      </div>

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Plaid */}
          <IntegrationCard
            name="Plaid"
            description="Bank account transaction sync"
            logo="🏦"
            connected={status.plaid.connected}
            mode={status.plaid.mode}
            detail={`${(status.plaid.items as object[]).length} account(s) linked`}
            credential={
              status.plaid.mode === "fixture"
                ? "Requires: PLAID_CLIENT_ID, PLAID_SECRET (Plaid dashboard → Keys)"
                : undefined
            }
            onSync={() => syncProvider("plaid", api.plaidSync)}
            syncing={syncing === "plaid"}
          />

          {/* QuickBooks */}
          <IntegrationCard
            name="QuickBooks Online"
            description="Invoices, bills, and chart of accounts"
            logo="📚"
            connected={status.quickbooks.connected}
            mode={status.quickbooks.mode}
            detail={status.quickbooks.company || status.quickbooks.status}
            credential={
              status.quickbooks.mode === "fixture"
                ? "Requires: QBO_CLIENT_ID, QBO_CLIENT_SECRET (Intuit Developer → Apps)"
                : undefined
            }
            onConnect={async () => {
              const r = await api.qboConnect();
              window.open(r.oauth_url, "_blank");
            }}
            onSync={() => syncProvider("qbo", api.qboSync)}
            syncing={syncing === "qbo"}
          />

          {/* Shopify */}
          <IntegrationCard
            name="Shopify"
            description="Payout sync — expected and actual disbursements"
            logo="🛒"
            connected={status.shopify.connected}
            mode={status.shopify.mode}
            detail={`${(status.shopify.shops as object[]).length} shop(s) connected`}
            credential={
              status.shopify.mode === "fixture"
                ? "Requires: SHOPIFY_API_KEY, SHOPIFY_API_SECRET + Shopify Partner approval"
                : undefined
            }
            shopifyConnect={!status.shopify.connected}
            shopDomain={shopDomain}
            onShopDomainChange={setShopDomain}
            onConnect={async () => {
              if (!shopDomain) { alert("Enter your Shopify store domain"); return; }
              const r = await api.shopifyConnect(shopDomain);
              window.open(r.oauth_url, "_blank");
            }}
            onSync={() => syncProvider("shopify", api.shopifySync)}
            syncing={syncing === "shopify"}
          />

          {/* Amazon */}
          <IntegrationCard
            name="Amazon Marketplace"
            description="Settlement and disbursement sync (SP-API)"
            logo="📦"
            connected={status.amazon.connected}
            mode={status.amazon.mode}
            detail={`${(status.amazon.accounts as object[]).length} account(s)`}
            credential={
              status.amazon.mode === "fixture"
                ? [
                    "Requires Amazon Seller Central API approval:",
                    "1. Register app in Seller Central → Developer Console",
                    "2. Request SP-API access (may take 1–5 business days)",
                    "3. Set AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET, AMAZON_REFRESH_TOKEN",
                  ].join("\n")
                : (status.amazon as { _blocker?: string })._blocker
            }
            onSync={() => syncProvider("amazon", api.amazonSync)}
            syncing={syncing === "amazon"}
          />
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <p className="text-sm font-semibold text-blue-800 mb-1">Fixture Mode</p>
        <p className="text-sm text-blue-700">
          Integrations in <strong>fixture mode</strong> use realistic sample data so you can explore the app
          without live credentials. All data flows through the same sync pipeline — only the data source differs.
          Once you add API keys to <code className="bg-blue-100 px-1 rounded">.env</code>, restart the backend
          and re-sync.
        </p>
      </div>
    </div>
  );
}

function IntegrationCard({
  name, description, logo, connected, mode, detail, credential,
  onConnect, onSync, syncing, shopifyConnect, shopDomain, onShopDomainChange,
}: {
  name: string;
  description: string;
  logo: string;
  connected: boolean;
  mode: string;
  detail: string;
  credential?: string;
  onConnect?: () => void;
  onSync?: () => void;
  syncing?: boolean;
  shopifyConnect?: boolean;
  shopDomain?: string;
  onShopDomainChange?: (v: string) => void;
}) {
  const isFixture = mode === "fixture" || mode === "demo" || mode === "not_configured";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{logo}</span>
          <div>
            <p className="font-semibold text-gray-900">{name}</p>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        </div>
        {connected ? (
          <span className="flex items-center gap-1 text-xs text-green-600 font-medium bg-green-50 px-2 py-1 rounded-full">
            <CheckCircle size={12} /> Connected
          </span>
        ) : isFixture ? (
          <span className="flex items-center gap-1 text-xs text-yellow-600 font-medium bg-yellow-50 px-2 py-1 rounded-full">
            <AlertTriangle size={12} /> Fixture
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-gray-500 font-medium bg-gray-50 px-2 py-1 rounded-full">
            <XCircle size={12} /> Not connected
          </span>
        )}
      </div>

      <p className="text-sm text-gray-600">{detail}</p>

      {credential && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-xs text-amber-700 font-medium mb-1">Required credentials</p>
          <pre className="text-xs text-amber-600 whitespace-pre-wrap">{credential}</pre>
        </div>
      )}

      {shopifyConnect && onShopDomainChange && (
        <div>
          <label className="text-xs text-gray-500 font-medium">Shop domain</label>
          <input
            className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="your-store.myshopify.com"
            value={shopDomain}
            onChange={e => onShopDomainChange(e.target.value)}
          />
        </div>
      )}

      <div className="flex gap-2">
        {onSync && (
          <button
            onClick={onSync}
            disabled={syncing}
            className="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing..." : "Sync Now"}
          </button>
        )}
        {onConnect && (
          <button
            onClick={onConnect}
            className="flex items-center gap-1.5 text-sm border border-gray-200 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50"
          >
            <ExternalLink size={13} />
            Connect
          </button>
        )}
      </div>
    </div>
  );
}
