import type { EventSummary } from "../api/types";

type Mark = "tick" | "cross" | "dot";

function markFor(eventType: string): Mark {
  if (
    eventType.includes("failed") ||
    eventType.includes("rejected") ||
    eventType === "approval.rejected"
  ) {
    return "cross";
  }
  if (
    eventType.includes("succeeded") ||
    eventType.includes("completed") ||
    eventType.includes("validated") ||
    eventType.includes("approved")
  ) {
    return "tick";
  }
  return "dot";
}

// Semantic-only: green tick = succeeded, red cross = failed, grey dot =
// everything in between (started, selected, requested). No category hues —
// what matters on a timeline is whether each step passed or failed.
const MARK_STYLE: Record<Mark, { symbol: string; color: string }> = {
  tick: { symbol: "✓", color: "var(--green)" },
  cross: { symbol: "✕", color: "var(--red)" },
  dot: { symbol: "", color: "var(--text-muted)" },
};

export function EventTimeline({ events }: { events: EventSummary[] }) {
  if (events.length === 0) {
    return <p className="muted">No events yet.</p>;
  }
  return (
    <div className="timeline">
      {events.map((e, i) => {
        const mark = markFor(e.event_type);
        const style = MARK_STYLE[mark];
        return (
          <div className="timeline-row" key={i}>
            <span className="timeline-time">{new Date(e.occurred_at).toLocaleTimeString()}</span>
            <span
              className={`timeline-mark${mark === "dot" ? " timeline-mark-dot" : ""}`}
              style={{ background: mark === "dot" ? "transparent" : style.color, color: style.color, borderColor: style.color }}
            >
              {mark === "dot" ? "" : style.symbol}
            </span>
            <span className="timeline-label">
              {e.event_type}
              {e.task_id && <span className="muted"> &middot; {e.task_id}</span>}
              {e.agent_id && <span className="muted"> &middot; {e.agent_id}</span>}
              {typeof e.payload?.error_code === "string" && (
                <span className="muted"> &middot; {e.payload.error_code}</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
