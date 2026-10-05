/**
 * SIH165 API Client — typed fetch wrapper for all backend endpoints
 */

const BASE = "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ReportListItem {
  id: string;
  site: string | null;
  shift_date: string | null;
  reporter_role: string | null;
  ingest_status: string;
  text_only_mode: boolean;
  stage1_flagged: boolean | null;
  sif_flag: boolean | null;
  calibrated_prob: number | null;
  confidence_band: "HIGH" | "LOW" | "AMBIGUOUS" | "OOD" | null;
  iogp_rules: string[];
  operational_state: "FLAGGED" | "NON_SIF" | "NEEDS_REVIEW" | null;
  routing_reason: string | null;
  decision: "AGREE" | "DISAGREE" | null;
}

export interface IGSpan {
  start: number;
  end: number;
  text: string;
  label: string;
  score: number;
}

export interface ReportDetail {
  id: string;
  site: string | null;
  country: string | null;
  industry_sector: string | null;
  shift_date: string | null;
  reporter_role: string | null;
  report_text: string;
  report_type: string | null;
  critical_risk: string | null;
  ingest_status: string;
  text_only_mode: boolean;
  lower_confidence_flag: boolean;
  features: {
    energy_types: string[];
    barrier_phrases: string[];
    barrier_status: string;
    has_energy_signal: boolean;
    has_barrier_failure: boolean;
    hazard_categories: string[];
    safety_mgmt_terms: string[];
    equipment_terms: string[];
    interlock_bypass_detected: boolean;
    hi_po: boolean | null;
    accident_level: string | null;
    potential_accident_level: string | null;
  } | null;
  prediction: {
    stage1_flagged: boolean | null;
    sif_flag: boolean | null;
    calibrated_prob: number | null;
    confidence_band: string | null;
    operational_state: string | null;
    iogp_rules: string[];
    cause_categories: string[];
    ood_score: number | null;
    routing_reason: string | null;
    shap_values: Record<string, number>;
    ig_spans: IGSpan[];
  } | null;
  decision: {
    decision: string;
    officer_role: string | null;
    notes: string | null;
    created_at: string;
  } | null;
}

export interface ReportListResponse {
  page: number;
  page_size: number;
  total_count: number;
  sif_flagged_count: number;
  needs_review_count: number;
  count: number;
  reports: ReportListItem[];
}

export interface ScoreStatus {
  total_predictions: number;
  stage2_unscored: number;
  sif_flagged: number;
  non_sif: number;
  needs_review: number;
}

export interface DashboardData {
  site_summary: {
    site: string;
    industry_sector: string;
    total_reports: number;
    sif_precursor_count: number;
    stage1_flagged_count: number;
    sif_rate_pct: number;
  }[];
  iogp_rule_frequency: { rule: string; count: number }[];
  cause_category_frequency: { cause: string; count: number }[];
  barrier_failure_by_site: { site: string; barrier_status: string; count: number }[];
}

export interface SiteRecallData {
  average_proxy_recall: number | null;
  sites: {
    site: string;
    total_reports: number;
    hi_po_count: number;
    sif_predicted: number;
    proxy_recall: number | null;
    below_average: boolean;
  }[];
}

export interface ActivityBreakdownData {
  activity_density: {
    activity: string;
    total_reports: number;
    sif_count: number;
    sif_rate_pct: number;
  }[];
  site_activity_matrix: {
    site: string;
    activity: string;
    sif_count: number;
  }[];
}

export interface TrendData {
  site_filter: string;
  trend: {
    month: string;
    total_reports: number;
    sif_count: number;
    sif_rate_pct: number;
  }[];
}

// ── API Functions ──────────────────────────────────────────────────────────────

export const api = {
  // Reports
  listReports: (params: {
    page?: number;
    page_size?: number;
    site?: string;
    confidence_band?: string;
    stage1_flagged?: boolean;
    status?: string;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.page)             q.set("page", String(params.page));
    if (params.page_size)        q.set("page_size", String(params.page_size));
    if (params.site)             q.set("site", params.site);
    if (params.confidence_band)  q.set("confidence_band", params.confidence_band);
    if (params.stage1_flagged !== undefined) q.set("stage1_flagged", String(params.stage1_flagged));
    if (params.status)           q.set("status", params.status);
    return request<ReportListResponse>(`/reports?${q}`);
  },

  getReport: (id: string) => request<ReportDetail>(`/reports/${id}`),

  getManualReviewQueue: (page = 1, page_size = 50) =>
    request<{ page: number; page_size: number; count: number; reports: ReportListItem[] }>(
      `/queue/manual-review?page=${page}&page_size=${page_size}`
    ),

  // Decisions
  submitDecision: (reportId: string, body: {
    officer_id: string;
    officer_role?: string;
    decision: "AGREE" | "DISAGREE";
    notes?: string;
  }) => request(`/reports/${reportId}/decision`, {
    method: "POST",
    body: JSON.stringify(body),
  }),

  // Scoring
  triggerStage2: (limit = 500) =>
    request(`/score/run?limit=${limit}`, { method: "POST" }),

  getScoreStatus: () => request<ScoreStatus>("/score/status"),

  // Dashboard
  getLeadershipDashboard: (site?: string) => {
    const q = site ? `?site=${site}` : "";
    return request<DashboardData>(`/dashboard/leadership${q}`);
  },

  getSiteRecall: () => request<SiteRecallData>("/dashboard/site-recall"),

  getActivityBreakdown: () =>
    request<ActivityBreakdownData>("/dashboard/activity-breakdown"),

  getSIFTrend: (site?: string) => {
    const q = site ? `?site=${encodeURIComponent(site)}` : "";
    return request<TrendData>(`/dashboard/trend${q}`);
  },

  // Audit
  getAuditLog: (params: { report_id?: string; event_type?: string; page?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.report_id)  q.set("report_id", params.report_id);
    if (params.event_type) q.set("event_type", params.event_type);
    if (params.page)       q.set("page", String(params.page));
    return request<{ count: number; entries: any[] }>(`/audit-log?${q}`);
  },

  // Active Learning
  getALQueue: () => request<{ count: number; items: any[] }>("/active-learning/queue"),

  submitLabel: (itemId: string, body: {
    corrected_sif: boolean;
    corrected_iogp?: string[];
    corrected_cause?: string[];
    labeled_by: string;
  }) => request(`/active-learning/${itemId}/label`, {
    method: "POST",
    body: JSON.stringify(body),
  }),

  // Ingest
  ingestFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/ingest`, { method: "POST", body: formData }).then((r) => r.json());
  },

  // Health
  health: () => fetch("http://localhost:8000/health").then((r) => r.json()),
};
