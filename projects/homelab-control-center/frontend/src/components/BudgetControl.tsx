import { useEffect, useMemo, useState } from "react";
import { clearToken, hasToken, setToken } from "../api/auth";
import {
  cancelPurchaseRequest,
  commitPurchaseRequest,
  createPurchaseRequest,
  decidePurchaseRequest,
  getApprovalQueue,
  getBudgets,
  getHistory,
  getRequests,
  settlePurchaseRequest,
  submitPurchaseRequest,
} from "../api/budget";
import type {
  BudgetSummary,
  LedgerEntry,
  MutationResult,
  PurchaseRequest,
  RequestVersion,
} from "../types/budget";


type View = "budgets" | "requests" | "approvals" | "history";

function currentVersion(request: PurchaseRequest): RequestVersion | undefined {
  return request.versions.find((version) => version.version === request.current_version);
}

function money(minor: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(minor / 100);
}

function mutationMessage(result: MutationResult): string {
  return `${result.financial_status} · execution ${result.execution_id || "none"}`;
}

export default function BudgetControl() {
  const [authenticated, setAuthenticated] = useState(hasToken());
  const [tokenInput, setTokenInput] = useState("");
  const [view, setView] = useState<View>("budgets");
  const [budgets, setBudgets] = useState<BudgetSummary[]>([]);
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [approvals, setApprovals] = useState<PurchaseRequest[]>([]);
  const [history, setHistory] = useState<LedgerEntry[]>([]);
  const [historyBudget, setHistoryBudget] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [budgetId, setBudgetId] = useState("");
  const [amountMinor, setAmountMinor] = useState("");
  const [purpose, setPurpose] = useState("");
  const [reference, setReference] = useState("");

  const selectedBudget = useMemo(
    () => budgets.find((budget) => budget.id === budgetId) || budgets[0],
    [budgetId, budgets]
  );

  function fail(reason: unknown) {
    const text = reason instanceof Error ? reason.message : String(reason);
    if (text.includes("401") || text.includes("403") || text.includes("authentication")) {
      setAuthenticated(false);
    }
    setError(text);
  }

  async function refresh() {
    try {
      setError("");
      const [nextBudgets, nextRequests, nextApprovals] = await Promise.all([
        getBudgets(),
        getRequests(),
        getApprovalQueue(),
      ]);
      setBudgets(nextBudgets);
      setRequests(nextRequests);
      setApprovals(nextApprovals);
      if (!budgetId && nextBudgets[0]) setBudgetId(nextBudgets[0].id);
    } catch (reason) {
      fail(reason);
    }
  }

  async function loadHistory(id: string) {
    if (!id) return;
    try {
      setError("");
      setHistory(await getHistory(id));
      setHistoryBudget(id);
    } catch (reason) {
      fail(reason);
    }
  }

  useEffect(() => {
    if (authenticated) void refresh();
    // Authentication is the intentional refresh boundary.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated]);

  function signIn() {
    setToken(tokenInput);
    setTokenInput("");
    setAuthenticated(true);
  }

  function signOut() {
    clearToken();
    setAuthenticated(false);
    setBudgets([]);
    setRequests([]);
  }

  async function createRequest() {
    if (!selectedBudget) return;
    try {
      const amount = Number(amountMinor);
      const created = await createPurchaseRequest({
        budget_id: selectedBudget.id,
        amount_minor: amount,
        currency: selectedBudget.currency,
        purpose,
        supporting_reference: reference,
      });
      setMessage(`Draft ${created.id} created.`);
      setAmountMinor("");
      setPurpose("");
      setReference("");
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  async function submit(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Submit ${money(version.amount_minor, version.currency)} from budget ${request.budget_id}, version ${version.version}?`
    )) return;
    try {
      await submitPurchaseRequest(request.id);
      setMessage(`Request ${request.id} submitted.`);
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  async function decide(request: PurchaseRequest, decision: "approved" | "rejected") {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `${decision === "approved" ? "Approve" : "Reject"} ${money(version.amount_minor, version.currency)} for budget ${request.budget_id}, request version ${version.version}?`
    )) return;
    try {
      await decidePurchaseRequest(request.id, decision, "Decided in Budget Control");
      setMessage(`Request ${request.id} ${decision}.`);
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  async function commit(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Create the governed commitment of ${money(version.amount_minor, version.currency)} against budget ${request.budget_id}, version ${version.version}?`
    )) return;
    try {
      const result = await commitPurchaseRequest(request.id);
      setMessage(mutationMessage(result));
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  async function settle(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    const raw = window.prompt("Final settlement in minor units", String(version.amount_minor));
    if (raw === null) return;
    const amount = Number(raw);
    if (!window.confirm(
      `Settle ${money(amount, version.currency)} for budget ${request.budget_id}, version ${version.version}? This is final.`
    )) return;
    try {
      const result = await settlePurchaseRequest(
        request.id,
        amount,
        `settle:${request.id}:${version.version}:${crypto.randomUUID()}`
      );
      setMessage(mutationMessage(result));
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  async function cancel(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Cancel the open ${money(version.amount_minor, version.currency)} commitment for budget ${request.budget_id}, version ${version.version}?`
    )) return;
    try {
      const result = await cancelPurchaseRequest(
        request.id,
        `cancel:${request.id}:${version.version}:${crypto.randomUUID()}`
      );
      setMessage(mutationMessage(result));
      await refresh();
    } catch (reason) {
      fail(reason);
    }
  }

  if (!authenticated) {
    return (
      <section className="budget-shell budget-login">
        <h2>Budget Control</h2>
        <p>Enter your operator token. Budget roles are enforced by the server.</p>
        <input
          type="password"
          value={tokenInput}
          onChange={(event) => setTokenInput(event.target.value)}
          placeholder="operator token"
        />
        <button onClick={signIn}>Sign in</button>
        {error && <p className="budget-error">{error}</p>}
      </section>
    );
  }

  return (
    <section className="budget-shell">
      <header className="budget-head">
        <div><p className="eyebrow">RMT · governed finance</p><h1>Budget Control</h1></div>
        <div><button onClick={() => void refresh()}>Refresh</button> <button onClick={signOut}>Sign out</button></div>
      </header>
      <nav className="budget-nav" aria-label="Budget views">
        <button onClick={() => setView("budgets")}>Budgets</button>
        <button onClick={() => setView("requests")}>Purchase Requests</button>
        <button onClick={() => setView("approvals")}>Approvals</button>
        <button onClick={() => { setView("history"); void loadHistory(historyBudget || budgets[0]?.id || ""); }}>Spending History</button>
      </nav>
      {message && <p className="budget-message">{message}</p>}
      {error && <p className="budget-error">{error}</p>}

      {view === "budgets" && <div className="budget-grid">
        {budgets.map((budget) => <article className="budget-card" key={budget.id}>
          <p className="eyebrow">{budget.period_start} — {budget.period_end}</p>
          <h2>{budget.name}</h2>
          <p>{budget.owner_type}: {budget.owner_name}</p>
          <p className="budget-amount">{money(budget.available_minor, budget.currency)}</p>
          <p>available · {budget.status}</p>
          <small>{budget.id}</small>
        </article>)}
        {budgets.length === 0 && <p>No budgets are visible for this principal.</p>}
      </div>}

      {view === "requests" && <>
        <div className="budget-form">
          <h2>New purchase request</h2>
          <select value={selectedBudget?.id || ""} onChange={(event) => setBudgetId(event.target.value)}>
            {budgets.map((budget) => <option key={budget.id} value={budget.id}>{budget.name} · {budget.currency}</option>)}
          </select>
          <input type="number" value={amountMinor} onChange={(event) => setAmountMinor(event.target.value)} placeholder="amount in minor units" />
          <input value={purpose} onChange={(event) => setPurpose(event.target.value)} placeholder="purpose" />
          <input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="supporting reference" />
          <button disabled={!selectedBudget || !amountMinor || !purpose} onClick={() => void createRequest()}>Create draft</button>
        </div>
        <RequestTable requests={requests} actions={(request) => <>
          {request.status === "draft" && <button onClick={() => void submit(request)}>Submit</button>}
          {request.status === "approved" && <button onClick={() => void commit(request)}>Apply commitment</button>}
          {request.status === "committed" && <><button onClick={() => void settle(request)}>Settle</button> <button onClick={() => void cancel(request)}>Cancel</button></>}
        </>} />
      </>}

      {view === "approvals" && <RequestTable requests={approvals} actions={(request) => <>
        <button onClick={() => void decide(request, "approved")}>Approve</button>{" "}
        <button onClick={() => void decide(request, "rejected")}>Reject</button>
      </>} />}

      {view === "history" && <>
        <label>Budget <select value={historyBudget} onChange={(event) => void loadHistory(event.target.value)}>
          <option value="">Select a budget</option>
          {budgets.map((budget) => <option key={budget.id} value={budget.id}>{budget.name}</option>)}
        </select></label>
        <table className="budget-table"><thead><tr><th>Time</th><th>Type</th><th>Amount</th><th>Request</th><th>Actor</th></tr></thead>
          <tbody>{history.map((entry) => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.entry_type}</td><td>{money(entry.amount_minor, entry.currency)}</td><td>{entry.request_id || "—"}</td><td>{entry.actor}</td></tr>)}</tbody>
        </table>
      </>}
    </section>
  );
}

function RequestTable({ requests, actions }: {
  requests: PurchaseRequest[];
  actions: (request: PurchaseRequest) => React.ReactNode;
}) {
  return <table className="budget-table"><thead><tr><th>Request</th><th>Purpose</th><th>Amount</th><th>Version</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>{requests.map((request) => {
      const version = currentVersion(request);
      return <tr key={request.id}><td><code>{request.id}</code></td><td>{version?.purpose}</td><td>{version ? money(version.amount_minor, version.currency) : "—"}</td><td>{request.current_version}</td><td><span className={`budget-state state-${request.status}`}>{request.status}</span></td><td>{actions(request)}</td></tr>;
    })}</tbody>
  </table>;
}
