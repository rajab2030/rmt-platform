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
  const [busy, setBusy] = useState("");

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
    setBusy("create");
    setError("");
    setMessage("");
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
    } finally {
      setBusy("");
    }
  }

  async function submit(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Submit ${money(version.amount_minor, version.currency)} from budget ${request.budget_id}, version ${version.version}?`
    )) return;
    setBusy(`submit:${request.id}`);
    setError("");
    setMessage("");
    try {
      await submitPurchaseRequest(request.id);
      setMessage(`Request ${request.id} submitted.`);
      await refresh();
    } catch (reason) {
      fail(reason);
    } finally {
      setBusy("");
    }
  }

  async function decide(request: PurchaseRequest, decision: "approved" | "rejected") {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `${decision === "approved" ? "Approve" : "Reject"} ${money(version.amount_minor, version.currency)} for budget ${request.budget_id}, request version ${version.version}?`
    )) return;
    setBusy(`${decision}:${request.id}`);
    setError("");
    setMessage("");
    try {
      await decidePurchaseRequest(request.id, decision, "Decided in Budget Control");
      setMessage(`Request ${request.id} ${decision}.`);
      await refresh();
    } catch (reason) {
      fail(reason);
    } finally {
      setBusy("");
    }
  }

  async function commit(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Create the governed commitment of ${money(version.amount_minor, version.currency)} against budget ${request.budget_id}, version ${version.version}?`
    )) return;
    setBusy(`commit:${request.id}`);
    setError("");
    setMessage("");
    try {
      const result = await commitPurchaseRequest(request.id);
      setMessage(mutationMessage(result));
      await refresh();
    } catch (reason) {
      fail(reason);
    } finally {
      setBusy("");
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
    setBusy(`settle:${request.id}`);
    setError("");
    setMessage("");
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
    } finally {
      setBusy("");
    }
  }

  async function cancel(request: PurchaseRequest) {
    const version = currentVersion(request);
    if (!version) return;
    if (!window.confirm(
      `Cancel the open ${money(version.amount_minor, version.currency)} commitment for budget ${request.budget_id}, version ${version.version}?`
    )) return;
    setBusy(`cancel:${request.id}`);
    setError("");
    setMessage("");
    try {
      const result = await cancelPurchaseRequest(
        request.id,
        `cancel:${request.id}:${version.version}:${crypto.randomUUID()}`
      );
      setMessage(mutationMessage(result));
      await refresh();
    } catch (reason) {
      fail(reason);
    } finally {
      setBusy("");
    }
  }

  const working = (key: string, text: string) => (busy === key ? "Working…" : text);
  const tab = (id: View) => (view === id ? "page" : undefined);

  if (!authenticated) {
    return (
      <section className="page page-narrow">
        <header><p className="eyebrow">RMT · governed finance</p><h1>Budget Control</h1></header>
        <div className="card">
          <p>Enter your operator token. Budget roles are enforced by the server.</p>
          <label className="field">
            Operator token
            <input
              type="password"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              placeholder="operator token"
            />
          </label>
          <div className="actions"><button className="primary" onClick={signIn}>Sign in</button></div>
          {error && <p className="msg msg-error" role="alert">{error}</p>}
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <header className="page-head">
        <div><p className="eyebrow">RMT · governed finance</p><h1>Budget Control</h1></div>
        <div className="actions"><button onClick={() => void refresh()}>Refresh</button><button onClick={signOut}>Sign out</button></div>
      </header>
      <nav className="subnav" aria-label="Budget views">
        <button aria-current={tab("budgets")} onClick={() => setView("budgets")}>Budgets</button>
        <button aria-current={tab("requests")} onClick={() => setView("requests")}>Purchase Requests</button>
        <button aria-current={tab("approvals")} onClick={() => setView("approvals")}>Approvals</button>
        <button aria-current={tab("history")} onClick={() => { setView("history"); void loadHistory(historyBudget || budgets[0]?.id || ""); }}>Spending History</button>
      </nav>
      {message && <p className="msg msg-ok" role="status">{message}</p>}
      {error && <p className="msg msg-error" role="alert">{error}</p>}

      {view === "budgets" && <div className="card-grid fill">
        {budgets.map((budget) => <article className="card" key={budget.id}>
          <p className="eyebrow">{budget.period_start} — {budget.period_end}</p>
          <h2>{budget.name}</h2>
          <p>{budget.owner_type}: {budget.owner_name}</p>
          <p className="budget-amount">{money(budget.available_minor, budget.currency)}</p>
          <p>available · {budget.status}</p>
          <small>{budget.id}</small>
        </article>)}
        {budgets.length === 0 && <p className="empty">No budgets are visible for this principal.</p>}
      </div>}

      {view === "requests" && <>
        <div className="card form-grid">
          <h2>New purchase request</h2>
          <label className="field">Budget<select value={selectedBudget?.id || ""} onChange={(event) => setBudgetId(event.target.value)}>
            {budgets.map((budget) => <option key={budget.id} value={budget.id}>{budget.name} · {budget.currency}</option>)}
          </select></label>
          <label className="field">Amount (minor units)<input type="number" value={amountMinor} onChange={(event) => setAmountMinor(event.target.value)} placeholder="amount in minor units" /></label>
          <label className="field">Purpose<input value={purpose} onChange={(event) => setPurpose(event.target.value)} placeholder="purpose" /></label>
          <label className="field">Supporting reference<input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="supporting reference" /></label>
          <button className="primary" disabled={!!busy || !selectedBudget || !amountMinor || !purpose} onClick={() => void createRequest()}>{working("create", "Create draft")}</button>
        </div>
        <RequestTable requests={requests} actions={(request) => <>
          {request.status === "draft" && <button disabled={!!busy} onClick={() => void submit(request)}>{working(`submit:${request.id}`, "Submit")}</button>}
          {request.status === "approved" && <button disabled={!!busy} onClick={() => void commit(request)}>{working(`commit:${request.id}`, "Apply commitment")}</button>}
          {request.status === "committed" && <div className="actions"><button disabled={!!busy} onClick={() => void settle(request)}>{working(`settle:${request.id}`, "Settle")}</button><button className="danger" disabled={!!busy} onClick={() => void cancel(request)}>{working(`cancel:${request.id}`, "Cancel")}</button></div>}
        </>} />
      </>}

      {view === "approvals" && <RequestTable requests={approvals} actions={(request) => <>
        <div className="actions"><button className="primary" disabled={!!busy} onClick={() => void decide(request, "approved")}>{working(`approved:${request.id}`, "Approve")}</button>
        <button className="danger" disabled={!!busy} onClick={() => void decide(request, "rejected")}>{working(`rejected:${request.id}`, "Reject")}</button></div>
      </>} />}

      {view === "history" && <>
        <label>Budget <select value={historyBudget} onChange={(event) => void loadHistory(event.target.value)}>
          <option value="">Select a budget</option>
          {budgets.map((budget) => <option key={budget.id} value={budget.id}>{budget.name}</option>)}
        </select></label>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Time</th><th>Type</th><th>Amount</th><th>Request</th><th>Actor</th></tr></thead>
          <tbody>{history.map((entry) => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.entry_type}</td><td>{money(entry.amount_minor, entry.currency)}</td><td>{entry.request_id || "—"}</td><td>{entry.actor}</td></tr>)}</tbody>
        </table></div>
      </>}
    </section>
  );
}

function RequestTable({ requests, actions }: {
  requests: PurchaseRequest[];
  actions: (request: PurchaseRequest) => React.ReactNode;
}) {
  if (requests.length === 0) return <p className="empty">No purchase requests.</p>;
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>Request</th><th>Purpose</th><th>Amount</th><th>Version</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>{requests.map((request) => {
      const version = currentVersion(request);
      return <tr key={request.id}><td><code>{request.id}</code></td><td>{version?.purpose}</td><td>{version ? money(version.amount_minor, version.currency) : "—"}</td><td>{request.current_version}</td><td><span className={`pill state-${request.status}`}>{request.status}</span></td><td>{actions(request)}</td></tr>;
    })}</tbody>
  </table></div>;
}
