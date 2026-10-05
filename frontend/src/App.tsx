import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import {
  ShieldAlert, LayoutDashboard, ClipboardList,
  BarChart3, BookOpen, FlaskConical, Upload, Activity
} from "lucide-react";

import TriageDashboard    from "./views/TriageDashboard";
import ReportDetail       from "./views/ReportDetail";
import ManualReviewQueue  from "./views/ManualReviewQueue";
import LeadershipDashboard from "./views/LeadershipDashboard";
import AuditLog           from "./views/AuditLog";
import ActiveLearning     from "./views/ActiveLearning";
import IngestView         from "./views/IngestView";
import "./index.css";

function Sidebar() {
  const loc = useLocation();

  return (
    <nav className="app-sidebar" aria-label="Primary">
      <div style={{ padding: "0 24px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ShieldAlert size={22} color="#000000" aria-hidden="true" />
          <div>
            <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", color: "#000000" }}>
              SIH165
            </div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
              SIF Precursor Engine
            </div>
          </div>
        </div>
      </div>

      <div className="divider" style={{ margin: "0 0 8px" }} />

      <div className="nav-section-label">HSE Officer</div>

      <NavLink to="/"
        className={({ isActive }) => `nav-item ${isActive && loc.pathname === "/" ? "nav-item--active" : ""}`}>
        <LayoutDashboard size={16} aria-hidden="true" />
        Triage Dashboard
      </NavLink>

      <NavLink to="/manual-review"
        className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
        <ClipboardList size={16} aria-hidden="true" />
        Manual Review Queue
      </NavLink>

      <NavLink to="/ingest"
        className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
        <Upload size={16} aria-hidden="true" />
        Upload Reports
      </NavLink>

      <div className="divider" style={{ margin: "8px 0" }} />

      <div className="nav-section-label">Leadership</div>

      <NavLink to="/leadership"
        className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
        <BarChart3 size={16} aria-hidden="true" />
        Analytics Dashboard
      </NavLink>

      <div className="divider" style={{ margin: "8px 0" }} />

      <div className="nav-section-label">System</div>

      <NavLink to="/audit"
        className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
        <BookOpen size={16} aria-hidden="true" />
        Audit Log
      </NavLink>

      <NavLink to="/active-learning"
        className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
        <FlaskConical size={16} aria-hidden="true" />
        Active Learning
      </NavLink>

      <div style={{ position: "absolute", bottom: 24, left: 24, right: 24 }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px",
          background: "#FFFFFF",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--color-border)",
        }}>
          <Activity size={12} color="#111111" aria-hidden="true" />
          <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            Engine v0.1 · live
          </span>
        </div>
      </div>
    </nav>
  );
}

function Header() {
  return (
    <header className="app-header">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <ShieldAlert size={18} color="#000000" aria-hidden="true" />
        <span style={{ fontWeight: 600, fontSize: "var(--text-sm)", color: "#000000" }}>
          SIF Precursor Detection Engine
        </span>
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
          Oil India Ltd · OISD / IOGP Life-Saving Rules
        </span>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout" style={{ position: "relative" }}>
        <Header />
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/"                element={<TriageDashboard />} />
            <Route path="/reports/:id"     element={<ReportDetail />} />
            <Route path="/manual-review"   element={<ManualReviewQueue />} />
            <Route path="/leadership"      element={<LeadershipDashboard />} />
            <Route path="/audit"           element={<AuditLog />} />
            <Route path="/active-learning" element={<ActiveLearning />} />
            <Route path="/ingest"          element={<IngestView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
