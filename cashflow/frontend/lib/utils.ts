import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(value: string | number | null | undefined, decimals = 0): string {
  if (value === null || value === undefined) return "$0";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

export function fmtDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function fmtShortDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr + "T00:00:00");
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

export function isOverdue(dateStr: string): boolean {
  return daysUntil(dateStr) < 0;
}

export const CATEGORY_LABELS: Record<string, string> = {
  vendor_bill: "Vendor Bill",
  payroll: "Payroll",
  tax: "Tax",
  rent: "Rent",
  insurance: "Insurance",
  loan: "Loan/Debt",
  subscription: "Subscription",
  recurring_expense: "Recurring",
  credit_card_payment: "Credit Card",
  inventory_po: "Inventory PO",
  supplier_deposit: "Supplier Deposit",
  manual: "Manual",
  other: "Other",
};

export const STATUS_COLORS: Record<string, string> = {
  scheduled: "text-blue-600 bg-blue-50",
  overdue: "text-red-600 bg-red-50",
  paid: "text-green-600 bg-green-50",
  partially_paid: "text-yellow-600 bg-yellow-50",
  cancelled: "text-gray-500 bg-gray-50",
  expected: "text-blue-600 bg-blue-50",
  received: "text-green-600 bg-green-50",
  written_off: "text-gray-500 bg-gray-50",
  partially_received: "text-yellow-600 bg-yellow-50",
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "border-red-500 bg-red-50 text-red-800",
  high: "border-orange-500 bg-orange-50 text-orange-800",
  medium: "border-yellow-500 bg-yellow-50 text-yellow-800",
  low: "border-blue-500 bg-blue-50 text-blue-800",
  info: "border-gray-300 bg-gray-50 text-gray-700",
};
