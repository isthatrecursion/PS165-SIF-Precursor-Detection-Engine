import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, LineChart, Line, Legend,
} from "recharts";
import { TrendingUp, AlertTriangle, Activity, MapPin } from "lucide-react";
import { api } from "../api";
import type { DashboardData, SiteRecallData, ActivityBreakdownData, TrendData } from "../api";

const ACCENT = "#8F1D1D";
const GREYS = ["#111111", "#333333", "#555555", "#6B6B6B", "#888888", "#AAAAAA"];
const RISK_COLOR = (pct: number) => pct >= 60 ? ACCENT : pct >= 35 ? "#111111" : "#6B6B6B";

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:"#FFFFFF", border:"1px solid var(--color-border)", borderRadius:"var(--radius-md)", padding:"10px 14px", fontSize:"var(--text-xs)" }}>
      <div style={{ fontWeight:600, marginBottom:4 }}>{label}</div>
      {payload.map((p: any) => <div key={p.dataKey} style={{ color: p.fill ?? p.color }}>{p.name}: {p.value}</div>)}
    </div>
  );
}

function shortActivity(act: string) {
  const map: Record<string,string> = {
    "Energy Isolation":"Energy Isolation","Fire Prevention":"Fire / Hot Work","Working at Height":"Work at Height",
    "Confined Space":"Confined Space","Safe Mechanical Lifting":"Lifting Ops","Vehicle / Mobile Equipment":"Driving / Vehicle",
    "Hazardous Substances":"Hazmat","Permit to Work":"Permit to Work","Slip/Trip/Fall Prevention":"Slip/Trip/Fall",
    "Mechanical":"Mechanical","Manual Handling":"Manual Handling","Line of Fire":"Line of Fire","SIMOPS":"SIMOPS","General Safety":"General Safety",
  };
  return map[act] ?? act;
}

export default function LeadershipDashboard() {
  const [dash, setDash]           = useState<DashboardData | null>(null);
  const [recall, setRecall]       = useState<SiteRecallData | null>(null);
  const [activity, setActivity]   = useState<ActivityBreakdownData | null>(null);
  const [trend, setTrend]         = useState<TrendData | null>(null);
  const [trendSite, setTrendSite] = useState<string>("");
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([api.getLeadershipDashboard(), api.getSiteRecall(), api.getActivityBreakdown(), api.getSIFTrend()])
      .then(([d,r,a,t]) => { setDash(d); setRecall(r); setActivity(a); setTrend(t); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { api.getSIFTrend(trendSite || undefined).then(setTrend); }, [trendSite]);

  if (loading) return (
    <div className="skeleton-block" aria-busy="true">
      <div className="skeleton" style={{ width: "36%" }} />
      <div className="skeleton" style={{ width: "80%" }} />
      <div className="skeleton" style={{ width: "64%" }} />
    </div>
  );

  const sites = recall?.sites.map(s => s.site).filter(Boolean) ?? [];
  const activityChart = (activity?.activity_density ?? []).slice(0,10).map(a => ({ ...a, label: shortActivity(a.activity) }));
  
  const groupedSiteSummary = Object.values((dash?.site_summary ?? []).reduce((acc: any, curr) => {
    if (!acc[curr.site]) acc[curr.site] = { ...curr };
    else {
      acc[curr.site].total_reports += curr.total_reports;
      acc[curr.site].sif_precursor_count += curr.sif_precursor_count;
      acc[curr.site].sif_rate_pct = acc[curr.site].total_reports ? 
        ((acc[curr.site].sif_precursor_count / acc[curr.site].total_reports) * 100).toFixed(1) : 0;
    }
    return acc;
  }, {}));

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize:"var(--text-2xl)", fontWeight:600, color:"#000000" }}>Leadership Analytics Dashboard</h1>
          <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-muted)", marginTop:4, maxWidth:"70ch" }}>
            Site-level SIF precursor rates. Individual reports are not shown here.
          </p>
        </div>
        <span className="badge badge--clear"><TrendingUp size={11}/> Aggregation Only</span>
      </div>

      {/* PANEL 1: Site Cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px, 1fr))", gap:"var(--space-4)", marginBottom:"var(--space-6)" }}>
        {groupedSiteSummary.map((s: any) => (
          <div key={s.site} className="card" style={{ borderLeft:`3px solid ${s.sif_rate_pct>=30?"var(--color-accent)":"#111111"}` }}>
            <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:4 }}>{s.site ?? "Unknown"}</div>
            <div style={{ fontSize:"var(--text-2xl)", fontWeight:600, fontFamily:"var(--font-mono)" }}>{s.sif_precursor_count}</div>
            <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-secondary)" }}>SIF of {s.total_reports} ({s.sif_rate_pct}%)</div>
          </div>
        ))}
      </div>

      {/* PANEL 2: IOGP Freq + Cause Pie */}
      <div className="grid-2" style={{ marginBottom:"var(--space-6)" }}>
        <div className="card">
          <div style={{ fontWeight:600, marginBottom:4, fontSize:"var(--text-sm)" }}>IOGP Rule Frequency</div>
          <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:16 }}>Most frequently triggered safety rules across all SIF-flagged reports</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={dash?.iogp_rule_frequency.slice(0,8)} layout="vertical">
              <CartesianGrid strokeDasharray="0" stroke="#E5E5E5"/>
              <XAxis type="number" tick={{ fill:"#6B6B6B", fontSize:11, fontFamily:"JetBrains Mono, monospace" }}/>
              <YAxis dataKey="rule" type="category" width={140} tick={{ fill:"#111111", fontSize:10 }}/>
              <Tooltip content={<CustomTooltip/>}/>
              <Bar dataKey="count" name="Count" radius={[0,0,0,0]}>
                {dash?.iogp_rule_frequency.slice(0,8).map((_,i) => <Cell key={i} fill={GREYS[i%GREYS.length]}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div style={{ fontWeight:600, marginBottom:4, fontSize:"var(--text-sm)" }}>Root Cause Distribution</div>
          <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:16 }}>Cause taxonomy across SIF-flagged reports (14-category OISD taxonomy)</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={dash?.cause_category_frequency.slice(0,6)} dataKey="count" nameKey="cause" cx="50%" cy="50%" outerRadius={80}
                label={({ cause, percent }: any) => `${cause.split("/")[0].trim()} (${(percent*100).toFixed(0)}%)`} labelLine={false} fontSize={9}>
                {dash?.cause_category_frequency.slice(0,6).map((_,i) => <Cell key={i} fill={GREYS[i%GREYS.length]}/>)}
              </Pie>
              <Tooltip content={<CustomTooltip/>}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* PANEL 3: Activity Density + Site x Activity (GAPS 1 & 2 CLOSED) */}
      <div className="grid-2" style={{ marginBottom:"var(--space-6)" }}>
        <div className="card">
          <div className="flex items-center" style={{ gap:8, marginBottom:4 }}>
            <Activity size={14} color="#111111"/>
            <div style={{ fontWeight:600, fontSize:"var(--text-sm)" }}>SIF Precursor Density by Activity</div>
          </div>
          <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:16 }}>Activities ranked by SIF rate - highest fatal-potential first</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={activityChart} layout="vertical" margin={{ left:8, right:24 }}>
              <CartesianGrid strokeDasharray="0" stroke="#E5E5E5"/>
              <XAxis type="number" unit="%" domain={[0,100]} tick={{ fill:"#6B6B6B", fontSize:11, fontFamily:"JetBrains Mono, monospace" }}/>
              <YAxis dataKey="label" type="category" width={130} tick={{ fill:"#111111", fontSize:10 }}/>
              <Tooltip content={({ active, payload }: any) => {
                if (!active || !payload?.length) return null;
                const d = payload[0]?.payload;
                return <div style={{ background:"#FFFFFF", border:"1px solid var(--color-border)", borderRadius:"var(--radius-md)", padding:"10px 14px", fontSize:"var(--text-xs)" }}>
                  <div style={{ fontWeight:600, marginBottom:4 }}>{d?.activity}</div>
                  <div>SIF Rate: <strong>{d?.sif_rate_pct}%</strong></div>
                  <div style={{ color:"var(--color-text-muted)" }}>{d?.sif_count} SIF of {d?.total_reports} total</div>
                </div>;
              }}/>
              <Bar dataKey="sif_rate_pct" name="SIF Rate %" radius={[0,0,0,0]}>
                {activityChart.map((a,i) => <Cell key={i} fill={RISK_COLOR(a.sif_rate_pct)}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="flex items-center" style={{ gap:8, marginBottom:4 }}>
            <MapPin size={14} color="#111111"/>
            <div style={{ fontWeight:600, fontSize:"var(--text-sm)" }}>Site x Activity - SIF Density</div>
          </div>
          <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:12 }}>Where each hazardous activity type is clustering - focus interventions here</div>
          <div style={{ overflowY:"auto", maxHeight:260 }}>
            <table className="data-table">
              <thead><tr><th>Site</th><th>Activity</th><th className="num">SIF Reports</th><th>Density</th></tr></thead>
              <tbody>
                {(activity?.site_activity_matrix ?? []).slice(0,15).map((row,i) => (
                  <tr key={i}>
                    <td style={{ fontSize:"var(--text-xs)", fontWeight:500 }}>{row.site}</td>
                    <td style={{ fontSize:"var(--text-xs)" }}>{shortActivity(row.activity)}</td>
                    <td className="num">{row.sif_count}</td>
                    <td><div style={{ width:`${Math.min(row.sif_count*8,100)}%`, minWidth:4, height:4, borderRadius:0, background:row.sif_count>=10?ACCENT:"#111111" }}/></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* PANEL 4: Monthly SIF Trend (GAP 3 CLOSED) */}
      <div className="card" style={{ marginBottom:"var(--space-6)" }}>
        <div className="flex items-center justify-between" style={{ marginBottom:4 }}>
          <div className="flex items-center" style={{ gap:8 }}>
            <TrendingUp size={14} color="#111111"/>
            <div style={{ fontWeight:600, fontSize:"var(--text-sm)" }}>
              Monthly SIF Precursor Trend {trendSite && <span style={{ color:"#111111", marginLeft:6 }}>— {trendSite}</span>}
            </div>
          </div>
          <select value={trendSite} onChange={e => setTrendSite(e.target.value)} style={{ background:"#FFFFFF", border:"1px solid var(--color-border)", borderRadius:"var(--radius-sm)", padding:"4px 10px", fontSize:"var(--text-xs)", color:"var(--color-text-primary)", cursor:"pointer" }}>
            <option value="">All Sites</option>
            {sites.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginBottom:16 }}>SIF precursor rate (%) per month - rising trend indicates escalating risk</div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trend?.trend ?? []} margin={{ left:0, right:16 }}>
            <CartesianGrid strokeDasharray="0" stroke="#E5E5E5"/>
            <XAxis dataKey="month" tick={{ fill:"#6B6B6B", fontSize:10, fontFamily:"JetBrains Mono, monospace" }} tickFormatter={v => v.slice(2)}/>
            <YAxis yAxisId="rate" unit="%" domain={[0,"auto"]} tick={{ fill:"#6B6B6B", fontSize:11, fontFamily:"JetBrains Mono, monospace" }}/>
            <YAxis yAxisId="count" orientation="right" tick={{ fill:"#6B6B6B", fontSize:11, fontFamily:"JetBrains Mono, monospace" }}/>
            <Tooltip content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]?.payload;
              return <div style={{ background:"#FFFFFF", border:"1px solid var(--color-border)", borderRadius:"var(--radius-md)", padding:"10px 14px", fontSize:"var(--text-xs)" }}>
                <div style={{ fontWeight:600, marginBottom:4 }}>{d?.month}</div>
                <div style={{ color:ACCENT }}>SIF Rate: <strong>{d?.sif_rate_pct}%</strong></div>
                <div style={{ color:"var(--color-text-muted)" }}>{d?.sif_count} SIF / {d?.total_reports} total</div>
              </div>;
            }}/>
            <Legend wrapperStyle={{ fontSize:"var(--text-xs)" }}/>
            <Line yAxisId="rate" type="monotone" dataKey="sif_rate_pct" name="SIF Rate (%)" stroke={ACCENT} strokeWidth={1.5} dot={{ r:2, fill:ACCENT }} activeDot={{ r:3 }}/>
            <Line yAxisId="count" type="monotone" dataKey="total_reports" name="Total Reports" stroke="#111111" strokeWidth={1} strokeDasharray="4 3" dot={false}/>
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* PANEL 5: Per-Site Recall Audit */}
      <div className="card">
        <div style={{ marginBottom:16 }}>
          <div style={{ fontWeight:600, fontSize:"var(--text-sm)" }}>Per-Site Model Recall Audit</div>
          <div style={{ fontSize:"var(--text-xs)", color:"var(--color-text-muted)", marginTop:4 }}>
            Sites below average recall are flagged. Avg proxy recall: <strong style={{ fontFamily:"var(--font-mono)" }}>{recall?.average_proxy_recall != null ? `${(recall.average_proxy_recall*100).toFixed(1)}%` : "—"}</strong>
          </div>
        </div>
        <div style={{ overflow:"hidden" }}>
          <table className="data-table">
            <thead><tr><th>Site</th><th className="num">Total</th><th className="num">Hi-Po</th><th className="num">SIF Predicted</th><th className="num">Proxy Recall</th><th>Status</th></tr></thead>
            <tbody>
              {recall?.sites.map((s) => (
                <tr key={s.site}>
                  <td style={{ fontSize:"var(--text-sm)", fontWeight:500 }}>{s.site ?? "—"}</td>
                  <td className="num">{s.total_reports}</td>
                  <td className="num">{s.hi_po_count}</td>
                  <td className="num">{s.sif_predicted}</td>
                  <td className="num">{s.proxy_recall != null ? `${(s.proxy_recall*100).toFixed(1)}%` : "—"}</td>
                  <td>{s.below_average ? <span className="badge badge--high"><AlertTriangle size={10}/> Below Avg</span> : <span className="badge badge--clear">On Target</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
