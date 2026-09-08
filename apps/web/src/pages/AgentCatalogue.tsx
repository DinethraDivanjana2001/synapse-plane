import { useEffect, useState } from "react";
import { listAgents } from "../api/client";
import type { AgentManifest } from "../api/types";

const IMPL_COLOR: Record<string, string> = {
  FULLY_IMPLEMENTED: "var(--green)",
  LIVE_EXTERNAL: "var(--green)",
  CONFIGURED: "var(--green)",
  mock: "var(--blue)",
  REGISTERED_NOT_CONFIGURED: "var(--gray)",
  catalogue_only: "var(--gray)",
  PLANNED: "var(--gray)",
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

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) return <p style={{ color: "var(--red)" }}>{error}</p>;
  if (!agents) return <p className="muted">Loading…</p>;

  return (
    <div className="agent-grid">
      {agents.map((a) => {
        const color = IMPL_COLOR[a.implementation_status] ?? "var(--gray)";
        return (
          <div className="card" key={a.agent_id}>
            <div className="spread">
              <strong>{a.name}</strong>
              <span
                className="badge"
                style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
              >
                {IMPL_LABEL[a.implementation_status] ?? a.implementation_status}
              </span>
            </div>
            <div className="muted">
              {a.agent_id} · v{a.version}
            </div>
            <p style={{ fontSize: 13 }}>{a.description}</p>
            <div>
              {a.capabilities.map((c) => (
                <span className="tag" key={c}>
                  {c}
                </span>
              ))}
            </div>
            <div className="pref-grid" style={{ marginTop: 10 }}>
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
                <div
                  className="progress-bar-fill"
                  style={{ width: `${a.reliability_score * 100}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
