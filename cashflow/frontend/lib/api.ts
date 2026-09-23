const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Auth helpers ─────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cashflow_token");
}

export function setToken(token: string) {
  localStorage.setItem("cashflow_token", token);
}

export function clearToken() {
  localStorage.removeItem("cashflow_token");
  localStorage.removeItem("cashflow_business_id");
}

export function getBusinessId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cashflow_business_id");
}

export function setBusinessId(id: string) {
  localStorage.setItem("cashflow_business_id", id);
}

// ── Core fetch ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  register: (email: string, password: string, full_name: string) =>
    apiFetch<{ access_token: string }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => apiFetch<User>("/api/v1/auth/me"),
};

// ── Business ─────────────────────────────────────────────────────────────────

export const business = {
  create: (data: { name: string; industry?: string; minimum_cash_reserve?: number }) =>
    apiFetch<Business>("/api/v1/businesses", { method: "POST", body: JSON.stringify(data) }),

  list: () => apiFetch<Business[]>("/api/v1/businesses/mine"),

  update: (id: string, data: Partial<Business>) =>
    apiFetch<Business>(`/api/v1/businesses/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  onboarding: (id: string, step: number) =>
    apiFetch<Business>(`/api/v1/businesses/${id}/onboarding`, {
      method: "POST",
      body: JSON.stringify({ step }),
    }),
};

// ── Dashboard / Safe-to-Spend ─────────────────────────────────────────────────

export const dashboard = {
  safeToSpend: (horizonWeeks = 8) =>
    apiFetch<SafeToSpendData>(`/api/v1/dashboard/safe-to-spend?horizon_weeks=${horizonWeeks}`),
};

// ── Cash Accounts ─────────────────────────────────────────────────────────────

export const cashAccounts = {
  list: () => apiFetch<CashAccount[]>("/api/v1/cash-accounts"),
  create: (data: Partial<CashAccount>) =>
    apiFetch<CashAccount>("/api/v1/cash-accounts", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CashAccount>) =>
    apiFetch<CashAccount>(`/api/v1/cash-accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/cash-accounts/${id}`, { method: "DELETE" }),
};

// ── Commitments ───────────────────────────────────────────────────────────────

export const commitments = {
  list: (params?: { status?: string; category?: string; overdue_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.category) q.set("category", params.category);
    if (params?.overdue_only) q.set("overdue_only", "true");
    return apiFetch<Commitment[]>(`/api/v1/commitments?${q}`);
  },
  create: (data: Partial<Commitment>) =>
    apiFetch<Commitment>("/api/v1/commitments", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Commitment>) =>
    apiFetch<Commitment>(`/api/v1/commitments/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  markPaid: (id: string) =>
    apiFetch<Commitment>(`/api/v1/commitments/${id}/mark-paid`, { method: "POST" }),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/commitments/${id}`, { method: "DELETE" }),
};

// ── Receivables ───────────────────────────────────────────────────────────────

export const receivables = {
  list: (params?: { status?: string; overdue_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.overdue_only) q.set("overdue_only", "true");
    return apiFetch<Receivable[]>(`/api/v1/receivables?${q}`);
  },
  create: (data: Partial<Receivable>) =>
    apiFetch<Receivable>("/api/v1/receivables", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Receivable>) =>
    apiFetch<Receivable>(`/api/v1/receivables/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  recordPayment: (id: string, amount: number, received_date: string) =>
    apiFetch<Receivable>(`/api/v1/receivables/${id}/payments`, {
      method: "POST",
      body: JSON.stringify({ amount, received_date }),
    }),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/receivables/${id}`, { method: "DELETE" }),
};

// ── Forecast ──────────────────────────────────────────────────────────────────

export const forecast = {
  current: () => apiFetch<ForecastSnapshot>("/api/v1/forecast/current"),
  compute: (horizonWeeks = 13) =>
    apiFetch<ForecastSnapshot>(`/api/v1/forecast/compute?horizon_weeks=${horizonWeeks}`, { method: "POST" }),
  history: () => apiFetch<ForecastSnapshot[]>("/api/v1/forecast/history"),
};

// ── Alerts ────────────────────────────────────────────────────────────────────

export const alerts = {
  list: (unreadOnly = false) =>
    apiFetch<Alert[]>(`/api/v1/alerts?unread_only=${unreadOnly}`),
  generate: () =>
    apiFetch<Alert[]>("/api/v1/alerts/generate", { method: "POST" }),
  markRead: (id: string) =>
    apiFetch<Alert>(`/api/v1/alerts/${id}/read`, { method: "POST" }),
  dismiss: (id: string) =>
    apiFetch<Alert>(`/api/v1/alerts/${id}/dismiss`, { method: "POST" }),
  count: () => apiFetch<{ unread_count: number }>("/api/v1/alerts/count"),
};

// ── Scenarios ─────────────────────────────────────────────────────────────────

export const scenarios = {
  list: () => apiFetch<Scenario[]>("/api/v1/scenarios"),
  create: (data: Partial<Scenario>) =>
    apiFetch<Scenario>("/api/v1/scenarios", { method: "POST", body: JSON.stringify(data) }),
  get: (id: string) => apiFetch<Scenario>(`/api/v1/scenarios/${id}`),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/scenarios/${id}`, { method: "DELETE" }),
};

// ── Credit Cards ──────────────────────────────────────────────────────────────

export const creditCards = {
  list: () => apiFetch<CreditCard[]>("/api/v1/credit-cards"),
  create: (data: Partial<CreditCard>) =>
    apiFetch<CreditCard>("/api/v1/credit-cards", { method: "POST", body: JSON.stringify(data) }),
};

// ── Purchase Orders ───────────────────────────────────────────────────────────

export const purchaseOrders = {
  list: () => apiFetch<PurchaseOrder[]>("/api/v1/purchase-orders"),
  create: (data: Partial<PurchaseOrder>) =>
    apiFetch<PurchaseOrder>("/api/v1/purchase-orders", { method: "POST", body: JSON.stringify(data) }),
};

// ── Weekly Review ─────────────────────────────────────────────────────────────

export const weeklyReview = {
  start: () =>
    apiFetch<WeeklyReviewSession>("/api/v1/weekly-review/start", { method: "POST" }),
  current: () =>
    apiFetch<WeeklyReviewSession | null>("/api/v1/weekly-review/current"),
  actionItem: (sessionId: string, itemId: string, action: string, data?: object) =>
    apiFetch<WeeklyReviewItem>(`/api/v1/weekly-review/${sessionId}/items/${itemId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, ...data }),
    }),
  complete: (sessionId: string) =>
    apiFetch<WeeklyReviewSession>(`/api/v1/weekly-review/${sessionId}/complete`, { method: "POST" }),
};

// ── Integrations ──────────────────────────────────────────────────────────────

export const integrations = {
  status: () => apiFetch<IntegrationStatus>("/api/v1/integrations/status"),
  plaidSync: () =>
    apiFetch<object>("/api/v1/integrations/plaid/sync", { method: "POST" }),
  qboSync: () =>
    apiFetch<object>("/api/v1/integrations/qbo/sync", { method: "POST" }),
  shopifySync: () =>
    apiFetch<object>("/api/v1/integrations/shopify/sync", { method: "POST" }),
  amazonSync: () =>
    apiFetch<object>("/api/v1/integrations/amazon/sync", { method: "POST" }),
  qboConnect: () =>
    apiFetch<{ oauth_url: string }>("/api/v1/integrations/qbo/connect"),
  shopifyConnect: (shop: string) =>
    apiFetch<{ oauth_url: string }>(`/api/v1/integrations/shopify/connect?shop=${shop}`),
};

// ── Reconciliation ────────────────────────────────────────────────────────────

export const reconciliation = {
  autoMatch: () =>
    apiFetch<{ matched: number; unmatched: number }>("/api/v1/reconciliation/auto-match", { method: "POST" }),
  transactions: () =>
    apiFetch<Transaction[]>("/api/v1/reconciliation/transactions"),
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Business {
  id: string;
  name: string;
  industry: string | null;
  currency: string;
  minimum_cash_reserve: string;
  fiscal_year_start_month: number;
  onboarding_completed: boolean;
  onboarding_step: number;
  created_at: string;
}

export interface CashAccount {
  id: string;
  business_id: string;
  name: string;
  account_type: string;
  institution_name: string | null;
  last_four: string | null;
  current_balance: string;
  balance_as_of: string | null;
  is_active: boolean;
  include_in_cash_position: boolean;
  created_at: string;
}

export interface Commitment {
  id: string;
  business_id: string;
  name: string;
  description: string | null;
  category: string;
  vendor_name: string | null;
  amount: string;
  amount_paid: string;
  remaining_amount: string;
  currency: string;
  due_date: string;
  paid_date: string | null;
  status: string;
  is_verified: boolean;
  confidence_level: string;
  is_recurring: boolean;
  recurring_frequency: string | null;
  credit_card_id: string | null;
  purchase_order_id: string | null;
  notes: string | null;
  tags: string[];
  created_at: string;
}

export interface Receivable {
  id: string;
  business_id: string;
  name: string;
  description: string | null;
  receivable_type: string;
  customer_name: string | null;
  invoice_number: string | null;
  amount: string;
  amount_received: string;
  remaining_amount: string;
  currency: string;
  invoice_date: string | null;
  expected_date: string;
  received_date: string | null;
  status: string;
  confidence_level: string;
  is_verified: boolean;
  external_source: string | null;
  notes: string | null;
  created_at: string;
}

export interface WeekForecast {
  week_number: number;
  week_start: string;
  week_end: string;
  opening_cash: string;
  expected_inflows: string;
  expected_outflows: string;
  closing_cash: string;
  reserve_threshold: string;
  below_reserve: boolean;
  inflow_items: Array<{ id: string; name: string; amount: string; date: string; confidence: string }>;
  outflow_items: Array<{ id: string; name: string; amount: string; date: string; category: string; confidence: string }>;
}

export interface Component {
  label: string;
  amount: string;
  description: string;
  items: object[];
}

export interface SafeToSpendData {
  safe_to_spend: string;
  current_cash: string;
  minimum_reserve: string;
  total_scheduled_outflows: string;
  total_expected_inflows: string;
  lowest_projected_cash: string;
  lowest_cash_week: string | null;
  has_cash_cliff: boolean;
  cash_cliff_date: string | null;
  cash_cliff_amount: string | null;
  components: Component[];
  weeks: WeekForecast[];
  as_of_date: string;
  horizon_weeks: number;
}

export interface ForecastWeek {
  id: string;
  week_number: number;
  week_start: string;
  week_end: string;
  opening_cash: string;
  expected_inflows: string;
  expected_outflows: string;
  closing_cash: string;
  reserve_threshold: string;
  below_reserve: boolean;
  actual_inflows: string | null;
  actual_outflows: string | null;
  actual_closing_cash: string | null;
  inflow_variance: string | null;
  outflow_variance: string | null;
  cash_variance: string | null;
}

export interface ForecastSnapshot {
  id: string;
  business_id: string;
  computed_at: string;
  as_of_date: string;
  horizon_weeks: number;
  opening_cash: string;
  safe_to_spend: string;
  minimum_cash_reserve: string;
  lowest_projected_cash: string;
  lowest_cash_week: string | null;
  has_cash_cliff: boolean;
  cash_cliff_date: string | null;
  cash_cliff_amount: string | null;
  weeks: ForecastWeek[];
}

export interface Alert {
  id: string;
  business_id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  related_amount: string | null;
  related_date: string | null;
  is_read: boolean;
  is_dismissed: boolean;
  is_resolved: boolean;
  commitment_id: string | null;
  receivable_id: string | null;
  fired_at: string;
}

export interface Scenario {
  id: string;
  business_id: string;
  name: string;
  description: string | null;
  scenario_type: string;
  amount: string;
  start_date: string;
  end_date: string | null;
  frequency: string | null;
  baseline_safe_to_spend: string | null;
  baseline_lowest_cash: string | null;
  projected_safe_to_spend: string | null;
  projected_lowest_cash: string | null;
  can_afford: boolean | null;
  reserve_impact: string | null;
  affected_weeks: string[];
  verdict_message: string | null;
  status: string;
  items: ScenarioItem[];
  created_at: string;
}

export interface ScenarioItem {
  week_start: string;
  baseline_closing_cash: string;
  scenario_closing_cash: string;
  baseline_outflows: string;
  scenario_outflows: string;
  scenario_additional_outflow: string;
}

export interface CreditCard {
  id: string;
  business_id: string;
  name: string;
  last_four: string | null;
  card_network: string | null;
  current_balance: string;
  credit_limit: string | null;
  statement_closing_day: number | null;
  payment_due_days: number;
  is_active: boolean;
  created_at: string;
}

export interface PurchaseOrder {
  id: string;
  business_id: string;
  po_number: string | null;
  supplier_name: string;
  description: string | null;
  total_amount: string;
  amount_paid: string;
  remaining_amount: string;
  currency: string;
  order_date: string | null;
  expected_delivery_date: string | null;
  status: string;
  installments: POInstallment[];
  created_at: string;
}

export interface POInstallment {
  id: string;
  installment_type: string;
  label: string;
  amount: string;
  due_date: string;
  is_paid: boolean;
  paid_date: string | null;
}

export interface WeeklyReviewItem {
  id: string;
  session_id: string;
  item_type: string;
  title: string;
  description: string | null;
  commitment_id: string | null;
  receivable_id: string | null;
  transaction_id: string | null;
  original_amount: string | null;
  original_date: string | null;
  action: string | null;
  confirmed_amount: string | null;
  confirmed_date: string | null;
  status: string;
  actioned_at: string | null;
}

export interface WeeklyReviewSession {
  id: string;
  business_id: string;
  week_start: string;
  week_end: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items: WeeklyReviewItem[];
}

export interface IntegrationStatus {
  plaid: { connected: boolean; mode: string; items: object[] };
  quickbooks: { connected: boolean; mode: string; company: string | null; status: string };
  shopify: { connected: boolean; mode: string; shops: object[] };
  amazon: { connected: boolean; mode: string; accounts: object[]; _blocker?: string };
}

export interface Transaction {
  id: string;
  business_id: string;
  transaction_date: string;
  description: string;
  amount: string;
  currency: string;
  reconciliation_status: string;
  source: string;
}
