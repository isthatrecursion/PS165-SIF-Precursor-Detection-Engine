import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, AlertCircle } from "lucide-react";
import { api } from "../api";

const REASON_LABEL: Record<string, string> = {
  OCR_FAILED:       "OCR Failed",
  LOW_CONFIDENCE:   "Low Confidence",
  AMBIGUOUS_OOD:    "Out-of-Distribution",
  MISSING_METADATA: "Missing Metadata",
};

export default function ManualReviewQueue() {
  const navigate = useNavigate();
  const [data, setData]     = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    api.getManualReviewQueue()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 600, color: "#000000" }}>Manual Review Queue</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4, maxWidth: "70ch" }}>
            Reports the model would not score: missing fields, OCR failure, or out-of-distribution language.
          </p>
        </div>
        <div className="badge badge--low" style={{ padding: "6px 14px" }}>
          <Clock size={12} /> {data?.count ?? "—"} pending
        </div>
      </div>

      {/* Why reports end up here — info box */}
      <div className="info-callout">
        <AlertCircle size={16} color="#111111" style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", maxWidth: "70ch" }}>
          <strong style={{ color: "#000000", fontWeight: 600 }}>Routing rule.</strong>{" "}
          Unscoreable reports come here instead of Non-SIF. A Non-SIF default on missing evidence would understate risk.
        </div>
      </div>

      {loading && (
        <div className="skeleton-block" aria-busy="true">
          <div className="skeleton" style={{ width: "50%" }} />
          <div className="skeleton" style={{ width: "88%" }} />
          <div className="skeleton" style={{ width: "72%" }} />
        </div>
      )}
      {error   && <div style={{ color: "var(--color-accent)", padding: 32 }}>{error}</div>}

      {!loading && !error && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {data?.count === 0 ? (
            <div style={{ padding: 48, color: "var(--color-text-muted)" }}>
              <div style={{ fontWeight: 600, color: "#000000" }}>Queue is empty</div>
              <div style={{ fontSize: "var(--text-sm)", marginTop: 4 }}>All ingested reports were scoreable.</div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report ID</th>
                  <th>Site</th>
                  <th className="num">Date</th>
                  <th>Routing Reason</th>
                  <th>Confidence Band</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data?.reports.map((r: any) => (
                  <tr key={r.id} id={`mr-row-${r.id.slice(0, 8)}`} onClick={() => navigate(`/reports/${r.id}`)}>
                    <td style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                      {r.id.slice(0, 12)}…
                    </td>
                    <td style={{ fontSize: "var(--text-xs)" }}>{r.site ?? "—"}</td>
                    <td className="num">
                      {r.shift_date ? new Date(r.shift_date).toLocaleDateString() : "—"}
                    </td>
                    <td>
                      <span className="reason-tag">
                        {REASON_LABEL[r.routing_reason] ?? r.routing_reason ?? "Unknown"}
                      </span>
                    </td>
                    <td>
                      {r.confidence_band && (
                        <span className={`badge badge--${(r.confidence_band as string).toLowerCase()}`}>
                          {r.confidence_band}
                        </span>
                      )}
                    </td>
                    <td>
                      <button className="btn btn--ghost" style={{ fontSize: "var(--text-xs)", padding: "4px 10px" }}
                        onClick={(e) => { e.stopPropagation(); navigate(`/reports/${r.id}`); }}>
                        Review →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
