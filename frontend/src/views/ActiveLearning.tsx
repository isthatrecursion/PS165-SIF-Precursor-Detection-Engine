import { useEffect, useState } from "react";
import { FlaskConical, CheckCircle } from "lucide-react";
import { api } from "../api";

export default function ActiveLearning() {
  const [data, setData]         = useState<any>(null);
  const [loading, setLoading]   = useState(true);
  const [labeling, setLabeling] = useState<Record<string, { sif: boolean; notes: string }>>({});
  const [done, setDone]         = useState<Set<string>>(new Set());

  useEffect(() => {
    api.getALQueue().then(setData).finally(() => setLoading(false));
  }, []);

  const submitLabel = async (itemId: string) => {
    const l = labeling[itemId];
    if (l === undefined) return;
    await api.submitLabel(itemId, {
      corrected_sif: l.sif,
      labeled_by: "officer-review",
    });
    setDone(d => new Set([...d, itemId]));
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 600, color: "#000000" }}>Active Learning Queue</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4, maxWidth: "70ch" }}>
            Low-confidence and disputed reports, ordered for labeling before the next retrain.
          </p>
        </div>
        <span className="badge badge--ambiguous">
          <FlaskConical size={11} /> {data?.count ?? "—"} pending labels
        </span>
      </div>

      {/* How it works info box */}
      <div className="info-callout">
        <FlaskConical size={16} color="#111111" style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", maxWidth: "70ch" }}>
          <strong style={{ color: "#000000", fontWeight: 600 }}>What lands here.</strong>{" "}
          Uncertain scores and officer disagreements. Labels you submit are used on the next retrain. Lowest confidence first.
        </div>
      </div>

      {loading && (
        <div className="skeleton-block" aria-busy="true">
          <div className="skeleton" style={{ width: "40%" }} />
          <div className="skeleton" style={{ width: "85%" }} />
          <div className="skeleton" style={{ width: "60%" }} />
        </div>
      )}

      {!loading && data?.count === 0 && (
        <div className="card" style={{ padding: 48 }}>
          <CheckCircle size={20} color="#111111" style={{ marginBottom: 12 }} />
          <div style={{ fontWeight: 600 }}>Queue is empty</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>
            No reports need relabeling.
          </div>
        </div>
      )}

      {!loading && data?.items?.map((item: any) => (
        <div key={item.id} className="card mb-4" style={{
          borderLeft: done.has(item.id) ? "3px solid #111111" : "3px solid var(--color-accent)",
          opacity: done.has(item.id) ? 0.6 : 1,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                {item.report_id?.slice(0, 12)}…
              </span>
              <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                <span className="reason-tag">{item.queue_reason}</span>
                {item.site && <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>{item.site}</span>}
                <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                  Model prob: {item.model_prob !== null ? `${Math.round(item.model_prob * 100)}%` : "—"}
                </span>
              </div>
            </div>
            {done.has(item.id) && (
              <span className="badge badge--clear"><CheckCircle size={10} /> Labeled</span>
            )}
          </div>

          {/* Report text snippet */}
          <div style={{
            background: "#FFFFFF", borderRadius: "var(--radius-md)",
            padding: "var(--space-4)", marginBottom: 16,
            border: "1px solid var(--color-border-subtle)",
            fontSize: "var(--text-sm)", color: "var(--color-text-secondary)",
            lineHeight: 1.7,
          }}>
            {item.report_text?.slice(0, 300)}{item.report_text?.length > 300 ? "…" : ""}
          </div>

          {/* Labeling controls */}
          {!done.has(item.id) && (
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontWeight: 500 }}>
                Correct label:
              </span>
              <button
                id={`label-sif-yes-${item.id.slice(0, 8)}`}
                className={`btn ${labeling[item.id]?.sif === true ? "btn--disagree" : "btn--ghost"}`}
                style={{ padding: "4px 16px", fontSize: "var(--text-xs)" }}
                onClick={() => setLabeling(l => ({ ...l, [item.id]: { sif: true, notes: "" } }))}
              >
                SIF Precursor
              </button>
              <button
                id={`label-sif-no-${item.id.slice(0, 8)}`}
                className={`btn ${labeling[item.id]?.sif === false ? "btn--agree" : "btn--ghost"}`}
                style={{ padding: "4px 16px", fontSize: "var(--text-xs)" }}
                onClick={() => setLabeling(l => ({ ...l, [item.id]: { sif: false, notes: "" } }))}
              >
                Not SIF
              </button>
              {labeling[item.id] !== undefined && (
                <button
                  id={`submit-label-${item.id.slice(0, 8)}`}
                  className="btn btn--primary"
                  style={{ padding: "4px 16px", fontSize: "var(--text-xs)" }}
                  onClick={() => submitLabel(item.id)}
                >
                  Submit Label
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
