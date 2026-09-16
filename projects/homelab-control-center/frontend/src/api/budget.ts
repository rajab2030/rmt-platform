import { authFetch } from "./governance";
import type {
  BudgetSummary,
  LedgerEntry,
  MutationResult,
  PurchaseRequest,
} from "../types/budget";


async function budgetJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await authFetch(path, { ...init, headers });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail?.message || body.detail || detail;
    } catch {
      // Preserve the HTTP status when the body is not JSON.
    }
    throw new Error(String(detail));
  }
  return (await response.json()) as T;
}
export async function getBudgets(): Promise<BudgetSummary[]> {
  return (await budgetJson<{ budgets: BudgetSummary[] }>("/budget/budgets")).budgets;
}

export async function getRequests(): Promise<PurchaseRequest[]> {
  return (await budgetJson<{ requests: PurchaseRequest[] }>("/budget/requests")).requests;
}

export async function getApprovalQueue(): Promise<PurchaseRequest[]> {
  return (await budgetJson<{ requests: PurchaseRequest[] }>("/budget/approvals")).requests;
}

export async function getHistory(budgetId: string): Promise<LedgerEntry[]> {
  return (
    await budgetJson<{ entries: LedgerEntry[] }>(
      `/budget/budgets/${encodeURIComponent(budgetId)}/history`
    )
  ).entries;
}

export async function createPurchaseRequest(body: {
  budget_id: string;
  amount_minor: number;
  currency: string;
  purpose: string;
  supporting_reference: string;
}): Promise<PurchaseRequest> {
  return budgetJson("/budget/requests", { method: "POST", body: JSON.stringify(body) });
}

export async function submitPurchaseRequest(id: string): Promise<PurchaseRequest> {
  return budgetJson(`/budget/requests/${encodeURIComponent(id)}/submit`, { method: "POST" });
}

export async function decidePurchaseRequest(
  id: string,
  decision: "approved" | "rejected",
  reason: string
): Promise<PurchaseRequest> {
  return budgetJson(`/budget/requests/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, reason }),
  });
}

export async function commitPurchaseRequest(id: string): Promise<MutationResult> {
  return budgetJson(`/budget/requests/${encodeURIComponent(id)}/commit`, { method: "POST" });
}

export async function settlePurchaseRequest(
  id: string,
  amountMinor: number,
  idempotencyKey: string
): Promise<MutationResult> {
  return budgetJson(`/budget/requests/${encodeURIComponent(id)}/settle`, {
    method: "POST",
    body: JSON.stringify({ amount_minor: amountMinor, idempotency_key: idempotencyKey }),
  });
}

export async function cancelPurchaseRequest(
  id: string,
  idempotencyKey: string
): Promise<MutationResult> {
  return budgetJson(`/budget/requests/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  });
}
