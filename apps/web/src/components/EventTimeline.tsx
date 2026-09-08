import type { EventSummary } from "../api/types";

const ICONS: Record<string, string> = {
  "execution.created": "→",
  "planning.started": "○",
  "plan.proposed": "○",
  "plan.validated": "✓",
  "plan.rejected": "✗",
  "approval.approved": "✓",
  "approval.rejected": "✗",
  "execution.completed": "✓",
  "execution.failed": "✗",
  "execution.resumed": "→",
};

export function EventTimeline({ events }: { events: EventSummary[] }) {
  if (events.length === 0) {
    return <p className="muted">No events yet.</p>;
  }
  return (
    <div>
      {events.map((e, i) => (
        <div className="timeline-item" key={i}>
          <span className="timeline-time">
            {new Date(e.occurred_at).toLocaleTimeString()}
          </span>
          <span>{ICONS[e.event_type] ?? "•"}</span>
          <span>
            {e.event_type}
            {e.task_id && <span className="muted"> · {e.task_id}</span>}
            {e.agent_id && <span className="muted"> · {e.agent_id}</span>}
            {typeof e.payload?.error_code === "string" && (
              <span className="muted"> · {e.payload.error_code}</span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
