// RMT-CAP-09 -- typed read-only API client for the Governed Operations console.
// Authenticated calls carry the operator token; /health + /metrics are open.
import { getApiBaseUrl } from "../config/runtime";
import { getToken } from "./auth";
import type {
  AgentStatus,
  EvidenceChain,
  HoldListResponse,
  VerificationListResponse,
} from "../types/governance";

export async function authFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(`${getApiBaseUrl()}${path}`, { ...init, headers });
}

async function throwOnUnauthorized(resp: Response): Promise<Response> {
  if (resp.status === 401 || resp.status === 403) {
    throw new Error(`auth_required_${resp.status}`);
  }
  if (!resp.ok) {
    throw new Error(`http_${resp.status}`);
  }
  return resp;
}

export async function getHolds(): Promise<HoldListResponse> {
  const resp = await throwOnUnauthorized(await authFetch("/ops/holds"));
  return (await resp.json()) as HoldListResponse;
}

export async function getVerifications(status?: string): Promise<VerificationListResponse> {
  const q = status && status !== "" ? `?effective_status=${encodeURIComponent(status)}` : "";
  const resp = await throwOnUnauthorized(await authFetch(`/ops/verifications${q}`));
  return (await resp.json()) as VerificationListResponse;
}

export async function getEvidence(actionId: string): Promise<EvidenceChain> {
  const resp = await throwOnUnauthorized(
    await authFetch(`/ops/evidence?action_id=${encodeURIComponent(actionId)}`)
  );
  return (await resp.json()) as EvidenceChain;
}

export async function getAgentStatus(): Promise<AgentStatus> {
  const resp = await throwOnUnauthorized(await authFetch("/agent/status"));
  return (await resp.json()) as AgentStatus;
}

// Approval continuation. /homelab/approve is the superset of /approve: it
// continues homelab holds (with the Learn + verify closure) and passes any
// non-homelab hold through exactly as the generic /approve would, so the
// console uses this one path for every hold.
export async function approveHomelabHold(approvalId: string, approved: boolean): Promise<Response> {
  return authFetch(
    `/homelab/approve?approval_id=${encodeURIComponent(approvalId)}&approved=${approved}`
  );
}
