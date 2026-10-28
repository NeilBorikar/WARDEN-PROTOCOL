/**
 * API Type Definitions for Mandate Arena
 * 
 * WHY:
 * Matches backend Pydantic models strictly, enforcing typed data flow
 * across runs, approvals, mandates, audit, results, and arena.
 */

export type Verdict = 'ALLOW' | 'ASK_OWNER' | 'BLOCK';

export type ProvenanceTag = 'OWNER' | 'VERIFIED_RECORD' | 'AGENT_DERIVED' | 'UNTRUSTED_EXTERNAL';

export interface DecisionReason {
  code: string;
  check_id: string;
  message: string;
}

export interface Decision {
  verdict: Verdict;
  reasons: DecisionReason[];
  policy_version: number;
  mandate_hash: string;
  request_hash: string;
  evaluated_at: string;
}

export interface Payee {
  id: string;
  email: string;
}

export interface PaymentRequest {
  request_id: string;
  mandate_id: string;
  intent_id: string;
  deal_id: string;
  tool_name: string;
  payee: Payee;
  amount_minor: number;
  currency: string;
  purpose: string;
  memo: string;
  provenance: Record<string, ProvenanceTag>;
  idempotency_key: string;
  created_at: string;
}

export interface DealItem {
  sku: string;
  qty: number;
  unit_price_minor: number;
}

export interface Deal {
  deal_id: string;
  intent_id: string;
  payee_id: string;
  items: DealItem[];
  total_minor: number;
  terms_hash: string;
}

export interface Turn {
  role: 'buyer' | 'seller' | 'verifier' | 'bouncer';
  message: string;
  tool_calls?: Array<{
    name: string;
    arguments: Record<string, unknown>;
  }>;
  timestamp?: string;
}

export interface VerifierOpinion {
  consistent: boolean;
  concerns: string[];
  suggested_verdict: Verdict;
}

export interface RunDetail {
  run_id: string;
  status: string;
  turns: Turn[];
  deal?: Deal | null;
  payment_request?: PaymentRequest | null;
  decision?: Decision | null;
  payment_executed: boolean;
  rail_payment_id?: string | null;
  verifier_opinion?: VerifierOpinion | null;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface RunSummary {
  run_id: string;
  status: string;
  turns_count: number;
  started_at: string;
  completed_at?: string | null;
  has_deal: boolean;
  has_payment: boolean;
  verdict?: Verdict | null;
}

export interface ApprovalItem {
  approval_id: string;
  request_id: string;
  request_hash: string;
  amount_minor: number;
  currency: string;
  payee_email: string;
  payee_id: string;
  purpose: string;
  memo: string;
  status: 'PENDING' | 'APPROVED' | 'DENIED' | 'EXPIRED';
  created_at: string;
  expires_at: string;
  reasons: DecisionReason[];
  resolved_at?: string | null;
  resolution_reason?: string | null;
}

export interface ExecutionOutcome {
  approval: ApprovalItem;
  executed: boolean;
  rail_payment_id?: string | null;
  error?: string | null;
}

export interface AllowedPayee {
  payee_id: string;
  display_name: string;
  paypal_email: string;
}

export interface Mandate {
  mandate_id: string;
  version: number;
  owner_id: string;
  agent_id: string;
  issued_at: string;
  expires_at: string;
  currency: string;
  per_payment_cap_minor: number;
  daily_cap_minor: number;
  max_payments_per_hour: number;
  approval_threshold_minor: number;
  allowed_payees: AllowedPayee[];
  allowed_purposes: string[];
  new_payee_policy: 'ASK_OWNER' | 'BLOCK';
  red_tier_policy: 'ASK_OWNER' | 'BLOCK';
  key_id: string;
  signature: string;
}

export interface IntentItem {
  sku: string;
  qty: number;
  max_unit_price_minor: number;
}

export interface Intent {
  intent_id: string;
  mandate_id: string;
  description: string;
  max_total_minor: number;
  items: IntentItem[];
  deadline: string;
  signature: string;
}

export interface AuditEvent {
  seq: number;
  ts: string;
  type: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
}

export interface ChainVerification {
  is_valid: boolean;
  verified_count: number;
  error?: string | null;
  checked_at: string;
}

export interface CategoryMetric {
  category: string;
  naive_break_in_rate: number;
  protected_break_in_rate: number;
  naive_money_lost_usd: number;
  protected_money_lost_usd: number;
  sample_count: number;
  blocked_count?: number;
}

export interface ResultsSummary {
  metrics_protected: {
    break_in_rate: number;
    money_lost_usd: number;
    false_alarm_rate: number;
    owner_interruption_rate: number;
    p50_latency_ms: number;
    p95_latency_ms: number;
    total_attack_scenarios: number;
    attacks_blocked: number;
    attacks_successful: number;
  };
  metrics_naive: {
    break_in_rate: number;
    money_lost_usd: number;
    false_alarm_rate: number;
    owner_interruption_rate: number;
    p50_latency_ms: number;
    p95_latency_ms: number;
    total_attack_scenarios: number;
    attacks_blocked: number;
    attacks_successful: number;
  };
  category_breakdown: CategoryMetric[];
  run_metadata: Record<string, unknown>;
}

export interface ArenaSession {
  session_id: string;
  mandate_id: string;
  intent_id: string;
  wallet_cap_daily_minor: number;
  allowed_merchant_email: string;
  allowed_sku: string;
  status: string;
  created_at: string;
}

export interface ArenaFeedItem {
  attempt_id: string;
  session_id: string;
  timestamp: string;
  attack_summary: string;
  verdict: Verdict;
  money_stolen_minor: number;
  reasons: string[];
}

export interface ArenaLeaderboard {
  total_attempts: number;
  total_blocked: number;
  total_escalated: number;
  total_money_stolen_minor: number;
  active_sessions: number;
  kill_switch_active: boolean;
}
