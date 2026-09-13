// RMT-CAP-09 -- types for the Governed Operations console.

export interface HeldItem {
  approval_id: string;
  component?: string | null;
  action_type?: string | null;
  kind?: string;
  granted_by?: string | null;
  agent_id?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
  age_seconds?: number | null;
  expired?: boolean;
  record_decision?: string | null;
  record_terminal?: boolean;
  actionable?: boolean;
  [key: string]: unknown;
}

export interface VerificationRow {
  execution_id?: string;
  action_id?: string;
  effective_status?: string;
  adapter?: string;
  reason?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface EvidenceChain {
  resolved: {
    action_id?: string | null;
    approval_id?: string | null;
    execution_id?: string | null;
  };
  authorizations: Record<string, unknown>[];
  approvals: Record<string, unknown>[];
  holds: Record<string, unknown>[];
  audit: Record<string, unknown>[];
  traces: Record<string, unknown>[];
  verifications: Record<string, unknown>[];
  provenance: Record<string, unknown>;
}

export interface AgentStatus {
  enabled?: boolean;
  llm?: { enabled: boolean };
  active_grants?: number;
  separation_of_duties?: boolean;
  dependency_map?: { sources?: string[] };
  [key: string]: unknown;
}

export interface HoldListResponse {
  holds: HeldItem[];
}

export interface VerificationListResponse {
  verifications: VerificationRow[];
}
