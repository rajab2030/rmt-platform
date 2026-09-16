export interface BudgetRole {
  principal: string;
  role: string;
}

export interface BudgetSummary {
  id: string;
  organization_id: string;
  name: string;
  owner_type: "department" | "project";
  owner_name: string;
  period_start: string;
  period_end: string;
  currency: string;
  status: string;
  available_minor: number;
  roles: BudgetRole[];
}

export interface RequestVersion {
  request_id: string;
  version: number;
  amount_minor: number;
  currency: string;
  purpose: string;
  supporting_reference: string;
  created_by: string;
  created_at: string;
}

export interface DomainDecision {
  id: string;
  request_version: number;
  decision: string;
  decided_by: string;
  reason: string;
  created_at: string;
}

export interface PurchaseRequest {
  id: string;
  organization_id: string;
  budget_id: string;
  requester: string;
  status: string;
  current_version: number;
  versions: RequestVersion[];
  decisions: DomainDecision[];
  created_at: string;
  updated_at: string;
}

export interface LedgerEntry {
  id: string;
  budget_id: string;
  entry_type: string;
  amount_minor: number;
  currency: string;
  request_id?: string | null;
  request_version?: number | null;
  actor: string;
  created_at: string;
}

export interface MutationResult {
  action_id?: string | null;
  approval_id?: string | null;
  authorization_id?: string | null;
  execution_id?: string | null;
  financial_status: string;
  instruction_digest?: string;
  replayed?: boolean;
}
