import { useEffect, useState } from "react";
import { BookOpen, RefreshCw } from "lucide-react";
import { api } from "../api";

const EVENT_COLOR: Record<string, string> = {
  INGESTED:  "#111111",
  PREDICTED: "#111111",
  DECIDED:   "#111111",
};

export default function AuditLog() {
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState("");
  const [page, setPage]       = useState(1);

  const load = () => {
    setLoading(true);
    api.getAuditLog({ event_type: filter || undefined, page })
      .then(setData)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter, page]);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 600, color: "#000000" }}>Audit Log</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4, maxWidth: "70ch" }}>
            Append-only record of ingest, prediction, and officer decisions.
          </p>
        </div>
        <button id="btn-refresh-audit" className="btn btn--ghost" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filter */}
      <div className="card mb-4" style={{ padding: "12px 20px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <BookOpen size={14} color="var(--color-text-muted)" />
          <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontWeight: 500 }}>Event Type:</span>
          <select id="filter-event-type" value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}
            style={{ width: "auto", padding: "4px 8px" }}>
            <option value="">All Events</option>
            <option value="INGESTED">INGESTED</option>
            <option value="PREDICTED">PREDICTED</option>
            <option value="DECIDED">DECIDED</option>
          </select>
          <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "auto" }}>
            {data?.count ?? "—"} entries
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading && (
          <div className="skeleton-block" aria-busy="true">
            <div className="skeleton" style={{ width: "45%" }} />
            <div className="skeleton" style={{ width: "90%" }} />
            <div className="skeleton" style={{ width: "70%" }} />
          </div>
        )}
        {!loading && (
          <table className="data-table">
            <thead>
              <tr>
                <th className="num">Timestamp</th>
                <th>Event</th>
                <th>Report ID</th>
                <th className="num">Model Score</th>
                <th>Officer Action</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {data?.entries?.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 32, color: "var(--color-text-muted)" }}>
                  No audit entries yet.
                </td></tr>
              )}
              {data?.entries?.map((e: any) => (
                <tr key={e.id}>
                  <td className="num">
                    {new Date(e.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      fontSize: "var(--text-xs)", fontWeight: 600,
                      color: EVENT_COLOR[e.event_type] ?? "var(--color-text-secondary)"
                    }}>
                      <span style={{ width: 6, height: 6, borderRadius: 0, background: EVENT_COLOR[e.event_type] ?? "var(--color-border)" }} />
                      {e.event_type}
                    </span>
                  </td>
                  <td style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                    {e.report_id?.slice(0, 12)}…
                  </td>
                  <td className="num">
                    {e.model_score !== null && e.model_score !== undefined
                      ? `${Math.round(e.model_score * 100)}%`
                      : "—"}
                  </td>
                  <td>
                    {e.officer_action && (
                      <span className={`badge ${e.officer_action === "AGREE" ? "badge--clear" : "badge--high"}`}>
                        {e.officer_action}
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                    {e.officer_role ?? "system"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {/* Pagination */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderTop: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>Page {page}</span>
          <div className="flex gap-2">
            <button className="btn btn--ghost" style={{ padding: "4px 12px" }} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← Prev</button>
            <button className="btn btn--ghost" style={{ padding: "4px 12px" }} onClick={() => setPage(p => p + 1)}>Next →</button>
          </div>
        </div>
      </div>
    </div>
  );
}
