// Colored status pill — single source of truth for status -> color across the app.

const COLORS: Record<string, string> = {
  COMPLETED: "var(--green)",
  SUCCEEDED: "var(--green)",
  APPROVED: "var(--green)",
  FAILED: "var(--red)",
  REJECTED: "var(--red)",
  CANCELLED: "var(--red)",
  WAITING_FOR_APPROVAL: "var(--amber)",
  RUNNING: "var(--blue)",
  RESUMING: "var(--blue)",
  READY: "var(--blue)",
  RETRYING: "var(--blue)",
  PENDING: "var(--text-muted)",
  BLOCKED: "var(--text-muted)",
  SKIPPED: "var(--text-muted)",
  PLANNING: "var(--text-muted)",
  PLAN_VALIDATION: "var(--text-muted)",
  CONTEXT_RETRIEVAL: "var(--text-muted)",
  RECEIVED: "var(--text-muted)",
  REPLANNING: "var(--text-muted)",
};

const PULSING = new Set(["RUNNING", "RESUMING", "RETRYING"]);

export function StatusBadge({ status }: { status: string }) {
  const color = COLORS[status] ?? "var(--text-muted)";
  const pulsing = PULSING.has(status);
  return (
    <span className="badge" style={{ background: `color-mix(in srgb, ${color} 16%, transparent)`, color }}>
      <span className={`status-dot${pulsing ? " pulse" : ""}`} />
      {status.replace(/_/g, " ")}
    </span>
  );
}
