// RMT-CAP-09 -- Governed Operations console (read-only + approve/reject).
import { useEffect, useState } from "react";
import { clearToken, hasToken, setToken } from "../api/auth";
import {
  approveHomelabHold,
  getAgentStatus,
  getEvidence,
  getHolds,
  getVerifications,
} from "../api/governance";
import type {
  AgentStatus,
  EvidenceChain,
  HeldItem,
  VerificationRow,
} from "../types/governance";

type View = "holds" | "verifications" | "evidence";

function verificationTone(status: string | undefined): string {
  if (!status) return "";
  if (status.includes("success")) return "pill-ok";
  if (status.includes("fail") || status.includes("mismatch")) return "pill-bad";
  return "pill-warn";
}

export default function GovernedConsole() {
  const [authenticated, setAuthenticated] = useState(hasToken());
  const [token, setTokenInput] = useState("");
  const [view, setView] = useState<View>("holds");

  const [holds, setHolds] = useState<HeldItem[]>([]);
  const [verifications, setVerifications] = useState<VerificationRow[]>([]);
  const [verificationFilter, setVerificationFilter] = useState("");

  const [actionId, setActionId] = useState("");
  const [evidence, setEvidence] = useState<EvidenceChain | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadHolds() {
    try {
      setError(null);
      const data = await getHolds();
      setHolds(data.holds || []);
    } catch (e) {
      handleAuthError(e);
    }
  }

  async function loadVerifications() {
    try {
      setError(null);
      const data = await getVerifications(verificationFilter);
      setVerifications(data.verifications || []);
    } catch (e) {
      handleAuthError(e);
    }
  }

  async function loadAgentStatus() {
    try {
      setAgentStatus(await getAgentStatus());
    } catch (e) {
      handleAuthError(e);
    }
  }

  function handleAuthError(e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("auth_required_")) {
      setAuthenticated(false);
      setError("Provide an operator token to continue.");
    } else {
      setError("Failed to load from the governed API.");
    }
  }

  function onLogin() {
    setToken(token);
    setAuthenticated(true);
    setTokenInput("");
    void loadHolds();
    void loadAgentStatus();
  }

  function onLogout() {
    clearToken();
    setAuthenticated(false);
    setHolds([]);
    setEvidence(null);
    setAgentStatus(null);
  }

  async function onApprove(hold: HeldItem, approved: boolean) {
    setMessage(null);
    setError(null);
    try {
      const id = hold.approval_id;
      // /homelab/approve is the documented superset of /approve: it continues
      // homelab holds (with the Learn + verify closure) and passes through any
      // non-homelab hold exactly as the generic /approve would.
      const resp = await approveHomelabHold(id, approved);
      if (resp.status === 401 || resp.status === 403) {
        setError(`Denied by policy (${resp.status}) — possibly separation of duties.`);
        setAuthenticated(false);
      } else if (resp.status === 200) {
        setMessage(`Approved ${id} (${approved ? "yes" : "no"}).`);
        await loadHolds();
      } else {
        setError(`Approve call returned HTTP ${resp.status}.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function onSearchEvidence(id: string) {
    if (!id) return;
    try {
      setError(null);
      setEvidence(await getEvidence(id));
    } catch (e) {
      handleAuthError(e);
    }
  }

  useEffect(() => {
    if (authenticated) {
      void loadHolds();
      void loadAgentStatus();
      setView("holds");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated]);

  if (!authenticated) {
    return (
      <section className="page page-narrow">
        <header>
          <p className="eyebrow">RMT · approvals &amp; evidence</p>
          <h1>Governed Operations</h1>
        </header>
        <div className="card">
          <p>
            Enter an operator token (from <code>auth.conf</code> /{" "}
            <code>RMT_OPERATOR_TOKENS</code>) to view held actions, verification
            evidence, and approve or reject holds. The token stays in your browser.
          </p>
          <input
            type="password"
            value={token}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder="operator token"
          />
          <div className="actions">
            <button className="primary" onClick={onLogin}>Sign in</button>
          </div>
          {error && <p className="msg msg-error">{error}</p>}
        </div>
      </section>
    );
  }

  const tab = (id: View) => (view === id ? "page" : undefined);

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">RMT · approvals &amp; evidence</p>
          <h1>Governed Operations</h1>
        </div>
        <button onClick={onLogout}>Sign out</button>
      </header>

      {agentStatus && (
        <div className="actions">
          <span className={`pill ${agentStatus.enabled ? "pill-ok" : ""}`}>
            Agent surface: {String(agentStatus.enabled ?? "?")}
          </span>
          <span className="pill">Active grants: {String(agentStatus.active_grants ?? "?")}</span>
          <span className={`pill ${agentStatus.separation_of_duties ? "pill-ok" : ""}`}>
            Separation of duties: {String(agentStatus.separation_of_duties ?? "?")}
          </span>
        </div>
      )}

      <nav className="subnav" aria-label="Governed views">
        <button aria-current={tab("holds")} onClick={() => { setView("holds"); void loadHolds(); }}>Holds</button>
        <button aria-current={tab("verifications")} onClick={() => { setView("verifications"); void loadVerifications(); }}>Verifications</button>
        <button aria-current={tab("evidence")} onClick={() => setView("evidence")}>Evidence by action</button>
      </nav>

      {message && <p className="msg msg-ok">{message}</p>}
      {error && <p className="msg msg-error">{error}</p>}

      {view === "holds" && (
        <>
          <h2>Approval Holds</h2>
          {holds.length === 0 ? (
            <p className="empty">No open approval holds.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>approval_id</th>
                    <th>component</th>
                    <th>action_type</th>
                    <th>actionable</th>
                    <th>expired</th>
                    <th>record</th>
                    <th>risk</th>
                    <th>granted_by</th>
                    <th>approve</th>
                  </tr>
                </thead>
                <tbody>
                  {holds.map((h) => (
                    <tr key={h.approval_id}>
                      <td><code>{h.approval_id}</code></td>
                      <td>{h.component ?? ""}</td>
                      <td>{h.action_type ?? ""}</td>
                      <td><span className={`pill ${h.actionable ? "pill-ok" : ""}`}>{h.actionable ? "yes" : "no"}</span></td>
                      <td><span className={`pill ${h.expired ? "pill-bad" : ""}`}>{h.expired ? "yes" : "no"}</span></td>
                      <td>{h.record_decision ?? ""}</td>
                      <td>{h.granted_by ?? ""}{h.agent_id ? ` (${h.agent_id})` : ""}</td>
                      <td>
                        <div className="actions">
                          <button className="primary" onClick={() => void onApprove(h, true)}>Approve</button>
                          <button className="danger" onClick={() => void onApprove(h, false)}>Reject</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {view === "verifications" && (
        <>
          <h2>Verification Ledger</h2>
          <label>
            effective_status
            <input
              value={verificationFilter}
              onChange={(e) => {
                setVerificationFilter(e.target.value);
                void loadVerifications();
              }}
              placeholder="e.g. verified_success"
            />
          </label>
          {verifications.length === 0 ? (
            <p className="empty">No verification records.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>execution_id</th>
                    <th>action_id</th>
                    <th>effective_status</th>
                    <th>reason</th>
                  </tr>
                </thead>
                <tbody>
                  {verifications.map((v) => (
                    <tr key={v.execution_id ?? JSON.stringify(v)}>
                      <td><code>{v.execution_id ?? ""}</code></td>
                      <td>{v.action_id ?? ""}</td>
                      <td><span className={`pill ${verificationTone(v.effective_status)}`}>{v.effective_status ?? ""}</span></td>
                      <td>{v.reason ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {view === "evidence" && (
        <>
          <h2>Evidence chain</h2>
          <label>
            action_id
            <input
              value={actionId}
              onChange={(e) => setActionId(e.target.value)}
              placeholder="action_id"
            />
            <button onClick={() => void onSearchEvidence(actionId)}>Look up</button>
          </label>
          {evidence && (
            <article className="card">
              <dl className="facts">
                <dt>action</dt>
                <dd><code>{evidence.resolved?.action_id ?? ""}</code></dd>
                <dt>approval</dt>
                <dd><code>{evidence.resolved?.approval_id ?? ""}</code></dd>
                <dt>execution</dt>
                <dd><code>{evidence.resolved?.execution_id ?? ""}</code></dd>
              </dl>
              <div className="stats">
                {(
                  [
                    ["authorizations", evidence.authorizations.length],
                    ["approvals", evidence.approvals.length],
                    ["holds", evidence.holds.length],
                    ["audit", evidence.audit.length],
                    ["traces", evidence.traces.length],
                    ["verifications", evidence.verifications.length],
                  ] as const
                ).map(([label, count]) => (
                  <div className="stat" key={label}>
                    <div className="stat-label">{label}</div>
                    <div className="stat-value">{count}</div>
                  </div>
                ))}
              </div>
            </article>
          )}
        </>
      )}
    </section>
  );
}
