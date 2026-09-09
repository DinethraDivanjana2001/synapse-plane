import { useEffect, useState } from "react";
import { listAgents } from "../api/client";
import type { AgentManifest } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  FULLY_IMPLEMENTED: "var(--green)",
  LIVE_EXTERNAL: "var(--green)",
  CONFIGURED: "var(--green)",
  mock: "var(--blue)",
  REGISTERED_NOT_CONFIGURED: "var(--text-muted)",
  catalogue_only: "var(--text-muted)",
  PLANNED: "var(--text-muted)",
  disabled: "var(--red)",
};

export function AgentCataloguePanel() {
  const [agents, setAgents] = useState<AgentManifest[]>([]);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  return (
    <div>
      <div className="section-title">Agent catalogue</div>
      {agents.map((a) => {
        const color = STATUS_COLOR[a.implementation_status] ?? "var(--text-muted)";
        return (
          <div className="card" key={a.agent_id}>
            <div className="spread">
              <strong style={{ fontSize: 13 }}>{a.name}</strong>
              <span className={`ownership-pill ${a.ownership}`}>{a.ownership}</span>
            </div>
            <div style={{ marginTop: 6 }}>
              {a.capabilities.slice(0, 3).map((c) => (
                <span className="tag" key={c}>
                  {c}
                </span>
              ))}
            </div>
            <div style={{ marginTop: 8 }}>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${a.reliability_score * 100}%`, background: color }}
                />
              </div>
            </div>
            <div className="muted" style={{ marginTop: 6, fontSize: 11 }}>
              {a.estimated_latency_ms}ms &middot; {a.implementation_status}
            </div>
          </div>
        );
      })}
      <div className="section-title" style={{ marginTop: 20 }}>
        Legend
      </div>
      <div className="muted" style={{ fontSize: 12, lineHeight: 1.8 }}>
        <div><span className="status-dot" style={{ color: "var(--text-muted)" }} /> Pending</div>
        <div><span className="status-dot pulse" style={{ color: "var(--blue)" }} /> Running</div>
        <div><span className="status-dot" style={{ color: "var(--green)" }} /> Succeeded</div>
        <div><span className="status-dot" style={{ color: "var(--red)" }} /> Failed</div>
        <div><span className="status-dot" style={{ color: "var(--amber)" }} /> Waiting approval</div>
      </div>
    </div>
  );
}
