export type Role = "ADMIN" | "ANALYST" | "REVIEWER" | "AUDITOR" | "VIEWER";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Platform {
  id: string;
  name: string;
  domain: string;
  reporting_url: string | null;
  api_endpoint: string | null;
  has_official_api: boolean;
  allowed_categories: string[];
  required_fields: string[];
  attachment_rules: Record<string, unknown>;
  rate_limit_notes: string | null;
  terms_url: string | null;
}

export interface Case {
  id: string;
  case_number: string;
  title: string;
  platform_id: string;
  target_id: string | null;
  report_category: string | null;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string | null;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Target {
  id: string;
  platform_id: string;
  username: string;
  display_name: string | null;
  profile_url: string;
  account_id: string | null;
  profile_description: string | null;
  account_created_at: string | null;
  public_followers: number | null;
  public_following: number | null;
  public_posts: number | null;
  verification_status: string;
  collected_at: string;
  collected_by: string | null;
  source_url: string;
}

export interface Evidence {
  id: string;
  evidence_number: string;
  case_id: string;
  content_id: string | null;
  type: string;
  source_url: string;
  description: string | null;
  original_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  sha256: string | null;
  collected_at: string;
  collected_by: string;
  verification_status: string;
  verification_notes: string | null;
}

export interface PolicyRule {
  id: string;
  policy_id: string;
  rule_code: string;
  category: string;
  description: string;
  severity: string;
  keywords: string | null;
}

export interface Policy {
  id: string;
  platform_id: string;
  name: string;
  policy_url: string | null;
  effective_date: string | null;
  last_updated: string | null;
  rules: PolicyRule[];
}

export interface Assessment {
  id: string;
  case_id: string;
  category: string;
  policy_rule_id: string | null;
  confidence: number;
  evidence_ids: string[];
  reason: string | null;
  missing_evidence: string[];
  requires_human_review: boolean;
  status: string;
  generated_by: string;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface ReadinessChecklistItem {
  key: string;
  label: string;
  weight: number;
  met: boolean;
}

export interface ReadinessPreview {
  score: number;
  level: "READY" | "NEEDS_REVIEW" | "INSUFFICIENT";
  missing_items: string[];
  items: ReadinessChecklistItem[];
  assessment_status: string | null;
}

export interface Report {
  id: string;
  report_number: string;
  case_id: string;
  assessment_id: string | null;
  platform_id: string;
  body: Record<string, unknown>;
  report_hash: string;
  readiness_score: number;
  readiness_level: "READY" | "NEEDS_REVIEW" | "INSUFFICIENT";
  missing_items: string[];
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewQueueItem {
  id: string;
  case_id: string;
  assessment_id: string | null;
  report_id: string | null;
  status: string;
  assigned_to: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata_json: Record<string, unknown> | null;
  timestamp: string;
}

export interface DashboardStats {
  total_cases: number;
  open_cases: number;
  under_review: number;
  validated_cases: number;
  reports_ready: number;
  reports_submitted: number;
  platform_responses: number;
  action_taken: number;
  rejected_reports: number;
  by_platform: Record<string, number>;
  by_violation_category: Record<string, number>;
  by_status: Record<string, number>;
  by_evidence_validity: Record<string, number>;
  timeline: { date: string; count: number }[];
}

export interface AccountFinderFinding {
  finding_number: string;
  category: string;
  source_url: string;
  observed_at: string | null;
  evidence_ids: string[];
  reasoning: string;
  policy_reference: string | null;
  confidence: number;
  status: string;
}

export interface AccountFinderResult {
  case_id: string | null;
  target_id: string;
  platform: string;
  profile_url: string;
  collection_status: string;
  findings: AccountFinderFinding[];
  summary: string;
  dossier_ready: boolean;
}
