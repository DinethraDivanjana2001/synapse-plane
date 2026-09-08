// Colored status pill — one shared source of truth for status -> color across the app.

const COLORS: Record<string, string> = {
  COMPLETED: "#3fb950",
  SUCCEEDED: "#3fb950",
  APPROVED: "#3fb950",
  FAILED: "#f85149",
  REJECTED: "#f85149",
  CANCELLED: "#f85149",
  WAITING_FOR_APPROVAL: "#d29922",
  RUNNING: "#58a6ff",
  RESUMING: "#58a6ff",
  READY: "#58a6ff",
  RETRYING: "#58a6ff",
  PENDING: "#6e7681",
  BLOCKED: "#6e7681",
  SKIPPED: "#6e7681",
  PLANNING: "#6e7681",
  PLAN_VALIDATION: "#6e7681",
  CONTEXT_RETRIEVAL: "#6e7681",
  RECEIVED: "#6e7681",
  REPLANNING: "#6e7681",
};

export function StatusBadge({ status }: { status: string }) {
  const color = COLORS[status] ?? "#6e7681";
  return (
    <span
      className="badge"
      style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
