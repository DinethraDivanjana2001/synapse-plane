import type { AgentManifest } from "../api/types";

const NOT_IMPLEMENTED = new Set(["catalogue_only", "PLANNED", "REGISTERED_NOT_CONFIGURED"]);

function colorFor(agent: AgentManifest): string {
  if (!agent.enabled || agent.health_status === "unavailable" || NOT_IMPLEMENTED.has(agent.implementation_status)) {
    return "var(--text-muted)";
  }
  if (agent.health_status === "degraded") return "var(--amber)";
  return "var(--green)";
}

export function AgentStatusDot({ agent }: { agent: AgentManifest }) {
  return (
    <div className="agent-dot-row">
      <span className="dot" style={{ background: colorFor(agent) }} />
      <span>{agent.name}</span>
    </div>
  );
}
