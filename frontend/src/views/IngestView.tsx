import { useState, useRef } from "react";
import { Upload, CheckCircle, AlertTriangle, FileText } from "lucide-react";
import { api } from "../api";

export default function IngestView() {
  const [dragging, setDragging]   = useState(false);
  const [file, setFile]           = useState<File | null>(null);
  const [result, setResult]       = useState<any>(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const inputRef                  = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleIngest = async () => {
    if (!file) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await api.ingestFile(file);
      if (r.detail) throw new Error(r.detail);
      setResult(r);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 600, color: "#000000" }}>Upload Safety Reports</h1>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4, maxWidth: "70ch" }}>
          CSV or Excel. Each row goes through the OCR gate, OISD feature extractor, and Stage 1 filter.
        </p>
      </div>

      {/* Drop zone */}
      <div
        id="drop-zone"
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `1px dashed ${dragging ? "#000000" : "var(--color-border)"}`,
          borderRadius: "var(--radius-md)",
          padding: "48px 32px",
          textAlign: "center",
          cursor: "pointer",
          background: "#FFFFFF",
          marginBottom: "var(--space-6)",
        }}
      >
        <Upload size={24} color="#111111"
          style={{ marginBottom: 12 }} />
        <div style={{ fontWeight: 600, marginBottom: 6 }}>
          {file ? file.name : "Drag & drop your CSV or Excel file here"}
        </div>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          {file
            ? `${(file.size / 1024).toFixed(1)} KB — ready to ingest`
            : "or click to browse · Supported: .csv, .xlsx, .xls"}
        </div>
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])} />
      </div>

      {/* Expected format info */}
      <div className="card mb-6">
        <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", marginBottom: 12 }}>Expected Column Format</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
          {[
            ["Description", "Full narrative text of the safety report (required)"],
            ["Potential Accident Level", "I–VI scale. IV/V/VI → SIF label"],
            ["Local", "Site identifier (e.g. Local_01)"],
            ["Countries", "Country name"],
            ["Critical Risk", "Risk category (maps to IOGP rules)"],
            ["Employee or Third Party", "Reporter role"],
            ["Data", "Incident date"],
            ["Industry Sector", "Sector classification"],
          ].map(([col, desc]) => (
            <div key={col} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <code style={{
                fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)",
                background: "#FFFFFF", padding: "2px 6px",
                borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)",
                flexShrink: 0, color: "#111111",
              }}>{col}</code>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>{desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Ingest button */}
      <button
        id="btn-ingest"
        className="btn btn--primary"
        onClick={handleIngest}
        disabled={!file || loading}
        style={{ opacity: !file || loading ? 0.5 : 1, marginBottom: "var(--space-6)" }}
      >
        <FileText size={14} />
        {loading ? "Ingesting…" : "Ingest File"}
      </button>

      {/* Error */}
      {error && (
        <div style={{ display: "flex", gap: 10, padding: 16, background: "#FFFFFF", border: "1px solid var(--color-accent)", borderRadius: "var(--radius-md)", color: "var(--color-accent)" }}>
          <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: "var(--text-sm)" }}>{error}</div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ padding: 24, background: "#FFFFFF", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
            <CheckCircle size={20} color="#111111" />
            <span style={{ fontWeight: 600, fontSize: "var(--text-lg)", color: "#000000" }}>
              Ingestion complete
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {[
              { label: "Total Processed",    val: result.total,          color: "#000000" },
              { label: "Processable",        val: result.processable,    color: "#111111" },
              { label: "Manual Review",      val: result.manual_review,  color: "#111111" },
              { label: "Stage 1 Flagged",    val: result.stage1_flagged, color: "var(--color-accent)" },
            ].map((s) => (
              <div key={s.label}>
                <div style={{ fontSize: "var(--text-3xl)", fontWeight: 600, fontFamily: "var(--font-mono)", color: s.color }}>{s.val}</div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 16 }}>
            Go to Triage and run Stage 2 to score flagged rows.
          </p>
        </div>
      )}
    </div>
  );
}
