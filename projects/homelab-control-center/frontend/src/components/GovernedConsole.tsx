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
      <div className="governed-token">
        <h2>Governed Operations Console</h2>
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
        <button onClick={onLogin}>Sign in</button>
        {error && <p className="governed-error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="governed">
      <div className="governed-head">
        <h2>Governed Operations Console</h2>
        <button onClick={onLogout}>Sign out</button>
      </div>

      {agentStatus && (
        <p className="governed-status">
          Agent surface: {String(agentStatus.enabled ?? "?")} · grants{" "}
          {String(agentStatus.active_grants ?? "?")} · SoD{" "}
          {String(agentStatus.separation_of_duties ?? "?")}
        </p>
      )}

      <nav className="governed-nav">
        <button onClick={() => { setView("holds"); void loadHolds(); }}>Holds</button>
        <button onClick={() => { setView("verifications"); void loadVerifications(); }}>Verifications</button>
        <button onClick={() => setView("evidence")}>Evidence by action</button>
      </nav>

      {message && <p className="governed-ok">{message}</p>}
      {error && <p className="governed-error">{error}</p>}

      {view === "holds" && (
        <>
          <h3>Approval Holds</h3>
          {holds.length === 0 ? (
            <p>No open approval holds.</p>
          ) : (
            <table className="governed-table">
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
                    <td>{h.actionable ? "yes" : "no"}</td>
                    <td>{h.expired ? "yes" : "no"}</td>
                    <td>{h.record_decision ?? ""}</td>
                    <td>{h.granted_by ?? ""}{h.agent_id ? ` (${h.agent_id})` : ""}</td>
                    <td>
                      <button onClick={() => void onApprove(h, true)}>Approve</button>{" "}
                      <button onClick={() => void onApprove(h, false)}>Reject</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {view === "verifications" && (
        <>
          <h3>Verification Ledger</h3>
          <label>
            effective_status{" "}
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
            <p>No verification records.</p>
          ) : (
            <table className="governed-table">
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
                    <td>{v.effective_status ?? ""}</td>
                    <td>{v.reason ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {view === "evidence" && (
        <>
          <h3>Evidence chain</h3>
          <label>
            action_id{" "}
            <input
              value={actionId}
              onChange={(e) => setActionId(e.target.value)}
              placeholder="action_id"
            />
            <button onClick={() => void onSearchEvidence(actionId)}>Look up</button>
          </label>
          {evidence && (
            <div className="governed-evidence">
              <p>
                resolved: action <code>{evidence.resolved?.action_id ?? ""}</code>,
                approval <code>{evidence.resolved?.approval_id ?? ""}</code>,
                execution <code>{evidence.resolved?.execution_id ?? ""}</code>
              </p>
              <p>authorizations: {evidence.authorizations.length}</p>
              <p>approvals: {evidence.approvals.length}</p>
              <p>holds: {evidence.holds.length}</p>
              <p>audit: {evidence.audit.length}</p>
              <p>traces: {evidence.traces.length}</p>
              <p>verifications: {evidence.verifications.length}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
