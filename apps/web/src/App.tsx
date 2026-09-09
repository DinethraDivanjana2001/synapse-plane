import type { ReactNode } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { AgentCataloguePanel } from "./components/AgentCataloguePanel";
import { Sidebar } from "./components/Sidebar";
import { IntentSubmission } from "./pages/IntentSubmission";
import { ExecutionDetail } from "./pages/ExecutionDetail";
import { AgentCatalogue } from "./pages/AgentCatalogue";
import { ExecutionHistory } from "./pages/ExecutionHistory";

function DashboardPage({ children }: { children: ReactNode }) {
  return (
    <div className="dashboard">
      <div className="dash-col left">
        <Sidebar />
      </div>
      <div className="dash-col center">{children}</div>
      <div className="dash-col right">
        <AgentCataloguePanel />
      </div>
    </div>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <nav className="topnav">
        <span className="brand">
          <span className="brand-mark" />
          SynapsePlane
        </span>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/agents">Agents</NavLink>
        <NavLink to="/history">History</NavLink>
      </nav>
      <Routes>
        <Route
          path="/"
          element={
            <DashboardPage>
              <IntentSubmission />
            </DashboardPage>
          }
        />
        <Route
          path="/executions/:id"
          element={
            <DashboardPage>
              <ExecutionDetail />
            </DashboardPage>
          }
        />
        <Route
          path="/agents"
          element={
            <div className="simple-page">
              <AgentCatalogue />
            </div>
          }
        />
        <Route
          path="/history"
          element={
            <div className="simple-page">
              <ExecutionHistory />
            </div>
          }
        />
      </Routes>
    </div>
  );
}
