import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Zap, Shield, AlertTriangle, Eye, CheckCircle, Clock } from "lucide-react";
import { api } from "../api";
import type { ReportDetail as ReportDetailData, IGSpan } from "../api";

// ── Sub-components ─────────────────────────────────────────────────────────────

function ScoreGauge({ prob }: { prob: number | null }) {
  if (prob === null) return null;
  const pct = Math.round(prob * 100);
  const cls = pct >= 70 ? "score-value--high" : pct >= 40 ? "score-value--medium" : "score-value--low";
  const color = pct >= 70 ? "var(--color-accent)" : "#111111";

  return (
    <div className="score-gauge-container">
      <div className={`score-value ${cls}`}>
        {pct}%
      </div>
      <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 4 }}>
        Calibrated SIF probability
      </div>
      <svg width={120} height={70} style={{ marginTop: 8 }} aria-hidden="true">
        <path d="M 10 65 A 50 50 0 0 1 110 65" fill="none" stroke="#E5E5E5" strokeWidth={4} />
        <path
          d="M 10 65 A 50 50 0 0 1 110 65"
          fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={`${pct * 1.57} 157`}
        />
      </svg>
    </div>
  );
}

function HighlightedText({ text, spans }: { text: string; spans: IGSpan[] }) {
  if (!spans.length) return <p className="highlighted-text">{text}</p>;

  // Sort spans by start position
  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;

  for (const span of sorted) {
    if (span.start > cursor) parts.push(text.slice(cursor, span.start));
    const cls = span.label.startsWith("BYPASS") ? "ig-span ig-span--high"
               : span.label.startsWith("BARRIER") ? "ig-span ig-span--high"
               : "ig-span";
    parts.push(
      <mark key={`${span.start}-${span.end}`} className={cls} title={`${span.label} (score: ${span.score})`}>
        {text.slice(span.start, span.end)}
      </mark>
    );
    cursor = span.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));

  return <p className="highlighted-text">{parts}</p>;
}

function SHAPChart({ values }: { values: Record<string, number> }) {
  const sorted = Object.entries(values)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 8);
  const max = Math.max(...sorted.map(([, v]) => Math.abs(v)));

  return (
    <div>
      {sorted.map(([name, val]) => (
        <div key={name} className="shap-bar-row">
          <div className="shap-label">{name.replace(/_/g, " ")}</div>
          <div className="shap-bar-track">
            <div
              className={`shap-bar-fill ${val >= 0 ? "shap-bar-fill--positive" : "shap-bar-fill--negative"}`}
              style={{ width: `${Math.abs(val) / max * 100}%` }}
            />
          </div>
          <div className="shap-value">{val > 0 ? "+" : ""}{val.toFixed(3)}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main View ──────────────────────────────────────────────────────────────────

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport]     = useState<ReportDetailData | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [officerId]             = useState("HSE-Duliajan-04");
  const [notes, setNotes]       = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted]   = useState<"AGREE" | "DISAGREE" | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getReport(id)
      .then((d: ReportDetailData) => setReport(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const submitDecision = async (decision: "AGREE" | "DISAGREE") => {
    if (!id || submitting) return;
    setSubmitting(true);
    try {
      await api.submitDecision(id, { officer_id: officerId, decision, notes });
      setSubmitted(decision);
      setReport(r => r ? { ...r, decision: { decision, officer_role: "safety_officer", notes, created_at: new Date().toISOString() } } : r);
    } finally { setSubmitting(false); }
  };

  if (loading) return (
    <div className="skeleton-block" aria-busy="true">
      <div className="skeleton" style={{ width: "30%" }} />
      <div className="skeleton" style={{ width: "90%" }} />
      <div className="skeleton" style={{ width: "75%" }} />
    </div>
  );

  if (error || !report) return (
    <div style={{ color: "var(--color-accent)", padding: 32 }}>Could not load report. {error}</div>
  );

  const pred  = report.prediction;
  const feat  = report.features;
  const prob  = pred?.calibrated_prob ?? null;
  const state = pred?.operational_state;

  return (
    <div className="animate-fade-in">
      {/* Back nav */}
      <button className="btn btn--ghost mb-6" style={{ padding: "6px 12px" }} onClick={() => navigate(-1)}>
        <ArrowLeft size={14} /> Back to Dashboard
      </button>

      {/* OOD / Low Confidence Banner */}
      {(report.lower_confidence_flag || state === "NEEDS_REVIEW") && (
        <div className="ood-banner">
          <span className="ood-banner__icon">REVIEW</span>
          <div>
            <div className="ood-banner__title">Manual Review Required</div>
            <div className="ood-banner__message">
              {report.text_only_mode
                ? "Site, shift, or equipment metadata is missing — AI confidence is reduced. Scores should be verified by a qualified HSE officer."
                : "This report's characteristics differ from the training distribution. The AI score may be less reliable than usual."}
              {pred?.ood_score && pred.ood_score > 3 && ` (OOD score: ${pred.ood_score.toFixed(2)})`}
            </div>
          </div>
        </div>
      )}

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: "var(--space-6)", alignItems: "start" }}>

        {/* LEFT: Report content */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>

          {/* Report metadata header */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 4, fontFamily: "var(--font-mono)" }}>
                  Report {report.id.slice(0, 8).toUpperCase()}
                </div>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                  {report.site && <span>{report.site}</span>}
                  {report.shift_date && <span>{new Date(report.shift_date).toLocaleDateString()}</span>}
                  {report.reporter_role && <span>{report.reporter_role}</span>}
                  {report.industry_sector && <span>{report.industry_sector}</span>}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {state === "FLAGGED"      && <AlertTriangle size={16} color="var(--color-accent)" />}
                {state === "NON_SIF"      && <CheckCircle   size={16} color="#111111" />}
                {state === "NEEDS_REVIEW" && <Clock         size={16} color="#6B6B6B" />}
                <span style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>{state ?? "Pending Scoring"}</span>
              </div>
            </div>

            {/* Highlighted narrative */}
            <div style={{ background: "var(--color-bg)", borderRadius: "var(--radius-md)", padding: "var(--space-5)", border: "1px solid var(--color-border-subtle)" }}>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                <Eye size={11} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Report Narrative — Highlighted Evidence
              </div>
              <HighlightedText text={report.report_text} spans={pred?.ig_spans ?? []} />
              <div style={{ marginTop: 12, display: "flex", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                  <span style={{ border: "1px solid #111111", borderRadius: 2, padding: "0 4px", fontFamily: "var(--font-mono)" }}>span</span>
                  Energy signal
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                  <span style={{ border: "1px solid var(--color-accent)", color: "var(--color-accent)", borderRadius: 2, padding: "0 4px", fontFamily: "var(--font-mono)" }}>span</span>
                  Barrier failure / Bypass
                </div>
              </div>
            </div>
          </div>

          {/* Feature vector tags */}
          {feat && (
            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: 16, fontSize: "var(--text-sm)" }}>Extracted Domain Features</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                    <Zap size={11} color="#111111" /> Energy Types
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {feat.energy_types.length === 0 && <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>None detected</span>}
                    {feat.energy_types.map(e => (
                      <span key={e} className="badge badge--low" style={{ textTransform: "capitalize" }}>{e.replace(/_/g, " ")}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                    <Shield size={11} color="var(--color-accent)" /> Barrier Status
                  </div>
                  <span className={`badge ${feat.barrier_status === "BYPASSED" || feat.barrier_status === "MISSING" ? "badge--high" : "badge--ambiguous"}`}>
                    {feat.barrier_status}
                  </span>
                </div>
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8 }}>Interlock Bypass</div>
                  <span className={`badge ${feat.interlock_bypass_detected ? "badge--high" : "badge--clear"}`}>
                    {feat.interlock_bypass_detected ? "DETECTED" : "Not detected"}
                  </span>
                </div>
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8 }}>Hi-Po Flag</div>
                  <span className={`badge ${feat.hi_po ? "badge--high" : "badge--clear"}`}>
                    {feat.hi_po ? `Hi-Po · Level ${feat.potential_accident_level}` : `Level ${feat.potential_accident_level ?? "—"}`}
                  </span>
                </div>
              </div>

              {/* Safety mgmt / equipment terms */}
              {(feat.safety_mgmt_terms.length > 0 || feat.equipment_terms.length > 0) && (
                <div style={{ marginTop: 16, display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {feat.safety_mgmt_terms.map(t => <span key={t} className="reason-tag">{t}</span>)}
                  {feat.equipment_terms.map(t => <span key={t} className="rule-chip">{t}</span>)}
                </div>
              )}
            </div>
          )}

          {/* SHAP feature attribution */}
          {pred?.shap_values && Object.keys(pred.shap_values).length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: 4, fontSize: "var(--text-sm)" }}>Feature Attribution (SHAP)</div>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 16 }}>
                Maroon bars raise SIF probability. Black bars lower it.
              </div>
              <SHAPChart values={pred.shap_values} />
            </div>
          )}
        </div>

        {/* RIGHT: Score panel + Officer decision */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", position: "sticky", top: 24 }}>

          {/* Score card */}
          <div className="card-raised" style={{ textAlign: "center" }}>
            <ScoreGauge prob={prob} />
            <div className="divider" />
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* IOGP Rules */}
              <div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8, textAlign: "left" }}>IOGP Rules Triggered</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(pred?.iogp_rules ?? []).map(r => <span key={r} className="rule-chip">{r}</span>)}
                  {(!pred?.iogp_rules || pred.iogp_rules.length === 0) && (
                    <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>None</span>
                  )}
                </div>
              </div>
              {/* Cause categories */}
              {pred?.cause_categories && pred.cause_categories.length > 0 && (
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 8, textAlign: "left" }}>Cause Categories</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {pred.cause_categories.map(c => <span key={c} className="reason-tag">{c}</span>)}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Officer Decision Card */}
          <div className="card">
            <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", marginBottom: 4 }}>Officer Decision</div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: 16 }}>
              Do you agree with the AI assessment?
            </div>

            {report.decision ? (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                  {report.decision.decision === "AGREE"
                    ? <CheckCircle size={16} color="#111111" />
                    : <AlertTriangle size={16} color="var(--color-accent)" />}
                  <span style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{report.decision.decision}</span>
                </div>
                {report.decision.notes && (
                  <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", fontStyle: "italic" }}>
                    "{report.decision.notes}"
                  </p>
                )}
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 8 }}>
                  Decision recorded · {new Date(report.decision.created_at).toLocaleString()}
                </p>
              </div>
            ) : (
              <div>
                <label className="field-label" htmlFor="input-officer-notes">Decision notes</label>
                <textarea
                  id="input-officer-notes"
                  placeholder="Optional. Recorded on the audit log."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  style={{
                    width: "100%", background: "#FFFFFF", border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)", color: "var(--color-text-primary)", padding: "var(--space-3)",
                    fontSize: "var(--text-sm)", fontFamily: "var(--font-sans)", marginBottom: 12, resize: "vertical",
                    outline: "none",
                  }}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    id="btn-agree"
                    className="btn btn--agree"
                    style={{ flex: 1 }}
                    onClick={() => submitDecision("AGREE")}
                    disabled={submitting || !!submitted}
                  >
                    <CheckCircle size={14} /> Agree
                  </button>
                  <button
                    id="btn-disagree"
                    className="btn btn--disagree"
                    style={{ flex: 1 }}
                    onClick={() => submitDecision("DISAGREE")}
                    disabled={submitting || !!submitted}
                  >
                    <AlertTriangle size={14} /> Disagree
                  </button>
                </div>
                {submitted && (
                  <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 8 }}>
                    Decision recorded.
                  </p>
                )}
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 12 }}>
                  Disagreement automatically adds this report to the active learning queue for model retraining.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
