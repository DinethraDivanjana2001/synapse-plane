import { NavLink, Route, Routes } from "react-router-dom";
import { IntentSubmission } from "./pages/IntentSubmission";
import { ExecutionDetail } from "./pages/ExecutionDetail";
import { AgentCatalogue } from "./pages/AgentCatalogue";

export function App() {
  return (
    <div className="app-shell">
      <nav className="nav">
        <span className="nav-brand">SynapsePlane</span>
        <NavLink to="/" end>
          New Intent
        </NavLink>
        <NavLink to="/agents">Agents</NavLink>
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<IntentSubmission />} />
          <Route path="/executions/:id" element={<ExecutionDetail />} />
          <Route path="/agents" element={<AgentCatalogue />} />
        </Routes>
      </main>
    </div>
  );
}
