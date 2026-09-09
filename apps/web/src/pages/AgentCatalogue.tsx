import { useEffect, useState } from "react";
import { listAgents } from "../api/client";
import type { AgentManifest } from "../api/types";

const IMPL_COLOR: Record<string, string> = {
  FULLY_IMPLEMENTED: "var(--green)",
  LIVE_EXTERNAL: "var(--green)",
  CONFIGURED: "var(--green)",
  mock: "var(--blue)",
  REGISTERED_NOT_CONFIGURED: "var(--text-muted)",
  catalogue_only: "var(--text-muted)",
  PLANNED: "var(--text-muted)",
  disabled: "var(--red)",
};

const IMPL_LABEL: Record<string, string> = {
  catalogue_only: "Not implemented — planned for future",
  PLANNED: "Not implemented — planned for future",
  REGISTERED_NOT_CONFIGURED: "Registered, not configured",
};

export function AgentCatalogue() {
  const [agents, setAgents] = useState<AgentManifest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [explainerOpen, setExplainerOpen] = useState(true);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) return <p style={{ color: "var(--red)" }}>{error}</p>;
  if (!agents) return <p className="muted">Loading...</p>;

  return (
    <div>
      <div className="info-box">
        <div className="spread" style={{ cursor: "pointer" }} onClick={() => setExplainerOpen((v) => !v)}>
          <strong>How agent selection works</strong>
          <span className="muted">{explainerOpen ? "hide" : "show"}</span>
        </div>
        {explainerOpen && (
          <div style={{ marginTop: 12 }}>
            <p className="muted" style={{ marginBottom: 8 }}>
              A task declares the capability it needs (e.g. <code>web.discover_places</code>).
              The capability router scores every eligible agent that advertises that
              capability, and the highest-scoring one is selected. If the selected agent
              fails with a transient error, the router excludes it and re-selects among
              the remaining eligible agents (agent-level fallback).
            </p>
            <div className="formula">
              score = 0.35&times;capability_fit + 0.25&times;reliability + 0.15&times;health +
              0.10&times;(1 - latency/max) + 0.10&times;(1 - cost/max) + 0.05&times;preference
            </div>
          </div>
        )}
      </div>

      <div className="agent-grid">
        {agents.map((a) => {
          const color = IMPL_COLOR[a.implementation_status] ?? "var(--text-muted)";
          return (
            <div className="card" key={a.agent_id}>
              <div className="spread">
                <strong>{a.name}</strong>
                <span className={`ownership-pill ${a.ownership}`}>{a.ownership}</span>
              </div>
              <div className="muted">
                {a.agent_id} &middot; v{a.version}
              </div>
              <p style={{ fontSize: 13 }}>{a.description}</p>
              <div>
                {a.capabilities.map((c) => (
                  <span className="tag" key={c}>
                    {c}
                  </span>
                ))}
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <span className="badge" style={{ background: `color-mix(in srgb, ${color} 16%, transparent)`, color }}>
                  {IMPL_LABEL[a.implementation_status] ?? a.implementation_status}
                </span>
              </div>
              <div className="pref-grid" style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 10, fontSize: 13 }}>
                <div>
                  <div className="muted">Trust</div>
                  {a.trust_status}
                </div>
                <div>
                  <div className="muted">Health</div>
                  {a.health_status}
                </div>
                <div>
                  <div className="muted">Latency</div>
                  {a.estimated_latency_ms} ms
                </div>
                <div>
                  <div className="muted">Cost units</div>
                  {a.estimated_cost_units}
                </div>
              </div>
              <div style={{ marginTop: 10 }}>
                <div className="muted" style={{ marginBottom: 4 }}>
                  Reliability {(a.reliability_score * 100).toFixed(0)}%
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${a.reliability_score * 100}%` }} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
