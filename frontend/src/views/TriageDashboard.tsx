import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, Filter, AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { api } from "../api";
import type { ReportListResponse } from "../api";

const BAND_LABEL: Record<string, string> = {
  HIGH: "High Risk", LOW: "Low Conf.", AMBIGUOUS: "Ambiguous", OOD: "Out-of-Dist."
};
const OP_STATE_ICON: Record<string, React.ReactNode> = {
  FLAGGED:      <AlertTriangle size={13} color="var(--color-accent)" />,
  NON_SIF:      <CheckCircle size={13} color="#111111" />,
  NEEDS_REVIEW: <Clock size={13} color="#6B6B6B" />,
};

function ConfBadge({ band }: { band: string | null }) {
  if (!band) return null;
  const cls = { HIGH: "badge--high", LOW: "badge--low", AMBIGUOUS: "badge--ambiguous", OOD: "badge--ood" }[band] ?? "badge--ood";
  return <span className={`badge ${cls}`}>{BAND_LABEL[band] ?? band}</span>;
}

function ProbBar({ prob }: { prob: number | null }) {
  if (prob === null) return <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>—</span>;
  const pct = Math.round(prob * 100);
  const color = pct >= 70 ? "var(--color-accent)" : "#111111";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
      <div style={{ width: 60, height: 4, background: "var(--color-border)", borderRadius: 0 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color }} />
      </div>
      <span style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)", color, fontVariantNumeric: "tabular-nums" }}>{pct}%</span>
    </div>
  );
}

export default function TriageDashboard() {
  const navigate = useNavigate();
  const [data, setData]       = useState<ReportListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [page, setPage]       = useState(1);
  const [filters, setFilters] = useState({ site: "", confidence_band: "", status: "", flagged: "" });
  const [scoring, setScoring] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params: Record<string, any> = { page, page_size: 50 };
      if (filters.site)             params.site = filters.site;
      if (filters.confidence_band)  params.confidence_band = filters.confidence_band;
      if (filters.status)           params.status = filters.status;
      if (filters.flagged === "true")  params.stage1_flagged = true;
      if (filters.flagged === "false") params.stage1_flagged = false;
      setData(await api.listReports(params));
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  const triggerScoring = async () => {
    setScoring(true);
    try { await api.triggerStage2(); setTimeout(() => { setScoring(false); load(); }, 2500); }
    catch { setScoring(false); }
  };

  return (
    <div className="animate-fade-in">
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 600, color: "#000000" }}>
            Officer Triage Dashboard
          </h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4, maxWidth: "70ch" }}>
            Queue of ingested reports, sorted for HSE officers. Open a row to agree or disagree with the score.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            id="btn-score-stage2"
            className="btn btn--primary"
            onClick={triggerScoring}
            disabled={scoring}
            style={{ opacity: scoring ? 0.6 : 1 }}
          >
            <RefreshCw size={14} />
            {scoring ? "Scoring…" : "Run Stage 2"}
          </button>
          <button id="btn-refresh-triage" className="btn btn--ghost" onClick={load}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="grid-3 mb-6">
        {[
          { label: "Total Reports",  val: data?.total_count ?? "—",
            sub: "matching current filter", color: "#000000" },
          { label: "SIF Flagged",    val: data?.sif_flagged_count ?? "—",
            sub: "require officer review", color: "var(--color-accent)" },
          { label: "Needs Review",   val: data?.needs_review_count ?? "—",
            sub: "low confidence / OOD", color: "#111111" },
        ].map((s) => (
          <div key={s.label} className="card" style={{ borderLeft: `3px solid ${s.color}` }}>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 600, fontFamily: "var(--font-mono)", color: s.color }}>{s.val}</div>
            <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginTop: 4 }}>{s.label}</div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Filter row */}
      <div className="card mb-4" style={{ padding: "12px 20px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <Filter size={14} color="var(--color-text-muted)" />
          {[
            { key: "flagged", label: "Stage 1", opts: [["", "All"], ["true", "Flagged"], ["false", "Cleared"]] },
            { key: "confidence_band", label: "Confidence", opts: [["", "All Bands"], ["HIGH", "High Risk"], ["LOW", "Low Conf."], ["AMBIGUOUS", "Ambiguous"], ["OOD", "OOD"]] },
            { key: "status", label: "Review Status", opts: [["", "All"], ["UNREVIEWED", "Unreviewed"], ["REVIEWED", "Reviewed"]] },
          ].map(({ key, label, opts }) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontWeight: 500 }}>{label}:</span>
              <select
                id={`filter-${key}`}
                value={(filters as any)[key]}
                onChange={(e) => { setFilters(f => ({ ...f, [key]: e.target.value })); setPage(1); }}
                style={{ width: "auto", padding: "4px 8px" }}
              >
                {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          ))}
          <button className="btn btn--ghost" style={{ padding: "4px 12px", fontSize: "var(--text-xs)" }}
            onClick={() => { setFilters({ site: "", confidence_band: "", status: "", flagged: "" }); setPage(1); }}>
            Clear
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading && (
          <div className="skeleton-block" aria-busy="true" aria-live="polite">
            <div className="skeleton" style={{ width: "40%" }} />
            <div className="skeleton" style={{ width: "92%" }} />
            <div className="skeleton" style={{ width: "88%" }} />
            <div className="skeleton" style={{ width: "70%" }} />
          </div>
        )}
        {error && (
          <div style={{ padding: 40, color: "var(--color-accent)" }}>
            Could not load reports. {error}
          </div>
        )}
        {!loading && !error && (
          <table className="data-table">
            <thead>
              <tr>
                <th>State</th>
                <th>Site</th>
                <th className="num">Date</th>
                <th>Reporter Role</th>
                <th className="num">Risk Score</th>
                <th>Confidence</th>
                <th>IOGP Rules</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {data?.reports.length === 0 && (
                <tr><td colSpan={8} style={{ padding: 32, color: "var(--color-text-muted)" }}>
                  No reports match the current filters.
                </td></tr>
              )}
              {data?.reports.map((r) => (
                <tr key={r.id} id={`row-${r.id.slice(0,8)}`} onClick={() => navigate(`/reports/${r.id}`)}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "var(--text-xs)", fontWeight: 500 }}>
                      {OP_STATE_ICON[r.operational_state ?? ""] ?? null}
                      {r.operational_state ?? "Pending"}
                    </div>
                  </td>
                  <td style={{ fontSize: "var(--text-xs)" }}>{r.site ?? "—"}</td>
                  <td className="num" style={{ fontSize: "var(--text-xs)" }}>
                    {r.shift_date ? new Date(r.shift_date).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ fontSize: "var(--text-xs)" }}>{r.reporter_role ?? "—"}</td>
                  <td className="num"><ProbBar prob={r.calibrated_prob} /></td>
                  <td><ConfBadge band={r.confidence_band} /></td>
                  <td>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {(r.iogp_rules ?? []).slice(0, 2).map((rule) => (
                        <span key={rule} className="rule-chip">{rule}</span>
                      ))}
                      {(r.iogp_rules ?? []).length > 2 && (
                        <span className="rule-chip">+{r.iogp_rules.length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`status-pill ${r.decision ? "status-pill--reviewed" : "status-pill--unreviewed"}`}>
                      {r.decision ? "Reviewed" : "Unreviewed"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {data && data.total_count > 0 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderTop: "1px solid var(--color-border)" }}>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
              Showing {((page - 1) * 50) + 1}–{Math.min(page * 50, data.total_count)} of {data.total_count} reports
            </span>
            <div className="flex gap-2">
              <button className="btn btn--ghost" style={{ padding: "4px 12px" }} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                ← Prev
              </button>
              <button className="btn btn--ghost" style={{ padding: "4px 12px" }} onClick={() => setPage(p => p + 1)} disabled={page * 50 >= data.total_count}>
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
